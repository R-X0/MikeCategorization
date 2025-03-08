import io
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Body
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

# New prompt template to convert extracted text into the structured JSON schema.
JSON_SCHEMA_PROMPT_TEMPLATE = """
Format the following extracted text into a JSON object that strictly follows the schema below. Ensure that the output is valid JSON with no additional commentary.

Schema:
{{
  "documentMetadata": {{
    "documentID": "Unique identifier for the document",
    "documentType": "Type/category (e.g., Invoice, Receipt, BankStatement, MerchantStatement, CreditMemo, PurchaseOrder, etc.)",
    "documentNumber": "Official reference number from the document",
    "documentDate": "YYYY-MM-DD (date issued)",
    "uploadDate": "YYYY-MM-DDTHH:MM:SSZ (date/time uploaded)",
    "source": {{
      "name": "Name of the issuer (vendor, bank, customer, etc.)",
      "type": "Category (Vendor, Customer, Bank, etc.)",
      "contact": {{
        "address": "Full address if available",
        "phone": "Contact phone number",
        "email": "Contact email address"
      }}
    }},
    "fileInfo": {{
      "fileName": "Original file name",
      "fileType": "Format (e.g., PDF, JPEG)",
      "pageCount": "Number of pages in the document",
      "OCRProcessed": "Boolean flag indicating whether OCR has been applied"
    }}
  }},
  "financialData": {{
    "currency": "Currency code (e.g., USD, EUR)",
    "subtotal": "Amount before any discounts or additional fees",
    "taxAmount": "Total tax applied (if any) – can be zero or omitted if not applicable",
    "discount": "Any discounts or adjustments applied",
    "totalAmount": "Final total monetary value on the document",
    "paymentStatus": "Status (e.g., Paid, Unpaid, Pending)",
    "paymentTerms": "Terms such as 'Net 30'",
    "dueDate": "YYYY-MM-DD (if a due date is specified)"
  }},
  "lineItems": [
    {{
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
    }}
  ],
  "partyInformation": {{
    "vendor": {{
      "name": "Vendor/Supplier name",
      "address": "Vendor address",
      "contact": "Vendor contact details (phone/email)",
      "taxID": "Tax identifier if available (optional)"
    }},
    "customer": {{
      "name": "Customer name",
      "address": "Customer address",
      "contact": "Customer contact details",
      "customerID": "Internal customer identifier"
    }},
    "bankDetails": {{
      "bankName": "Name of the bank",
      "accountNumber": "Bank account number",
      "routingNumber": "Routing or sort code"
    }}
  }},
  "paymentInformation": {{
    "paymentMethod": "Method (e.g., Cash, Credit Card, EFT, Direct Deposit)",
    "transactionID": "Identifier for electronically processed payments",
    "paidDate": "YYYY-MM-DD (date when payment was made)",
    "bankDetails": {{
      "bankName": "If relevant, bank name for the transaction",
      "accountNumber": "Account number associated with payment",
      "routingNumber": "Routing number for bank transfers"
    }}
  }},
  "fixedAssetData": {{
    "assetID": "Unique asset identifier",
    "description": "Description of the fixed asset or inventory item",
    "acquisitionDate": "YYYY-MM-DD (date of purchase/acquisition)",
    "purchasePrice": "Cost of acquiring the asset",
    "depreciationMethod": "Method used (e.g., Straight-line, Declining Balance)",
    "currentValue": "Current book value of the asset",
    "location": "Physical location of the asset (if applicable)"
  }},
  "additionalData": {{
    "notes": "Any annotations or internal comments",
    "attachments": [
      "Link(s) or reference(s) to supplementary files, if applicable"
    ],
    "referenceNumbers": [
      "Other relevant reference numbers (e.g., purchase order numbers, shipping numbers)"
    ],
    "auditTrail": [
      {{
        "action": "Description of the processing step (e.g., 'uploaded', 'OCR extracted')",
        "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "user": "User or system that performed the action"
      }}
    ]
  }}
}}

Extracted Text:
{extracted_text}
"""

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
    Verify the extraction accuracy by comparing row and column sums with their totals
    in the document itself, rather than applying financial formulas that may not apply.
    
    Parameters:
    json_data (dict): The structured JSON data extracted from the document
    
    Returns:
    dict: Original JSON with added extraction verification results
    """
    try:
        # First, detect document type to apply appropriate verification rules
        document_type = detect_document_type(json_data)
        
        # Create a prompt for Gemini that focuses on extraction accuracy
        verification_prompt = f"""
        Analyze this financial document data to verify EXTRACTION ACCURACY, not mathematical correctness.
        
        DOCUMENT TYPE: {document_type.upper()}
        
        CRITICAL INSTRUCTIONS:
        1. DO NOT verify financial formulas (like subtotal + tax = total) unless explicitly stated in the document.
        2. Instead, focus on verifying that values were correctly extracted from the document:
           - Verify column sums match their stated totals in the document
           - Verify row calculations match their stated results in the document
           - Identify likely OCR/extraction errors (e.g., "0" extracted as "O", "1" as "l", etc.)
        
        3. Apply different verification approaches based on document type:
        
           FOR PAYMENT PROCESSING STATEMENTS OR MERCHANT STATEMENTS:
           - Verify that column sums match the extracted totals shown in the document itself
           - DO NOT assume that totals should equal the sum of line items unless explicitly stated
           - Simply check if the extraction matches what's actually in the document
        
           FOR INVOICES AND RECEIPTS:
           - Verify that extracted line items match their stated totals in the document
           - Check that document's own calculated values were correctly extracted
        
           FOR BANK STATEMENTS:
           - Verify that transaction amounts were correctly extracted
           - Check that running balances match what's shown in the document
        
        4. When reviewing numerical values:
           - Check for common extraction errors with decimal points (e.g., 1.00 vs 100)
           - Check for common digit extraction errors (e.g., 7 vs 1, 8 vs 3, 5 vs 6)
           - Verify that signs (positive/negative) were correctly captured
        
        IMPORTANT GUIDELINES:
        - Your primary goal is to verify EXTRACTION ACCURACY, not financial correctness
        - The document itself might contain mathematical errors - that's not what you're checking
        - You're checking if the JSON data accurately represents what's actually in the document
        - Focus on clear extraction errors where digits or decimal points were misread
        
        Financial Data:
        {json.dumps(json_data, indent=2)}
        
        Return your verification as JSON with this strict structure:
        {{
          "extractionVerified": Boolean (true if extraction is accurate, false if clear extraction errors exist),
          "discrepancies": [
            {{
              "type": "String (LineItem, Column Total, Row Sum, etc.)",
              "location": "String (reference to where in the document this occurs)",
              "documentValue": "String/Number (what appears to be in the document)",
              "extractedValue": "String/Number (what was extracted in the JSON)",
              "likelyCorrectValue": "String/Number (the most likely correct value)",
              "confidence": "String (High, Medium, Low)"
            }}
          ],
          "summary": "String (brief explanation of extraction verification results)"
        }}
        
        Only include discrepancies that appear to be EXTRACTION ERRORS, not mathematical inconsistencies in the document itself.
        Rate the confidence of each discrepancy based on the clarity of the extraction error.
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
            
            # Filter out low confidence discrepancies if there are too many
            if "discrepancies" in verification_results and len(verification_results["discrepancies"]) > 10:
                # Keep only high and medium confidence issues
                significant_issues = [d for d in verification_results["discrepancies"] 
                                     if d.get("confidence", "Low") in ["High", "Medium"]]
                
                # If we still have more than 5 discrepancies, prioritize high confidence only
                if len(significant_issues) > 5:
                    high_confidence_issues = [d for d in significant_issues 
                                              if d.get("confidence", "") == "High"]
                    # If we have high confidence issues, use only those
                    if high_confidence_issues:
                        verification_results["discrepancies"] = high_confidence_issues
                    else:
                        # Otherwise use the top 5 medium issues
                        verification_results["discrepancies"] = significant_issues[:5]
                else:
                    verification_results["discrepancies"] = significant_issues
            
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

