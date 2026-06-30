# Ernest Market — Manual Setup Guide

Complete these steps **in order**. After each section, run the test command to verify before moving on.

---

## Step 0 — Project already done on your machine

```powershell
cd "D:\ET Projects\client\ernest-market"
venv\Scripts\activate
pip install -r requirements.txt
```

Run offline tests (no credentials needed):

```powershell
python scripts\test_filter.py
python scripts\test_state.py
```

Both should print `All Part 2 ... tests passed.`

Run full report anytime:

```powershell
python scripts\run_all_tests.py
```

---

## Step 1 — eBay data source (pick one)

### Option A — ScraperAPI (testing, no eBay developer account)

1. Sign up at [ScraperAPI](https://dashboard.scraperapi.com/home)
2. Copy your API key from the dashboard
3. Update `.env`:

```env
EBAY_BACKEND=scraperapi
SCRAPERAPI_KEY=your_scraperapi_key
```

4. Test:

```powershell
python scripts\test_ebay.py
python scripts\scan_dry_run.py
```

### Option B — Official eBay API (production / client handoff)

1. Go to [https://developer.ebay.com/](https://developer.ebay.com/) and sign in.
2. Open **My Account → Application Keys**.
3. Copy **Sandbox** or **Production** App ID + Cert ID.
4. Update `.env`:

```env
EBAY_BACKEND=official
EBAY_CLIENT_ID=your_real_app_id
EBAY_CLIENT_SECRET=your_real_cert_id
EBAY_ENV=sandbox
```

Use `EBAY_ENV=production` only with Production keys.

5. Test:

```powershell
python scripts\test_ebay.py
```

---

## Step 2 — Buy rules (`config.yaml`)

Already exists. Edit keywords and prices for Ernest:

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

### Test Part 2 live (no Telegram/Sheets yet)

```powershell
python scripts\scan_dry_run.py
python scripts\scan_dry_run.py
```

Second run should show fewer or zero **NEW** deals (dedupe working).

---

## Step 3 — Telegram bot + private channel

### Manual steps

1. Open Telegram → search **@BotFather**.
2. Send `/newbot` → follow prompts → save the **bot token**.
3. Create a **private channel** (e.g. `Ernest Deals`).
4. Open channel → **Manage channel → Administrators → Add administrator**.
5. Add your bot (must be able to **post messages**).
6. Post any message in the channel.
7. Get channel ID — open in browser (replace TOKEN):
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Find `"chat":{"id":-100xxxxxxxxxx}` — that is `TELEGRAM_CHANNEL_ID`.

### Update `.env`

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefYourRealToken
TELEGRAM_CHANNEL_ID=-1001234567890
```

### Test

```powershell
python scripts\test_telegram.py
```

Check your Telegram channel for the test message.

---

## Step 4 — Google Sheets

### Manual steps

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create project: `ernest-market-monitor`.
3. Enable **Google Sheets API**.
4. **IAM & Admin → Service Accounts → Create service account**.
5. Create **JSON key** → download file.
6. Save as:
   ```
   secrets/google-credentials.json
   ```
7. Create a Google Sheet in your Drive.
8. Copy Sheet ID from URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```
9. **Share the sheet** with the service account email from the JSON file:
   ```
   something@ernest-market-monitor.iam.gserviceaccount.com
   ```
   Permission: **Editor**.

### Update `.env`

```env
GOOGLE_SHEETS_ID=your_real_sheet_id
GOOGLE_CREDENTIALS_PATH=./secrets/google-credentials.json
```

### Test

```powershell
python scripts\test_sheets.py
```

Open the sheet — a TEST row should appear.

---

## Step 5 — Full end-to-end

```powershell
python main.py --check
python main.py --once
```

- `--check` → Telegram test + Sheets test only
- `--once` → full scan: eBay → filter → dedupe → Telegram + Sheet

Run twice to confirm deduplication:

```powershell
python main.py --once
python main.py --once
```

Second run should not re-alert the same listings.

---

## Step 6 — Schedule (Windows Task Scheduler)

Use **`--once` every 5 minutes** instead of one long scan. Each run processes a **rotating batch** of rules (default: 8 per run) so all 39+ rules are covered over time without hitting Telegram rate limits.

Recommended `.env` tuning (copy from `.env.example` if missing):

| Variable | Default | Purpose |
|----------|---------|---------|
| `RULES_PER_RUN` | `8` | Rules per scheduled run (`0` = all rules) |
| `RULE_SEARCH_DELAY_SECONDS` | `1` | Pause between eBay searches |
| `TELEGRAM_ALERT_DELAY_SECONDS` | `1.5` | Pause after each Telegram alert |
| `TELEGRAM_MAX_RETRIES` | `5` | Retry on HTTP 429 using `retry_after` |
| `MAX_ALERTS_PER_RUN` | `20` | Cap alerts per run (`0` = unlimited) |

With 39 rules and `RULES_PER_RUN=8`, a full cycle takes about **25 minutes** at a 5-minute schedule.

1. Open **Task Scheduler** → Create Basic Task.
2. Name: `Ernest eBay Monitor`.
3. Trigger: Daily, repeat every **5 minutes** for 24 hours.
4. Action: Start a program
   - Program: `D:\ET Projects\client\ernest-market\venv\Scripts\python.exe`
   - Arguments: `D:\ET Projects\client\ernest-market\main.py --once`
   - Start in: `D:\ET Projects\client\ernest-market`

Batch position is stored in `data/rule_batch_state.json` and advances automatically after each run.

---

## Step 7 — Mercari (RapidAPI)

Mercari has no official public search API. This project uses **RapidAPI mercari-item-search**.

### Manual steps

1. Create a free account at [RapidAPI](https://rapidapi.com/)
2. Open [mercari-item-search API](https://rapidapi.com/k19862217/api/mercari-item-search)
3. Click **Subscribe to Test** (pick Basic/Free or paid plan)
4. Copy your **X-RapidAPI-Key** from the API dashboard
5. Update `.env`:

```env
MERCARI_ENABLED=true
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_MERCARI_HOST=mercari-item-search.p.rapidapi.com
```

When `MERCARI_ENABLED=true`, each eBay rule in `config.yaml` is automatically mirrored as a Mercari rule (39 → 78 rules total).

### Test Mercari

```powershell
python scripts\test_mercari.py --keyword "dexcom" --limit 5
python main.py --check
python main.py --once
```

Alerts will show `Mercari Match:` in Telegram and a **Marketplace** column in Google Sheets.

---

## Step 8 — Client handoff (Ernest)

Deliver to client **without**:
- Your `.env`
- `secrets/google-credentials.json`
- `data/seen_listings.json`

Include:
- Full project folder
- `.env.example`
- `config.example.yaml`
- `SETUP.md`
- `README.md`

Ernest creates his own accounts and follows this guide on his machine.

---

## Quick troubleshooting

| Error | Fix |
|-------|-----|
| `invalid_client` (eBay 401) | Wrong Client ID/Secret or sandbox/production mismatch |
| Telegram `Unauthorized` | Invalid bot token |
| Telegram message not in channel | Bot not added as channel admin |
| Sheets permission denied | Share sheet with service account email as Editor |
| `google-credentials.json` not found | Place JSON in `secrets/` folder |
| No listings found | Widen keyword or raise `max_price` temporarily |

---

## Current test status checklist

- [ ] `python scripts\test_filter.py` — offline
- [ ] `python scripts\test_state.py` — offline
- [ ] `python scripts\test_ebay.py` — needs real eBay keys
- [ ] `python scripts\scan_dry_run.py` — needs real eBay keys
- [ ] `python scripts\test_telegram.py` — needs real Telegram setup
- [ ] `python scripts\test_sheets.py` — needs Google service account
- [ ] `python main.py --check` — needs Telegram + Sheets
- [ ] `python main.py --once` — full pipeline
- [ ] `python scripts\run_all_tests.py` — all green
