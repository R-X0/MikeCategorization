import io
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from PyPDF2 import PdfReader, PdfWriter  # Install via pip install PyPDF2

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API key loaded from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Step 1: Raw extraction prompt remains unchanged.
RAW_PROMPT = "List every single thing exactly as it appears on the document, each column and row, in full"

# Helper function to load a schema file
def load_schema(schema_id):
    """
    Load the specified JSON schema from file
    
    Parameters:
    schema_id (str): Identifier for the schema to load
    
    Returns:
    dict: The loaded schema or None if not found
    """
    schema_mapping = {
        "1040": "1040.json",
        "2848": "2848.json",
        "8821": "8821.json",
        "941": "941.json",
        "payroll": "payroll.json",
        "generic": None  # Generic schema doesn't need a specific file
    }
    
    if schema_id not in schema_mapping:
        return None
        
    filename = schema_mapping.get(schema_id)
    if filename is None:
        return None
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(script_dir)
    # Construct absolute path to the schema file
    schema_path = os.path.join(project_root, filename)
    
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading schema {schema_id} from {schema_path}: {e}")
        return None

# Function to generate a schema-specific prompt
def generate_schema_prompt(schema_id, extracted_text):
    """
    Generate a prompt for extraction based on the selected schema
    
    Parameters:
    schema_id (str): Identifier for the schema to use
    extracted_text (str): Raw text extracted from the document
    
    Returns:
    str: The prompt to use for extraction
    """
    # Load the requested schema
    schema = load_schema(schema_id)
    
    # Generic document schema for fallback
    GENERIC_SCHEMA = """
    {
      "documentMetadata": {
        "documentID": "Unique identifier for the document",
        "documentType": "Type/category (e.g., Invoice, Receipt, BankStatement, MerchantStatement, CreditMemo, PurchaseOrder, etc.)",
        "documentNumber": "Official reference number from the document",
        "documentDate": "YYYY-MM-DD (date issued)",
        "uploadDate": "YYYY-MM-DDTHH:MM:SSZ (date/time uploaded)",
        "source": {
          "name": "Name of the issuer (vendor, bank, customer, etc.)",
          "type": "Category (Vendor, Customer, Bank, etc.)",
          "contact": {
            "address": "Full address if available",
            "phone": "Contact phone number",
            "email": "Contact email address"
          }
        },
        "fileInfo": {
          "fileName": "Original file name",
          "fileType": "Format (e.g., PDF, JPEG)",
          "pageCount": "Number of pages in the document",
          "OCRProcessed": "Boolean flag indicating whether OCR has been applied"
        }
      },
      "financialData": {
        "currency": "Currency code (e.g., USD, EUR)",
        "subtotal": "Amount before any discounts or additional fees",
        "taxAmount": "Total tax applied (if any) – can be zero or omitted if not applicable",
        "discount": "Any discounts or adjustments applied",
        "totalAmount": "Final total monetary value on the document",
        "paymentStatus": "Status (e.g., Paid, Unpaid, Pending)",
        "paymentTerms": "Terms such as 'Net 30'",
        "dueDate": "YYYY-MM-DD (if a due date is specified)"
      },
      "lineItems": [
        {
          "itemID": "Unique identifier for the line item or transaction",
          "description": "Short description of the product, service, or transaction",
          "quantity": "Number of units or hours (if invoicing for services)",
          "unit": "Unit of measure (e.g., hours, pieces, kg, etc.)",
          "unitPrice": "Price per unit or hourly rate",
          "totalPrice": "Calculated total for the line item",
          "tax": "Tax amount applicable to this line item (if any)",
          "transactionType": "For bank/merchant statements (e.g., Debit, Credit)",
          "balance": "Running balance after the transaction (if applicable)",
          "category": "Optional field to classify the line item (e.g., Service, Product)"
        }
      ],
      "partyInformation": {
        "vendor": {
          "name": "Vendor/Supplier name",
          "address": "Vendor address",
          "contact": "Vendor contact details (phone/email)",
          "taxID": "Tax identifier if available (optional)"
        },
        "customer": {
          "name": "Customer name",
          "address": "Customer address",
          "contact": "Customer contact details",
          "customerID": "Internal customer identifier"
        },
        "bankDetails": {
          "bankName": "Name of the bank",
          "accountNumber": "Bank account number",
          "routingNumber": "Routing or sort code"
        }
      },
      "paymentInformation": {
        "paymentMethod": "Method (e.g., Cash, Credit Card, EFT, Direct Deposit)",
        "transactionID": "Identifier for electronically processed payments",
        "paidDate": "YYYY-MM-DD (date when payment was made)",
        "bankDetails": {
          "bankName": "If relevant, bank name for the transaction",
          "accountNumber": "Account number associated with payment",
          "routingNumber": "Routing number for bank transfers"
        }
      },
      "fixedAssetData": {
        "assetID": "Unique asset identifier",
        "description": "Description of the fixed asset or inventory item",
        "acquisitionDate": "YYYY-MM-DD (date of purchase/acquisition)",
        "purchasePrice": "Cost of acquiring the asset",
        "depreciationMethod": "Method used (e.g., Straight-line, Declining Balance)",
        "currentValue": "Current book value of the asset",
        "location": "Physical location of the asset (if applicable)"
      },
      "additionalData": {
        "notes": "Any annotations or internal comments",
        "attachments": [
          "Link(s) or reference(s) to supplementary files, if applicable"
        ],
        "referenceNumbers": [
          "Other relevant reference numbers (e.g., purchase order numbers, shipping numbers)"
        ],
        "auditTrail": [
          {
            "action": "Description of the processing step (e.g., 'uploaded', 'OCR extracted')",
            "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
            "user": "User or system that performed the action"
          }
        ]
      }
    }
    """
    
    # Base prompt template
    prompt_template = """
    Format the following extracted text into a JSON object that strictly follows the schema below. Ensure that the output is valid JSON with no additional commentary.
    
    Schema:
    {schema}
    
    Extracted Text:
    {extracted_text}
    """
    
    # If we have a specific schema, use it; otherwise, use the generic one
    if schema:
        schema_json = json.dumps(schema, indent=2)
        
        # For tax forms, add some specific instructions
        if schema_id in ["1040", "2848", "8821", "941"]:
            schema_prompt = f"""
            Format the following extracted text from an IRS tax form into a JSON object that strictly follows the schema below.
            This is specifically for IRS Form {schema_id}. Pay special attention to the form fields, numbers, checkboxes, and taxpayer information.
            
            Schema:
            {schema_json}
            
            Extracted Text:
            {extracted_text}
            """
        # For payroll data
        elif schema_id == "payroll":
            schema_prompt = f"""
            Format the following extracted text from a payroll document into a JSON object that strictly follows the schema below.
            This is specifically for payroll data. Pay special attention to employee details, earnings, deductions, and tax information.
            
            Schema:
            {schema_json}
            
            Extracted Text:
            {extracted_text}
            """
        else:
            schema_prompt = prompt_template.format(schema=schema_json, extracted_text=extracted_text)
    else:
        # Use the generic schema as fallback
        schema_prompt = prompt_template.format(schema=GENERIC_SCHEMA, extracted_text=extracted_text)
    
    return schema_prompt

