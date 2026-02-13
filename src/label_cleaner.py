#!/usr/bin/env python3
"""
Transaction Label Cleaning Pipeline

3-stage pipeline to clean and categorize transaction descriptions:
1. Normalize: Strip ACH noise, store numbers, city/state, prefixes
2. Pattern Match: Query merchant_mappings table (longest pattern wins)
3. LLM Classification: Use AI knowledge to identify unknown merchants

Usage:
    python src/label_cleaner.py --dry-run    # Preview changes without writing to DB
    python src/label_cleaner.py --apply      # Apply changes to database
"""

import re
import argparse
import duckdb
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

from config import get_db_path


# ============================================================================
# STAGE 1: NORMALIZATION
# ============================================================================

def normalize_description(desc: str) -> str:
    """
    Clean transaction description by removing noise patterns.
    
    Strips:
    - ACH noise (DES:, PPD, ID:, INDN:, CO ID:, WEB)
    - Store numbers (#0671, standalone 4-5 digit numbers)
    - Trailing city/state (LOS ANGELES CA)
    - Common prefixes (SQ *, TST *, DD *, DLO *)
    
    Args:
        desc: Raw transaction description
        
    Returns:
        Normalized description string
    """
    if not desc:
        return ""
    
    text = desc.strip()
    
    # Collapse multiple whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip ACH/payroll noise patterns
    text = re.sub(r'\bDES:[^\s]+', '', text)
    text = re.sub(r'\bID:\S+', '', text)
    text = re.sub(r'\bINDN:[^:]+(?=\s+CO\s+ID:|$)', '', text)
    text = re.sub(r'\bCO\s+ID:\S+', '', text)
    text = re.sub(r'\b(WEB|PPD)\b', '', text)
    
    # Strip store numbers (#XXXX or 4-5 digit standalone numbers)
    text = re.sub(r'#\d{4,5}', '', text)
    text = re.sub(r'\b\d{4,5}\b', '', text)
    
    # Strip trailing city/state patterns (CITY STATE)
    text = re.sub(r'\s+[A-Z][A-Z\s]+\s+[A-Z]{2}$', '', text)
    
    # Strip common prefixes
    for prefix in [r'SQ\s*\*\s*', r'TST\s*\*\s*', r'DD\s*\*\s*', r'DLO\s*\*\s*']:
        text = re.sub(f'^{prefix}', '', text, flags=re.IGNORECASE)
    
    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# ============================================================================
# STAGE 2: PATTERN MATCHING
# ============================================================================

def find_matching_pattern(
    conn: duckdb.DuckDBPyConnection, 
    description: str
) -> Optional[Tuple[str, str, str, str]]:
    """
    Find matching merchant mapping using database patterns.
    
    Uses LIKE matching and returns longest pattern match for specificity.
    
    Args:
        conn: Database connection
        description: Description to match (can be raw or normalized)
        
    Returns:
        (pattern, merchant, category, category_group) or None if no match
    """
    result = conn.execute("""
        SELECT pattern, merchant, category, category_group
        FROM merchant_mappings
        WHERE ? LIKE '%' || pattern || '%'
        ORDER BY LENGTH(pattern) DESC
        LIMIT 1
    """, (description,)).fetchone()
    
    if result:
        return result[0], result[1], result[2], result[3]
    return None


# ============================================================================
# STAGE 3: LLM CLASSIFICATION
# ============================================================================

