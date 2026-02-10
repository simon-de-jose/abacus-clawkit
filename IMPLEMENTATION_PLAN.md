# Abacus ClawKit — Implementation Plan

*Project Abacus: Personal finance tracking & visualization platform*
*Inspired by Monarch Money, built on the same stack as Health ClawKit*

---

## Architecture Overview

```
iCloud: data-for-jose/abacus-imports/
    ├── Chase*.CSV
    ├── Citi*.CSV          (future)
    └── BoA*.CSV           (future)
         ↓
   [CSV Parser & Normalizer]
         ↓
   DuckDB: userdata/abacus/abacus.duckdb
         ↓
   [FastAPI Backend]
         ↓
   [Web Dashboard — ECharts + Vanilla JS]
   http://localhost:3001
```

**Tech Stack** (mirrors health-clawkit):
- **Database:** DuckDB
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla HTML/CSS/JS + ECharts
- **Charts:** ECharts 5.5 (already proven in health project)

---

## Database Schema

### Table: `accounts`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Primary key (e.g., 'chase_2948') |
| name | VARCHAR | Display name (e.g., 'Chase Freedom') |
| bank | VARCHAR | Bank name |
| last_four | VARCHAR | Last 4 digits |
| type | VARCHAR | credit/debit/checking |
| created_at | TIMESTAMP | |

### Table: `transactions`
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Hash of (date + amount + description + account) for dedup |
| transaction_date | DATE | When the transaction occurred |
| post_date | DATE | When it posted |
| description | VARCHAR | Raw merchant description from bank |
| merchant | VARCHAR | Cleaned merchant name (via mapping) |
| bank_category | VARCHAR | Category from bank CSV |
| category | VARCHAR | Our refined category |
| category_group | VARCHAR | Parent group (e.g., "Food & Drink" → "Living") |
| type | VARCHAR | Sale/Return/Payment |
| amount | DECIMAL(10,2) | Negative = expense, positive = income/refund |
| account_id | VARCHAR | FK to accounts |
| memo | VARCHAR | |
| needs_review | BOOLEAN | True if merchant/category not yet mapped |
| file_hash | VARCHAR | SHA256 of source file (for dedup) |
| created_at | TIMESTAMP | When imported |

### Table: `merchant_mappings`
| Column | Type | Description |
|--------|------|-------------|
| pattern | VARCHAR | Regex or substring to match description |
| merchant | VARCHAR | Clean merchant name |
| category | VARCHAR | Assigned category |
| category_group | VARCHAR | Assigned group |

### Table: `import_log`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment |
| filename | VARCHAR | Source file name |
| file_hash | VARCHAR | SHA256 for dedup |
| rows_imported | INTEGER | |
| rows_skipped | INTEGER | Duplicates skipped |
| imported_at | TIMESTAMP | |

### Category Taxonomy

**Groups → Categories:**
- **Food & Drink** → Groceries, Dining Out, Coffee & Drinks, Delivery
- **Housing** → Rent/Mortgage, Utilities, Home Maintenance
- **Transportation** → Gas, Auto Insurance, Maintenance, Parking, Uber/Lyft
- **Shopping** → Clothing, Electronics, Household, Amazon, Pet Supplies
- **Health** → Insurance, Medical, Pharmacy, Fitness
- **Entertainment** → Streaming, Events, Hobbies
- **Bills & Subscriptions** → Phone, Internet, Software, Subscriptions
- **Travel** → Hotels, Flights, Car Rental, Travel Activities
- **Pets** → Food, Litter, Vet, Insurance
- **Personal** → Haircut, Education, Professional Services
- **Income** → Salary, Refunds, Credits

---

## Dashboard Pages (Monarch-Inspired)

### Page 1: Dashboard (Home)
- **Monthly summary card:** Total spent, total income, net
- **Spending by category:** Donut/pie chart (ECharts)
- **Spending trend:** Bar chart — last 6 months comparison
- **Recent transactions:** Last 10, quick-glance table
- **Top merchants:** This month

### Page 2: Transactions
- **Full transaction table** with search, filter, sort
- **Filters:** Date range, category, account, amount range, type
- **Inline category edit** (click to reclassify)
- **Needs Review badge** for unmapped transactions
- **Pagination**