def detect_document_type(json_data):
    """
    Detect the document type from the JSON data to apply appropriate verification rules.
    
    Parameters:
    json_data (dict): The structured JSON data extracted from the document
    
    Returns:
    str: Document type - 'invoice', 'receipt', 'payment_processing', 'bank_statement', or 'other'
    """
    # Get the document type from metadata if available
    doc_type = json_data.get("documentMetadata", {}).get("documentType", "").lower()
    
    # Check for specific document type indicators
    if doc_type in ["merchantstatement", "merchant_statement", "payment_processing_statement", 
                    "processor_statement", "acquirer_statement"]:
        return "payment_processing"
    
    # Check for bank statement indicators
    if doc_type in ["bankstatement", "bank_statement", "account_statement"]:
        return "bank_statement"
    
    # Check for invoice indicators
    if doc_type in ["invoice", "bill"]:
        return "invoice"
    
    # Check for receipt indicators
    if doc_type in ["receipt", "sales_receipt"]:
        return "receipt"
    
    # If no explicit type, analyze the content to determine type
    
    # Check for payment processing statement indicators
    if any(keyword in str(json_data).lower() for keyword in 
           ["interchange", "merchant id", "card summary", "chargebacks", 
            "settlement", "processor", "acquirer", "mastercard", "visa fees"]):
        return "payment_processing"
    
    # Check for card transaction indicators (high volume of transactions)
    line_items = json_data.get("lineItems", [])
    if len(line_items) > 20 and any("card" in str(item).lower() for item in line_items):
        return "payment_processing"
    
    # Check for special fields that indicate payment processing
    if "credits" in str(json_data).lower() and "sales" in str(json_data).lower() and "settlement" in str(json_data).lower():
        return "payment_processing"
    
    # Check for indicators of a bank statement
    if any(keyword in str(json_data).lower() for keyword in 
           ["account number", "routing number", "beginning balance", "ending balance", 
            "deposits", "withdrawals", "account summary"]):
        return "bank_statement"
    
    # Check for invoice indicators (if not already detected)
    if "invoice" in str(json_data).lower() or "bill to" in str(json_data).lower():
        return "invoice"
    
    # Default to invoice verification rules if we can't determine
    return "invoice"

