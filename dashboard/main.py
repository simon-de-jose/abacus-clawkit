"""Abacus Dashboard - FastAPI Backend"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import duckdb
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict
from calendar import monthrange

# Add parent src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import get_db_path

app = FastAPI(title="Abacus Dashboard")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = str(get_db_path())

# Serve static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    # Static folder doesn't exist yet - will be created in Phase 4
    pass


def get_db():
    """Get database connection (read-write to avoid DuckDB mixed-mode locking conflicts)"""
    return duckdb.connect(DB_PATH)


@app.get("/")
async def read_root():
    """Serve index.html"""
    return FileResponse("static/index.html")


@app.get("/transactions")
async def read_transactions():
    return FileResponse("static/transactions.html")


@app.get("/cashflow")
async def read_cashflow():
    return FileResponse("static/cashflow.html")


@app.get("/reports")
async def read_reports():
    return FileResponse("static/reports.html")


@app.get("/reports/cashflow")
async def read_reports_cashflow():
    return FileResponse("static/reports.html")


@app.get("/reports/spending")
async def read_reports_spending():
    return FileResponse("static/reports.html")


@app.get("/accounts")
async def read_accounts():
    return FileResponse("static/accounts.html")


@app.get("/api/overview")
async def get_overview(date_from: Optional[str] = None, date_to: Optional[str] = None):
    """Get overview stats for a date range (defaults to latest month with data)"""
    try:
        conn = get_db()
        
        if date_from and date_to:
            month_start = date.fromisoformat(date_from)
            month_end = date.fromisoformat(date_to)
        else:
            # Find the latest month with data
            latest = conn.execute("""
                SELECT MAX(transaction_date) FROM transactions
            """).fetchone()
            if latest and latest[0]:
                latest_date = latest[0]
                month_start = date(latest_date.year, latest_date.month, 1)
                _, last_day = monthrange(latest_date.year, latest_date.month)
                month_end = date(latest_date.year, latest_date.month, last_day)
            else:
                today = date.today()
                month_start = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                month_end = date(today.year, today.month, last_day)
        
        # Total spent (negative amounts = expenses, exclude transfers)
        result = conn.execute("""
            SELECT SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
        """, (month_start, month_end)).fetchone()
        total_spent = float(result[0]) if result[0] else 0.0
        
        # Total income (positive amounts)
        result = conn.execute("""
            SELECT SUM(amount) as total
            FROM transactions 
            WHERE amount > 0 
            AND transaction_date >= ? AND transaction_date <= ?
        """, (month_start, month_end)).fetchone()
        total_income = float(result[0]) if result[0] else 0.0
        
        # Net
        net = total_income - total_spent
        
        # Transaction count
        result = conn.execute("""
            SELECT COUNT(*) as count
            FROM transactions 
            WHERE transaction_date >= ? AND transaction_date <= ?
        """, (month_start, month_end)).fetchone()
        transaction_count = int(result[0])
        
        # Top categories (expenses only, exclude transfers)
        top_categories = conn.execute("""
            SELECT category, SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND category IS NOT NULL
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        """, (month_start, month_end)).fetchall()
        
        conn.close()
        
        month_label = month_start.strftime("%B %Y")
        
        return JSONResponse({
            "total_spent": round(total_spent, 2),
            "total_income": round(total_income, 2),
            "net": round(net, 2),
            "transaction_count": transaction_count,
            "month_label": month_label,
            "top_categories": [
                {"category": row[0], "amount": round(float(row[1]), 2)}
                for row in top_categories
            ]
        })
    except Exception as e:
        print(f"Error in /api/overview: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/overview/ytd")
async def get_overview_ytd():
    """Get Year-to-Date overview stats"""
    try:
        conn = get_db()
        # Get current year
        current_year = date.today().year
        year_start = date(current_year, 1, 1)
        
        # Total spent YTD (exclude transfers)
        result = conn.execute("""
            SELECT SUM(ABS(amount)) FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ?
        """, (year_start,)).fetchone()
        total_spent = float(result[0]) if result[0] else 0.0
        
        # Total income YTD
        result = conn.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE amount > 0 AND transaction_date >= ?
        """, (year_start,)).fetchone()
        total_income = float(result[0]) if result[0] else 0.0
        
        # Spending by category_group YTD (exclude transfers)
        # IMPORTANT: Include NULL categories as "Uncategorized"
        groups = conn.execute("""
            SELECT COALESCE(category_group, 'Uncategorized') as grp, SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ?
            GROUP BY grp
            ORDER BY total DESC
        """, (year_start,)).fetchall()
        
        # Count months with data for average
        months_result = conn.execute("""
            SELECT COUNT(DISTINCT DATE_TRUNC('month', transaction_date))
            FROM transactions WHERE transaction_date >= ?
        """, (year_start,)).fetchone()
        months_count = max(int(months_result[0]), 1)
        
        conn.close()
        return JSONResponse({
            "total_spent_ytd": round(total_spent, 2),
            "total_income_ytd": round(total_income, 2),
            "net_ytd": round(total_income - total_spent, 2),
            "avg_monthly_spend": round(total_spent / months_count, 2),
            "months_counted": months_count,
            "year": current_year,
            "spending_by_group": [
                {"group": row[0], "amount": round(float(row[1]), 2)}
                for row in groups
            ]
        })
    except Exception as e:
        print(f"Error in /api/overview/ytd: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/transactions")
