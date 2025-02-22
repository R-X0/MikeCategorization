# File: export.py
import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import List
from models import Transaction

def to_csv(transactions: List[Transaction]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["transaction_date", "amount", "description", "account_code", "category"])
    for tx in transactions:
        writer.writerow([
            tx.transaction_date.isoformat(),
            tx.amount,
            tx.description,
            tx.account_code,
            tx.category
        ])
    return output.getvalue()

def to_json(transactions: List[Transaction]) -> str:
    transactions_dict = [tx.dict() for tx in transactions]
    return json.dumps(transactions_dict, indent=2)

def to_xml(transactions: List[Transaction]) -> str:
    root = ET.Element("Transactions")
    for tx in transactions:
        tx_elem = ET.SubElement(root, "Transaction")
        for field, value in tx.dict().items():
            child = ET.SubElement(tx_elem, field)
            child.text = str(value)
    return ET.tostring(root, encoding="unicode")

def to_qbo(transactions: List[Transaction]) -> str:
    """
    Simulate exporting transactions to QBO (QuickBooks Online) format.
    """
    qbo_lines = ["!TRNS\tTRNSTYPE\tDATE\tAMOUNT\tNAME\tMEMO"]
    for tx in transactions:
        line = f"TRNS\tCHECK\t{tx.transaction_date.strftime('%m/%d/%Y')}\t{tx.amount}\t{tx.description}\t{tx.account_code}"
        qbo_lines.append(line)
    qbo_lines.append("ENDTRNS")
    return "\n".join(qbo_lines)
