# Abacus ClawKit 🧮

Personal finance tracker inspired by Monarch Money. Built with FastAPI, DuckDB, and ECharts.

## Features

- 📊 Beautiful dashboard with spending insights
- 💳 Multi-account transaction tracking
- 🏷️ Automatic merchant & category mapping
- 📈 Cash flow visualization with Sankey diagrams
- 📉 Spending trends & reports
- 🔄 CSV import from Chase (more banks coming)

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** DuckDB (embedded analytics)
- **Frontend:** Vanilla JS + ECharts 5.5
- **Design:** Monarch Money-inspired UI

## Quick Start

```bash
# 1. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Initialize database
python3 src/init_db.py

# 4. Import transactions
python3 src/import_csv.py /path/to/chase.csv

# 5. Start dashboard
cd dashboard
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

Dashboard will be available at: http://localhost:3001

## Project Structure

```
abacus-clawkit/
├── src/                    # Backend logic
│   ├── config.py          # Configuration
│   ├── init_db.py         # Database schema & seeds
│   ├── import_csv.py      # CSV import script
│   ├── categorizer.py     # Category mapping
│   └── parsers/           # Bank-specific parsers
│       └── chase.py
├── dashboard/             # Web UI
│   ├── main.py           # FastAPI server
│   └── static/           # HTML/CSS/JS
└── data/                 # Seed data
```

## Database Schema

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for full schema details.

**Tables:**
- `accounts` — Bank accounts
- `transactions` — All transactions with categories
- `merchant_mappings` — Merchant → category rules
- `import_log` — Import history

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT
