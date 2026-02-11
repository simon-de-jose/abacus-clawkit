"""Bank of America CSV parser"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import re

def detect(file_path: str) -> bool:
    """Check if file looks like a BofA statement export"""
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        return first_line.strip().startswith('Description,,Summary Amt')

def parse(file_path: str) -> List[Dict]:
    """Parse Bank of America CSV export
    
    Format: Summary header block, then blank line, then:
    Date, Description, Amount, Running Bal.
    """
    transactions = []
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split on the transaction header line
    # Find "Date,Description,Amount,Running Bal."
    lines = content.strip().split('\n')
    
    # Find where transaction data starts
    data_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Date,Description,Amount'):
            data_start = i
            break
    
    if data_start is None:
        raise ValueError("Could not find transaction data header in BofA file")
    
    # Parse from data_start using csv reader
    transaction_text = '\n'.join(lines[data_start:])
    reader = csv.DictReader(transaction_text.split('\n'))
    
    for row in reader:
        date_str = row.get('Date', '').strip()
        description = row.get('Description', '').strip()
        amount_str = row.get('Amount', '').strip()
        
        if not date_str or not description or not amount_str:
            continue
        
        # Skip "Beginning balance" and "Ending balance" rows
        if 'Beginning balance' in description or 'Ending balance' in description:
            continue
        
        # Parse date
        transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
        
        # Parse amount (remove commas, already signed: negative = debit)
        amount = float(amount_str.replace(',', ''))
        
        # Determine type
        if amount >= 0:
            txn_type = 'Credit'
        else:
            txn_type = 'Debit'
        
        transaction = {
            'transaction_date': transaction_date,
            'post_date': transaction_date,  # BofA doesn't have separate post date
            'description': description,
            'bank_category': '',
            'type': txn_type,
            'amount': amount,
            'memo': None,
        }
        
        transactions.append(transaction)
    
    return transactions