async def verify_extraction(json_data):
    """
    Verify the mathematical accuracy of the extracted data by focusing on 
    calculation discrepancies rather than trivial formatting differences.
    
    Parameters:
    json_data (dict): The structured JSON data extracted from the document
    
    Returns:
    dict: Original JSON with added extraction verification results
    """
    try:
        # First, detect document type to apply appropriate verification rules
        document_type = detect_document_type(json_data)
        
        # Update the prompt to focus on mathematical verification
        verification_prompt = f"""
        Analyze this financial document data to verify MATHEMATICAL ACCURACY only.
        
        DOCUMENT TYPE: {document_type.upper()}
        
        CRITICAL INSTRUCTIONS:
        1. IGNORE all formatting differences (e.g., "90" vs 90, spaces, character encoding)
        2. IGNORE data type differences (string vs number) - only care about the numeric value
        3. FOCUS ONLY on verification of financial calculations:
           - For invoices: Check if quantity × price = line totals
           - For all documents: Verify line items sum up to stated subtotals or totals
           - Check if subtotal + tax = total amount (where applicable)
           - For statements: Verify opening balance + transactions = closing balance
         
        4. Mathematical rules that should be checked:
           - Line items: quantity × unit price = line total
           - Document totals: sum of line totals = subtotal
           - Tax calculation: subtotal × tax rate = tax amount
           - Final total: subtotal + tax + fees - discounts = total amount
        
        Financial Data:
        {json.dumps(json_data, indent=2)}
        
        Return your verification as JSON with this strict structure:
        {{
          "extractionVerified": Boolean (true if calculations are accurate, false if calculation errors exist),
          "discrepancies": [
            {{
              "type": "String (Line Total, Subtotal, Tax Calculation, etc.)",
              "location": "String (reference to where in the document this calculation occurs)",
              "expectedValue": "Number (what the calculation should produce)",
              "extractedValue": "Number (what was extracted in the document)",
              "likelyCorrectValue": "Number (the most likely correct value)",
              "formula": "String (the formula used for this calculation)",
              "confidence": "String (High, Medium, Low)"
            }}
          ],
          "summary": "String (brief explanation of calculation verification results)"
        }}
        
        ONLY include discrepancies that are TRUE CALCULATION ERRORS where numbers don't add up correctly.
        DO NOT flag differences in formatting, string representations, or character encoding.
        """
        
        # Make the API call to Gemini
        verification_response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[verification_prompt],
            config={
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
        )
        
        # Extract verification results
        try:
            verification_results = json.loads(verification_response.text)
            
            # Keep only significant calculation discrepancies
            if "discrepancies" in verification_results and len(verification_results["discrepancies"]) > 0:
                # Filter out any discrepancies where the numeric values are actually the same
                significant_issues = []
                for d in verification_results["discrepancies"]:
                    # Try to convert both values to floats for comparison
                    try:
                        expected = float(str(d.get("expectedValue", "0")).replace(",", ""))
                        actual = float(str(d.get("extractedValue", "0")).replace(",", ""))
                        
                        # Only keep discrepancies where values are numerically different
                        if abs(expected - actual) > 0.01:  # Allow for small rounding differences
                            significant_issues.append(d)
                    except:
                        # If we can't convert to float, keep the discrepancy
                        significant_issues.append(d)
                
                verification_results["discrepancies"] = significant_issues
                
                # Update the verification status based on filtered discrepancies
                verification_results["extractionVerified"] = len(significant_issues) == 0
                
                # Update summary if needed
                if len(significant_issues) == 0 and not verification_results["extractionVerified"]:
                    verification_results["summary"] = "No significant calculation discrepancies found after filtering."
                    verification_results["extractionVerified"] = True
            
            # Add verification results to the original JSON
            json_data["extractionVerification"] = verification_results
            
        except json.JSONDecodeError as e:
            # If the response isn't valid JSON, create a simple error structure
            json_data["extractionVerification"] = {
                "extractionVerified": False,
                "discrepancies": [],
                "summary": f"Error parsing verification results: {str(e)}",
                "rawResponse": verification_response.text
            }
        
        return json_data
        
    except Exception as e:
        # If verification fails, add error information to the JSON
        json_data["extractionVerification"] = {
            "extractionVerified": False,
            "discrepancies": [],
            "summary": f"Error during extraction verification: {str(e)}"
        }
        return json_data

