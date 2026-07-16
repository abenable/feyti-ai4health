# Feyti Demo

Feyti is a regulatory document intelligence demo built on top of the original PaperMind app. Users upload a PDF or DOCX file; the app extracts its text (OCR if scanned), classifies it into an ICH-M4 CTD section with Gemini, and files it into a live dossier folder.

The stack uses a Next.js frontend and a FastAPI backend, with Gemini handling extraction OCR and classification.

## Features

- Drag-and-drop upload for `.pdf` and `.docx` files
- Automatic extraction + OCR for scanned pages
- Gemini structured-output classification into CTD sections
- Live dossier tree that grows as documents are filed
- Health status indicator in the frontend
- Direct browser-to-API communication
- Env-based configuration for local and Docker setups

## Architecture

The app has two services:

- `frontend/`: Next.js 16 on Bun
- `backend/`: FastAPI on Python 3.10 with `uv`

The browser calls the backend directly using `NEXT_PUBLIC_API_URL`. For local development, point it at `http://127.0.0.1:8000`.

## Prerequisites

- Docker & Docker Compose (optional)
- Bun
- Python 3.10+
- `uv`
- A Google Gemini API Key

## Run With Docker

1. Create the backend env file:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Set your Gemini API key in `backend/.env`:
   ```env
   GEMINI_API_KEY=your-gemini-api-key
   ```

2. Create the frontend env file:
   ```bash
   cp frontend/.env.example frontend/.env
   ```
   Set the public API origin in `frontend/.env`:
   ```env
   NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
   ```

3. Start the stack:
   ```bash
   docker compose up --build -d
   ```

4. Open `http://localhost:3000`.

Because `NEXT_PUBLIC_API_URL` is embedded into the frontend bundle, changing `frontend/.env` requires rebuilding the frontend image.

## Run Locally Without Docker

1. Set up the backend env:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. Start the backend:
   ```bash
   cd backend
   uv sync
   uv run python -m uvicorn main:app --reload
   ```

3. Set up frontend env for local development:
   ```bash
   cp frontend/.env.example frontend/.env.local
   ```
   Then set:
   ```env
   NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
   ```

4. Start the frontend:
   ```bash
   cd frontend
   bun install
   bun run dev
   ```

5. Open `http://localhost:3000`.

## Environment Variables

### `backend/.env`

```env
GEMINI_API_KEY=your-gemini-api-key
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### `frontend/.env` for Docker

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### `frontend/.env.local` for local frontend development

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Verification

- `bun run lint`
- `bun run build`
- `uv run pytest tests/test_pipeline.py`
- `uv run python -m compileall app main.py`

## Stack

- [Next.js 16](https://nextjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://aistudio.google.com/)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [Bun](https://bun.sh/) & [uv](https://github.com/astral-sh/uv)
