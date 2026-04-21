---
name: build-project-scaffold
description: >-
  Creates the project directory structure, requirements.txt, README.md,
  .gitignore, config.py, and a sample book for the Live Reading Predictor.
  Use when bootstrapping the VoiceRag project from scratch.
---

# Build Project Scaffold

## Goal

Create the complete directory structure and foundational files for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P0 — Foundation** (must run before all other skills)

Other skills depend on the directory structure, `config.py`, and placeholder files this skill creates. If this skill fails, no other skill can proceed.

## Guardrails

1. **Scope lock**: ONLY create files listed in the Directory Structure below. Do NOT create any additional files, modules, or directories not specified here.
2. **No implementation**: Placeholder files must contain ONLY a docstring and a TODO comment. Do NOT write any functional code in files owned by other skills (`main.py`, `speech.py`, `search.py`, `database.py`, `audio_capture.py`, `ingest_books.py`, `index.html`, `style.css`, `script.js`).
3. **Config is sacred**: Copy `config.py` exactly as specified below. Do NOT add, remove, or rename any config variable — other skills import these by exact name.
4. **No dependency changes**: Use the exact packages listed in `requirements.txt`. Do NOT add extra packages, pin versions arbitrarily, or swap libraries.
5. **No overwriting**: If a file already exists with functional code (not a placeholder), do NOT overwrite it. Only create files that are missing.
6. **Sample book integrity**: The sample book MUST start with the exact lines specified below — other skills' verification steps depend on this content.

## Directory Structure to Create

```
VoiceRag/
├── backend/
│   ├── __init__.py
│   ├── main.py              # (placeholder — built by build-api-layer)
│   ├── audio_capture.py     # (placeholder — built by build-speech-module)
│   ├── speech.py            # (placeholder — built by build-speech-module)
│   ├── search.py            # (placeholder — built by build-search-engine)
│   ├── database.py          # (placeholder — built by build-database)
│   └── config.py            # Configuration constants
├── frontend/
│   ├── index.html           # (placeholder — built by build-frontend)
│   ├── style.css            # (placeholder — built by build-frontend)
│   └── script.js            # (placeholder — built by build-frontend)
├── data/
│   └── books/
│       └── sample_book.txt  # Public domain sample for testing
├── scripts/
│   ├── __init__.py
│   └── ingest_books.py      # (placeholder — built by build-database)
├── tests/
│   └── __init__.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Files to Create

### 1. config.py

```python
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WHISPER_MODEL = "medium"
AUDIO_CHUNK_SEC = 3
AUDIO_OVERLAP_SEC = 1
AUDIO_SAMPLE_RATE = 16000
ROLLING_BUFFER_WORDS = 20
SEARCH_PHRASE_LEN = 15
SEARCH_MIN_PHRASE = 5
UPCOMING_LINES = 5
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8000
DB_PATH = os.path.join(BASE_DIR, "data", "library.db")
BOOKS_DIR = os.path.join(BASE_DIR, "data", "books")
FILLER_WORDS = {"um", "uh", "like", "you know", "so", "well", "actually", "basically"}
```

### 2. requirements.txt

Use the latest versions available — run `pip install` without pinning, or pin to known-good versions:

```
openai-whisper
fastapi
uvicorn[standard]
pyaudio
websockets
numpy
```

### 3. .gitignore

```
__pycache__/
*.pyc
*.pyo
data/library.db
.env
venv/
.venv/
*.egg-info/
dist/
build/
```

### 4. README.md

Write a concise README covering:
- Project name and one-line description
- Prerequisites (Python 3.10+)
- Installation steps (`pip install -r requirements.txt`)
- How to ingest books (`python scripts/ingest_books.py`)
- How to run the server (`uvicorn backend.main:app`)
- How to open the display (browser at `http://localhost:8000`)
- Project structure table
- Tech stack summary

### 5. sample_book.txt

Write the first 3 chapters of "A Tale of Two Cities" by Charles Dickens (public domain) directly into the file. Do NOT attempt to fetch from the internet. The agent knows this text. Include at least 100 lines so the search engine has meaningful data to test against.

The file MUST start with these lines (used by other skills' verification tests):

```
It was the best of times, it was the worst of times,
it was the age of wisdom, it was the age of foolishness,
it was the epoch of belief, it was the epoch of incredulity,
it was the season of Light, it was the season of Darkness,
it was the spring of hope, it was the winter of despair,
```

### 6. Placeholder files

For every file that another skill will build (`main.py`, `speech.py`, `search.py`, `database.py`, `audio_capture.py`, `index.html`, `style.css`, `script.js`, `ingest_books.py`), create a placeholder with a module docstring describing its purpose and a `# TODO: implemented by build-<skill-name> skill` comment. Also create `scripts/__init__.py` (empty file) so `python -m scripts.ingest_books` works. This prevents import errors during incremental development.

## Verification

After creating all files, run:
```bash
find /home/tnaik/ws/VoiceRag -type f | head -30
```
Confirm all directories and files exist.
