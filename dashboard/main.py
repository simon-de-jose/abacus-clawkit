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
    """Get database connection"""
    return duckdb.connect(DB_PATH, read_only=True)


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
        
        # Total spent (negative amounts = expenses)
        result = conn.execute("""
            SELECT SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
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
        
        # Top categories (expenses only)
        top_categories = conn.execute("""
            SELECT category, SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
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
        
        # Total spent YTD
        result = conn.execute("""
            SELECT SUM(ABS(amount)) FROM transactions 
            WHERE amount < 0 AND transaction_date >= ?
        """, (year_start,)).fetchone()
        total_spent = float(result[0]) if result[0] else 0.0
        
        # Total income YTD
        result = conn.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE amount > 0 AND transaction_date >= ?
        """, (year_start,)).fetchone()
        total_income = float(result[0]) if result[0] else 0.0
        
        # Spending by category_group YTD (high-level: Dining, Grocery level, NOT boba/coffee level)
        # IMPORTANT: Include NULL categories as "Uncategorized"
        groups = conn.execute("""
            SELECT COALESCE(category_group, 'Uncategorized') as grp, SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 AND transaction_date >= ?
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
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
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
        
        # Get expenses by category group and category
        expenses_data = conn.execute("""
            SELECT 
                COALESCE(category_group, 'Uncategorized') as grp,
                COALESCE(category, 'Uncategorized') as cat,
                SUM(ABS(amount)) as total
            FROM transactions 
            WHERE amount < 0 
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=True)