### Page 3: Cash Flow (Sankey)
- **Sankey diagram:** Income → Category Groups → Categories
- **Monthly bar chart:** Income vs. Expenses stacked
- **Date range selector**

### Page 4: Reports
- **Spending by category over time** (stacked area chart)
- **Month-over-month comparison** (grouped bar)
- **Top merchants** (horizontal bar)
- **Category breakdown table** with amounts and percentages
- **Recurring vs. one-time** split

### Page 5: Accounts
- **List of connected accounts** with last import date
- **Import status / file history**

---

## Implementation Steps

### Phase 1: Project Setup & Database ✅→⬜
- [ ] **Step 1.1:** Initialize project structure (README, .gitignore, requirements.txt, config.yaml)
- [ ] **Step 1.2:** Create DuckDB schema (init_db.py)
- [ ] **Step 1.3:** Seed category taxonomy and initial merchant mappings
- [ ] **Step 1.4:** Git init + first commit

### Phase 2: CSV Import Pipeline ⬜
- [ ] **Step 2.1:** Build Chase CSV parser (parse the exact format from Juan's test file)
- [ ] **Step 2.2:** Build normalizer (clean merchant names, map categories)
- [ ] **Step 2.3:** Build import script with dedup (file hash + transaction hash)
- [ ] **Step 2.4:** Import Juan's test CSV and validate data
- [ ] **Step 2.5:** Build import watcher (scan iCloud folder for new files)
- [ ] **Step 2.6:** Git commit checkpoint

### Phase 3: FastAPI Backend ⬜
- [ ] **Step 3.1:** Setup FastAPI app with config
- [ ] **Step 3.2:** API: GET /api/overview (dashboard summary stats)
- [ ] **Step 3.3:** API: GET /api/transactions (paginated, filterable)
- [ ] **Step 3.4:** API: GET /api/categories/spending (breakdown by category/group)
- [ ] **Step 3.5:** API: GET /api/cashflow (monthly income vs expenses)
- [ ] **Step 3.6:** API: GET /api/cashflow/sankey (sankey diagram data)
- [ ] **Step 3.7:** API: GET /api/merchants/top (top merchants by spend)
- [ ] **Step 3.8:** API: GET /api/reports/trends (spending over time by category)
- [ ] **Step 3.9:** API: PUT /api/transactions/{id}/category (recategorize)
- [ ] **Step 3.10:** API: GET /api/accounts (account list + import status)
- [ ] **Step 3.11:** Git commit checkpoint

### Phase 4: Dashboard Frontend ⬜
- [ ] **Step 4.1:** Base layout — sidebar nav, header, responsive grid (Monarch-style dark/light)
- [ ] **Step 4.2:** Dashboard page — summary cards, donut chart, trend bar, recent transactions
- [ ] **Step 4.3:** Transactions page — full table with search/filter/sort/pagination
- [ ] **Step 4.4:** Cash Flow page — Sankey diagram + monthly bars
- [ ] **Step 4.5:** Reports page — stacked area, month comparison, top merchants
- [ ] **Step 4.6:** Accounts page — import status, file history
- [ ] **Step 4.7:** Polish — colors, hover states, responsive, loading states
- [ ] **Step 4.8:** Git commit checkpoint

### Phase 5: Skill Setup & Integration ⬜
- [ ] **Step 5.1:** Create `~/clawd/skills/abacus/` skill folder with SKILL.md
- [ ] **Step 5.2:** Add import cron concept (check for new files in iCloud)
- [ ] **Step 5.3:** Final README with usage instructions
- [ ] **Step 5.4:** Final git commit + tag v0.1.0

---

## Design Notes

**Color Palette (Monarch-inspired):**
- Primary: `#1A1A2E` (dark navy sidebar)
- Accent: `#E94560` (coral/red for spending)
- Income: `#0F9D58` (green)
- Background: `#F5F5F7` (light gray)
- Cards: `#FFFFFF`
- Category colors: ECharts default palette (vibrant, distinguishable)

**UI Principles:**
- Clean, minimal — lots of whitespace
- Left sidebar navigation (icon + label)
- Date range picker in header (global filter)
- Cards with subtle shadows
- Charts are the hero — big, interactive, beautiful

---

## File Structure

```
~/Projects/abacus-clawkit/
├── README.md
├── IMPLEMENTATION_PLAN.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore
├── requirements.txt
├── config.yaml
├── src/
│   ├── config.py
│   ├── init_db.py
│   ├── import_csv.py
│   ├── parsers/
│   │   ├── chase.py
│   │   ├── citi.py          (future)
│   │   └── boa.py           (future)
│   ├── categorizer.py
│   └── merchant_mapper.py
├── dashboard/
│   ├── main.py              (FastAPI)
│   └── static/
│       ├── index.html        (Dashboard)
│       ├── transactions.html
│       ├── cashflow.html
│       ├── reports.html
│       ├── accounts.html
│       ├── styles.css
│       ├── app.js
│       └── components/
│           ├── sidebar.js
│           ├── charts.js
│           └── table.js
├── data/
│   └── merchant_mappings.json
└── tests/
    └── test_import.py

~/clawd/skills/abacus/
├── SKILL.md
└── README.md

~/clawd/userdata/abacus/
└── abacus.duckdb
```

---

## Merchant Mapping (Initial — based on Juan's Chase data)

From analyzing the test CSV:
| Pattern | Merchant | Category | Group |
|---------|----------|----------|-------|
| AMAZON MKTPL* | Amazon | Amazon | Shopping |
| Amazon.com* | Amazon | Amazon | Shopping |
| CHEWY.COM | Chewy | Pet Supplies | Pets |
| NIJIYA MARKET | Nijiya Market | Groceries | Food & Drink |
| Whole Foods* | Whole Foods | Groceries | Food & Drink |
| WOOGA SULLUNGTANG | Wooga Sullungtang | Dining Out | Food & Drink |
| TST*SWEET WHEAT | Sweet Wheat Bakery | Coffee & Drinks | Food & Drink |
| UBER *TRIP / UBER* TRIP | Uber | Rideshare | Transportation |
| Spectrum* | Spectrum | Internet/Phone | Bills & Subscriptions |
| TESLA SUBSCRIPTION | Tesla | Auto Insurance | Transportation |
| CINEMARK* | Cinemark | Entertainment | Entertainment |
| GOOGLE *YouTube* | YouTube Premium | Streaming | Bills & Subscriptions |
| TAOBAO.COM | Taobao | Shopping | Shopping |
| CHIPOTLE* | Chipotle | Dining Out | Food & Drink |
| COSTCO* | Costco | Groceries | Food & Drink |
| ROVER.COM | Rover | Pet Sitting | Pets |
| HUBERMAN LAB | Huberman Lab | Subscriptions | Bills & Subscriptions |
| Booking.com* | Booking.com | Hotels | Travel |
| HOTEL * | Hotel | Hotels | Travel |
| OXXO* | OXXO | Convenience | Food & Drink |
| MADEWELL | Madewell | Clothing | Shopping |
| SEPHORA* | Sephora | Personal Care | Personal |
| STARBUCKS* | Starbucks | Coffee & Drinks | Food & Drink |
| SQ *DELICES DU CHEF | Délices du Chef | Dining Out | Food & Drink |
| TACOMASA* | Tacomasa | Dining Out | Food & Drink |
| FOOD.APPLE.COM | Apple (Food) | Subscriptions | Bills & Subscriptions |
| SUPERBCUT* | Supercuts | Haircut | Personal |
| Tesla Insurance* | Tesla Insurance | Auto Insurance | Transportation |

---

## Status Tracking

| Phase | Status | Started | Completed |
|-------|--------|---------|-----------|
| Phase 1: Setup | ⬜ Not started | | |
| Phase 2: Import | ⬜ Not started | | |
| Phase 3: Backend | ⬜ Not started | | |
| Phase 4: Frontend | ⬜ Not started | | |
| Phase 5: Skill | ⬜ Not started | | |

---

*Plan created: 2026-02-09*
*Target: Overnight build — deliver by morning*
