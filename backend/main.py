"""FastAPI application — WebSocket handler, REST endpoints, module wiring."""

import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.audio_capture import AudioCapture
from backend.config import (
    AUDIO_CHUNK_SEC,
    AUDIO_OVERLAP_SEC,
    AUDIO_SAMPLE_RATE,
    WEBSOCKET_HOST,
    WEBSOCKET_PORT,
)
from backend.database import init_db, ingest_book, list_books
from backend.search import SearchResult, search_passage
from backend.speech import RollingBuffer, load_model, normalize_text, transcribe_chunk

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

whisper_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_model
    init_db()
    whisper_model = load_model()
    yield


app = FastAPI(title="Live Reading Predictor", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend")),
    name="static",
)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.get("/api/books")
async def get_books():
    books = list_books()
    return {"books": books}


@app.post("/api/ingest")
async def ingest(
    file: UploadFile,
    title: str = Form(...),
    author: str = Form(...),
):
    suffix = os.path.splitext(file.filename or ".txt")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        book_id = ingest_book(tmp_path, title, author)
    finally:
        os.unlink(tmp_path)

    return {"book_id": book_id, "title": title, "status": "success"}


@app.get("/api/search")
async def manual_search(q: str = ""):
    if not q.strip():
        return {"status": "not_found"}

    result = search_passage(q)
    if result is None:
        return {"status": "not_found"}

    return {"status": "found", **asdict(result)}


# ---------------------------------------------------------------------------
# WebSocket — live speech-to-search pipeline
# ---------------------------------------------------------------------------


def _build_ws_payload(
    result: SearchResult | None,
    transcript: str,
) -> dict:
    """Build the frozen JSON contract payload for the WebSocket client."""
    if result is None:
        status = "listening" if not transcript else "not_found"
        return {
            "status": status,
            "book_title": None,
            "author": None,
            "matched_text": None,
            "upcoming_lines": [],
            "confidence": 0,
            "transcript": transcript,
        }

    return {
        "status": "found",
        "book_title": result.book_title,
        "author": result.author,
        "matched_text": result.matched_text,
        "upcoming_lines": result.upcoming_lines,
        "confidence": result.confidence,
        "transcript": transcript,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    capture = AudioCapture(
        sample_rate=AUDIO_SAMPLE_RATE,
        chunk_duration=AUDIO_CHUNK_SEC,
        overlap=AUDIO_OVERLAP_SEC,
    )
    buffer = RollingBuffer()

    try:
        await asyncio.to_thread(capture.start)
    except RuntimeError as exc:
        await ws.send_json({"status": "error", "message": str(exc)})
        await ws.close()
        return

    try:
        while True:
            try:
                audio_chunk = await asyncio.to_thread(capture.get_chunk)
            except RuntimeError as exc:
                logger.error("Audio capture error: %s", exc)
                await ws.send_json({"status": "error", "message": str(exc)})
                break

            try:
                raw_text = await asyncio.to_thread(
                    transcribe_chunk, whisper_model, audio_chunk
                )
            except Exception:
                logger.exception("Whisper transcription failed, skipping chunk")
                continue

            cleaned = normalize_text(raw_text)
            if cleaned:
                buffer.add(cleaned)

            query = buffer.get_query()
            transcript = query

            result = search_passage(query) if query else None

            payload = _build_ws_payload(result, transcript)
            await ws.send_json(payload)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Unexpected error in WebSocket handler")
    finally:
        capture.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=WEBSOCKET_HOST,
        port=WEBSOCKET_PORT,
        reload=True,
    )
