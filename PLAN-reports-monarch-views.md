# Plan: Monarch-Style Reports Views (Cash Flow + Spending)

## Goal
Replace the current single Reports page with two sub-tab views matching Monarch Money's Reports section:
1. **Cash Flow** tab — Sankey diagram with summary cards
2. **Spending** tab — Donut chart + transaction list + summary sidebar

## Reference (from Monarch screenshots)

### Cash Flow Tab
- **Top bar:** "Reports" title with sub-tabs: Cash Flow | Spending (active tab highlighted in orange)
- **Top right:** "This month" date picker dropdown + "Filters" button
- **4 summary cards:** Total Income | Total Expenses | Total Net Income | Savings Rate
- **Sankey chart area:**
  - Header: "CASH FLOW" label + date range (e.g., "Dec 1, 2024 - Dec 31, 2024")
  - Controls: "By category & group" dropdown, view toggle icons (sankey/bar/table)
  - Sankey flows: Income sources → "Income" node → expense category groups → individual categories
  - Each node shows amount and percentage

### Spending Tab
- **Top bar:** Same sub-tabs, "Spending" active (orange)
- **Top right:** Same "This month" + "Filters"
- **Spending by Category section:**
  - Header: "SPENDING BY CATEGORY" + date range
  - Controls: "By category" dropdown | "Total amounts" / "Change over time" toggle | chart type icons | Share button
  - Large donut chart with total in center (e.g., "$3,528.37 Total")
  - Category legend: grid of categories with colored dots, amounts, and percentages
  - "Show all categories" expandable link
- **Bottom section (two columns):**
  - **Left (wider): Transactions list**
    - Header: "Transactions" + "Edit multiple" + "Sort" dropdown
    - Grouped by date with daily total
    - Each row: merchant icon | merchant name | category badge | account badge | amount | chevron
  - **Right (narrower): Summary card**
    - Total transactions count
    - Largest transaction
    - Average transaction
    - Total spending
    - "Download CSV" link

## Implementation Steps

### Step 1: Update Backend API (`dashboard/main.py`)

**1a. New endpoint: `GET /api/reports/cashflow-sankey`**
- Params: `date_from`, `date_to` (default: current month)
- Returns: Sankey data with proper Income → Category Group → Category flow
- Include amounts and percentages on each node
- Also return summary: total_income, total_expenses, net_income, savings_rate

**1b. New endpoint: `GET /api/reports/spending-summary`**
- Params: `date_from`, `date_to` (default: current month)
- Returns: `{ total_transactions, largest_transaction, average_transaction, total_spending }`

**1c. Enhance existing endpoints:**
- `GET /api/categories/spending` — already exists, ensure it returns data correctly
- `GET /api/transactions` — already exists with filtering, good as-is
- `GET /api/cashflow/sankey` — already exists but needs enhancement for proper Monarch-style flow

### Step 2: Update Sidebar (`components/sidebar.js`)
- Change "Reports" link to point to `/reports/cashflow` (default sub-tab)
- Keep Reports as the active page for both sub-tabs

### Step 3: Update Routes (`dashboard/main.py`)
- Add routes: `GET /reports/cashflow` and `GET /reports/spending`
- Both serve the new reports page (single HTML with client-side tab switching)

### Step 4: Create New Reports Page (`static/reports.html`)

**4a. Page structure:**
```
<body data-page="Reports">
  <div class="main-content">
    <!-- Sub-tab navigation -->
    <div class="reports-header">
      <h2>Reports</h2>
      <div class="sub-tabs">
        <a class="sub-tab active" data-tab="cashflow">Cash Flow</a>
        <a class="sub-tab" data-tab="spending">Spending</a>
      </div>
      <div class="header-controls">
        <div class="date-picker">This month ▾</div>
      </div>
    </div>
    
    <!-- Cash Flow Tab Content -->
    <div id="tab-cashflow" class="tab-content active">
      <!-- 4 summary cards -->
      <!-- Sankey chart with controls -->
    </div>
    
    <!-- Spending Tab Content -->
    <div id="tab-spending" class="tab-content">
      <!-- Donut chart + category legend -->
      <!-- Transactions list + Summary sidebar -->
    </div>
  </div>
</body>
```

