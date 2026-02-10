"""CSV import script with deduplication"""

import hashlib
import duckdb
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from config import get_db_path, get_import_folder
from parsers import chase
from categorizer import apply_categorization

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def calculate_transaction_id(transaction: Dict, account_id: str) -> str:
    """Generate unique transaction ID from transaction data"""
    # Create a stable hash from key fields
    key = f"{transaction['transaction_date']}|{transaction['amount']}|{transaction['description']}|{account_id}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def get_or_create_account(conn: duckdb.DuckDBPyConnection, bank: str, last_four: str = None) -> str:
    """Get existing account or create new one"""
    # For now, use a simple account ID based on bank name
    account_id = f"{bank.lower()}_{'****' if not last_four else last_four}"
    
    # Check if exists
    result = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    
    if not result:
        # Create account
        conn.execute("""
            INSERT INTO accounts (id, name, bank, last_four, type)
            VALUES (?, ?, ?, ?, ?)
        """, (account_id, f"{bank} Account", bank, last_four or "****", "credit"))
        print(f"  Created account: {account_id}")
    
    return account_id

def import_csv(file_path: str, bank: str = "Chase") -> Dict:
    """Import CSV file with deduplication
    
    Returns: dict with import stats
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"\n📁 Importing: {file_path.name}")
    print(f"   Bank: {bank}")
    
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)
    
    # Connect to database
    db_path = get_db_path()
    conn = duckdb.connect(str(db_path))
    
    # Check if file already imported
    existing = conn.execute(
        "SELECT filename, imported_at FROM import_log WHERE file_hash = ?",
        (file_hash,)
    ).fetchone()
    
    if existing:
        print(f"   ⚠️  File already imported: {existing[0]} at {existing[1]}")
        conn.close()
        return {
            'filename': file_path.name,
            'rows_imported': 0,
            'rows_skipped': 0,
            'already_imported': True
        }
    
    # Parse CSV based on bank
    if bank.lower() == "chase":
        transactions = chase.parse(str(file_path))
    else:
        raise ValueError(f"Unsupported bank: {bank}")
    
    print(f"   Parsed {len(transactions)} transactions")
    
    # Get or create account
    account_id = get_or_create_account(conn, bank)
    
    # Import transactions
    rows_imported = 0
    rows_skipped = 0
    
    for txn in transactions:
        # Apply categorization
        txn = apply_categorization(conn, txn)
        
        # Generate transaction ID
        txn_id = calculate_transaction_id(txn, account_id)
        
        # Check if transaction already exists
        existing_txn = conn.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (txn_id,)
        ).fetchone()
        
        if existing_txn:
            rows_skipped += 1
            continue
        
        # Insert transaction
        conn.execute("""
            INSERT INTO transactions (
                id, transaction_date, post_date, description, merchant,
                bank_category, category, category_group, type, amount,
                account_id, memo, needs_review, file_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            txn_id,
            txn['transaction_date'],
            txn['post_date'],
            txn['description'],
            txn['merchant'],
            txn['bank_category'],
            txn['category'],
            txn['category_group'],
            txn['type'],
            txn['amount'],
            account_id,
            txn['memo'],
            txn['needs_review'],
            file_hash
        ))
        rows_imported += 1
    
    # Log the import
    conn.execute("""
        INSERT INTO import_log (filename, file_hash, rows_imported, rows_skipped)
        VALUES (?, ?, ?, ?)
    """, (file_path.name, file_hash, rows_imported, rows_skipped))
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Imported: {rows_imported} new transactions")
    if rows_skipped > 0:
        print(f"   ⏭️  Skipped: {rows_skipped} duplicates")
    
    return {
        'filename': file_path.name,
        'rows_imported': rows_imported,
        'rows_skipped': rows_skipped,
        'already_imported': False
    }

def import_folder(folder_path: str = None):
    """Import all CSV files from a folder"""
    if folder_path is None:
        folder_path = get_import_folder()
    
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    # Find all CSV files
    csv_files = list(folder_path.glob("*.csv")) + list(folder_path.glob("*.CSV"))
    
    if not csv_files:
        print(f"No CSV files found in: {folder_path}")
        return
    
    print(f"\n🗂️  Found {len(csv_files)} CSV files in: {folder_path}")
    
    total_imported = 0
    total_skipped = 0
    
    for csv_file in csv_files:
        result = import_csv(str(csv_file), bank="Chase")
        total_imported += result['rows_imported']
        total_skipped += result['rows_skipped']
    
    print(f"\n📊 Summary:")
    print(f"   Total imported: {total_imported}")
    print(f"   Total skipped: {total_skipped}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Import specific file
        file_path = sys.argv[1]
        import_csv(file_path)
    else:
        # Import from default folder
        import_folder()
