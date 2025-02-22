# File: storage.py
from typing import List
from models import Transaction, Feedback

_transactions = []
_feedbacks = []

def add_transactions(transactions: List[Transaction]):
    _transactions.extend(transactions)

def get_transactions() -> List[Transaction]:
    return _transactions

def add_feedback(feedback: Feedback):
    _feedbacks.append(feedback)
