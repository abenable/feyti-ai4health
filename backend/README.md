# Feyti Demo Backend

This is the FastAPI backend for the Feyti regulatory document demo. It accepts uploaded PDF and DOCX files, extracts their text (with OCR for scanned pages), classifies them into an ICH-M4 CTD section via Gemini, and files them into a filesystem-backed dossier.

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)

## Environment

Copy the example env file:

```bash
cp .env.example .env
```

Supported variables:

```env
GEMINI_API_KEY=your-gemini-api-key
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

`GEMINI_API_KEY` is required. `BACKEND_CORS_ORIGINS` should include every frontend origin that will call the API from a browser.

## Local Development

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Start the API:
   ```bash
   uv run python -m uvicorn main:app --reload
   ```

3. Health check:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

## API Endpoints

### `POST /api/v1/documents/analyze`

Upload a PDF or DOCX file for a Gemini summary (original PaperMind behavior).

### `POST /api/v1/documents/process`

Run the full Feyti pipeline: extract, classify, and file into the dossier.

### `GET /api/v1/dossier/tree`

Return the accumulated dossier structure.

### `GET /health`

Returns `{ "status": "ok" }`.
