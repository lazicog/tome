# Tome

AI-powered learning companion for technical books (PDFs).

## Phase 1 Features

- Upload a technical PDF
- Background PDF processing (extract -> chunk -> embed -> store)
- RAG retrieval with ChromaDB + BM25 hybrid scoring
- Chat with a Tutor agent over your uploaded book
- Streaming responses over SSE
- Basic Next.js UI (book library + chat page)

## Tech Stack

- Backend: FastAPI, LangChain chat models, ChromaDB, sentence-transformers, PyMuPDF
- Frontend: Next.js (App Router), TypeScript

## Quick Start

1. Copy env:

```bash
cp .env.example .env
```

2. Run with Docker:

```bash
docker compose up
```

3. Open:

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Manual Run

### Backend

```bash
cd backend
python -m venv .venv
# activate venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `GET /api/health`
- `GET /api/books`
- `POST /api/books` (multipart PDF upload)
- `GET /api/books/{book_id}`
- `POST /api/books/{book_id}/chat` (SSE)
