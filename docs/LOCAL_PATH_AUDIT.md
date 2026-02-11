# Local Path Audit & Fixes

**Date:** 2026-02-10  
**Status:** ✅ Complete

## Summary

All hardcoded local paths have been removed from the project and replaced with environment variable support and relative paths.

---

## Files Fixed

### 1. `config.yaml`
**Before:**
- Line 4: `/Users/ye/clawd/userdata/abacus/abacus.duckdb`
- Line 7: `/Users/ye/Library/Mobile Documents/com~apple~CloudDocs/data-for-jose/abacus-imports/`

**After:**
- Database: `./data/abacus.duckdb` (relative path)
- Import folder: `./imports` (relative path)

**Notes:** Both paths can now be overridden via environment variables.

---

### 2. `src/config.py`
**Changes:**
- Added environment variable support for `ABACUS_DB_PATH`
- Added environment variable support for `ABACUS_IMPORT_DIR`
- Added logic to resolve relative paths from project root
- Priority: env var → config.yaml → default

**Code additions:**
```python
# Check environment variable first
env_path = os.getenv("ABACUS_DB_PATH")
if env_path:
    return Path(env_path)

# If relative, resolve from project root
if not db_path.is_absolute():
    db_path = PROJECT_ROOT / db_path
```

---

### 3. `verify_import.py`
**Before:**
- Line 3: `duckdb.connect('/Users/ye/clawd/userdata/abacus/abacus.duckdb')`

**After:**
```python
from src.config import get_db_path
conn = duckdb.connect(str(get_db_path()))
```

---

### 4. `dashboard/static/accounts.html`
**Before:**
- Line 63: Hardcoded iCloud path in import instructions

**After:**
- Generic instructions referencing `config.yaml` and `ABACUS_IMPORT_DIR`
- Text: "Place the CSV file in your configured import folder (see config.yaml or set ABACUS_IMPORT_DIR)"

---

### 5. `README.md`
**Changes:**
- Removed hardcoded `/Users/ye/Projects/abacus-clawkit` from setup instructions
- Updated "Quick Start" to use generic `cd abacus-clawkit`
- Removed hardcoded iCloud path from import instructions
- Added "Configuration" section explaining environment variables
- Updated database section to use `get_db_path()` helper
- Updated merchant mapping instructions to use relative path

**New sections:**
- Configuration with environment variables
- Generic import folder instructions

---

### 6. `CONTRIBUTING.md`
**Before:**
- Line 6: `cd /Users/ye/Projects/abacus-clawkit`

**After:**
- Generic `cd abacus-clawkit`
- Added step to copy `.env.example` to `.env`

---

### 7. `.env.example` (NEW FILE)
**Created:** Environment variable template with examples

**Contents:**
- `ABACUS_DB_PATH` — Custom database location
- `ABACUS_IMPORT_DIR` — Custom import folder
- Example showing iCloud folder path (commented)

---

## Files NOT Changed (Historical Docs)

These files in `docs/` contain historical paths but were left unchanged as they are internal documentation:
- `docs/BUILD_SUMMARY.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/VERIFICATION.md`

**Rationale:** These are project history/planning documents, not user-facing configuration or code.

---

## Verification

### ✅ No hardcoded paths remain in active code
Scanned with: `grep -r "/Users/ye" --include="*.py" --include="*.js" --include="*.html"`  
**Result:** No matches in src/, dashboard/, or root files (excluding docs/)

### ✅ All imports use config module
- `src/init_db.py` → uses `get_db_path()`
- `src/import_csv.py` → uses `get_db_path()` and `get_import_folder()`
- `verify_import.py` → uses `get_db_path()`

### ✅ Environment variables work
Users can now override paths with:
```bash
export ABACUS_DB_PATH=/custom/path/db.duckdb
export ABACUS_IMPORT_DIR=/custom/imports/
```

---

## Migration Guide

For existing users with data at `/Users/ye/clawd/userdata/abacus/abacus.duckdb`:

1. **Option A: Use environment variables (recommended)**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   ABACUS_DB_PATH=/Users/ye/clawd/userdata/abacus/abacus.duckdb
   ABACUS_IMPORT_DIR=/Users/ye/Library/Mobile Documents/com~apple~CloudDocs/data-for-jose/abacus-imports/
   ```

2. **Option B: Move data to new structure**
   ```bash
   mkdir -p data imports
   mv /Users/ye/clawd/userdata/abacus/abacus.duckdb* data/
   # Now use default config.yaml paths
   ```

---

## Benefits

1. **Portability** — Project works on any machine without path changes
2. **Privacy** — No personal paths in version control
3. **Flexibility** — Users can configure paths via env vars or config.yaml
4. **Standard conventions** — Follows common project structure (./data, ./imports)
5. **Documentation** — .env.example shows users how to customize

---

**End of audit report.**