async def get_transactions(
    search: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    per_page: int = 50
):
    """Get paginated, filterable transactions"""
    try:
        conn = get_db()
        
        # Build WHERE clauses
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(description LIKE ? OR merchant LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if category:
            where_clauses.append("category = ?")
            params.append(category)
        
        if date_from:
            where_clauses.append("transaction_date >= ?")
            params.append(date_from)
        
        if date_to:
            where_clauses.append("transaction_date <= ?")
            params.append(date_to)
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_result = conn.execute(f"""
            SELECT COUNT(*) FROM transactions {where_sql}
        """, params).fetchone()
        total = int(count_result[0])
        
        # Get paginated results
        offset = (page - 1) * per_page
        transactions = conn.execute(f"""
            SELECT 
                id, transaction_date, post_date, description, merchant,
                category, category_group, type, amount, account_id, 
                needs_review, memo
            FROM transactions 
            {where_sql}
            ORDER BY transaction_date DESC, post_date DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()
        
        conn.close()
        
        return JSONResponse({
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "transactions": [
                {
                    "id": row[0],
                    "transaction_date": str(row[1]),
                    "post_date": str(row[2]) if row[2] else None,
                    "description": row[3],
                    "merchant": row[4],
                    "category": row[5],
                    "category_group": row[6],
                    "type": row[7],
                    "amount": float(row[8]),
                    "account_id": row[9],
                    "needs_review": bool(row[10]),
                    "memo": row[11]
                }
                for row in transactions
            ]
        })
    except Exception as e:
        print(f"Error in /api/transactions: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/categories/spending")
async def get_category_spending(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get spending breakdown by category and category_group"""
    try:
        conn = get_db()
        
        # Default to latest month with data if no dates provided
        if not date_from or not date_to:
            conn_temp = get_db()
            latest = conn_temp.execute("SELECT MAX(transaction_date) FROM transactions").fetchone()
            conn_temp.close()
            if latest and latest[0]:
                ld = latest[0]
                date_from = date(ld.year, ld.month, 1)
                _, last_day = monthrange(ld.year, ld.month)
                date_to = date(ld.year, ld.month, last_day)
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                date_to = date(today.year, today.month, last_day)
        
        result = conn.execute("""
            SELECT 
                category_group, 
                category, 
                SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND category IS NOT NULL
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY category_group, category
            ORDER BY total DESC
        """, (date_from, date_to)).fetchall()
        
        conn.close()
        
        return JSONResponse({
            "categories": [
                {
                    "category_group": row[0],
                    "category": row[1],
                    "amount": round(float(row[2]), 2)
                }
                for row in result
            ]
        })
    except Exception as e:
        print(f"Error in /api/categories/spending: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/cashflow")
async def get_cashflow(months: int = 12):
    """Get monthly income vs expenses for last N months"""
    try:
        conn = get_db()
        
        result = conn.execute(f"""
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 AND (is_transfer IS NULL OR is_transfer = FALSE) THEN ABS(amount) ELSE 0 END) as expenses
            FROM transactions 
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
            GROUP BY DATE_TRUNC('month', transaction_date)
            ORDER BY month DESC
            LIMIT {months}
        """).fetchall()
        
        conn.close()
        
        return JSONResponse({
            "cashflow": [
                {
                    "month": str(row[0])[:10],
                    "income": round(float(row[1]), 2),
                    "expenses": round(float(row[2]), 2),
                    "net": round(float(row[1]) - float(row[2]), 2)
                }
                for row in result
            ]
        })
    except Exception as e:
        print(f"Error in /api/cashflow: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/cashflow/sankey")
async def get_sankey(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get Sankey diagram data: Income -> Category Groups -> Categories"""
    try:
        conn = get_db()
        
        # Default to latest month with data
        if not date_from or not date_to:
            conn_temp = get_db()
            latest = conn_temp.execute("SELECT MAX(transaction_date) FROM transactions").fetchone()
            conn_temp.close()
            if latest and latest[0]:
                ld = latest[0]
                date_from = date(ld.year, ld.month, 1)
                _, last_day = monthrange(ld.year, ld.month)
                date_to = date(ld.year, ld.month, last_day)
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                date_to = date(today.year, today.month, last_day)
        
        # Get income by category
        income_data = conn.execute("""
            SELECT COALESCE(category, 'Uncategorized'), SUM(amount) as total
            FROM transactions 
            WHERE amount > 0 
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY category
        """, (date_from, date_to)).fetchall()
        
        # Get expenses by category group and category (exclude transfers)
        expenses_data = conn.execute("""
            SELECT 
                COALESCE(category_group, 'Uncategorized') as grp,
                COALESCE(category, 'Uncategorized') as cat,
                SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY grp, cat
        """, (date_from, date_to)).fetchall()
        
        conn.close()
        
        # Build Sankey: Income → Category Groups → Categories
        # Use prefixed names to avoid collisions (e.g., "Shopping" as group vs category)
        nodes = []
        links = []
        node_set = set()
        
        def add_node(name):
            if name not in node_set:
                node_set.add(name)
                nodes.append({"name": name})
        
        # Total expenses node
        add_node("Total Spending")
        
        # Aggregate expenses by group first
        group_totals = {}
        for row in expenses_data:
            group = row[0] or "Uncategorized"
            amount = float(row[2])
            group_totals[group] = group_totals.get(group, 0) + amount
        
        # Add group nodes and links from Total Spending → Groups
        for group, total in sorted(group_totals.items(), key=lambda x: -x[1]):
            add_node(group)
            links.append({
                "source": "Total Spending",
                "target": group,
                "value": round(total, 2)
            })
        
        # Add category nodes and links from Groups → Categories
        for row in expenses_data:
            group = row[0] or "Uncategorized"
            category = row[1]
            amount = float(row[2])
            
            if not category:
                continue
            
            # Avoid self-links when category name == group name
            display_cat = category if category != group else f"{category} (items)"
            add_node(display_cat)
            links.append({
                "source": group,
                "target": display_cat,
                "value": round(amount, 2)
            })
        
        return JSONResponse({
            "nodes": nodes,
            "links": links
        })
    except Exception as e:
        print(f"Error in /api/cashflow/sankey: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/merchants/top")
async def get_top_merchants(
    limit: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get top merchants by total spend"""
    try:
        conn = get_db()
        
        # Default to latest month with data
        if not date_from or not date_to:
            conn_temp = get_db()
            latest = conn_temp.execute("SELECT MAX(transaction_date) FROM transactions").fetchone()
            conn_temp.close()
            if latest and latest[0]:
                ld = latest[0]
                date_from = date(ld.year, ld.month, 1)
                _, last_day = monthrange(ld.year, ld.month)
                date_to = date(ld.year, ld.month, last_day)
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                date_to = date(today.year, today.month, last_day)
        
        result = conn.execute("""
            SELECT merchant, SUM(ABS(amount)) as total, COUNT(*) as count
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND merchant IS NOT NULL
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY merchant
            ORDER BY total DESC
            LIMIT ?
        """, (date_from, date_to, limit)).fetchall()
        
        conn.close()
        
        return JSONResponse({
            "merchants": [
                {
                    "merchant": row[0],
                    "total": round(float(row[1]), 2),
                    "count": int(row[2])
                }
                for row in result
            ]
        })
    except Exception as e:
        print(f"Error in /api/merchants/top: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/reports/trends")
async def get_trends(months: int = 6):
    """Get spending by category over time (monthly)"""
    try:
        conn = get_db()
        
        result = conn.execute(f"""
            SELECT 
                DATE_TRUNC('month', transaction_date) as month,
                category,
                SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND category IS NOT NULL
            AND transaction_date >= CURRENT_DATE - INTERVAL '{months} months'
            GROUP BY DATE_TRUNC('month', transaction_date), category
            ORDER BY month DESC, total DESC
        """).fetchall()
        
        conn.close()
        
        # Group by month
        trends = {}
        for row in result:
            month = str(row[0])[:10]
            category = row[1]
            amount = round(float(row[2]), 2)
            
            if month not in trends:
                trends[month] = {}
            trends[month][category] = amount
        
        return JSONResponse({
            "trends": trends
        })
    except Exception as e:
        print(f"Error in /api/reports/trends: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class CategoryUpdate(BaseModel):
    category: str
    category_group: str


@app.put("/api/transactions/{transaction_id}/category")
async def update_transaction_category(transaction_id: str, update: CategoryUpdate):
    """Update transaction category"""
    try:
        conn = duckdb.connect(DB_PATH)  # Need write access
        
        # Check if transaction exists
        result = conn.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Update category
        conn.execute("""
            UPDATE transactions 
            SET category = ?, category_group = ?, needs_review = FALSE
            WHERE id = ?
        """, (update.category, update.category_group, transaction_id))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({"success": True})
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in PUT /api/transactions/{transaction_id}/category: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/accounts")
async def get_accounts():
    """Get account list with last import info"""
    try:
        conn = get_db()
        
        accounts = conn.execute("""
            SELECT 
                a.id, a.name, a.bank, a.last_four, a.type,
                COUNT(t.id) as transaction_count,
                MAX(t.transaction_date) as last_transaction
            FROM accounts a
            LEFT JOIN transactions t ON a.id = t.account_id
            GROUP BY a.id, a.name, a.bank, a.last_four, a.type
        """).fetchall()
        
        # Get import history
        imports = conn.execute("""
            SELECT filename, rows_imported, rows_skipped, imported_at
            FROM import_log
            ORDER BY imported_at DESC
        """).fetchall()
        
        conn.close()
        
        return JSONResponse({
            "accounts": [
                {
                    "id": row[0],
                    "name": row[1],
                    "bank": row[2],
                    "last_four": row[3],
                    "type": row[4],
                    "transaction_count": int(row[5]),
                    "last_transaction": str(row[6]) if row[6] else None
                }
                for row in accounts
            ],
            "imports": [
                {
                    "filename": row[0],
                    "rows_imported": int(row[1]),
                    "rows_skipped": int(row[2]),
                    "imported_at": str(row[3])
                }
                for row in imports
            ]
        })
    except Exception as e:
        print(f"Error in /api/accounts: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/categories")
async def get_categories():
    """Get all categories for dropdowns"""
    try:
        from config import get_category_taxonomy
        
        taxonomy = get_category_taxonomy()
        
        # Flatten into list
        categories = []
        for group, cats in taxonomy.items():
            for cat in cats:
                categories.append({
                    "category": cat,
                    "category_group": group
                })
        
        return JSONResponse({"categories": categories})
    except Exception as e:
        print(f"Error in /api/categories: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/reports/cashflow-sankey")
async def get_cashflow_sankey_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get enhanced Sankey data for Cash Flow report with summary stats"""
    try:
        conn = get_db()
        
        # Default to current month
        if not date_from or not date_to:
            conn_temp = get_db()
            latest = conn_temp.execute("SELECT MAX(transaction_date) FROM transactions").fetchone()
            conn_temp.close()
            if latest and latest[0]:
                ld = latest[0]
                date_from = date(ld.year, ld.month, 1)
                _, last_day = monthrange(ld.year, ld.month)
                date_to = date(ld.year, ld.month, last_day)
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                date_to = date(today.year, today.month, last_day)
        
        # Get income by category (income sources)
        income_data = conn.execute("""
            SELECT COALESCE(category, 'Other Income'), SUM(amount) as total
            FROM transactions 
            WHERE amount > 0 
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY category
        """, (date_from, date_to)).fetchall()
        
        # Get expenses by category group and category (exclude transfers)
        expenses_data = conn.execute("""
            SELECT 
                COALESCE(category_group, 'Uncategorized') as grp,
                COALESCE(category, 'Other') as cat,
                SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
            GROUP BY grp, cat
        """, (date_from, date_to)).fetchall()
        
        # Summary stats
        total_income_result = conn.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE amount > 0 
            AND transaction_date >= ? AND transaction_date <= ?
        """, (date_from, date_to)).fetchone()
        total_income = float(total_income_result[0]) if total_income_result[0] else 0.0
        
        total_expenses_result = conn.execute("""
            SELECT SUM(ABS(amount)) FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
        """, (date_from, date_to)).fetchone()
        total_expenses = float(total_expenses_result[0]) if total_expenses_result[0] else 0.0
        
        conn.close()
        
        # Build Sankey nodes and links
        # Flow: Income sources → "Income" → Category Groups → Categories
        nodes = []
        links = []
        node_set = set()
        
        def add_node(name):
            if name not in node_set:
                node_set.add(name)
                nodes.append({"name": name})
        
        # Add "Income" aggregate node
        add_node("Income")
        
        # Income sources → Income
        for row in income_data:
            source = row[0]
            amount = float(row[1])
            add_node(source)
            links.append({
                "source": source,
                "target": "Income",
                "value": round(amount, 2)
            })
        
        # Aggregate expenses by group
        group_totals = {}
        for row in expenses_data:
            group = row[0]
            amount = float(row[2])
            group_totals[group] = group_totals.get(group, 0) + amount
        
        # Income → Category Groups
        for group, total in sorted(group_totals.items(), key=lambda x: -x[1]):
            add_node(group)
            links.append({
                "source": "Income",
                "target": group,
                "value": round(total, 2)
            })
        
        # Category Groups → Categories
        for row in expenses_data:
            group = row[0]
            category = row[1]
            amount = float(row[2])
            
            # Avoid self-links
            display_cat = category if category != group else f"{category} (items)"
            add_node(display_cat)
            links.append({
                "source": group,
                "target": display_cat,
                "value": round(amount, 2)
            })
        
        net_income = total_income - total_expenses
        savings_rate = (net_income / total_income * 100) if total_income > 0 else 0
        
        return JSONResponse({
            "nodes": nodes,
            "links": links,
            "summary": {
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "net_income": round(net_income, 2),
                "savings_rate": round(savings_rate, 1)
            }
        })
    except Exception as e:
        print(f"Error in /api/reports/cashflow-sankey: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/reports/spending-summary")
async def get_spending_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Get spending summary stats for the Spending tab"""
    try:
        conn = get_db()
        
        # Default to current month
        if not date_from or not date_to:
            conn_temp = get_db()
            latest = conn_temp.execute("SELECT MAX(transaction_date) FROM transactions").fetchone()
            conn_temp.close()
            if latest and latest[0]:
                ld = latest[0]
                date_from = date(ld.year, ld.month, 1)
                _, last_day = monthrange(ld.year, ld.month)
                date_to = date(ld.year, ld.month, last_day)
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
                _, last_day = monthrange(today.year, today.month)
                date_to = date(today.year, today.month, last_day)
        
        # Total transactions (expenses only, exclude transfers)
        count_result = conn.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
        """, (date_from, date_to)).fetchone()
        total_transactions = int(count_result[0])
        
        # Largest transaction
        largest_result = conn.execute("""
            SELECT merchant, ABS(amount) as amt
            FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
            ORDER BY amt DESC
            LIMIT 1
        """, (date_from, date_to)).fetchone()
        largest_merchant = largest_result[0] if largest_result else "—"
        largest_amount = float(largest_result[1]) if largest_result else 0.0
        
        # Average transaction
        avg_result = conn.execute("""
            SELECT AVG(ABS(amount)) FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
        """, (date_from, date_to)).fetchone()
        average_transaction = float(avg_result[0]) if avg_result and avg_result[0] else 0.0
        
        # Total spending
        total_result = conn.execute("""
            SELECT SUM(ABS(amount)) FROM transactions 
            WHERE amount < 0 
            AND (is_transfer IS NULL OR is_transfer = FALSE)
            AND transaction_date >= ? AND transaction_date <= ?
        """, (date_from, date_to)).fetchone()
        total_spending = float(total_result[0]) if total_result and total_result[0] else 0.0
        
        conn.close()
        
        return JSONResponse({
            "total_transactions": total_transactions,
            "largest_merchant": largest_merchant,
            "largest_amount": round(largest_amount, 2),
            "average_transaction": round(average_transaction, 2),
            "total_spending": round(total_spending, 2)
        })
    except Exception as e:
        print(f"Error in /api/reports/spending-summary: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/transactions/export")
async def export_transactions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None
):
    """Export transactions as CSV"""
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        conn = get_db()
        
        # Build WHERE clauses
        where_clauses = []
        params = []
        
        if date_from:
            where_clauses.append("transaction_date >= ?")
            params.append(date_from)
        
        if date_to:
            where_clauses.append("transaction_date <= ?")
            params.append(date_to)
        
        if category:
            where_clauses.append("category = ?")
            params.append(category)
        
        # Default to expenses only
        where_clauses.append("amount < 0")
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        transactions = conn.execute(f"""
            SELECT 
                transaction_date, merchant, description, category, 
                category_group, ABS(amount) as amount, account_id
            FROM transactions 
            {where_sql}
            ORDER BY transaction_date DESC
        """, params).fetchall()
        
        conn.close()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Merchant', 'Description', 'Category', 'Category Group', 'Amount', 'Account'])
        
        for row in transactions:
            writer.writerow([
                str(row[0]),
                row[1] or '',
                row[2] or '',
                row[3] or '',
                row[4] or '',
                f"{row[5]:.2f}",
                row[6] or ''
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=transactions_{date_from or 'all'}_{date_to or 'all'}.csv"
            }
        )
    except Exception as e:
        print(f"Error in /api/transactions/export: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========================================
# TRANSACTION REVIEW FEATURE ENDPOINTS
# ========================================

@app.get("/review")
async def read_review():
    """Serve review.html"""
    return FileResponse("static/review.html")


@app.get("/categories")
async def read_categories_page():
    """Serve categories.html"""
    return FileResponse("static/categories.html")


@app.get("/api/review")
async def get_review_transactions(
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "amount",  # amount | date
    account_id: Optional[str] = None
):
    """Get paginated unreviewed transactions"""
    try:
        conn = get_db()
        
        # Build WHERE clauses
        where_clauses = ["review_status = 'suggested'", "(is_transfer = FALSE OR is_transfer IS NULL)"]
        params = []
        
        if account_id:
            where_clauses.append("account_id = ?")
            params.append(account_id)
        
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Determine sort
        if sort_by == "date":
            order_sql = "ORDER BY transaction_date DESC"
        elif sort_by == "date_asc":
            order_sql = "ORDER BY transaction_date ASC"
        else:  # amount (default)
            order_sql = "ORDER BY ABS(amount) DESC"
        
        # Get total count
        count_result = conn.execute(f"""
            SELECT COUNT(*) FROM transactions {where_sql}
        """, params).fetchone()
        total = int(count_result[0])
        
        # Get paginated results
        offset = (page - 1) * per_page
        transactions = conn.execute(f"""
            SELECT 
                id, transaction_date, description, merchant,
                category, category_group, amount, account_id
            FROM transactions 
            {where_sql}
            {order_sql}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()
        
        # Get review stats
        stats = conn.execute("""
            SELECT 
                COUNT(CASE WHEN review_status = 'suggested' AND (is_transfer IS NULL OR is_transfer = FALSE) THEN 1 END) as pending,
                COUNT(CASE WHEN review_status = 'confirmed' THEN 1 END) as confirmed,
                COUNT(CASE WHEN review_status = 'corrected' THEN 1 END) as corrected,
                COUNT(CASE WHEN is_transfer = TRUE THEN 1 END) as transfers
            FROM transactions
        """).fetchone()
        
        conn.close()
        
        return JSONResponse({
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "transactions": [
                {
                    "id": row[0],
                    "transaction_date": str(row[1]),
                    "description": row[2],
                    "merchant": row[3],
                    "category": row[4],
                    "category_group": row[5],
                    "amount": float(row[6]),
                    "account_id": row[7]
                }
                for row in transactions
            ],
            "stats": {
                "pending": int(stats[0]),
                "confirmed": int(stats[1]),
                "corrected": int(stats[2]),
                "transfers": int(stats[3])
            }
        })
    except Exception as e:
        print(f"Error in /api/review: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class ReviewConfirmRequest(BaseModel):
    pass  # No body needed, just confirms current state


@app.post("/api/transactions/{transaction_id}/review")
async def confirm_transaction(transaction_id: str, request: Optional[ReviewConfirmRequest] = None):
    """Confirm a transaction (accept current category)"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Check if transaction exists
        result = conn.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Set review_status to confirmed
        conn.execute("""
            UPDATE transactions 
            SET review_status = 'confirmed'
            WHERE id = ?
        """, (transaction_id,))
        
        # Get updated transaction
        updated = conn.execute("""
            SELECT id, transaction_date, description, merchant, category, 
                   category_group, amount, account_id, review_status
            FROM transactions 
            WHERE id = ?
        """, (transaction_id,)).fetchone()
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "transaction": {
                "id": updated[0],
                "transaction_date": str(updated[1]),
                "description": updated[2],
                "merchant": updated[3],
                "category": updated[4],
                "category_group": updated[5],
                "amount": float(updated[6]),
                "account_id": updated[7],
                "review_status": updated[8]
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in POST /api/transactions/{transaction_id}/review: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class CorrectCategoryRequest(BaseModel):
    category_id: str
    apply_to_similar: bool = False


@app.post("/api/transactions/{transaction_id}/correct")
async def correct_transaction(transaction_id: str, request: CorrectCategoryRequest):
    """Change category and auto-learn from the transaction"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Get the category details
        category_result = conn.execute("""
            SELECT c.name, c.group_id, g.name as group_name
            FROM categories c
            JOIN category_groups g ON c.group_id = g.id
            WHERE c.id = ?
        """, (request.category_id,)).fetchone()
        
        if not category_result:
            conn.close()
            raise HTTPException(status_code=404, detail="Category not found")
        
        category_name, group_id, group_name = category_result
        
        # Get the transaction details
        txn = conn.execute("""
            SELECT id, description, merchant FROM transactions WHERE id = ?
        """, (transaction_id,)).fetchone()
        
        if not txn:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        txn_id, description, merchant = txn
        
        # Extract pattern from description (strip trailing numbers, amounts, etc.)
        import re
        pattern = re.sub(r'\s*\d+$', '', description)  # Remove trailing digits
        pattern = re.sub(r'\s*#\d+$', '', pattern)    # Remove trailing #123
        pattern = pattern.strip()
        
        # Use merchant if available, otherwise use cleaned description
        merchant_name = merchant or pattern
        
        # Update the transaction
        conn.execute("""
            UPDATE transactions 
            SET category = ?, 
                category_group = ?,
                review_status = 'corrected'
            WHERE id = ?
        """, (category_name, group_name, transaction_id))
        
        # Create or update merchant mapping
        mapping_created = False
        if pattern and merchant_name:
            # Check if mapping exists
            existing = conn.execute("""
                SELECT id FROM merchant_mappings WHERE pattern = ?
            """, (pattern,)).fetchone()
            
            if existing:
                # Update existing mapping
                conn.execute("""
                    UPDATE merchant_mappings 
                    SET category = ?, category_group = ?, merchant = ?
                    WHERE pattern = ?
                """, (category_name, group_name, merchant_name, pattern))
            else:
                # Get next ID for merchant_mappings
                max_id_result = conn.execute("""
                    SELECT COALESCE(MAX(id), 0) + 1 FROM merchant_mappings
                """).fetchone()
                next_id = max_id_result[0]
                
                # Create new mapping
                conn.execute("""
                    INSERT INTO merchant_mappings (id, pattern, merchant, category, category_group)
                    VALUES (?, ?, ?, ?, ?)
                """, (next_id, pattern, merchant_name, category_name, group_name))
                mapping_created = True
        
        updated_count = 1
        
        # Apply to similar transactions if requested
        if request.apply_to_similar and pattern:
            result = conn.execute("""
                UPDATE transactions
                SET category = ?,
                    category_group = ?,
                    review_status = 'corrected'
                WHERE UPPER(description) LIKE '%' || UPPER(?) || '%'
                AND review_status = 'suggested'
                AND id != ?
            """, (category_name, group_name, pattern, transaction_id))
            
            # Get count of updated rows (DuckDB returns affected rows)
            updated_count += result.fetchone()[0] if result else 0
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "updated_count": updated_count,
            "mapping_created": mapping_created,
            "pattern": pattern
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in POST /api/transactions/{transaction_id}/correct: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/transactions/{transaction_id}/transfer")
async def mark_as_transfer(transaction_id: str):
    """Mark a transaction as a transfer"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Get the transaction
        txn = conn.execute("""
            SELECT id, amount, transaction_date, account_id
            FROM transactions WHERE id = ?
        """, (transaction_id,)).fetchone()
        
        if not txn:
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        txn_id, amount, txn_date, account_id = txn
        
        # Mark as transfer
        conn.execute("""
            UPDATE transactions 
            SET is_transfer = TRUE, review_status = 'confirmed'
            WHERE id = ?
        """, (transaction_id,))
        
        # Try to find a matching transaction to pair
        pairs = conn.execute("""
            SELECT id
            FROM transactions
            WHERE ABS(ABS(amount) - ABS(?)) < 0.01
            AND amount * ? < 0
            AND account_id != ?
            AND ABS(DATEDIFF('day', transaction_date, ?)) <= 3
            AND is_transfer = TRUE
            AND transfer_pair_id IS NULL
            AND id != ?
            LIMIT 1
        """, (amount, amount, account_id, txn_date, transaction_id)).fetchone()
        
        pair_id = None
        if pairs:
            pair_id = pairs[0]
            # Link both transactions
            conn.execute("""
                UPDATE transactions
                SET transfer_pair_id = ?
                WHERE id IN (?, ?)
            """, (transaction_id, transaction_id, pair_id))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "paired": pair_id is not None,
            "pair_id": pair_id
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in POST /api/transactions/{transaction_id}/transfer: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class BatchReviewRequest(BaseModel):
    transaction_ids: List[str]


@app.post("/api/transactions/batch-review")
async def batch_review(request: BatchReviewRequest):
    """Bulk confirm transactions"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Update all transactions in the list
        placeholders = ','.join(['?' for _ in request.transaction_ids])
        conn.execute(f"""
            UPDATE transactions 
            SET review_status = 'confirmed'
            WHERE id IN ({placeholders})
        """, request.transaction_ids)
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "count": len(request.transaction_ids)
        })
    except Exception as e:
        print(f"Error in POST /api/transactions/batch-review: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/categories/all")
async def get_all_categories():
    """Get full category list with groups, icons, colors, and usage stats"""
    try:
        conn = get_db()
        
        # Get all category groups
        groups = conn.execute("""
            SELECT id, name, icon, color, sort_order
            FROM category_groups
            ORDER BY sort_order, name
        """).fetchall()
        
        # Get all categories with usage count
        categories = conn.execute("""
            SELECT 
                c.id, c.name, c.icon, c.color, c.group_id, c.type, c.sort_order, c.hidden,
                COUNT(t.id) as usage_count
            FROM categories c
            LEFT JOIN transactions t ON c.name = t.category
            GROUP BY c.id, c.name, c.icon, c.color, c.group_id, c.type, c.sort_order, c.hidden
            ORDER BY c.sort_order, c.name
        """).fetchall()
        
        conn.close()
        
        # Build nested structure
        groups_with_categories = []
        for group in groups:
            group_id, name, icon, color, sort_order = group
            group_cats = [
                {
                    "id": cat[0],
                    "name": cat[1],
                    "icon": cat[2],
                    "color": cat[3],
                    "type": cat[5],
                    "hidden": bool(cat[7]),
                    "usage_count": int(cat[8])
                }
                for cat in categories if cat[4] == group_id
            ]
            
            groups_with_categories.append({
                "id": group_id,
                "name": name,
                "icon": icon,
                "color": color,
                "sort_order": sort_order,
                "categories": group_cats
            })
        
        return JSONResponse({
            "groups": groups_with_categories
        })
    except Exception as e:
        print(f"Error in /api/categories/all: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class CreateCategoryRequest(BaseModel):
    name: str
    icon: str = "📦"
    color: str = "#6B7280"
    group_id: str
    type: str = "expense"


@app.post("/api/categories")
async def create_category(request: CreateCategoryRequest):
    """Create a new category"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Generate ID from name
        import re
        cat_id = re.sub(r'[^\w\s-]', '', request.name.lower())
        cat_id = re.sub(r'[-\s]+', '-', cat_id).strip('-')
        cat_id = f"{request.group_id}-{cat_id}"
        
        # Insert category
        conn.execute("""
            INSERT INTO categories (id, name, icon, color, group_id, type, sort_order, hidden)
            VALUES (?, ?, ?, ?, ?, ?, 999, FALSE)
        """, (cat_id, request.name, request.icon, request.color, request.group_id, request.type))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "id": cat_id
        })
    except Exception as e:
        print(f"Error in POST /api/categories: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    group_id: Optional[str] = None
    hidden: Optional[bool] = None


@app.put("/api/categories/{category_id}")
async def update_category(category_id: str, request: UpdateCategoryRequest):
    """Edit a category"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Build update query dynamically
        updates = []
        params = []
        
        if request.name is not None:
            updates.append("name = ?")
            params.append(request.name)
        if request.icon is not None:
            updates.append("icon = ?")
            params.append(request.icon)
        if request.color is not None:
            updates.append("color = ?")
            params.append(request.color)
        if request.group_id is not None:
            updates.append("group_id = ?")
            params.append(request.group_id)
        if request.hidden is not None:
            updates.append("hidden = ?")
            params.append(request.hidden)
        
        if not updates:
            conn.close()
            return JSONResponse({"success": True, "message": "No changes"})
        
        params.append(category_id)
        
        conn.execute(f"""
            UPDATE categories 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        return JSONResponse({"success": True})
    except Exception as e:
        print(f"Error in PUT /api/categories/{category_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class CreateCategoryGroupRequest(BaseModel):
    name: str
    icon: str = "📂"
    color: str = "#6B7280"


@app.post("/api/category-groups")
async def create_category_group(request: CreateCategoryGroupRequest):
    """Create a new category group"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Generate ID from name
        import re
        group_id = re.sub(r'[^\w\s-]', '', request.name.lower())
        group_id = re.sub(r'[-\s]+', '-', group_id).strip('-')
        
        # Insert group
        conn.execute("""
            INSERT INTO category_groups (id, name, icon, color, sort_order)
            VALUES (?, ?, ?, ?, 999)
        """, (group_id, request.name, request.icon, request.color))
        
        conn.commit()
        conn.close()
        
        return JSONResponse({
            "success": True,
            "id": group_id
        })
    except Exception as e:
        print(f"Error in POST /api/category-groups: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


class UpdateCategoryGroupRequest(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@app.put("/api/category-groups/{group_id}")
async def update_category_group(group_id: str, request: UpdateCategoryGroupRequest):
    """Edit a category group"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # Build update query dynamically
        updates = []
        params = []
        
        if request.name is not None:
            updates.append("name = ?")
            params.append(request.name)
        if request.icon is not None:
            updates.append("icon = ?")
            params.append(request.icon)
        if request.color is not None:
            updates.append("color = ?")
            params.append(request.color)
        
        if not updates:
            conn.close()
            return JSONResponse({"success": True, "message": "No changes"})
        
        params.append(group_id)
        
        conn.execute(f"""
            UPDATE category_groups 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        return JSONResponse({"success": True})
    except Exception as e:
        print(f"Error in PUT /api/category-groups/{group_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/review/stats")
async def get_review_stats():
    """Get review queue statistics"""
    try:
        conn = get_db()
        
        stats = conn.execute("""
            SELECT 
                COUNT(CASE WHEN review_status = 'suggested' AND (is_transfer IS NULL OR is_transfer = FALSE) THEN 1 END) as pending,
                COUNT(CASE WHEN review_status = 'confirmed' THEN 1 END) as confirmed,
                COUNT(CASE WHEN review_status = 'corrected' THEN 1 END) as corrected,
                COUNT(CASE WHEN is_transfer = TRUE THEN 1 END) as transfers
            FROM transactions
        """).fetchone()
        
        conn.close()
        
        return JSONResponse({
            "pending": int(stats[0]),
            "confirmed": int(stats[1]),
            "corrected": int(stats[2]),
            "transfers": int(stats[3])
        })
    except Exception as e:
        print(f"Error in /api/review/stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
