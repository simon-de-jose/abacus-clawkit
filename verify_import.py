import duckdb
from src.config import get_db_path

conn = duckdb.connect(str(get_db_path()))

print('Total transactions:', conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0])
print('Categorized:', conn.execute('SELECT COUNT(*) FROM transactions WHERE merchant IS NOT NULL').fetchone()[0])
print('Needs review:', conn.execute('SELECT COUNT(*) FROM transactions WHERE needs_review = TRUE').fetchone()[0])
print('\nSample transactions:')
for row in conn.execute('SELECT transaction_date, merchant, category, amount FROM transactions ORDER BY transaction_date DESC LIMIT 5').fetchall():
    merchant = row[1] if row[1] else '[UNCATEGORIZED]'
    category = row[2] if row[2] else '[NONE]'
    print(f'  {row[0]} | {merchant:30s} | {category:20s} | ${row[3]:>8.2f}')
