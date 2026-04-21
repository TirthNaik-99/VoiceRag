# Live Reading Predictor

Predicts and displays upcoming text from an author's published books during a live reading session.

## Prerequisites

- Python 3.10+
- A microphone (built-in or external)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Ingest books

Place `.txt` book files in `data/books/`, then run:

```bash
python -m scripts.ingest_books
```

### 2. Start the server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 3690
```

### 3. Open the display

Navigate to `http://localhost:3690` in your browser.

## Project Structure

| Directory | Purpose |
|---|---|
| `backend/` | Python backend — FastAPI, Whisper STT, SQLite FTS5, search logic |
| `frontend/` | Browser display — HTML/CSS/JS with WebSocket client |
| `data/books/` | Raw `.txt` book files for ingestion |
| `scripts/` | Utility scripts (book ingestion) |
| `tests/` | Test suite |
| `prototype/` | System design documentation |

## Tech Stack

| Component | Technology |
|---|---|
| Speech-to-Text | OpenAI Whisper (local) |
| Database + Search | SQLite FTS5 |
| Backend | Python + FastAPI |
| Frontend | Vanilla JS + WebSocket |
