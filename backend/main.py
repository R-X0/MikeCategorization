import io
import asyncio
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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
    return json_response.text

@app.post("/process-pdf")
async def process_file(file: UploadFile = File(...)):
    file_content = await file.read()
    combined_response_text = ""
    
    try:
        if file.content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(file_content))
            # Create tasks for all pages concurrently.
            tasks = [process_page(page) for page in pdf_reader.pages]
            page_results = await asyncio.gather(*tasks)
            combined_response_text = "\n\n".join(page_results)
        else:
            # For non-PDF files, handle similarly (processing remains sequential here).
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
            combined_response_text += json_response.text

        # Return the combined Gemini responses as plain text.
        return {"response": combined_response_text.strip()}
    except Exception as e:
        return {"error": "Request failed", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
