#!/usr/bin/env python3
"""
Migration: Add projects and project_transactions tables

Creates:
- projects: Track projects with budgets, dates, and lifecycle status
- project_transactions: Many-to-many relationship between projects and transactions
"""

import duckdb
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_db_path


def migrate():
    """Create projects and project_transactions tables (idempotent)"""
    
    db_path = get_db_path()
    print(f"Running migration on: {db_path}")
    
    conn = duckdb.connect(str(db_path))
    
    # Check if projects table already exists
    try:
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'projects'
        """).fetchone()
        
        if result:
            print("✓ Table 'projects' already exists, skipping migration")
            conn.close()
            return
    except Exception as e:
        print(f"Error checking for existing table: {e}")
        pass
    
    # Create sequences
    print("Creating sequences...")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS projects_seq START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS project_transactions_seq START 1")
    
    # Create projects table
    print("Creating 'projects' table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY DEFAULT nextval('projects_seq'),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('draft', 'active', 'complete', 'archived')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            archived_at TIMESTAMP,
            start_date DATE,
            end_date DATE,
            budget_amount DECIMAL(10, 2),
            color TEXT DEFAULT '#3B82F6',
            ai_suggested BOOLEAN DEFAULT FALSE,
            ai_confidence DECIMAL(3, 2),
            ai_reasoning TEXT,
            tags TEXT,
            location TEXT
        )
    """)
    
    # Create project_transactions table
    print("Creating 'project_transactions' table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_transactions (
            id INTEGER PRIMARY KEY DEFAULT nextval('project_transactions_seq'),
            project_id INTEGER NOT NULL,
            transaction_id VARCHAR NOT NULL,
            status TEXT NOT NULL DEFAULT 'accepted' CHECK(status IN ('proposed', 'accepted', 'rejected')),
            proposed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            match_reason TEXT,
            match_confidence DECIMAL(3, 2),
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            UNIQUE(project_id, transaction_id)
        )
    """)
    
    # Create indexes
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_transactions_project_id ON project_transactions(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_transactions_transaction_id ON project_transactions(transaction_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_transactions_status ON project_transactions(status)")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration complete!")


if __name__ == "__main__":
    migrate()
