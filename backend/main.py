# File: main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import Transaction, Feedback
import transaction_extraction
import categorization
import export
import file_processing
import ai_extraction  # Now uses our inline dummy OCR function
import storage

app = FastAPI(title="Automated Transaction Processing Platform")

# Allow CORS so the React frontend can access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Endpoint to upload a file containing transaction data.
    For PDF files, uses OCR+AI extraction; for others, uses CSV/text extraction.
    """
    try:
        file_contents = await file.read()
        if file.filename.lower().endswith(".pdf"):
            transactions = ai_extraction.process_pdf_file(file.filename, file_contents)
        else:
            transactions = transaction_extraction.process_file(file.filename, file_contents)
        
        # Save transactions in our in-memory datastore
        storage.add_transactions(transactions)
        
        # Schedule background categorization
        background_tasks.add_task(file_processing.batch_process, transactions)
        
        return {"status": "Processing started", "transaction_count": len(transactions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def get_transactions():
    """
    Retrieve processed transactions from storage.
    """
    return {"transactions": [tx.dict() for tx in storage.get_transactions()]}

@app.post("/api/feedback")
def submit_feedback(feedback: Feedback):
    """
    Submit user feedback on transaction categorization.
    """
    categorization.process_feedback(feedback.transaction_id, feedback.corrected_category)
    storage.add_feedback(feedback)
    return {"status": "Feedback received", "feedback": feedback.dict()}

@app.get("/api/export")
def export_data(format: str = "csv"):
    """
    Export transactions in the requested format (csv, json, xml, or qbo).
    """
    transactions = storage.get_transactions()
    try:
        if format.lower() == "csv":
            file_data = export.to_csv(transactions)
        elif format.lower() == "json":
            file_data = export.to_json(transactions)
        elif format.lower() == "xml":
            file_data = export.to_xml(transactions)
        elif format.lower() == "qbo":
            file_data = export.to_qbo(transactions)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        return {"export_data": file_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{transaction_id}")
def research_transaction(transaction_id: str):
    """
    Perform dummy AI research on an ambiguous transaction.
    This endpoint now returns static research data.
    """
    transactions = storage.get_transactions()
    transaction = next((tx for tx in transactions if tx.transaction_id == transaction_id), None)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Dummy research result (in place of an external AI research module)
    research_result = {
        "confidence": "low",
        "recommendation": "Dummy research result: please review the transaction.",
        "additional_context": "No additional context available."
    }
    return {"transaction_id": transaction_id, "research": research_result}
