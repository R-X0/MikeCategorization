# File: transaction_extraction.py
import datetime
from typing import List
from models import Transaction

def process_file(filename: str, file_contents: bytes) -> List[Transaction]:
    """
    Extract transactions from a CSV/plain-text file.
    Assumes each line is: date,amount,description,account_code.
    """
    try:
        extracted_text = file_contents.decode('utf-8', errors='ignore')
    except Exception:
        extracted_text = ""
    
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
