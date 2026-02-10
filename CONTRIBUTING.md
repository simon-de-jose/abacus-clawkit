# Contributing to Abacus ClawKit

## Development Setup

1. **Clone & setup:**
   ```bash
   cd /Users/ye/Projects/abacus-clawkit
   python3 -m venv .venv
   source .venv/bin/activate
   pip3 install -r requirements.txt
   ```

2. **Initialize database:**
   ```bash
   python3 src/init_db.py
   ```

3. **Run development server:**
   ```bash
   cd dashboard
   uvicorn main:app --host 0.0.0.0 --port 3001 --reload
   ```

## Project Philosophy

- **Simplicity:** No ORM, no React, no webpack. Vanilla everything.
- **Performance:** DuckDB is fast. Keep it fast.
- **Beauty:** Charts are the hero. Make them stunning.
- **Privacy:** All data stays local. No cloud sync.

## Code Style

- **Python:** Follow PEP 8. Use type hints.
- **JavaScript:** ES6+. No build step. Keep it readable.
- **SQL:** Format queries for readability. Use CTEs for complex logic.

## Adding a New Bank Parser

1. Create `src/parsers/bankname.py`
2. Implement `parse(file_path) -> List[Dict]`
3. Normalize to standard transaction schema
4. Add merchant mappings to seed data
5. Update config.yaml

## Testing

Import the test CSV and verify:
- Transaction count matches
- Categories are mapped correctly
- Dashboard loads without errors
- Charts render with real data

## Commit Guidelines

- Use conventional commits: `feat:`, `fix:`, `docs:`, `style:`
- Reference issues where applicable
- Keep commits focused and atomic