async def process_page(page, schema="generic"):
    # Write the individual page to a BytesIO stream.
    pdf_writer = PdfWriter()
    pdf_writer.add_page(page)
    page_stream = io.BytesIO()
    pdf_writer.write(page_stream)
    page_stream.seek(0)

    # Create a Gemini Part from the page bytes.
    file_part = types.Part.from_bytes(
        data=page_stream.getvalue(),
        mime_type="application/pdf"
    )

    # Step 1: Extract raw text from the page.
    raw_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash-exp",
        contents=[RAW_PROMPT, file_part],
        config={
            "max_output_tokens": 40000,
            "response_mime_type": "text/plain"
        }
    )
    raw_text = raw_response.text

    # Step 2: Convert the raw text into structured JSON using the schema-specific prompt
    json_prompt = generate_schema_prompt(schema, raw_text)
    json_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash",
        contents=[json_prompt],
        config={
            "max_output_tokens": 40000,
            "response_mime_type": "application/json"
        }
    )
    
    # Return the JSON response to be merged later
    return json_response.text

def deep_merge(base, addition):
    """
    Recursively merge two dictionaries.
    - Lists are concatenated
    - Dictionaries are merged recursively
    - For other values, non-null values are preferred over null values
    - For other cases where both values are non-null, the first occurrence (base) is kept
    
    Parameters:
    base (dict): The base dictionary to merge into
    addition (dict): The dictionary to merge from
    
    Returns:
    dict: The merged dictionary
    """
    # Create a copy to avoid modifying the original
    result = base.copy()
    
    for key, value in addition.items():
        # If key not in result, just add it
        if key not in result:
            result[key] = value
        else:
            # If both are lists, extend the base list
            if isinstance(result[key], list) and isinstance(value, list):
                result[key].extend(value)
            
            # If both are dictionaries, merge them recursively
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            
            # For boolean values, use logical OR (True if either is True)
            elif isinstance(result[key], bool) and isinstance(value, bool):
                result[key] = result[key] or value
            
            # For other values, prefer non-null values over null/empty ones
            elif result[key] is None and value is not None:
                result[key] = value
            # If both values exist and neither is None, keep the base value (first page)
    
    return result

def merge_page_results(page_results):
    """
    Merge JSON results from multiple pages.
    For document-level fields, we assume they are the same across pages and only keep the first occurrence.
    For list fields, we concatenate them, regardless of where they appear in the JSON structure.
    """
    merged = None
    
    # Process each page
    for result in page_results:
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            continue  # Optionally log or handle the error
            
        if merged is None:
            merged = data
        else:
            # Use deep merge to recursively combine the data
            merged = deep_merge(merged, data)
    
    # Remove any extractionVerification fields - we'll perform a new verification on the complete document
    if merged and "extractionVerification" in merged:
        del merged["extractionVerification"]
            
    return merged

@app.post("/process-pdf")
async def process_file(file: UploadFile = File(...), schema: str = Form("generic")):
    file_content = await file.read()
    
    try:
        if file.content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(file_content))
            # Process each page concurrently using the per-page processing function.
            tasks = [process_page(page, schema) for page in pdf_reader.pages]
            page_results = await asyncio.gather(*tasks)
            
            # Merge the JSON results from each page.
            merged_result = merge_page_results(page_results)
            
            # Perform extraction verification on the complete document
            final_result = await verify_extraction(merged_result)
            
            combined_response_text = json.dumps(final_result, indent=2)
        else:
            # For non-PDF files, process with schema selection
            file_part = types.Part.from_bytes(
                data=file_content,
                mime_type=file.content_type
            )
            raw_response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash-exp",
                contents=[RAW_PROMPT, file_part],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "text/plain"
                }
            )
            raw_text = raw_response.text
            
            # Use schema-specific prompt template
            json_prompt = generate_schema_prompt(schema, raw_text)
            
            json_response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=[json_prompt],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "application/json"
                }
            )
            
            # For non-PDF files (single page), add extraction verification
            try:
                json_data = json.loads(json_response.text)
                final_json = await verify_extraction(json_data)
                combined_response_text = json.dumps(final_json, indent=2)
            except json.JSONDecodeError:
                combined_response_text = json_response.text

        # Return the merged Gemini response.
        return {"response": combined_response_text.strip()}
    except Exception as e:
        return {"error": "Request failed", "detail": str(e)}

