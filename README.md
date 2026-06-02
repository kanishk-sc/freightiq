# FreightIQ

AI-powered freight invoice auditor. Upload a PDF freight invoice, extract structured fields with Claude, and run an AI billing audit to catch anomalies.

## Stack

- **Frontend:** React, TypeScript, Tailwind CSS (Vite)
- **Backend:** FastAPI, SQLModel (SQLite), pdfplumber, Anthropic Claude
- **CI:** GitHub Actions (Ruff + TypeScript)

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Anthropic API key](https://console.anthropic.com/)

## Setup

### 1. API key

Set your Anthropic API key in the environment:

**Windows (PowerShell):**

```powershell
$env:ANTHROPIC_API_KEY = "your-api-key-here"
```

**macOS / Linux:**

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. Backend

```bash
cd freightiq/backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Generate a sample invoice PDF (optional, includes intentional billing errors for testing):

```bash
python generate_sample.py
```

Start the API server on port **8000**:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend

In a second terminal:

```bash
cd freightiq/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api/*` to `http://localhost:8000`.

## Usage

1. **Upload** — Drop `backend/sample_invoice.pdf` (or any freight invoice PDF).
2. **Review** — View extracted carrier, dates, route, and line items.
3. **Audit** — Click **Run Audit** to flag math errors, duplicates, missing fields, and more.
4. **Dashboard** — See totals and recent invoices with flag counts.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload PDF, extract fields, store invoice |
| POST | `/audit/{invoice_id}` | Run AI audit, store flags |
| GET | `/invoices` | List invoices with flag counts |
| GET | `/invoices/{invoice_id}` | Full invoice + audit flags |
| GET | `/dashboard` | Aggregate stats |

## Project layout

```
freightiq/
  backend/          # FastAPI app
  frontend/         # React UI
  .github/workflows/ci.yml
```

## Development

```bash
# Backend lint
cd backend && ruff check .

# Frontend typecheck
cd frontend && npm run typecheck
```

## License

MIT
