# Abacus ClawKit 🧮

Personal finance tracker inspired by Monarch Money. Built with FastAPI, DuckDB, and ECharts.

## Features

- 📊 **Beautiful Dashboard** — Monarch-inspired UI with summary cards and interactive charts
- 💳 **Transaction Tracking** — Multi-account support with search, filters, and pagination
- 🏷️ **Smart Categorization** — Automatic merchant mapping with manual override
- 📈 **Cash Flow Analysis** — Sankey diagrams showing money flow from income to expenses
- 📉 **Spending Insights** — Trends over time, top merchants, category breakdowns
- 🔄 **CSV Import** — Import from Chase (more banks coming soon)
- 🔒 **Privacy First** — All data stored locally in DuckDB

## Screenshots

**Dashboard:**
- Summary cards: Total Spent, Total Income, Net, Transaction Count
- Donut chart: Spending by category
- Bar chart: Monthly spending trend
- Recent transactions & top merchants

**Transactions:**
- Full transaction table with inline category editing
- Search by merchant/description
- Filter by category, date range
- "Needs Review" badge for uncategorized transactions

**Cash Flow:**
- Sankey diagram: Income → Category Groups → Categories
- Stacked bar: Monthly income vs expenses

**Reports:**
- Stacked area: Spending by category over time
- Line chart: Month-over-month comparison
- Horizontal bar: Top merchants
- Category breakdown table with percentages

**Accounts:**
- Connected accounts list
- Import history with row counts and timestamps

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** DuckDB (embedded analytics database)
- **Frontend:** Vanilla JavaScript + ECharts 5.5
- **Design:** Monarch Money-inspired (dark navy sidebar, coral/green accents, clean cards)

## Quick Start

```bash
# 1. Setup virtual environment
cd /Users/ye/Projects/abacus-clawkit
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Initialize database
python3 src/init_db.py

# 4. Import transactions
python3 src/import_csv.py sample_data.csv

# 5. Start dashboard
cd dashboard
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

Dashboard will be available at: **http://localhost:3001**

## Importing from iCloud

Place CSV files in:
```
/Users/ye/Library/Mobile Documents/com~apple~CloudDocs/data-for-jose/abacus-imports/
```

Then run:
```bash
python3 src/import_csv.py
# Or specify a file:
python3 src/import_csv.py /path/to/chase.csv
```

**Deduplication:** Files and transactions are automatically deduplicated using SHA256 hashes.

## Project Structure

```
abacus-clawkit/
├── src/                          # Backend logic
│   ├── config.py                # Configuration loader
│   ├── init_db.py               # Database schema & seeds
│   ├── import_csv.py            # CSV import with dedup
│   ├── categorizer.py           # Merchant → category mapper
│   └── parsers/
│       └── chase.py             # Chase CSV parser
├── dashboard/
│   ├── main.py                  # FastAPI server (port 3001)
│   └── static/
│       ├── index.html           # Dashboard home
│       ├── transactions.html    # Transaction list
│       ├── cashflow.html        # Cash flow visualization
│       ├── reports.html         # Spending reports
│       ├── accounts.html        # Accounts & import history
│       ├── styles.css           # Monarch-inspired styles
│       └── components/
│           ├── sidebar.js       # Reusable sidebar
│           ├── charts.js        # ECharts helpers
│           └── table.js         # Table rendering
├── config.yaml                  # Configuration
├── requirements.txt             # Python dependencies
└── IMPLEMENTATION_PLAN.md       # Full project plan
```

## API Endpoints

### GET /api/overview
Monthly summary: total spent, income, net, transaction count, top categories

### GET /api/transactions
Paginated transaction list with filters:
- `search` — Search description/merchant
- `category` — Filter by category
- `date_from`, `date_to` — Date range
- `page`, `per_page` — Pagination

### GET /api/categories/spending
Category breakdown with amounts and groups

### GET /api/cashflow
Monthly income vs expenses (last N months)

### GET /api/cashflow/sankey
Sankey diagram data: nodes and links for income → groups → categories

### GET /api/merchants/top
Top merchants by total spend

### GET /api/reports/trends
Spending by category over time (monthly)

### PUT /api/transactions/{id}/category
Update transaction category:
```json
{
  "category": "Groceries",
  "category_group": "Food & Drink"
}
```

### GET /api/accounts
Account list with transaction counts and import history

### GET /api/categories
All categories (for dropdowns)

## Database

**Location:** `/Users/ye/clawd/userdata/abacus/abacus.duckdb`

**Schema:**
- `accounts` — id, name, bank, last_four, type
- `transactions` — id (hash), dates, description, merchant, category, amount, needs_review
- `merchant_mappings` — pattern (regex/substring), merchant, category, category_group
- `import_log` — filename, file_hash, rows_imported, rows_skipped, imported_at

**Query Example:**
```python
import duckdb
conn = duckdb.connect('/Users/ye/clawd/userdata/abacus/abacus.duckdb')
result = conn.execute("SELECT * FROM transactions LIMIT 10").fetchall()
```

## Adding Merchant Mappings

### Option 1: Update init_db.py
Add to the `merchant_mappings` list in `src/init_db.py`, then:
```bash
rm /Users/ye/clawd/userdata/abacus/abacus.duckdb*
python3 src/init_db.py
python3 src/import_csv.py sample_data.csv
```

### Option 2: Insert directly
```sql
INSERT INTO merchant_mappings (pattern, merchant, category, category_group)
VALUES ('TRADER JOE*', 'Trader Joes', 'Groceries', 'Food & Drink');
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Adding new bank parsers
- Testing procedures
- Commit conventions

## Roadmap

- [ ] Citi & Bank of America parsers
- [ ] Recurring transaction detection
- [ ] Budget tracking & alerts
- [ ] Mobile app (iOS/Android)
- [ ] Multi-user support
- [ ] Export to CSV/PDF

## License

MIT