# Define request model for vendor research
class VendorResearchRequest(BaseModel):
    vendor_name: str

@app.post("/research-vendor")
async def research_vendor(request: VendorResearchRequest):
    vendor_name = request.vendor_name
    
    if not vendor_name:
        return {"error": "No vendor name provided"}
    
    try:
        # Create a specific prompt asking for the single most likely entity and detailed info about it
        prompt = f"""
        Research the vendor "{vendor_name}" and identify the SINGLE most likely business or entity that this name refers to. 
        
        IMPORTANT: DO NOT list multiple possible interpretations or multiple businesses.
        Determine the most probable, prominent, or common business that matches this name and ONLY provide information about that ONE business.
        
        For this single most likely business, provide as much detail as possible about:
        - What this company does (main business focus)
        - Their products or services in detail
        - Company size, scale of operations, and market position
        - Company history and important milestones
        - Locations, reach, or distribution
        - Any other relevant details that would be helpful to know
        
        Again, I want information about the single most likely match only, not a list of possibilities.
        """
        
        # Use Google Search as a tool for grounding
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Send the request to Gemini API with search enabled
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"],
                temperature=0.2, # Lower temperature to make response more focused
            )
        )
        
        # Return the response as-is
        return {"response": response.text}
        
    except Exception as e:
        print(f"Error researching vendor: {str(e)}")
        return {"error": f"Error researching vendor: {str(e)}"}

# Define request model for financial categorization
class FinancialCategorizationRequest(BaseModel):
    vendor_info: str
    document_data: dict
    transaction_purpose: str = ""  # Renamed to clarify it's about the transaction, not the vendor