**4b. Cash Flow tab content:**
- Summary grid: 4 cards (Total Income, Total Expenses, Total Net Income, Savings Rate)
- Sankey chart section with "CASH FLOW" header, date range, view controls
- Full-width Sankey using ECharts (already have `createSankeyChart`)

**4c. Spending tab content:**
- Donut chart section with total in center, category legend as a grid
- Two-column bottom: transactions list (left ~70%) + summary sidebar (right ~30%)
- Transaction rows grouped by date with daily subtotals
- Summary card with key stats + Download CSV button

### Step 5: Add CSS Styles (`static/styles.css`)

New styles needed:
- `.reports-header` — flex layout with title, sub-tabs, and date controls
- `.sub-tabs` / `.sub-tab` — tab navigation styling (orange active state)
- `.tab-content` — show/hide tab panels
- `.date-picker` — date range selector button
- `.spending-chart-section` — layout for donut + legend grid
- `.category-legend` — grid of category items with colored dots
- `.transactions-grouped` — date-grouped transaction list
- `.daily-header` — date row with daily total
- `.transaction-row` — individual transaction with merchant, category, account, amount
- `.summary-sidebar` — right sidebar summary card
- `.sankey-controls` — control bar above Sankey chart

### Step 6: JavaScript Logic

**6a. Tab switching:**
- URL-driven: `/reports/cashflow` and `/reports/spending`
- Click sub-tab → update URL + show/hide tab content
- Read URL on load to set active tab

**6b. Date range picker:**
- Dropdown with presets: This month, Last month, Last 3 months, Last 6 months, Year to date, Custom
- On change → reload all data for both tabs

**6c. Cash Flow data loading:**
- Fetch `/api/reports/cashflow-sankey` → render summary cards + Sankey
- Sankey should show: Income sources (left) → "Income" (middle) → Expense groups → Categories (right)

**6d. Spending data loading:**
- Fetch `/api/categories/spending` → render donut chart + category legend
- Fetch `/api/transactions` with date filters → render grouped transaction list
- Fetch `/api/reports/spending-summary` → render summary sidebar
- Donut: total in center, categories as colored segments
- Legend: 3-column grid, each item has colored dot + name + amount + percentage

### Step 7: Enhance Charts (`components/charts.js`)

**7a. Enhanced Sankey chart:**
- Labels show amount + percentage (e.g., "$1,593.00 (37.75%)")
- Color-coded by category group
- Proper left-to-right flow: sources → Income → groups → categories

**7b. Enhanced Donut chart (for Spending):**
- Large center label showing total amount
- Hover shows category detail
- No legend on chart itself (legend is external grid)

### Step 8: Download CSV
- New endpoint: `GET /api/transactions/export` — returns CSV file
- Params: `date_from`, `date_to`, `category`
- Button in Summary sidebar triggers download

## File Changes Summary

| File | Action |
|------|--------|
| `dashboard/main.py` | Add 3 new endpoints + 2 new routes |
| `dashboard/static/reports.html` | Complete rewrite with dual-tab layout |
| `dashboard/static/styles.css` | Add ~100 lines of new styles |
| `dashboard/static/components/charts.js` | Enhance Sankey + add center-label donut |
| `dashboard/static/components/sidebar.js` | Update Reports link |

## Testing
1. Start server: `cd dashboard && ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 3001 --reload`
2. Navigate to `http://localhost:3001/reports/cashflow`
3. Verify: summary cards populate, Sankey renders with real data
4. Click "Spending" tab → verify donut + transactions + summary
5. Test date picker changes
6. Test CSV download
