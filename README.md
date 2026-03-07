# Abacus ClawKit — Dashboard

> 🧮 **This repo is the Abacus dashboard only.**
> 
> The skill, scripts, and SQL docs live at: [simon-de-jose/abacus](https://github.com/simon-de-jose/abacus)

---

## What's Here

```
abacus-clawkit/
├── dashboard/          ← FastAPI web dashboard
│   ├── main.py         ← API + serving
│   └── static/         ← HTML/CSS/JS frontend
├── .venv/              ← Shared venv (dashboard + scripts both use this)
├── requirements.txt
└── config.yaml         ← Dashboard config (DB path, server settings)
```

## Running the Dashboard

```bash
cd ~/Projects/abacus-clawkit

# Start the dashboard
.venv/bin/python3 -m uvicorn dashboard.main:app --reload --host 0.0.0.0 --port 3001

# Or from inside dashboard/
cd dashboard
python3 -m uvicorn main:app --reload --port 3001
```

Open: http://localhost:3001

## Shared venv

The `.venv/` here is shared with the skill scripts in `~/clawd/skills/abacus/scripts/`.
Don't move it — the skill's `config.yaml` points to this venv path.

## Database

**DuckDB lives at:** `~/clawd/userdata/abacus/abacus.duckdb`

Never move it. It's referenced by both this dashboard and the skill config.

## Scripts + Sync

Scripts (sync, import, categorize) are in the skill repo:
```bash
cd ~/clawd/skills/abacus
bash shell/paths.sh --json    # check paths
$PYTHON scripts/sync_simplefin.py    # sync latest
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for dev workflow.
