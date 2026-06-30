# Ernest Market

Production-grade Python automation that monitors **eBay** listings against configurable buy rules and sends qualified deals to **Telegram** and **Google Sheets**.

## Features

- Official **eBay Browse API** or **ScraperAPI** (switch via `EBAY_BACKEND` in `.env`)
- Keyword + min/max price filtering from `config.yaml`
- Exclude-word filtering (e.g. "broken", "for parts")
- Deduplication via local JSON state (no database)
- Telegram channel alerts
- Google Sheets logging
- Rotating file logs
- Single-run mode for Task Scheduler (`--once`)
- Loop mode for continuous polling
- **React dashboard** (`frontend/`) with FastAPI wrapper (`api/`) — see [FRONTEND.md](FRONTEND.md)

## Requirements

- Python 3.10+
- Windows, macOS, or Linux
- eBay Developer account (production keys)
- Telegram bot + private channel
- Google Cloud service account + Google Sheet

## Quick start

### 1. Install dependencies

```bash
cd ernest-market
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

Edit `.env` with your credentials (see **Manual setup** below).

### 3. Configure buy rules

```bash
copy config.example.yaml config.yaml
```

Edit `config.yaml` with Ernest's keywords and price limits.

### Part 2 — Filter & dedupe (eBay only, no alerts)

Part 2 only needs **eBay keys** in `.env` (Telegram/Sheets not required yet).

```bash
# Offline filter logic tests (no API keys)
python scripts/test_filter.py
python scripts/test_state.py

# Live eBay + filter + dedupe dry-run (prints new deals, does NOT alert)
python scripts/scan_dry_run.py

# See rejection breakdown
python scripts/scan_dry_run.py --verbose-rejects

# Persist seen IDs after validating output
python scripts/scan_dry_run.py --mark-seen
```

### 4. Place Google credentials

Download the service account JSON from Google Cloud Console and save it as:

```
secrets/google-credentials.json
```

### 5. Run connectivity tests

```bash
python scripts/run_all_tests.py    # full report (recommended)
python scripts/test_ebay.py
python scripts/test_telegram.py
python scripts/test_sheets.py
```

See **SETUP.md** for detailed manual setup steps for each integration.

### 6. Run the monitor

```bash
# Single scan (recommended for Task Scheduler)
python main.py --once

# Continuous loop
python main.py

# Telegram + Sheets only (no eBay scan)
python main.py --check
```

## Project structure

```
ernest-market/
├── main.py                  # Entry point
├── config.example.yaml      # Buy rules template
├── .env.example             # Secrets template
├── requirements.txt
├── src/
│   ├── settings.py          # Environment config
│   ├── config_loader.py     # YAML rules
│   ├── ebay_auth.py         # OAuth token management
│   ├── ebay_client.py       # Browse API search
│   ├── filter.py            # Keyword/price filtering
│   ├── filter_scan.py       # Part 2 pipeline (no alerts)
│   ├── state.py             # Seen listing dedupe
│   ├── notifier_telegram.py # Telegram alerts
│   ├── sheets_logger.py     # Google Sheets logging
│   ├── pipeline.py          # Orchestrator
│   └── logging_setup.py     # Logging config
├── scripts/
│   ├── test_ebay.py
│   ├── test_filter.py
│   ├── test_state.py
│   ├── scan_dry_run.py
│   ├── test_telegram.py
│   └── test_sheets.py
├── data/                    # seen_listings.json (runtime)
├── logs/                    # app.log (runtime)
└── secrets/                 # google-credentials.json (you provide)
```

## Windows Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: Daily, repeat every **5 minutes** for 24 hours
3. Action: Start a program
   - Program: `C:\path\to\ernest-market\venv\Scripts\python.exe`
   - Arguments: `C:\path\to\ernest-market\main.py --once`
   - Start in: `C:\path\to\ernest-market`
4. Run whether user is logged on or not (optional)

## config.yaml reference

```yaml
rules:
  - keyword: "vintage camera"
    max_price: 75
    min_price: 10
    match_in: title
    exclude_words:
      - "broken"
      - "for parts"
```

| Field | Description |
|-------|-------------|
| `keyword` | eBay search term |
| `max_price` | Maximum buy price (USD) |
| `min_price` | Minimum price (optional, default 0) |
| `match_in` | `title` or `title_and_description` |
| `exclude_words` | Skip listings containing these words |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing required environment variable` | Copy `.env.example` → `.env` and fill all values |
| eBay OAuth failed | Verify Client ID/Secret; check `EBAY_ENV` matches key type |
| eBay 401 during search | Regenerate production keys; ensure Browse API is enabled |
| Telegram test fails | Bot must be **admin** of the private channel |
| Wrong channel ID | Use `getUpdates` API or @getidsbot to find negative channel ID |
| Sheets permission denied | Share sheet with service account email as **Editor** |
| Same deal alerts twice | Check `data/seen_listings.json` is writable |
| No matches | Widen keyword or raise `max_price` temporarily to test |

## Security

- Never commit `.env`, `secrets/*.json`, or `data/seen_listings.json`
- Rotate credentials if accidentally exposed
- Use Ernest's own eBay/Google accounts for production handoff

## Phase 1 scope

- eBay marketplace monitoring only
- No PostgreSQL, no AI, no Sentry