def classify_with_llm(description: str) -> Optional[Tuple[str, str, str]]:
    """
    Use AI knowledge to classify unknown merchant descriptions.
    
    Context: User lives in Hawthorne CA, travels to France (Corsica), Spain 
    (Barcelona), Peru, Colombia, Mexico. Common merchants include highway tolls 
    (ESCOTA/VINCI = French highway, TUNELSPAN = Barcelona tunnel), transit 
    (TMB = Barcelona metro), visa services (TLS = TLScontact).
    
    Args:
        description: Normalized transaction description
        
    Returns:
        (merchant, category, category_group) or None if unidentifiable
    """
    desc_upper = description.upper()
    desc_lower = description.lower()
    
    # French highway tolls
    if any(x in desc_upper for x in ['ESCOTA', 'VINCI AUTOROUTE', 'SANEF', 'APRR']):
        return ('French Highway Toll', 'Tolls', 'Transportation')
    
    # Barcelona tunnel toll
    if 'TUNELSPAN' in desc_upper or 'TUNEL SPAN' in desc_upper:
        return ('Barcelona Tunnel Toll', 'Tolls', 'Transportation')
    
    # Barcelona metro
    if 'TMB' in desc_upper and any(x in desc_upper for x in ['BARCELONA', 'BCN', 'METRO']):
        return ('TMB Barcelona Metro', 'Public Transit', 'Transportation')
    
    # TLScontact (visa services)
    if 'TLS' in desc_upper and any(x in desc_lower for x in ['contact', 'visa', 'consular']):
        return ('TLScontact', 'Visa Services', 'Travel')
    
    # Corsica-specific merchants
    if 'AJACCIO' in desc_upper or 'BASTIA' in desc_upper or 'PORTO VECCHIO' in desc_upper:
        if any(x in desc_upper for x in ['CARREFOUR', 'SUPER U', 'LECLERC']):
            return ('Corsica Supermarket', 'Groceries', 'Food & Drink')
        return ('Corsica Merchant', 'Shopping', 'Shopping')
    
    # Common international patterns
    if 'MERCADONA' in desc_upper:
        return ('Mercadona', 'Groceries', 'Food & Drink')
    
    if 'CARREFOUR' in desc_upper:
        return ('Carrefour', 'Groceries', 'Food & Drink')
    
    if 'OXXO' in desc_upper:
        return ('OXXO', 'Convenience', 'Food & Drink')
    
    if 'METRO' in desc_upper and any(x in desc_upper for x in ['LIMA', 'CDMX', 'BARCELONA', 'MADRID']):
        return ('Metro Transit', 'Public Transit', 'Transportation')
    
    # Rideshare services
    if 'CABIFY' in desc_upper:
        return ('Cabify', 'Rideshare', 'Transportation')
    
    if 'BEAT' in desc_upper and 'RIDE' in desc_upper:
        return ('Beat', 'Rideshare', 'Transportation')
    
    # Airlines (common for international travel)
    if any(x in desc_upper for x in ['IBERIA', 'VUELING', 'AIR FRANCE', 'LATAM', 'AVIANCA']):
        for airline in ['IBERIA', 'VUELING', 'AIR FRANCE', 'LATAM', 'AVIANCA']:
            if airline in desc_upper:
                return (airline.title(), 'Airlines', 'Travel')
    
    # Pharmacies
    if any(x in desc_upper for x in ['FARMACIA', 'PHARMACIE', 'PHARMACY', 'CVS', 'WALGREENS']):
        return ('Pharmacy', 'Healthcare', 'Health')
    
    # Gas stations
    if any(x in desc_upper for x in ['SHELL', 'BP ', 'CHEVRON', 'TOTAL', 'REPSOL', 'CEPSA']):
        for station in ['SHELL', 'BP', 'CHEVRON', 'TOTAL', 'REPSOL', 'CEPSA']:
            if station in desc_upper:
                return (station.title(), 'Gas', 'Transportation')
    
    # Parking
    if 'PARKING' in desc_upper or 'APARCAMIENTO' in desc_upper:
        return ('Parking', 'Parking', 'Transportation')
    
    # Hawthorne CA area merchants
    if 'HAWTHORNE' in desc_upper:
        if 'RALPHS' in desc_upper or 'TRADER JOE' in desc_upper:
            return ('Hawthorne Grocery', 'Groceries', 'Food & Drink')
        return ('Hawthorne Merchant', 'Shopping', 'Shopping')
    
    # If truly unidentifiable, return None
    return None


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

def process_unmatched_transactions(
    conn: duckdb.DuckDBPyConnection,
    dry_run: bool = True
) -> Tuple[List[Dict], Dict]:
    """
    Run the 3-stage pipeline on unmatched transactions.
    
    Args:
        conn: Database connection
        dry_run: If True, don't write to database
        
    Returns:
        (new_mappings, stats) where:
            new_mappings: List of dicts with pattern, merchant, category, category_group
            stats: Dict with before/after counts
    """
    # Get unmatched distinct descriptions
    unmatched = conn.execute("""
        SELECT DISTINCT description
        FROM transactions
        WHERE merchant IS NULL
        ORDER BY description
    """).fetchall()
    
    total_unmatched = len(unmatched)
    
    print(f"📊 Found {total_unmatched} unmatched distinct descriptions")
    print(f"{'=' * 70}")
    
    # Track new mappings to add
    new_mappings = []
    seen_patterns = set()
    
    # Get existing patterns to avoid duplicates
    existing = conn.execute("SELECT pattern FROM merchant_mappings").fetchall()
    existing_patterns = {p[0] for p in existing}
    
    for (description,) in unmatched:
        # Stage 1: Normalize
        normalized = normalize_description(description)
        
        # Stage 2: Try pattern matching on normalized version
        match = find_matching_pattern(conn, normalized)
        
        if match:
            pattern, merchant, category, category_group = match
            print(f"✓ Matched via pattern: {description[:50]}")
            print(f"  → {merchant} ({category})")
            continue
        
        # Stage 3: LLM classification
        classification = classify_with_llm(normalized)
        
        if classification:
            merchant, category, category_group = classification
            
            # Use normalized description as pattern (avoid duplicates)
            pattern = normalized
            
            # Skip if pattern already exists or we've seen it this run
            if pattern in existing_patterns or pattern in seen_patterns:
                continue
            
            seen_patterns.add(pattern)
            
            new_mappings.append({
                'pattern': pattern,
                'merchant': merchant,
                'category': category,
                'category_group': category_group,
                'example': description
            })
            
            print(f"🤖 LLM classified: {description[:50]}")
            print(f"  → {merchant} ({category} / {category_group})")
        else:
            print(f"⚠️  Skipped (unidentifiable): {description[:50]}")
    
    print(f"{'=' * 70}")
    print(f"📈 Generated {len(new_mappings)} new mappings")
    
    stats = {
        'total_unmatched_before': total_unmatched,
        'new_mappings_count': len(new_mappings)
    }
    
    return new_mappings, stats


