"""Chase CSV parser"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict

def parse(file_path: str) -> List[Dict]:
    """Parse Chase CSV file and return normalized transactions
    
    Expected columns:
    Transaction Date, Post Date, Description, Category, Type, Amount, Memo
    """
    transactions = []
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Parse dates
            transaction_date = datetime.strptime(row['Transaction Date'], '%m/%d/%Y').date()
            post_date = datetime.strptime(row['Post Date'], '%m/%d/%Y').date()
            
            # Parse amount (negative = expense, positive = income/refund)
            amount = float(row['Amount'])
            
            transaction = {
                'transaction_date': transaction_date,
                'post_date': post_date,
                'description': row['Description'].strip(),
                'bank_category': row['Category'].strip(),
                'type': row['Type'].strip(),  # Sale/Return/Payment
                'amount': amount,
                'memo': row['Memo'].strip() if row['Memo'] else None,
            }
            
            transactions.append(transaction)
    
    return transactions
