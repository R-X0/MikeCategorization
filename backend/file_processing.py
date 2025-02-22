# File: file_processing.py
from typing import List
from models import Transaction
import categorization

def batch_process(transactions: List[Transaction]):
    """
    Simulate background batch processing (e.g., categorization).
    """
    categorized = categorization.categorize_transactions(transactions)
    print("Batch processed transactions:")
    for tx in categorized:
        print(tx.dict())