def apply_new_mappings(
    conn: duckdb.DuckDBPyConnection,
    new_mappings: List[Dict]
) -> int:
    """
    Insert new mappings into merchant_mappings table.
    
    Args:
        conn: Database connection
        new_mappings: List of mapping dicts
        
    Returns:
        Number of mappings inserted
    """
    if not new_mappings:
        return 0
    
    # Get next ID
    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM merchant_mappings").fetchone()[0]
    next_id = max_id + 1
    
    inserted = 0
    for i, mapping in enumerate(new_mappings):
        try:
            conn.execute("""
                INSERT INTO merchant_mappings (id, pattern, merchant, category, category_group, source)
                VALUES (?, ?, ?, ?, ?, 'llm')
            """, (
                next_id + i,
                mapping['pattern'],
                mapping['merchant'],
                mapping['category'],
                mapping['category_group']
            ))
            inserted += 1
        except Exception as e:
            print(f"⚠️  Failed to insert pattern '{mapping['pattern']}': {e}")
    
    conn.commit()
    return inserted


def recategorize_transactions(conn: duckdb.DuckDBPyConnection) -> int:
    """
    Re-run categorization on transactions with merchant = NULL.
    
    Args:
        conn: Database connection
        
    Returns:
        Number of transactions updated
    """
    # Update transactions using merchant_mappings
    result = conn.execute("""
        UPDATE transactions
        SET 
            merchant = mm.merchant,
            category = mm.category,
            category_group = mm.category_group,
            needs_review = FALSE
        FROM (
            SELECT 
                t.id as txn_id,
                mm.merchant,
                mm.category,
                mm.category_group
            FROM transactions t
            JOIN merchant_mappings mm 
                ON t.description LIKE '%' || mm.pattern || '%'
            WHERE t.merchant IS NULL
            AND mm.pattern IN (
                SELECT pattern
                FROM merchant_mappings
                ORDER BY LENGTH(pattern) DESC
            )
        ) mm
        WHERE transactions.id = mm.txn_id
    """).fetchone()
    
    conn.commit()
    
    # Return count of updated rows
    return result[0] if result else 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Clean and categorize transaction labels using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing to database'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes to database'
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")
    
    db_path = get_db_path()
    print(f"🗄️  Database: {db_path}\n")
    
    conn = duckdb.connect(str(db_path))
    
    # Get initial stats
    total_txns = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    unmatched_before = conn.execute("SELECT COUNT(*) FROM transactions WHERE merchant IS NULL").fetchone()[0]
    
    print(f"📊 Initial State:")
    print(f"   Total transactions: {total_txns:,}")
    print(f"   Unmatched: {unmatched_before:,}")
    print()
    
    # Run pipeline
    new_mappings, stats = process_unmatched_transactions(conn, dry_run=args.dry_run)
    
    if args.apply and new_mappings:
        print(f"\n💾 Applying changes to database...")
        
        # Insert new mappings
        inserted = apply_new_mappings(conn, new_mappings)
        print(f"   ✓ Inserted {inserted} new mappings")
        
        # Recategorize transactions
        updated = recategorize_transactions(conn)
        print(f"   ✓ Updated {updated} transactions")
        
        # Get final stats
        unmatched_after = conn.execute("SELECT COUNT(*) FROM transactions WHERE merchant IS NULL").fetchone()[0]
        
        print(f"\n{'=' * 70}")
        print(f"📈 Summary:")
        print(f"   Unmatched before: {unmatched_before:,}")
        print(f"   New mappings added: {inserted}")
        print(f"   Transactions updated: {updated}")
        print(f"   Unmatched after: {unmatched_after:,}")
        print(f"   Coverage improvement: {updated / total_txns * 100:.1f}%")
        print(f"{'=' * 70}")
        
    elif args.dry_run:
        print(f"\n🔍 Dry run complete - no changes written to database")
        print(f"   Run with --apply to save these {len(new_mappings)} new mappings")
    
    conn.close()


if __name__ == "__main__":
    main()
