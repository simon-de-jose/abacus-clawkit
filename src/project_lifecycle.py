#!/usr/bin/env python3
"""
Project Lifecycle Automation

Auto-complete and auto-archive projects based on dates and status.

Rules:
- Auto-complete: Projects with status='active' and end_date < today
- Auto-archive: Projects with status='complete' and completed_at > 90 days ago
"""

import duckdb
from pathlib import Path
from datetime import date, datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_db_path


def auto_complete_projects(conn, dry_run: bool = False) -> int:
    """Auto-complete projects past their end date"""
    today = date.today()
    
    # Find projects to complete
    projects = conn.execute("""
        SELECT id, name, end_date
        FROM projects
        WHERE status = 'active' 
        AND end_date < ?
    """, (today,)).fetchall()
    
    if not projects:
        print("✓ No projects to auto-complete")
        return 0
    
    print(f"\nFound {len(projects)} project(s) to auto-complete:")
    for project in projects:
        print(f"  - {project[1]} (ended {project[2]})")
    
    if dry_run:
        print("\n[DRY RUN] Would complete these projects")
        return len(projects)
    
    # Update projects
    conn.execute("""
        UPDATE projects
        SET status = 'complete', completed_at = CURRENT_TIMESTAMP
        WHERE status = 'active' AND end_date < ?
    """, (today,))
    
    conn.commit()
    print(f"\n✅ Auto-completed {len(projects)} project(s)")
    return len(projects)


def auto_archive_projects(conn, dry_run: bool = False) -> int:
    """Auto-archive projects completed more than 90 days ago"""
    archive_cutoff = datetime.now() - timedelta(days=90)
    
    # Find projects to archive
    projects = conn.execute("""
        SELECT id, name, completed_at
        FROM projects
        WHERE status = 'complete'
        AND completed_at < ?
    """, (archive_cutoff,)).fetchall()
    
    if not projects:
        print("✓ No projects to auto-archive")
        return 0
    
    print(f"\nFound {len(projects)} project(s) to auto-archive:")
    for project in projects:
        days_ago = (datetime.now() - project[2]).days
        print(f"  - {project[1]} (completed {days_ago} days ago)")
    
    if dry_run:
        print("\n[DRY RUN] Would archive these projects")
        return len(projects)
    
    # Update projects
    conn.execute("""
        UPDATE projects
        SET status = 'archived', archived_at = CURRENT_TIMESTAMP
        WHERE status = 'complete' AND completed_at < ?
    """, (archive_cutoff,))
    
    conn.commit()
    print(f"\n✅ Auto-archived {len(projects)} project(s)")
    return len(projects)


def run_lifecycle_automation(dry_run: bool = False):
    """Run all lifecycle automation tasks"""
    db_path = get_db_path()
    print(f"Running project lifecycle automation on: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)
    
    conn = duckdb.connect(str(db_path))
    
    try:
        completed_count = auto_complete_projects(conn, dry_run)
        archived_count = auto_archive_projects(conn, dry_run)
        
        print("\n" + "=" * 60)
        print(f"Summary: {completed_count} completed, {archived_count} archived")
        
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Project lifecycle automation")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    
    args = parser.parse_args()
    run_lifecycle_automation(dry_run=args.dry_run)
