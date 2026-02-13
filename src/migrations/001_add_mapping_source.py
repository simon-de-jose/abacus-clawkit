#!/usr/bin/env python3
"""
Migration: Add source column to merchant_mappings table

Adds a 'source' column to track where mappings came from:
- 'seed' for original seed data
- 'manual' for user-added mappings
- 'llm' for AI-generated mappings
"""

import duckdb
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_db_path


def migrate():
    """Add source column to merchant_mappings table (idempotent)"""
    
    db_path = get_db_path()
    print(f"Running migration on: {db_path}")
    
    conn = duckdb.connect(str(db_path))
    
    # Check if column already exists
    try:
        result = conn.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'merchant_mappings' AND column_name = 'source'
        """).fetchone()
        
        if result:
            print("✓ Column 'source' already exists, skipping migration")
            conn.close()
            return
    except Exception:
        # Table might not exist yet, proceed with migration
        pass
    
    # Add the column
    print("Adding 'source' column...")
    conn.execute("""
        ALTER TABLE merchant_mappings 
        ADD COLUMN source VARCHAR DEFAULT 'manual'
    """)
    
    # Update existing rows to 'seed'
    print("Updating existing rows to source='seed'...")
    rows_updated = conn.execute("""
        UPDATE merchant_mappings 
        SET source = 'seed' 
        WHERE source = 'manual'
    """).fetchone()
    
    conn.commit()
    conn.close()
    
    print(f"✅ Migration complete! Updated {rows_updated[0] if rows_updated else 0} rows")


if __name__ == "__main__":
    migrate()
