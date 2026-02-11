"""Citi CSV parser"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict

def detect(file_path: str) -> bool:
    """Check if file looks like a citi export"""
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        return 'Status' in first_line and 'Member Name' in first_line

def parse(file_path: str) -> List[Dict]:
    """Parse citi CSV export
    
    Expected columns: Status, Date, Description, Debit, Credit, Member Name
    """
    transactions = []
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            date_str = row.get('Date', '').strip()
            description = row.get('Description', '').strip()
            debit_str = row.get('Debit', '').strip()
            credit_str = row.get('Credit', '').strip()
            
            if not date_str or not description:
                continue
            
            # Parse date
            transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
            
            # Calculate amount: credits positive, debits negative
            if credit_str:
                amount = float(credit_str.replace(',', ''))
                txn_type = 'Credit'
            elif debit_str:
                amount = -float(debit_str.replace(',', ''))
                txn_type = 'Debit'
            else:
                continue
            
            transaction = {
                'transaction_date': transaction_date,
                'post_date': transaction_date,
                'description': description,
                'bank_category': '',
                'type': txn_type,
                'amount': amount,
                'memo': None,
            }
            
            transactions.append(transaction)
    
    return transactions
