# FreightIQ
AI-powered freight invoice auditor. Upload a PDF freight invoice → 
extracts structured data → flags billing anomalies using Claude.

## What it does
- Parses unstructured freight PDFs into structured line-item records
- Detects anomalies: math errors, duplicate charges, missing fields, suspicious amounts
- Dashboard showing audit history, error counts, and exception records

## Stack
React · TypeScript · FastAPI · Claude API · SQLite · GitHub Actions CI

## Setup
1. Clone the repo
2. Copy `backend/.env.example` to `backend/.env` and add your Anthropic API key
3. Start backend: `cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`
4. Start frontend: `cd frontend && npm install && npm run dev`
5. Open http://localhost:5173

## Running with Docker

docker build -t freightiq-backend ./backend

docker run --env-file backend/.env -p 8000:8000 freightiq-backend