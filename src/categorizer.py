"""Transaction categorizer using merchant mappings"""

import duckdb
from typing import Dict, Optional, Tuple

def categorize_transaction(conn: duckdb.DuckDBPyConnection, description: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Match transaction description against merchant mappings
    
    Returns: (merchant, category, category_group) or (None, None, None) if no match
    """
    # Try to find a matching pattern
    result = conn.execute("""
        SELECT merchant, category, category_group
        FROM merchant_mappings
        WHERE ? LIKE '%' || pattern || '%'
        ORDER BY LENGTH(pattern) DESC
        LIMIT 1
    """, (description,)).fetchone()
    
    if result:
        return result[0], result[1], result[2]
    else:
        return None, None, None

def apply_categorization(conn: duckdb.DuckDBPyConnection, transaction: Dict) -> Dict:
    """Apply categorization to a transaction dict
    
    Adds: merchant, category, category_group, needs_review
    """
    merchant, category, category_group = categorize_transaction(conn, transaction['description'])
    
    transaction['merchant'] = merchant
    transaction['category'] = category
    transaction['category_group'] = category_group
    transaction['needs_review'] = merchant is None
    
    return transaction
