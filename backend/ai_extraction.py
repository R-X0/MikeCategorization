# File: ai_extraction.py
import datetime
from typing import List
from models import Transaction

def perform_ocr(file_contents: bytes) -> str:
    """
    Dummy OCR: simply decode the bytes using UTF-8.
    """
    try:
        return file_contents.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def process_pdf_file(filename: str, file_contents: bytes) -> List[Transaction]:
    """
    Process a PDF file by performing dummy OCR then extracting transactions.
    """
    extracted_text = perform_ocr(file_contents)
    transactions = []
    lines = extracted_text.splitlines()
    for line in lines:
        parts = line.split(',')
        if len(parts) >= 4:
            try:
                tx = Transaction(
                    transaction_date=datetime.datetime.strptime(parts[0].strip(), "%Y-%m-%d"),
                    amount=float(parts[1].strip()),
                    description=parts[2].strip(),
                    account_code=parts[3].strip(),
                    category=None
                )
                transactions.append(tx)
            except Exception:
                continue
    return transactions
