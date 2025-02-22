# File: models.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

class Transaction(BaseModel):
    transaction_id: Optional[str] = None
    transaction_date: datetime
    amount: float
    description: str
    account_code: str
    category: Optional[str] = None

    def __init__(self, **data):
        if 'transaction_id' not in data or data['transaction_id'] is None:
            data['transaction_id'] = str(uuid.uuid4())
        super().__init__(**data)

class Feedback(BaseModel):
    transaction_id: str
    corrected_category: str
    comments: Optional[str] = None
