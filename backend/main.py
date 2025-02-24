import io
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

# Step 1: Raw extraction prompt remains the same.
RAW_PROMPT = "List every single thing exactly as it appears on the document, each column and row, in full"

# New prompt template for converting the raw data into plain text format.
TEXT_PROMPT_TEMPLATE = """
Format the following raw extracted data into a neatly organized text document.
Ensure the output is plain text with clear structure and no additional commentary.

Raw Data:
{raw_data}
"""

@app.post("/process-pdf")
async def process_file(file: UploadFile = File(...)):
    file_content = await file.read()
    results = []

    try:
        if file.content_type == "application/pdf":
            # Use PdfReader to read the PDF
            pdf_reader = PdfReader(io.BytesIO(file_content))
            # Process each page individually
            for page_number, page in enumerate(pdf_reader.pages, start=1):
                # Write the individual page to a BytesIO stream
                pdf_writer = PdfWriter()
                pdf_writer.add_page(page)
                page_stream = io.BytesIO()
                pdf_writer.write(page_stream)
                page_stream.seek(0)

                # Create a Gemini Part from the page bytes
                file_part = types.Part.from_bytes(
                    data=page_stream.getvalue(),
                    mime_type="application/pdf"
                )

                # Step 1: Extract raw data from the page.
                raw_response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[RAW_PROMPT, file_part],
                    config={
                        "max_output_tokens": 40000,
                        "response_mime_type": "text/plain"
                    }
                )
                raw_text = raw_response.text

                # Step 2: Convert the raw output into plain text document format.
                text_prompt = TEXT_PROMPT_TEMPLATE.format(raw_data=raw_text)
                text_response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[text_prompt],
                    config={
                        "max_output_tokens": 40000,
                        "response_mime_type": "text/plain"
                    }
                )
                results.append(f"--- Page {page_number} ---\n{text_response.text}")

        else:
            # For non-PDF types, you can handle them as before
            file_part = types.Part.from_bytes(
                data=file_content,
                mime_type=file.content_type
            )
            raw_response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[RAW_PROMPT, file_part],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "text/plain"
                }
            )
            raw_text = raw_response.text
            text_prompt = TEXT_PROMPT_TEMPLATE.format(raw_data=raw_text)
            text_response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[text_prompt],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "text/plain"
                }
            )
            results.append(text_response.text)

        # Combine page outputs in order
        combined_text = "\n\n".join(results)
        return {"response": combined_text}
    except Exception as e:
        return {"error": "Request failed", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
