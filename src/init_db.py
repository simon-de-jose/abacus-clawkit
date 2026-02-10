"""Initialize Abacus DuckDB database with schema and seed data"""

import duckdb
from pathlib import Path
from datetime import datetime
from config import get_db_path, get_category_taxonomy

def init_database():
    """Create database schema and seed initial data"""
    
    db_path = get_db_path()
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    conn = duckdb.connect(str(db_path))
    
    # Create accounts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            bank VARCHAR NOT NULL,
            last_four VARCHAR,
            type VARCHAR NOT NULL,  -- credit/debit/checking
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create transactions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR PRIMARY KEY,
            transaction_date DATE NOT NULL,
            post_date DATE,
            description VARCHAR NOT NULL,
            merchant VARCHAR,
            bank_category VARCHAR,
            category VARCHAR,
            category_group VARCHAR,
            type VARCHAR NOT NULL,  -- Sale/Return/Payment
            amount DECIMAL(10,2) NOT NULL,
            account_id VARCHAR,
            memo VARCHAR,
            needs_review BOOLEAN DEFAULT FALSE,
            file_hash VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    
    # Create indexes for common queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)")
    
    # Create merchant_mappings table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS merchant_mappings (
            id INTEGER PRIMARY KEY,
            pattern VARCHAR NOT NULL UNIQUE,
            merchant VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            category_group VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create import_log table
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS import_log_seq START 1
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('import_log_seq'),
            filename VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL UNIQUE,
            rows_imported INTEGER DEFAULT 0,
            rows_skipped INTEGER DEFAULT 0,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✓ Schema created")
    
    # Seed merchant mappings (from implementation plan)
    merchant_mappings = [
        ("AMAZON MKTPL*", "Amazon", "Amazon", "Shopping"),
        ("Amazon.com*", "Amazon", "Amazon", "Shopping"),
        ("CHEWY.COM", "Chewy", "Pet Supplies", "Pets"),
        ("NIJIYA MARKET", "Nijiya Market", "Groceries", "Food & Drink"),
        ("Whole Foods*", "Whole Foods", "Groceries", "Food & Drink"),
        ("WOOGA SULLUNGTANG", "Wooga Sullungtang", "Dining Out", "Food & Drink"),
        ("TST*SWEET WHEAT", "Sweet Wheat Bakery", "Coffee & Drinks", "Food & Drink"),
        ("UBER *TRIP", "Uber", "Rideshare", "Transportation"),
        ("UBER* TRIP", "Uber", "Rideshare", "Transportation"),
        ("Spectrum*", "Spectrum", "Internet/Phone", "Bills & Subscriptions"),
        ("TESLA SUBSCRIPTION", "Tesla", "Auto Insurance", "Transportation"),
        ("CINEMARK*", "Cinemark", "Entertainment", "Entertainment"),
        ("GOOGLE *YouTube*", "YouTube Premium", "Streaming", "Bills & Subscriptions"),
        ("TAOBAO.COM", "Taobao", "Shopping", "Shopping"),
        ("CHIPOTLE*", "Chipotle", "Dining Out", "Food & Drink"),
        ("COSTCO*", "Costco", "Groceries", "Food & Drink"),
        ("ROVER.COM", "Rover", "Pet Sitting", "Pets"),
        ("HUBERMAN LAB", "Huberman Lab", "Subscriptions", "Bills & Subscriptions"),
        ("Booking.com*", "Booking.com", "Hotels", "Travel"),
        ("HOTEL *", "Hotel", "Hotels", "Travel"),
        ("OXXO*", "OXXO", "Convenience", "Food & Drink"),
        ("MADEWELL", "Madewell", "Clothing", "Shopping"),
        ("SEPHORA*", "Sephora", "Personal Care", "Personal"),
        ("STARBUCKS*", "Starbucks", "Coffee & Drinks", "Food & Drink"),
        ("SQ *DELICES DU CHEF", "Délices du Chef", "Dining Out", "Food & Drink"),
        ("TACOMASA*", "Tacomasa", "Dining Out", "Food & Drink"),
        ("FOOD.APPLE.COM", "Apple (Food)", "Subscriptions", "Bills & Subscriptions"),
        ("SUPERBCUT*", "Supercuts", "Haircut", "Personal"),
        ("Tesla Insurance*", "Tesla Insurance", "Auto Insurance", "Transportation"),
    ]
    
    # Check if already seeded
    count = conn.execute("SELECT COUNT(*) FROM merchant_mappings").fetchone()[0]
    
    if count == 0:
        for i, (pattern, merchant, category, group) in enumerate(merchant_mappings, start=1):
            conn.execute("""
                INSERT INTO merchant_mappings (id, pattern, merchant, category, category_group)
                VALUES (?, ?, ?, ?, ?)
            """, (i, pattern, merchant, category, group))
        print(f"✓ Seeded {len(merchant_mappings)} merchant mappings")
    else:
        print(f"✓ Merchant mappings already exist ({count} rows)")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database initialization complete!")
    print(f"   Location: {db_path}")

if __name__ == "__main__":
    init_database()
