from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types

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
    # Read the file content
    file_content = await file.read()
    
    # Create a media part from the file content
    file_part = types.Part.from_bytes(
        data=file_content,
        mime_type=file.content_type
    )
    
    # Use the inline approach to generate content
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",  # Use the experimental Gemini model
            contents=[prompt, file_part]
        )
        return {"response": response.text}
    except Exception as e:
        return {"error": "Request failed", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
