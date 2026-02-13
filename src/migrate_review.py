#!/usr/bin/env python3
"""
Migration script for Abacus Transaction Review feature
Creates category_groups, categories tables, adds review columns to transactions,
seeds data from config.yaml, and backfills existing transactions.

Idempotent: Safe to run multiple times.
"""

import duckdb
import sys
from pathlib import Path
from config import get_db_path, get_category_taxonomy
import re

# Color palette for category groups (distinct, accessible colors)
GROUP_COLORS = {
    "Food & Drink": "#FF6B6B",      # Red
    "Housing": "#4ECDC4",            # Teal
    "Transportation": "#95E1D3",     # Mint
    "Shopping": "#F38181",           # Coral
    "Health": "#AA96DA",             # Purple
    "Entertainment": "#FCBAD3",      # Pink
    "Bills & Subscriptions": "#FFD93D", # Yellow
    "Travel": "#6BCF7F",             # Green
    "Pets": "#C7CEEA",               # Lavender
    "Personal": "#FFEAA7",           # Light Yellow
    "Income": "#81C784",             # Light Green
    "Transfer": "#90A4AE",           # Gray
}

# Icons for category groups
GROUP_ICONS = {
    "Food & Drink": "🍽️",
    "Housing": "🏠",
    "Transportation": "🚗",
    "Shopping": "🛍️",
    "Health": "❤️",
    "Entertainment": "🎬",
    "Bills & Subscriptions": "📱",
    "Travel": "✈️",
    "Pets": "🐱",
    "Personal": "👤",
    "Income": "💰",
    "Transfer": "⇄",
}

# Icons for specific categories
CATEGORY_ICONS = {
    # Food & Drink
    "Groceries": "🛒",
    "Dining Out": "🍴",
    "Coffee & Drinks": "☕",
    "Delivery": "🛵",
    "Convenience": "🏪",
    
    # Housing
    "Rent/Mortgage": "🏘️",
    "Utilities": "⚡",
    "Home Maintenance": "🔧",
    
    # Transportation
    "Gas": "⛽",
    "Auto Insurance": "🛡️",
    "Maintenance": "🔧",
    "Parking": "🅿️",
    "Rideshare": "🚕",
    
    # Shopping
    "Clothing": "👕",
    "Electronics": "💻",
    "Household": "🏠",
    "Amazon": "📦",
    "Pet Supplies": "🐾",
    
    # Health
    "Insurance": "🏥",
    "Medical": "🩺",
    "Pharmacy": "💊",
    "Fitness": "💪",
    
    # Entertainment
    "Streaming": "📺",
    "Events": "🎫",
    "Hobbies": "🎨",
    
    # Bills & Subscriptions
    "Phone": "📞",
    "Internet/Phone": "🌐",
    "Software": "💾",
    "Subscriptions": "🔄",
    
    # Travel
    "Hotels": "🏨",
    "Flights": "🛫",
    "Car Rental": "🚙",
    "Travel Activities": "🗺️",
    
    # Pets
    "Pet Food": "🐾",
    "Litter": "🧹",
    "Vet": "🏥",
    "Pet Insurance": "🛡️",
    "Pet Sitting": "🏡",
    
    # Personal
    "Haircut": "✂️",
    "Education": "📚",
    "Professional Services": "💼",
    "Personal Care": "🧴",
    
    # Income
    "Salary": "💵",
    "Refunds": "🔄",
    "Credits": "💳",
    
    # Transfer
    "Transfer": "⇄",
}

# Transfer detection patterns (uppercase)
TRANSFER_PATTERNS = [
    r'\bPAYMENT\b',
    r'\bPYMT\b',
    r'\bXFER\b',
    r'\bTRANSFER\b',
    r'\bAUTOPAY\b',
    r'\bAPPLECARD\b',
    r'\bGSBANK\b',
    r'\bCHASE\b',
    r'\bCREDIT CARD\b',
]


