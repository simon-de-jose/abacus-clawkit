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
    
    # Location hints for trip detection
    LOCATION_HINTS = {
        "France": ["paris", "avignon", "marseille", "french", "sncf", "france", "lyon", "nice", "cannes",
                   "musee", "jardin exotique", "matisse", "granet", "glanum", "calendal", "tholonet",
                   "hotel du centre", "radisson scandinavie", "cote d'azur", "provence"],
        "Spain": ["barcelona", "madrid", "spain", "espana", "iberia", "vueling", "montserrat",
                  "park guell", "casa batllo", "la pedrera", "sagrada", "metro barcelona", "arenas barcelona",
                  "avolta barcelona", "hertz spain"],
        "Mexico": ["oxxo", "mexico", "mex ", "puerto vallarta", "cdmx", "cancun", "guadalajara",
                   "san miguel", "guanajuato", "playa", "tulum", "bjx"],
        "Japan": ["tokyo", "japan", "shinkansen", "narita", "haneda", "konbini", "lawson", "7-eleven jp"],
        "UK": ["london", "heathrow", "gatwick", "british airways", "tfl", "oyster"],
        "Italy": ["roma", "rome", "milano", "venice", "firenze", "florence", "trenitalia"],
        "Generic Foreign": ["duty free", "airport", "forex", "currency exchange"]
    }
    
    # Advance booking merchants
    ADVANCE_MERCHANTS = ["booking.com", "airbnb", "vrbo", "expedia", "hotels.com",
                         "airline", "flight", "delta", "united", "american air", "southwest",
                         "kayak", "hopper", "travel insurance"]
    
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
        
        # Pattern 1: Smart Trip Detection (replaces generic travel category burst)
        print("🔍 Pattern 1: Smart Trip Detection")
        trip_proposals = self.detect_trips()
        proposals.extend(trip_proposals)
        print(f"   Found {len(trip_proposals)} trip proposals\n")
        
        # Pattern 2: Merchant Category Burst (excluding travel)
        print("🔍 Pattern 2: Merchant Category Burst (Non-Travel)")
        burst_proposals = self.detect_category_burst()
        proposals.extend(burst_proposals)
        print(f"   Found {len(burst_proposals)} proposals\n")
        
        # Pattern 3: Keyword Matching
        print("🔍 Pattern 3: Keyword Matching")
        keyword_proposals = self.detect_keyword_patterns()
        proposals.extend(keyword_proposals)
        print(f"   Found {len(keyword_proposals)} proposals\n")
        
        # Pattern 4: Temporal Clustering
        print("🔍 Pattern 4: Temporal Clustering")
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
        """Detect unusual frequency of spending in specific categories (excluding Travel)"""
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
                    AND category_group NOT IN ('Transfer', 'Income', 'Travel')
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
                    AND category_group NOT IN ('Transfer', 'Income', 'Travel')
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
    
    def detect_trips(self) -> List[Dict]:
        """Detect individual trips based on away periods and location detection"""
        proposals = []
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        # Step 1: Build home merchant baseline
        home_merchants_query = """
            SELECT DISTINCT merchant
            FROM transactions
            WHERE merchant IS NOT NULL
            GROUP BY merchant
            HAVING COUNT(DISTINCT strftime(transaction_date, '%Y-%m')) >= 3
                AND COUNT(*) >= 6
        """
        home_merchants = [row[0].lower() for row in self.conn.execute(home_merchants_query).fetchall()]
        
        if not home_merchants:
            print("   No home merchants identified - skipping trip detection")
            return proposals
        
        print(f"   Identified {len(home_merchants)} home merchants as baseline")
        
        # Step 2: Find away periods (3+ consecutive days without home merchants but with activity)
        # Get all transaction dates in the lookback period
        all_dates_query = """
            SELECT DISTINCT transaction_date
            FROM transactions
            WHERE transaction_date >= ?
                AND amount < 0
            ORDER BY transaction_date
        """
        all_dates = [row[0] for row in self.conn.execute(all_dates_query, (cutoff_date,)).fetchall()]
        
        if not all_dates:
            return proposals
        
        # For each date, check if it has home merchant activity
        away_periods = []
        current_away_start = None
        current_away_end = None
        
        for current_date in all_dates:
            # Check if this date has home merchant transactions
            home_check_query = """
                SELECT COUNT(*)
                FROM transactions
                WHERE transaction_date = ?
                    AND LOWER(merchant) IN ({})
            """.format(','.join(['?' for _ in home_merchants]))
            
            has_home = self.conn.execute(home_check_query, [current_date] + home_merchants).fetchone()[0] > 0
            
            # Check if this date has any non-home transactions
            non_home_check_query = """
                SELECT COUNT(*)
                FROM transactions
                WHERE transaction_date = ?
                    AND amount < 0
                    AND (merchant IS NULL OR LOWER(merchant) NOT IN ({}))
            """.format(','.join(['?' for _ in home_merchants]))
            
            has_non_home = self.conn.execute(non_home_check_query, [current_date] + home_merchants).fetchone()[0] > 0
            
            if not has_home and has_non_home:
                # We're in an away period
                if current_away_start is None:
                    current_away_start = current_date
                current_away_end = current_date
            else:
                # Back home or no activity
                if current_away_start is not None:
                    # Check if away period is 3+ days
                    days_away = (current_away_end - current_away_start).days + 1
                    if days_away >= 3:
                        away_periods.append({
                            'start_date': current_away_start,
                            'end_date': current_away_end
                        })
                    current_away_start = None
                    current_away_end = None
        
        # Close any remaining away period
        if current_away_start is not None:
            days_away = (current_away_end - current_away_start).days + 1
            if days_away >= 3:
                away_periods.append({
                    'start_date': current_away_start,
                    'end_date': current_away_end
                })
        
        # Step 2.5: Merge away periods that are close together (within 2 days)
        # This handles multi-destination trips where there might be brief home activity
        merged_periods = []
        if away_periods:
            current_merged = away_periods[0].copy()
            
            for period in away_periods[1:]:
                # Check if this period is within 2 days of the current merged period
                days_gap = (period['start_date'] - current_merged['end_date']).days
                
                if days_gap <= 3:  # 3 days or less gap (allows for 1-2 day home breaks)
                    # Merge into current period
                    current_merged['end_date'] = period['end_date']
                else:
                    # Save current and start new
                    merged_periods.append(current_merged)
                    current_merged = period.copy()
            
            # Don't forget the last one
            merged_periods.append(current_merged)
        
        away_periods = merged_periods
        print(f"   Found {len(away_periods)} potential away periods (after merging)")
        
        # Step 3: For each away period, detect locations and build trip proposal
        for period in away_periods:
            start_date = period['start_date']
            end_date = period['end_date']
            
            # Get all transactions during this period
            trip_txns_query = """
                SELECT id, merchant, description
                FROM transactions
                WHERE transaction_date BETWEEN ? AND ?
                    AND amount < 0
                    AND (merchant IS NULL OR LOWER(merchant) NOT IN ({}))
            """.format(','.join(['?' for _ in home_merchants]))
            
            trip_txns = self.conn.execute(trip_txns_query, [start_date, end_date] + home_merchants).fetchall()
            
            if len(trip_txns) < 3:
                continue  # Not enough transactions for a trip
            
            # Extract locations
            location_counts = {}
            for txn_id, merchant, description in trip_txns:
                text = f"{merchant or ''} {description or ''}".lower()
                
                for location, keywords in self.LOCATION_HINTS.items():
                    for keyword in keywords:
                        if keyword in text:
                            location_counts[location] = location_counts.get(location, 0) + 1
                            break  # Only count once per transaction per location
            
            # Determine top locations
            if location_counts:
                # Sort by count, take locations with significant matches
                sorted_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
                
                # Take top location(s) - include secondary if it has at least 30% of top location's count
                top_locations = [sorted_locations[0][0]]
                if len(sorted_locations) > 1:
                    threshold = sorted_locations[0][1] * 0.3
                    for loc, count in sorted_locations[1:]:
                        if count >= threshold and loc != "Generic Foreign":
                            top_locations.append(loc)
                
                # Remove "Generic Foreign" if we have specific locations
                if len(top_locations) > 1 and "Generic Foreign" in top_locations:
                    top_locations.remove("Generic Foreign")
            else:
                top_locations = []
            
            # Generate trip name
            trip_name = self.generate_trip_name(top_locations, start_date)
            
            # Get transaction IDs and total
            trip_txn_ids = [txn[0] for txn in trip_txns]
            
            total_query = """
                SELECT SUM(ABS(amount))
                FROM transactions
                WHERE id IN ({})
            """.format(','.join(['?' for _ in trip_txn_ids]))
            
            total_amount = float(self.conn.execute(total_query, trip_txn_ids).fetchone()[0] or 0)
            
            # Detect advance bookings for this trip
            advance_bookings = self.detect_advance_bookings(start_date, end_date, home_merchants)
            
            # Combine trip transactions with advance bookings
            all_txn_ids = trip_txn_ids + [ab['id'] for ab in advance_bookings]
            
            if advance_bookings:
                advance_total = sum(ab['amount'] for ab in advance_bookings)
                total_amount += advance_total
                print(f"   Found {len(advance_bookings)} advance bookings (${advance_total:.2f}) for {trip_name}")
            
            # Skip if similar project exists
            if self._similar_project_exists(trip_name, start_date, end_date):
                continue
            
            # Calculate confidence based on location detection and transaction count
            base_confidence = 0.70
            if top_locations and "Generic Foreign" not in top_locations:
                base_confidence = 0.75  # Higher confidence with specific location
            if len(all_txn_ids) >= 10:
                base_confidence += 0.05
            if len(all_txn_ids) >= 20:
                base_confidence += 0.05
            
            confidence = min(0.85, base_confidence)
            
            location_str = ", ".join(top_locations) if top_locations else "unknown location"
            reasoning = f"Found {len(trip_txn_ids)} transactions during away period to {location_str}"
            if advance_bookings:
                reasoning += f" (+ {len(advance_bookings)} advance bookings)"
            
            proposals.append({
                'name': trip_name,
                'description': f"Trip detected based on away period analysis",
                'pattern_type': 'smart_trip',
                'confidence': round(confidence, 2),
                'reasoning': reasoning,
                'start_date': start_date,
                'end_date': end_date,
                'transaction_ids': all_txn_ids,
                'total_amount': float(total_amount),
                'advance_bookings': advance_bookings  # For debugging
            })
        
        return proposals
    
    def detect_advance_bookings(self, trip_start: date, trip_end: date, home_merchants: List[str]) -> List[Dict]:
        """Find pre-trip bookings for a given trip"""
        advance_window_start = trip_start - timedelta(days=60)
        advance_window_end = trip_start - timedelta(days=1)
        
        if advance_window_end < advance_window_start:
            return []
        
        # Build merchant conditions
        advance_conditions = " OR ".join([
            f"LOWER(merchant) LIKE '%{merchant}%'" for merchant in self.ADVANCE_MERCHANTS
        ])
        
        query = f"""
            SELECT id, transaction_date, merchant, description, amount
            FROM transactions
            WHERE transaction_date BETWEEN ? AND ?
                AND amount < 0
                AND (
                    {advance_conditions}
                    OR LOWER(description) LIKE '%booking%'
                    OR LOWER(description) LIKE '%airbnb%'
                    OR category IN ('Hotels', 'Flights', 'Car Rental')
                    OR category_group = 'Travel'
                )
        """
        
        results = self.conn.execute(query, (advance_window_start, advance_window_end)).fetchall()
        
        advance_bookings = []
        for txn_id, txn_date, merchant, description, amount in results:
            # Calculate confidence based on proximity to trip
            days_before = (trip_start - txn_date).days
            
            if days_before <= 7:
                match_confidence = 0.75
            elif days_before <= 30:
                match_confidence = 0.60
            else:
                match_confidence = 0.45
            
            advance_bookings.append({
                'id': txn_id,
                'date': txn_date,
                'merchant': merchant,
                'amount': abs(float(amount)),
                'confidence': match_confidence,
                'days_before': days_before
            })
        
        return advance_bookings
    
    def generate_trip_name(self, locations: List[str], start_date: date) -> str:
        """Generate readable trip name"""
        if not locations:
            return f"Trip ({start_date.strftime('%b %Y')})"
        if len(locations) == 1:
            return f"{locations[0]} Trip ({start_date.strftime('%b %Y')})"
        return f"{' & '.join(locations)} Trip ({start_date.strftime('%b %Y')})"
    
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
                # For smart trips, we need to handle advance bookings separately
                if proposal['pattern_type'] == 'smart_trip' and 'advance_bookings' in proposal:
                    advance_booking_ids = {ab['id'] for ab in proposal['advance_bookings']}
                    
                    for txn_id in proposal['transaction_ids']:
                        # Check if this is an advance booking
                        if txn_id in advance_booking_ids:
                            # Find the booking to get its confidence
                            booking = next(ab for ab in proposal['advance_bookings'] if ab['id'] == txn_id)
                            self.conn.execute("""
                                INSERT INTO project_transactions (
                                    project_id, transaction_id, status, match_reason, match_confidence
                                ) VALUES (?, ?, 'proposed', 'advance_booking', ?)
                            """, (project_id, txn_id, booking['confidence']))
                        else:
                            # Regular trip transaction
                            self.conn.execute("""
                                INSERT INTO project_transactions (
                                    project_id, transaction_id, status, match_reason, match_confidence
                                ) VALUES (?, ?, 'proposed', ?, ?)
                            """, (project_id, txn_id, proposal['pattern_type'], proposal['confidence']))
                else:
                    # Non-trip proposals - use standard linking
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
