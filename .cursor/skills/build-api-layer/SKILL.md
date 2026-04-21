---
name: build-api-layer
description: >-
  Builds the FastAPI backend with REST endpoints and WebSocket handler that
  wires together speech, search, and database modules for the Live Reading
  Predictor. Creates main.py. Use when building or modifying the API server.
---

# Build API Layer

## Goal

Implement the FastAPI application at `backend/main.py` for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P3 — Integration Layer** (depends on: ALL other backend skills — build-database, build-search-engine, build-speech-module; blocks: nothing)

This is the last backend skill to run. It wires all modules together. It must NOT be run until all dependency skills have completed and their interfaces are finalized.

## Guardrails

1. **Scope lock**: ONLY modify `backend/main.py`. Do NOT touch `database.py`, `search.py`, `speech.py`, `audio_capture.py`, `config.py`, or any frontend file.
2. **No re-implementation**: Import and use functions from other modules exactly as they are. Do NOT duplicate logic that already exists in `database.py`, `search.py`, or `speech.py` (e.g., do NOT write SQL queries directly in `main.py`).
3. **Interface consumption only**: Use the exact function names and signatures defined by other skills. If an import fails, the dependency skill has a bug — do NOT work around it by reimplementing the function in `main.py`.
4. **No new dependencies**: Do NOT add packages beyond `fastapi` and `uvicorn`. No Flask, no Django, no Socket.IO.
5. **WebSocket JSON contract is frozen**: The JSON payload format shown below is what the frontend expects. Do NOT add, remove, or rename fields without updating the `build-frontend` skill.
6. **No business logic in routes**: Route handlers should be thin wrappers. Search logic stays in `search.py`, transcription in `speech.py`, DB operations in `database.py`.
7. **Lifespan, not startup events**: Use the `lifespan` context manager pattern shown below. Do NOT use `@app.on_event("startup")` — it's deprecated and triggers side effects on import.
8. **Single model instance**: Load Whisper model ONCE in lifespan. Store in module-level variable. Do NOT load per-request or per-WebSocket-connection.
9. **No CORS for prototype**: Do NOT add CORS middleware unless explicitly asked. The frontend is served from the same origin.

## Context

Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` section 3.5 (API Layer) for full specifications.

## Dependencies

This module imports from:
- `backend.database` — `init_db()`, `ingest_book()`, `list_books()`
- `backend.search` — `search_passage()`, `SearchResult`
- `backend.speech` — `load_model()`, `transcribe_chunk()`, `normalize_text()`, `RollingBuffer`
- `backend.audio_capture` — `AudioCapture`
- `backend.config` — all configuration constants

External packages:
- `fastapi`
- `uvicorn`

## File: backend/main.py

### Application Setup

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Live Reading Predictor")
```

- Mount `frontend/` directory as static files at `/static`. Use the project root to construct the path:
  ```python
  import os
  BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")
  ```
- Use a `lifespan` context manager (not the deprecated `@app.on_event("startup")`):
  ```python
  from contextlib import asynccontextmanager

  whisper_model = None

  @asynccontextmanager
  async def lifespan(app):
      global whisper_model
      init_db()
      whisper_model = load_model()
      yield

  app = FastAPI(title="Live Reading Predictor", lifespan=lifespan)
  ```
  This ensures model loading only happens when the server actually starts, not on import.

### Endpoints

#### GET /
Serve `frontend/index.html`.

#### GET /api/books
Return JSON list of all ingested books.

```json
{
  "books": [
    {"book_id": 1, "title": "A Tale of Two Cities", "author": "Charles Dickens", "ingested_at": "..."}
  ]
}
```

#### POST /api/ingest
Accept a text file upload + title + author form fields. Ingest into database.

```json
{"book_id": 1, "title": "...", "status": "success"}
```

Note: `ingest_book()` returns only `book_id`. If you want to include a line count in the response, query `SELECT COUNT(*) FROM lines WHERE book_id = ?` after ingestion.

#### GET /api/search?q=...
Manual search endpoint for testing. Returns SearchResult as JSON or `{"status": "not_found"}`.

#### WebSocket /ws

The core real-time endpoint. Flow:

```
1. Client connects
2. Server starts audio capture in background thread
3. Server enters loop:
   a. Get audio chunk from AudioCapture
   b. Transcribe with Whisper
   c. Normalize text
   d. Add to RollingBuffer
   e. Call search_passage(buffer.get_query())
   f. Send result to client as JSON:
      {
        "status": "found" | "not_found" | "listening",
        "book_title": "..." | null,
        "author": "..." | null,
        "matched_text": "..." | null,
        "upcoming_lines": [...] | [],
        "confidence": 0.95 | 0,
        "transcript": "current transcribed text"
      }
4. On disconnect: stop audio capture, clean up
```

### Error Handling

- Wrap WebSocket loop in try/except for `WebSocketDisconnect`
- If AudioCapture fails (no mic), send error JSON to client: `{"status": "error", "message": "No microphone found"}`
- If Whisper fails on a chunk, skip it and continue with next chunk
- Log all errors to console with timestamps

### Running the Server

The file should be runnable with:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Include an `if __name__ == "__main__"` block:
```python
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

## Important Notes

- The WebSocket handler runs audio capture → transcription → search in a loop. Each iteration takes ~3 seconds (audio chunk duration).
- Use `asyncio.to_thread()` for blocking calls (Whisper transcribe, audio capture) to avoid blocking the event loop.
- The Whisper model should be loaded ONCE at startup and stored as a module-level variable, not loaded per-connection.
- Static files path should be relative to the project root, not the backend directory.

## Verification

After building, the sub-agent MUST verify by:
1. Confirm no syntax errors: `python -c "import ast; ast.parse(open('backend/main.py').read()); print('OK')"` (do NOT import the module directly — it triggers lifespan/model loading)
2. Verify the file contains all expected route decorators: `@app.get("/")`, `@app.get("/api/books")`, `@app.post("/api/ingest")`, `@app.get("/api/search")`, `@app.websocket("/ws")`
3. Verify the file imports from `backend.database`, `backend.search`, `backend.speech`, `backend.audio_capture`
4. Do NOT start the actual server (requires mic + Whisper model download)