@app.post("/categorize-transaction")
async def categorize_transaction(request: FinancialCategorizationRequest):
    vendor_info = request.vendor_info
    document_data = request.document_data
    transaction_purpose = request.transaction_purpose
    
    if not vendor_info or not document_data:
        return {"error": "Missing required information"}
    
    try:
        # Create a prompt that includes the categorization options and asks Gemini to categorize the transaction
        prompt = f"""
        Based on the information below, please categorize this transaction according to accounting principles.
        
        CRITICAL INSTRUCTION: You must categorize from the perspective of the INVOICE RECIPIENT (the customer being billed), NOT from the vendor's perspective. 
        
        For example:
        - If this is an invoice FROM a vendor TO our business, it should typically be categorized as an Expense, Asset, or Liability
        - If this is a receipt we issued TO a customer FROM our business, it would be categorized as Revenue
        
        This categorization is for the accounting records of the business RECEIVING the invoice/document.
        
        Return a JSON object with the following structure:
        {{
            "companyName": "The name of the company that issued the invoice (the vendor)",
            "description": "A detailed description of what this business does",
            "category": "The most appropriate accounting category from the list below",
            "subcategory": "The most appropriate subcategory",
            "ledgerType": "The ledger entry type",
            "explanation": "A detailed explanation of why this categorization was chosen, including the factors considered and accounting principles applied"
        }}
        
        Here are the available categories, subcategories, and ledger types:
        
        Parent Category | Subcategory | Ledger Entry Type
        ---------------|-------------|------------------
        Revenue | Product Sales | Revenue
        Revenue | Service Revenue | Revenue
        Revenue | Rental Revenue | Revenue
        Revenue | Commission Revenue | Revenue
        Revenue | Subscription Revenue | Revenue
        Revenue | Other Income | Revenue
        Cost of Goods Sold (COGS) | Raw Materials | Expense (COGS)
        Cost of Goods Sold (COGS) | Direct Labor | Expense (COGS)
        Cost of Goods Sold (COGS) | Manufacturing Overhead | Expense (COGS)
        Cost of Goods Sold (COGS) | Freight and Delivery | Expense (COGS)
        Operating Expenses | Salaries and Wages | Expense (Operating)
        Operating Expenses | Rent | Expense (Operating)
        Operating Expenses | Utilities | Expense (Operating)
        Operating Expenses | Office Supplies | Expense (Operating)
        Operating Expenses | Business Software / IT Expenses | Expense (Operating)
        Operating Expenses | HR Expenses | Expense (Operating)
        Operating Expenses | Marketing and Advertising | Expense (Operating)
        Operating Expenses | Travel and Entertainment | Expense (Operating)
        Operating Expenses | Insurance | Expense (Operating)
        Operating Expenses | Repairs and Maintenance | Expense (Operating)
        Operating Expenses | Depreciation | Expense (Operating)
        Administrative Expenses | Professional Fees | Expense (Administrative)
        Administrative Expenses | Office Expenses | Expense (Administrative)
        Administrative Expenses | Postage and Shipping | Expense (Administrative)
        Administrative Expenses | Communication Expense | Expense (Administrative)
        Administrative Expenses | Bank Fees and Charges | Expense (Administrative)
        Financial Expenses | Interest Expense | Expense (Financial)
        Financial Expenses | Loan Fees | Expense (Financial)
        Financial Expenses | Credit Card Fees | Expense (Financial)
        Other Expenses | Miscellaneous | Expense (Other)
        Other Expenses | Donations/Charitable Contributions | Expense (Other)
        Other Expenses | Loss on Disposal of Assets | Expense (Other)
        Assets – Current | Cash and Cash Equivalents | Asset (Current)
        Assets – Current | Accounts Receivable | Asset (Current)
        Assets – Current | Inventory | Asset (Current)
        Assets – Current | Prepaid Expenses | Asset (Current)
        Assets – Current | Short-term Investments | Asset (Current)
        Assets – Fixed / Long-term | Property, Plant, and Equipment | Asset (Fixed)
        Assets – Fixed / Long-term | Furniture and Fixtures | Asset (Fixed)
        Assets – Fixed / Long-term | Vehicles | Asset (Fixed)
        Assets – Fixed / Long-term | Machinery and Equipment | Asset (Fixed)
        Assets – Fixed / Long-term | Computer Equipment | Asset (Fixed)
        Assets – Intangible | Patents | Asset (Intangible)
        Assets – Intangible | Trademarks | Asset (Intangible)
        Assets – Intangible | Copyrights | Asset (Intangible)
        Assets – Intangible | Goodwill | Asset (Intangible)
        Assets – Intangible | Capitalized Software | Asset (Intangible)
        Liabilities – Current | Accounts Payable | Liability (Current)
        Liabilities – Current | Short-term Loans | Liability (Current)
        Liabilities – Current | Accrued Liabilities | Liability (Current)
        Liabilities – Current | Current Portion of Long-term Debt | Liability (Current)
        Liabilities – Long-term | Long-term Loans | Liability (Long-term)
        Liabilities – Long-term | Bonds Payable | Liability (Long-term)
        Liabilities – Long-term | Deferred Tax Liabilities | Liability (Long-term)
        Equity | Common Stock | Equity
        Equity | Retained Earnings | Equity
        Equity | Additional Paid-in Capital | Equity
        Equity | Dividends/Distributions | Equity
        Adjusting / Journal Entries | Accruals/Deferrals/Depreciation Adjustments | Adjustment
        
        Vendor Information (the seller/company that sent the invoice):
        {vendor_info}
        
        Document Data:
        {json.dumps(document_data, indent=2)}
        
        Transaction Purpose (what the invoice is for):
        {transaction_purpose}
        
        REMEMBER: Categorize from the perspective of the business RECEIVING this invoice - the customer being billed, NOT from the perspective of the vendor who issued it.
        
        In the explanation field, be thorough about why this specific category, subcategory, and ledger type was chosen. 
        Consider the nature of the transaction, the items or services involved, accounting best practices, and how this 
        classification aligns with standard chart of accounts structures.
        """
        
        # Send the request to Gemini API
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
        )
        
        # Return the response
        try:
            # Try to parse the response as JSON
            categorization_json = json.loads(response.text)
            return {"response": categorization_json}
        except json.JSONDecodeError:
            # If it's not valid JSON, return the raw text
            return {"response": response.text}
            
    except Exception as e:
        print(f"Error categorizing transaction: {str(e)}")
        return {"error": f"Error categorizing transaction: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)