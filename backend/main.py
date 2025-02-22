from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
import requests
from dotenv import load_dotenv

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

# Your Anthropic API key (loaded from .env)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

@app.post("/process-pdf")
async def process_pdf(prompt: str = Form(...), file: UploadFile = File(...)):
    # Read PDF file and convert to base64 string
    file_content = await file.read()
    pdf_base64 = base64.b64encode(file_content).decode("utf-8")

    # Build JSON payload according to Claude PDF processing API docs
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    # Send request to the Claude API
    response = requests.post(CLAUDE_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        api_response = response.json()
        # Extract just the text from the response content
        text_parts = []
        for part in api_response.get("content", []):
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        text_response = "\n".join(text_parts)
        return {"response": text_response}
    else:
        return {
            "error": "Request failed",
            "status_code": response.status_code,
            "detail": response.text
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
