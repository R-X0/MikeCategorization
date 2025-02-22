# File: categorization.py
from typing import List
from models import Transaction

def categorize_transactions(transactions: List[Transaction]) -> List[Transaction]:
    """
    Apply a simple rule-based categorization.
    """
    for tx in transactions:
        if tx.amount < 100:
            tx.category = "Low Value"
        else:
            tx.category = "High Value"
    return transactions

def process_feedback(transaction_id: str, corrected_category: str):
    """
    Process user feedback for a transaction.
    """
    print(f"Feedback received for Transaction ID {transaction_id}: set to '{corrected_category}'")