async def process_page(page):
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

    # Step 2: Convert the raw text into structured JSON using your schema.
    json_prompt = JSON_SCHEMA_PROMPT_TEMPLATE.format(extracted_text=raw_text)
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

def merge_page_results(page_results):
    """
    Merge JSON results from multiple pages.
    For document-level fields, we assume they are the same across pages and only keep the first occurrence.
    For list fields (e.g., lineItems), we concatenate them.
    """
    merged = None
    
    # First, merge all the basic document data
    for result in page_results:
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            continue  # Optionally log or handle the error
            
        if merged is None:
            merged = data
        else:
            # Merge lineItems arrays if they exist
            if "lineItems" in data and isinstance(data["lineItems"], list):
                merged.setdefault("lineItems", []).extend(data["lineItems"])
            
            # Merge additionalData arrays (attachments, referenceNumbers, auditTrail)
            if "additionalData" in data:
                for key in ["attachments", "referenceNumbers", "auditTrail"]:
                    if key in data["additionalData"]:
                        merged.setdefault("additionalData", {}).setdefault(key, []).extend(
                            data["additionalData"][key]
                        )
    
    # Remove any extractionVerification fields - we'll perform a new verification on the complete document
    if merged and "extractionVerification" in merged:
        del merged["extractionVerification"]
            
    return merged

@app.post("/process-pdf")
async def process_file(file: UploadFile = File(...)):
    file_content = await file.read()
    
    try:
        if file.content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(file_content))
            # Process each page concurrently using the per-page processing function.
            tasks = [process_page(page) for page in pdf_reader.pages]
            page_results = await asyncio.gather(*tasks)
            
            # Merge the JSON results from each page.
            merged_result = merge_page_results(page_results)
            
            # Perform extraction verification on the complete document
            final_result = await verify_extraction(merged_result)
            
            combined_response_text = json.dumps(final_result, indent=2)
        else:
            # For non-PDF files, process as before.
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
            json_prompt = JSON_SCHEMA_PROMPT_TEMPLATE.format(extracted_text=raw_text)
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