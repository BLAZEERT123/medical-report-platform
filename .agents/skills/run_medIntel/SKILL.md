---
name: run_medIntel
description: >
  Run the MedIntel Medical Report Intelligence Platform. Triggered when the user says
  "run", "start", "launch", "start the app", "run the project", or similar.
  Starts the FastAPI backend and the Vite React frontend for this project.
---

# Run MedIntel Platform

When triggered, start the full MedIntel stack - FastAPI backend + Vite frontend - using the project venv.

## Project Layout

`
medical-report-platform/
├── venv/                    <- Python virtual environment
├── backend/main.py          <- FastAPI app entry point
├── frontend-web/            <- Vite + React frontend
└── .env                     <- API keys / config
`

## Step 1 — Start the FastAPI Backend (background task)

`powershell
# From the project root (medical-report-platform/)
.\\venv\\Scripts\\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
`

- Backend runs on http://127.0.0.1:8000
- Swagger docs at http://127.0.0.1:8000/docs
- Wait ~3 seconds for startup before opening the frontend.

## Step 2 — Start the Vite Frontend

`powershell
# From frontend-web/ subdirectory
npm run dev
`

- Frontend serves on http://localhost:5173

## Step 3 — Health Check

`powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing
`

Expected response: {"status":"ok","version":"1.0.0"}

## Common Issues

- ModuleNotFoundError: use .\\venv\\Scripts\\python, not global python
- Port 8000 in use: Get-Process -Name python | Stop-Process
- OPENAI_API_KEY missing: edit .env and set OPENAI_API_KEY=sk-...
- Tesseract not found: install from https://github.com/UB-Mannheim/tesseract/wiki

## Bug Fixes Applied

### False CRITICAL alerts for in-range values (fixed in flagging_service.py)

_parse_range() now handles:
- Reference ranges with trailing units e.g. "13 - 17 g/dL"
- Word separator e.g. "70 to 110"
- All Unicode dash variants (en-dash, em-dash, figure-dash)

Previously, ranges with units or "to" separators failed to parse,
returning (None, None), which bypassed the in-range guard in _is_critical()
and caused values correctly within the lab's stated normal range to be
incorrectly flagged CRITICAL.
