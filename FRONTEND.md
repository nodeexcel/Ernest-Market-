# Ernest Market Dashboard (Frontend + API)

A React + Tailwind dashboard with a thin FastAPI wrapper around the **existing** scan pipeline. No changes to `src/pipeline.py` or core backend logic.

## Architecture

```
frontend/   → React + Tailwind (port 5173)
api/        → FastAPI wrapper (port 8000)
src/        → Existing Ernest Market pipeline (unchanged)
```

## Prerequisites

- Python 3.10+ with project venv activated
- Node.js 18+
- Configured `.env`, `config.yaml`, and Google credentials (same as CLI)

## 1. Install API dependencies

```powershell
cd "d:\ET Projects\client\ernest-market"
.\venv\Scripts\activate
pip install -r api\requirements.txt
```

## 2. Start the API server

```powershell
uvicorn api.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

## 3. Install and run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

## Production build

```powershell
cd frontend
npm run build
npm run preview
```

Serve `frontend/dist` behind your reverse proxy and proxy `/api` to uvicorn.

## Dashboard pages

| Page | Description |
|------|-------------|
| **Overview** | Stats, charts, scan controls, activity feed |
| **Live Processing** | Step-by-step progress, logs, scan triggers |
| **Results** | Searchable deals table + Excel/CSV download |
| **Configuration** | Edit buy rules (`config.yaml`) |
| **History** | Past dashboard scans + exports |

## Notes

- **Full scan** uses the same `ScanPipeline` as `python main.py --once`
- **Dry run** uses `FilterScanPipeline` (no Telegram/Sheets alerts)
- Deal data is read from your **Google Sheet**; exports generate `.xlsx` / `.csv`
- Task Scheduler can still run `main.py --once` independently; avoid concurrent scans