def slugify(text):
    """Convert text to slug format (lowercase, hyphens)"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def create_tables(conn):
    """Create category_groups and categories tables if they don't exist"""
    print("Creating tables...")
    
    # Create category_groups table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_groups (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            icon VARCHAR DEFAULT '📂',
            color VARCHAR DEFAULT '#6B7280',
            sort_order INTEGER DEFAULT 0
        )
    """)
    
    # Create categories table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            icon VARCHAR DEFAULT '📦',
            color VARCHAR DEFAULT '#6B7280',
            group_id VARCHAR REFERENCES category_groups(id),
            type VARCHAR DEFAULT 'expense',
            sort_order INTEGER DEFAULT 0,
            hidden BOOLEAN DEFAULT FALSE
        )
    """)
    
    print("✓ Tables created")


def add_transaction_columns(conn):
    """Add review columns to transactions table"""
    print("Adding transaction columns...")
    
    # Check if columns already exist
    columns = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'transactions'
    """).fetchall()
    
    existing_cols = {col[0] for col in columns}
    
    # Add review_status column
    if 'review_status' not in existing_cols:
        conn.execute("""
            ALTER TABLE transactions 
            ADD COLUMN review_status VARCHAR DEFAULT 'suggested'
        """)
        print("  - Added review_status column")
    else:
        print("  - review_status column already exists")
    
    # Add is_transfer column
    if 'is_transfer' not in existing_cols:
        conn.execute("""
            ALTER TABLE transactions 
            ADD COLUMN is_transfer BOOLEAN DEFAULT FALSE
        """)
        print("  - Added is_transfer column")
    else:
        print("  - is_transfer column already exists")
    
    # Add transfer_pair_id column
    if 'transfer_pair_id' not in existing_cols:
        conn.execute("""
            ALTER TABLE transactions 
            ADD COLUMN transfer_pair_id VARCHAR
        """)
        print("  - Added transfer_pair_id column")
    else:
        print("  - transfer_pair_id column already exists")
    
    print("✓ Transaction columns updated")


def seed_categories(conn):
    """Seed category_groups and categories from config.yaml"""
    print("Seeding categories...")
    
    taxonomy = get_category_taxonomy()
    
    # Add Transfer group
    taxonomy["Transfer"] = ["Transfer"]
    
    sort_order = 0
    category_sort_order = 0
    
    for group_name, categories in taxonomy.items():
        group_id = slugify(group_name)
        group_icon = GROUP_ICONS.get(group_name, "📂")
        group_color = GROUP_COLORS.get(group_name, "#6B7280")
        
        # Determine group type
        if group_name == "Income":
            group_type = "income"
        elif group_name == "Transfer":
            group_type = "transfer"
        else:
            group_type = "expense"
        
        # Insert or update category_group (idempotent)
        conn.execute("""
            INSERT INTO category_groups (id, name, icon, color, sort_order)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                icon = EXCLUDED.icon,
                color = EXCLUDED.color,
                sort_order = EXCLUDED.sort_order
        """, (group_id, group_name, group_icon, group_color, sort_order))
        
        print(f"  - Group: {group_icon} {group_name}")
        
        # Insert categories for this group
        for cat_name in categories:
            cat_id = slugify(f"{group_name}-{cat_name}")
            cat_icon = CATEGORY_ICONS.get(cat_name, "📦")
            cat_color = group_color  # Use same color as group
            
            conn.execute("""
                INSERT INTO categories (id, name, icon, color, group_id, type, sort_order, hidden)
                VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    icon = EXCLUDED.icon,
                    color = EXCLUDED.color,
                    group_id = EXCLUDED.group_id,
                    type = EXCLUDED.type,
                    sort_order = EXCLUDED.sort_order
            """, (cat_id, cat_name, cat_icon, cat_color, group_id, group_type, category_sort_order))
            
            category_sort_order += 1
        
        sort_order += 1
    
    print("✓ Categories seeded")


def backfill_review_status(conn):
    """Backfill review_status for existing transactions"""
    print("Backfilling review status...")
    
    # Transactions with merchant_mapping → confirmed
    result = conn.execute("""
        UPDATE transactions
        SET review_status = 'confirmed'
        WHERE id IN (
            SELECT t.id
            FROM transactions t
            JOIN merchant_mappings m ON UPPER(t.description) LIKE '%' || UPPER(m.pattern) || '%'
            WHERE t.category IS NOT NULL
        )
        AND review_status = 'suggested'
    """)
    confirmed_count = result.fetchone()
    print(f"  - Marked {confirmed_count[0] if confirmed_count else 0} transactions as confirmed (matched merchant mappings)")
    
    # Transactions with category but no mapping → keep as suggested
    result = conn.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE category IS NOT NULL
        AND review_status = 'suggested'
    """)
    suggested_count = result.fetchone()[0]
    print(f"  - {suggested_count} transactions remain as suggested")
    
    # Transactions with no category → suggested
    result = conn.execute("""
        UPDATE transactions
        SET review_status = 'suggested'
        WHERE category IS NULL
    """)
    
    print("✓ Review status backfilled")


