# Session Notes — VoiceRag Prototype Build

**Date:** April 20, 2026
**Machine used:** Linux remote server (tnaik@mvtnaik, no audio hardware)

---

## What Was Built

A live reading predictor prototype — when an author reads from their book into a mic, the system:
1. Captures audio via microphone
2. Converts speech to text using Whisper (local, offline)
3. Searches a SQLite FTS5 database for matching passages
4. Displays the next 4-5 lines on screen via WebSocket

## Architecture

```
Mic → PyAudio → Whisper STT → Search Agent (SQLite FTS5) → WebSocket → Browser Display
```

## Tech Stack

| Component | Technology |
|---|---|
| Speech-to-Text | OpenAI Whisper (local, medium model) |
| Database + Search | SQLite FTS5 |
| Backend | Python + FastAPI |
| Frontend | Vanilla JS + WebSocket (dark theme) |
| Port | 3690 |

## Project Structure

```
VoiceRag/
├── backend/
│   ├── config.py          ← Configuration constants (port=3690, model=medium, etc.)
│   ├── database.py        ← SQLite FTS5 schema + ingestion + search
│   ├── search.py          ← Phrase matching with 15→10→7→5 word fallback
│   ├── speech.py          ← Whisper STT + text normalization + RollingBuffer
│   ├── audio_capture.py   ← PyAudio mic capture with overlap
│   └── main.py            ← FastAPI + WebSocket + all wiring
├── frontend/
│   ├── index.html         ← Dark-themed teleprompter display
│   ├── style.css          ← #0d1117 background, large text
│   └── script.js          ← WebSocket client + auto-reconnect
├── data/
│   ├── books/sample_book.txt  ← 105-line test content
│   └── library.db             ← SQLite DB (auto-created on ingest)
├── scripts/ingest_books.py    ← CLI book ingestion tool
├── prototype/
│   └── 1st_PROTO_SYSTEM_DESIGN.md  ← Full system design document
├── .cursor/
│   ├── skills/            ← 6 build skills + SKILL_MAP.md
│   └── agents/            ← 6 builder subagents
├── requirements.txt
├── .gitignore
└── README.md
```

## What Worked on Linux

- Server starts successfully
- Whisper model loads (medium, on CPU)
- Frontend loads correctly (dark theme, WebSocket connects)
- Search API works: `/api/search?q=the+river+flowed+quietly+under+the+old+stone+bridge`
- Book ingestion works: 94 lines indexed from sample book
- All static files serve correctly (after fix — see issues below)

## Issues Encountered on Linux (All Fixed)

### 1. PyAudio build failed — missing portaudio headers
```
Fix: sudo apt-get install portaudio19-dev && pip install pyaudio
```

### 2. python-multipart not installed
```
Fix: pip install python-multipart (also added to requirements.txt)
```

### 3. Static files 404 (style.css, script.js)
```
Cause: index.html linked "style.css" but static files mounted at "/static"
Fix: Changed href to "/static/style.css" and src to "/static/script.js"
Already fixed in the repo — no action needed.
```

### 4. ALSA/JACK errors — no microphone on remote Linux
```
Cause: Remote Linux server has no audio hardware (no sound card, no mic)
Fix: Run on a machine with a microphone (Mac laptop)
This is NOT a code bug — the code is correct. The server just needs a mic.
```

---

## Steps for Mac Setup (NO CODE CHANGES NEEDED)

Everything is already fixed in the repo. Just run these commands:

### Step 1: Clone or copy the project
```bash
git clone <your-repo-url>
cd VoiceRag
```

### Step 2: Install system dependency (PortAudio for PyAudio)
```bash
brew install portaudio
```

### Step 3: Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Ingest the sample book
```bash
python -m scripts.ingest_books
```
This creates `data/library.db` with 94 indexed lines.

### Step 6: Start the server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 3690
```
First run downloads the Whisper "medium" model (~1.5 GB). This takes a few minutes once.

### Step 7: Open browser
```
http://localhost:3690
```

### Step 8: Speak into your Mac mic
Read lines from the sample book. For example, say:
> "The river flowed quietly under the old stone bridge"

The display should show the next 5 lines from the book.

---

## Quick API Test (No Mic Needed)

To verify search works without speaking:
```
http://localhost:3690/api/search?q=the+river+flowed+quietly+under+the+old+stone+bridge
```

To see ingested books:
```
http://localhost:3690/api/books
```

---

## Important Notes

- The `data/library.db` file is in `.gitignore` — you must run `python -m scripts.ingest_books` on each new machine
- The Whisper model downloads to `~/.cache/whisper/` — one-time download per machine
- The venv directory is also gitignored — create a new one on each machine
- Port is set to **3690** in `backend/config.py`
- All code changes from this session are already committed/saved — no manual fixes needed on Mac
