from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import io

# Import pdf2image for PDF-to-image conversion
from pdf2image import convert_from_bytes

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for local development (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your Gemini API key (loaded from .env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

@app.post("/process-pdf")
async def process_file(prompt: str = Form(...), file: UploadFile = File(...)):
    file_content = await file.read()

    # Check if the uploaded file is a PDF
    if file.content_type == "application/pdf":
        try:
            # Convert the PDF bytes to a list of PIL Image objects, one per page
            pages = convert_from_bytes(file_content)
            image_parts = []

            # Convert each page to a JPEG image in-memory and create a media part
            for page in pages:
                buf = io.BytesIO()
                page.save(buf, format='JPEG')  # Save the page as JPEG
                buf.seek(0)
                image_part = types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="image/jpeg"
                )
                image_parts.append(image_part)

            # Prepare contents with the prompt followed by image parts in order
            contents = [prompt] + image_parts

            # Call Gemini with the ordered content list
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",  # Use the experimental Gemini model
                contents=contents
            )
            return {"response": response.text}
        except Exception as e:
            return {"error": "Request failed", "detail": str(e)}
    else:
        # For non-PDF files (e.g., images), process as before
        file_part = types.Part.from_bytes(
            data=file_content,
            mime_type=file.content_type
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[prompt, file_part]
            )
            return {"response": response.text}
        except Exception as e:
            return {"error": "Request failed", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