def detect_transfers(conn):
    """Auto-detect and mark likely transfers"""
    print("Detecting transfers...")
    
    # Build pattern matching SQL using LIKE (DuckDB compatible)
    pattern_conditions = " OR ".join([
        f"UPPER(description) LIKE '%{pattern.replace(r'\b', '').replace('\\', '')}%'"
        for pattern in TRANSFER_PATTERNS
    ])
    
    # Mark transactions matching transfer patterns
    result = conn.execute(f"""
        UPDATE transactions
        SET is_transfer = TRUE
        WHERE ({pattern_conditions})
        AND is_transfer = FALSE
    """)
    transfer_count = result.fetchone()
    print(f"  - Marked {transfer_count[0] if transfer_count else 0} transactions as likely transfers")
    
    # Try to pair transfers (same absolute amount, close dates, opposite signs, different accounts)
    print("  - Attempting to pair transfers...")
    
    # Find potential pairs
    pairs = conn.execute("""
        SELECT 
            t1.id as id1,
            t2.id as id2
        FROM transactions t1
        JOIN transactions t2 ON 
            ABS(t1.amount) = ABS(t2.amount)
            AND t1.amount * t2.amount < 0  -- Opposite signs
            AND t1.account_id != t2.account_id  -- Different accounts
            AND ABS(DATEDIFF('day', t1.transaction_date, t2.transaction_date)) <= 3  -- Within 3 days
            AND t1.id < t2.id  -- Avoid duplicates
        WHERE t1.is_transfer = TRUE
        AND t2.is_transfer = TRUE
        AND t1.transfer_pair_id IS NULL
        AND t2.transfer_pair_id IS NULL
    """).fetchall()
    
    # Link pairs
    pair_count = 0
    for pair in pairs:
        id1, id2 = pair
        # Use the first ID as the pair ID
        conn.execute("""
            UPDATE transactions
            SET transfer_pair_id = ?
            WHERE id IN (?, ?)
        """, (id1, id1, id2))
        pair_count += 1
    
    print(f"  - Paired {pair_count} transfer transactions")
    print("✓ Transfer detection complete")


def main():
    """Run the migration"""
    print("=" * 60)
    print("Abacus Transaction Review - Database Migration")
    print("=" * 60)
    
    db_path = get_db_path()
    print(f"\nDatabase: {db_path}")
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Run `abacus import` first to create the database.")
        sys.exit(1)
    
    conn = duckdb.connect(str(db_path))
    
    try:
        # Step 1: Create tables
        create_tables(conn)
        
        # Step 2: Add transaction columns
        add_transaction_columns(conn)
        
        # Step 3: Seed categories
        seed_categories(conn)
        
        # Step 4: Backfill review status
        backfill_review_status(conn)
        
        # Step 5: Detect transfers
        detect_transfers(conn)
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
