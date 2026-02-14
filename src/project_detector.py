#!/usr/bin/env python3
"""
AI Detection Engine for Project Tagging

Analyzes transactions and proposes draft projects based on three detection patterns:
1. Merchant Category Burst - Unusual spending frequency in specific categories
2. Keyword Matching - Travel/event/project keywords in merchant/description
3. Temporal Clustering - Bursts of transactions at the same merchant

Usage:
    python src/project_detector.py --lookback-days 60 --min-confidence 0.60 --dry-run
"""

import argparse
import duckdb
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config import get_db_path


# Detection patterns configuration
KEYWORD_PATTERNS = {
    "Travel": {
        "keywords": ["hotel", "flight", "airbnb", "vrbo", "airline", "resort", "booking", "tsa", "expedia"],
        "confidence": 0.75,
        "window_days": 30
    },
    "Events": {
        "keywords": ["wedding", "birthday", "conference", "convention", "festival", "concert", "party"],
        "confidence": 0.70,
        "window_days": 30
    },
    "Home Projects": {
        "keywords": ["renovation", "remodel", "moving", "contractor", "hardware", "home depot", "lowe"],
        "confidence": 0.65,
        "window_days": 45
    }
}


class ProjectDetector:
    """Analyzes transactions and detects potential projects"""
    
    def __init__(self, db_path: Path, lookback_days: int = 60, min_confidence: float = 0.60):
        self.db_path = db_path
        self.lookback_days = lookback_days
        self.min_confidence = min_confidence
        self.conn = duckdb.connect(str(db_path))
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def detect_all_patterns(self, dry_run: bool = False) -> List[Dict]:
        """Run all detection patterns and return proposed projects"""
        print(f"🔍 Analyzing transactions from the last {self.lookback_days} days...")
        print(f"   Minimum confidence threshold: {self.min_confidence}")
        print()
        
        proposals = []
        
        # Pattern 1: Merchant Category Burst
        print("🔍 Pattern 1: Merchant Category Burst")
        burst_proposals = self.detect_category_burst()
        proposals.extend(burst_proposals)
        print(f"   Found {len(burst_proposals)} proposals\n")
        
        # Pattern 2: Keyword Matching
        print("🔍 Pattern 2: Keyword Matching")
        keyword_proposals = self.detect_keyword_patterns()
        proposals.extend(keyword_proposals)
        print(f"   Found {len(keyword_proposals)} proposals\n")
        
        # Pattern 3: Temporal Clustering
        print("🔍 Pattern 3: Temporal Clustering")
        cluster_proposals = self.detect_temporal_clustering()
        proposals.extend(cluster_proposals)
        print(f"   Found {len(cluster_proposals)} proposals\n")
        
        # Filter by confidence threshold
        filtered_proposals = [p for p in proposals if p['confidence'] >= self.min_confidence]
        
        print(f"📊 Total proposals: {len(proposals)}")
        print(f"📊 After confidence filter: {len(filtered_proposals)}")
        print()
        
        if not dry_run and filtered_proposals:
            created = self.create_draft_projects(filtered_proposals)
            print(f"✅ Created {created} draft projects")
        elif dry_run:
            print("🔸 Dry run - no projects created")
            self._print_proposals(filtered_proposals)
        
        return filtered_proposals
    
    def detect_category_burst(self) -> List[Dict]:
        """Detect unusual frequency of spending in specific categories"""
        proposals = []
        
        # Calculate date range
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        # Get category spending patterns
        query = """
            WITH historical AS (
                -- Historical average (older than lookback period)
                SELECT 
                    category_group,
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT strftime(transaction_date, '%Y-%m')) as months,
                    COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT strftime(transaction_date, '%Y-%m')), 0) as avg_per_month
                FROM transactions
                WHERE transaction_date < ?
                    AND category_group IS NOT NULL
                    AND category_group != 'Transfer'
                    AND category_group != 'Income'
                    AND amount < 0
                GROUP BY category_group
                HAVING COUNT(*) >= 3
            ),
            recent AS (
                -- Recent period activity
                SELECT 
                    category_group,
                    COUNT(*) as recent_count,
                    MIN(transaction_date) as start_date,
                    MAX(transaction_date) as end_date,
                    ARRAY_AGG(id) as transaction_ids,
                    SUM(ABS(amount)) as total_amount
                FROM transactions
                WHERE transaction_date >= ?
                    AND category_group IS NOT NULL
                    AND category_group != 'Transfer'
                    AND category_group != 'Income'
                    AND amount < 0
                GROUP BY category_group
            )
            SELECT 
                r.category_group,
                r.recent_count,
                COALESCE(h.avg_per_month, 0) as historical_avg,
                r.start_date,
                r.end_date,
                r.transaction_ids,
                r.total_amount,
                r.recent_count * 1.0 / NULLIF(h.avg_per_month, 1) as burst_ratio
            FROM recent r
            LEFT JOIN historical h ON r.category_group = h.category_group
            WHERE r.recent_count >= 5
                AND (h.avg_per_month IS NULL OR r.recent_count > h.avg_per_month * 2)
            ORDER BY burst_ratio DESC
        """
        
        results = self.conn.execute(query, (cutoff_date, cutoff_date)).fetchall()
        
        for row in results:
            category_group, count, avg, start_date, end_date, txn_ids, total, ratio = row
            
            # Skip if similar project exists
            if self._similar_project_exists(category_group, start_date, end_date):
                continue
            
            # Calculate confidence based on burst ratio
            confidence = min(0.75, 0.60 + (ratio - 2.0) * 0.05)
            
            proposals.append({
                'name': f"{category_group} Project",
                'description': f"Detected unusual {category_group} spending activity",
                'pattern_type': 'category_burst',
                'confidence': round(confidence, 2),
                'reasoning': f"Found {count} transactions (historical avg: {avg:.1f}/month, {ratio:.1f}x increase)",
                'start_date': start_date,
                'end_date': end_date,
                'transaction_ids': txn_ids,
                'total_amount': float(total)
            })
        
        return proposals
    
    def detect_keyword_patterns(self) -> List[Dict]:
        """Detect travel/event/project keywords in merchant/description"""
        proposals = []
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        for pattern_name, config in KEYWORD_PATTERNS.items():
            keywords = config['keywords']
            window_days = config['window_days']
            base_confidence = config['confidence']
            
            # Build keyword search condition
            keyword_conditions = " OR ".join([
                f"LOWER(merchant) LIKE '%{kw}%' OR LOWER(description) LIKE '%{kw}%'"
                for kw in keywords
            ])
            
            query = f"""
                WITH matching_transactions AS (
                    SELECT 
                        id,
                        transaction_date,
                        merchant,
                        description,
                        amount,
                        category_group
                    FROM transactions
                    WHERE transaction_date >= ?
                        AND ({keyword_conditions})
                        AND amount < 0
                ),
                grouped AS (
                    -- Group transactions within window_days of each other
                    SELECT 
                        MIN(transaction_date) as start_date,
                        MAX(transaction_date) as end_date,
                        ARRAY_AGG(id) as transaction_ids,
                        COUNT(*) as txn_count,
                        SUM(ABS(amount)) as total_amount,
                        STRING_AGG(DISTINCT merchant, ', ') as merchants
                    FROM matching_transactions
                    GROUP BY 
                        -- Simple grouping: floor to window periods
                        (CAST(EPOCH(transaction_date) AS INTEGER) / ({window_days} * 86400))
                )
                SELECT * FROM grouped
                WHERE txn_count >= 3
                ORDER BY start_date DESC
            """
            
            results = self.conn.execute(query, (cutoff_date,)).fetchall()
            
            for row in results:
                start_date, end_date, txn_ids, count, total, merchants = row
                
                # Skip if similar project exists
                if self._similar_project_exists(pattern_name, start_date, end_date):
                    continue
                
                # Adjust confidence based on transaction count
                confidence = min(0.80, base_confidence + (count - 3) * 0.02)
                
                proposals.append({
                    'name': f"{pattern_name}: {start_date.strftime('%b %Y')}",
                    'description': f"Detected {pattern_name.lower()} activity based on keywords",
                    'pattern_type': 'keyword_match',
                    'confidence': round(confidence, 2),
                    'reasoning': f"Found {count} transactions matching {pattern_name.lower()} keywords: {merchants[:100]}",
                    'start_date': start_date,
                    'end_date': end_date,
                    'transaction_ids': txn_ids,
                    'total_amount': float(total)
                })
        
        return proposals
    
    def detect_temporal_clustering(self) -> List[Dict]:
        """Detect bursts of transactions at the same merchant"""
        proposals = []
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        query = """
            WITH merchant_activity AS (
                SELECT 
                    merchant,
                    transaction_date,
                    id,
                    amount
                FROM transactions
                WHERE transaction_date >= ?
                    AND merchant IS NOT NULL
                    AND merchant != 'Amazon'  -- Too generic
                    AND category_group NOT IN ('Transfer', 'Income')
                    AND amount < 0
            ),
            -- Historical baseline: how often do we normally visit this merchant?
            historical AS (
                SELECT 
                    merchant,
                    COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT strftime(transaction_date, '%Y-%m')), 0) as avg_per_month
                FROM transactions
                WHERE transaction_date < ?
                    AND merchant IS NOT NULL
                GROUP BY merchant
            ),
            -- Recent 14-day windows
            recent_clusters AS (
                SELECT 
                    m.merchant,
                    MIN(m.transaction_date) as start_date,
                    MAX(m.transaction_date) as end_date,
                    ARRAY_AGG(m.id) as transaction_ids,
                    COUNT(*) as txn_count,
                    SUM(ABS(m.amount)) as total_amount
                FROM merchant_activity m
                GROUP BY 
                    m.merchant,
                    -- Group by 14-day windows
                    (CAST(EPOCH(m.transaction_date) AS INTEGER) / (14 * 86400))
                HAVING COUNT(*) >= 3
            )
            SELECT 
                r.merchant,
                r.start_date,
                r.end_date,
                r.transaction_ids,
                r.txn_count,
                r.total_amount,
                COALESCE(h.avg_per_month, 0) as historical_avg
            FROM recent_clusters r
            LEFT JOIN historical h ON r.merchant = h.merchant
            WHERE 
                -- Either no history or significantly more than normal
                (h.avg_per_month IS NULL OR r.txn_count > h.avg_per_month * 1.5)
                AND r.txn_count >= 3
            ORDER BY r.txn_count DESC
        """
        
        results = self.conn.execute(query, (cutoff_date, cutoff_date)).fetchall()
        
        for row in results:
            merchant, start_date, end_date, txn_ids, count, total, avg = row
            
            # Skip if similar project exists
            if self._similar_project_exists(merchant, start_date, end_date):
                continue
            
            # Calculate confidence based on burst intensity
            burst_ratio = count / max(avg, 1)
            confidence = min(0.70, 0.55 + burst_ratio * 0.05)
            
            proposals.append({
                'name': f"{merchant} Activity",
                'description': f"Multiple transactions at {merchant} in short period",
                'pattern_type': 'temporal_cluster',
                'confidence': round(confidence, 2),
                'reasoning': f"Found {count} transactions in {(end_date - start_date).days + 1} days (normal: {avg:.1f}/month)",
                'start_date': start_date,
                'end_date': end_date,
                'transaction_ids': txn_ids,
                'total_amount': float(total)
            })
        
        return proposals
    
    def _similar_project_exists(self, name_hint: str, start_date: date, end_date: date) -> bool:
        """Check if a similar project already exists or was rejected"""
        # Check for date overlap and similar name
        query = """
            SELECT COUNT(*) 
            FROM projects
            WHERE status IN ('draft', 'active')
                AND (
                    -- Date range overlaps
                    (start_date <= ? AND (end_date IS NULL OR end_date >= ?))
                    OR (start_date >= ? AND start_date <= ?)
                )
                AND (
                    -- Similar name (contains key words)
                    LOWER(name) LIKE LOWER(?)
                )
        """
        
        # Extract key words from name hint
        key_words = f"%{name_hint.split()[0]}%"
        
        result = self.conn.execute(query, (
            end_date, start_date,  # Overlap check
            start_date, end_date,
            key_words
        )).fetchone()
        
        if result[0] > 0:
            return True
        
        # Check if similar pattern was rejected before
        rejection_query = """
            SELECT COUNT(*)
            FROM ai_learning_log al
            JOIN projects p ON al.project_id = p.id
            WHERE al.accepted = FALSE
                AND (
                    -- Date range overlaps
                    (p.start_date <= ? AND (p.end_date IS NULL OR p.end_date >= ?))
                    OR (p.start_date >= ? AND p.start_date <= ?)
                )
                AND LOWER(p.name) LIKE LOWER(?)
                AND al.feedback_date >= ?
        """
        
        # Only check rejections from the last 90 days
        lookback_date = date.today() - timedelta(days=90)
        
        rejection_result = self.conn.execute(rejection_query, (
            end_date, start_date,
            start_date, end_date,
            key_words,
            lookback_date
        )).fetchone()
        
        return rejection_result[0] > 0
    
    def create_draft_projects(self, proposals: List[Dict]) -> int:
        """Create draft projects from proposals"""
        created = 0
        
        for proposal in proposals:
            try:
                # Insert project
                insert_query = """
                    INSERT INTO projects (
                        name, description, status, start_date, end_date,
                        ai_suggested, ai_confidence, ai_reasoning
                    ) VALUES (?, ?, 'draft', ?, ?, TRUE, ?, ?)
                    RETURNING id
                """
                
                project_id = self.conn.execute(insert_query, (
                    proposal['name'],
                    proposal['description'],
                    proposal['start_date'],
                    proposal['end_date'],
                    proposal['confidence'],
                    proposal['reasoning']
                )).fetchone()[0]
                
                # Link transactions
                for txn_id in proposal['transaction_ids']:
                    self.conn.execute("""
                        INSERT INTO project_transactions (
                            project_id, transaction_id, status, match_reason, match_confidence
                        ) VALUES (?, ?, 'proposed', ?, ?)
                    """, (
                        project_id,
                        txn_id,
                        proposal['pattern_type'],
                        proposal['confidence']
                    ))
                
                self.conn.commit()
                created += 1
                print(f"✅ Created: {proposal['name']} ({proposal['confidence']} confidence)")
                
            except Exception as e:
                print(f"❌ Error creating project '{proposal['name']}': {e}")
                self.conn.rollback()
        
        return created
    
    def _print_proposals(self, proposals: List[Dict]):
        """Pretty-print proposals for dry run"""
        if not proposals:
            print("No proposals to display")
            return
        
        print("\n" + "="*80)
        print("PROPOSALS (Dry Run)")
        print("="*80)
        
        for i, p in enumerate(proposals, 1):
            print(f"\n{i}. {p['name']}")
            print(f"   Confidence: {p['confidence']} | Pattern: {p['pattern_type']}")
            print(f"   Period: {p['start_date']} to {p['end_date']}")
            print(f"   Transactions: {len(p['transaction_ids'])} | Total: ${p['total_amount']:.2f}")
            print(f"   Reasoning: {p['reasoning']}")
        
        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description="Detect potential projects from transactions")
    parser.add_argument("--lookback-days", type=int, default=60,
                        help="Number of days to look back (default: 60)")
    parser.add_argument("--min-confidence", type=float, default=0.60,
                        help="Minimum confidence threshold (default: 0.60)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't create projects, just show what would be created")
    
    args = parser.parse_args()
    
    # Validate args
    if args.lookback_days <= 0:
        print("Error: lookback-days must be positive")
        sys.exit(1)
    
    if not (0 <= args.min_confidence <= 1):
        print("Error: min-confidence must be between 0 and 1")
        sys.exit(1)
    
    # Run detection
    db_path = get_db_path()
    print(f"Database: {db_path}")
    print()
    
    detector = ProjectDetector(db_path, args.lookback_days, args.min_confidence)
    
    try:
        proposals = detector.detect_all_patterns(dry_run=args.dry_run)
    finally:
        detector.close()


if __name__ == "__main__":
    main()
