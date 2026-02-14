#!/usr/bin/env python3
"""
Migration: Add AI learning log table

Creates:
- ai_learning_log: Track acceptance/rejection of AI-suggested projects for learning
"""

import duckdb
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_db_path


def migrate():
    """Create ai_learning_log table (idempotent)"""
    
    db_path = get_db_path()
    print(f"Running migration on: {db_path}")
    
    conn = duckdb.connect(str(db_path))
    
    # Check if table already exists
    try:
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'ai_learning_log'
        """).fetchone()
        
        if result:
            print("✓ Table 'ai_learning_log' already exists, skipping migration")
            conn.close()
            return
    except Exception as e:
        print(f"Error checking for existing table: {e}")
        pass
    
    # Create sequence
    print("Creating sequence...")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS ai_learning_seq START 1")
    
    # Create ai_learning_log table
    print("Creating 'ai_learning_log' table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_learning_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('ai_learning_seq'),
            project_id INTEGER,
            accepted BOOLEAN NOT NULL,
            pattern_type TEXT,
            confidence_at_proposal DECIMAL(3, 2),
            feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            feedback_note TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Create indexes
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_learning_project_id ON ai_learning_log(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_learning_accepted ON ai_learning_log(accepted)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_learning_pattern_type ON ai_learning_log(pattern_type)")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration complete!")


if __name__ == "__main__":
    migrate()
