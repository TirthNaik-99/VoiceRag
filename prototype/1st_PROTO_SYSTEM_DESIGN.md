# System Design Document: Live Reading Predictor

## 1. System Overview

| Field | Details |
|---|---|
| **Project Name** | Live Reading Predictor |
| **Purpose** | Predict and display upcoming text from an author's published books during a live reading |
| **Architecture Style** | Monolithic (single machine, single process) |
| **Deployment** | Local (laptop) |
| **Target Latency** | < 2 seconds end-to-end |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HP ZBook 8 G1i (32 GB RAM)                       │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │ MICROPHONE   │                                                        │
│  │ (Built-in /  │                                                        │
│  │  External)   │                                                        │
│  └──────┬──────┘                                                        │
│         │ Raw Audio (PCM, 16kHz)                                        │
│         v                                                               │
│  ┌──────────────────────────────────────────────────┐                    │
│  │              PYTHON BACKEND (FastAPI)            │                    │
│  │                                                  │                    │
│  │  ┌────────────┐    ┌────────────┐    ┌────────┐  │   ┌────────────┐  │
│  │  │ Audio      │    │ Whisper    │    │ Search │  │   │ SQLite     │  │
│  │  │ Capture    │───>│ STT       │───>│ Agent  │──┼──>│ FTS5       │  │
│  │  │ (PyAudio)  │    │ (medium)  │    │        │  │   │ (library.db│) │
│  │  └────────────┘    └────────────┘    └───┬────┘  │   └────────────┘  │
│  │                                          │       │                    │
│  │                                     WebSocket    │                    │
│  │                                          │       │                    │
│  └──────────────────────────────────────────┼───────┘                    │
│                                             │                            │
│                                             v                            │
│                                    ┌─────────────────┐                   │
│                                    │ BROWSER          │                   │
│                                    │ (Chrome/Firefox) │                   │
│                                    │                  │                   │
│                                    │ Live Display     │                   │
│                                    │ (Vanilla JS +   │                   │
│                                    │  WebSocket)      │                   │
│                                    └─────────────────┘                   │
│                                             │                            │
│                                        HDMI / Screen                     │
│                                             v                            │
│                                    ┌─────────────────┐                   │
│                                    │ PROJECTOR /      │                   │
│                                    │ AUDIENCE SCREEN  │                   │
│                                    └─────────────────┘                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 Audio Capture Module

```
Module: audio_capture.py

Responsibility: Continuously capture audio from microphone in chunks

Input:  Raw microphone stream
Output: Audio chunks (3-5 second windows)

┌──────────────────────────────────────────────────────┐
│                                                      │
│   Mic ──> PyAudio Stream ──> Audio Buffer (ring)     │
│                                    │                 │
│                              Every 3 seconds         │
│                                    │                 │
│                                    v                 │
│                           Emit audio chunk           │
│                           to Whisper module           │
│                                                      │
└──────────────────────────────────────────────────────┘

Config:
  - Sample rate:    16000 Hz
  - Channels:       1 (mono)
  - Chunk duration: 3 seconds (configurable)
  - Format:         16-bit PCM
  - Overlap:        1 second (to avoid cutting words at boundaries)
```

### 3.2 Speech-to-Text Module (Whisper)

```
Module: speech.py

Responsibility: Convert audio chunks to text

Input:  Audio chunk (3 seconds of PCM audio)
Output: Transcribed text string

┌──────────────────────────────────────────────────────┐
│                                                      │
│   Audio Chunk                                        │
│       │                                              │
│       v                                              │
│   Whisper Model (medium)                             │
│       │                                              │
│       v                                              │
│   Raw Transcription                                  │
│       │                                              │
│       v                                              │
│   Text Normalizer                                    │
│   - Lowercase                                        │
│   - Remove filler words (um, uh, you know)           │
│   - Strip extra whitespace                           │
│       │                                              │
│       v                                              │
│   Cleaned Text ──> Rolling Buffer                    │
│                                                      │
└──────────────────────────────────────────────────────┘

Rolling Buffer:
  - Maintains last 20-30 words spoken
  - Sliding window: drops oldest words as new ones arrive
  - This buffer is what gets sent to the Search Agent

  Example:
    Time 0s:  "it was the best of times"
    Time 3s:  "it was the best of times it was the worst of times"
    Time 6s:  "the worst of times it was the age of wisdom"
              (oldest words dropped to keep ~20-30 word window)
```

### 3.3 Search Agent

```
Module: search.py

Responsibility: Find matching passage in database, return next lines

Input:  Query string (last 15-20 words from rolling buffer)
Output: Match result (book title, matched line, next 5 lines) OR "not found"

┌──────────────────────────────────────────────────────┐
│                                                      │
│   Rolling Buffer (last 20 words)                     │
│       │                                              │
│       v                                              │
│   Build FTS5 Query                                   │
│   - Extract last 15 words                            │
│   - Format as phrase query: "word1 word2 word3..."   │
│       │                                              │
│       v                                              │
│   ┌──────────────────────────────┐                   │
│   │ Strategy 1: Exact phrase     │                   │
│   │ MATCH '"it was the best of"' │──> Found? ──> Yes │
│   └──────────────────────────────┘              │    │
│       │ No                                      │    │
│       v                                         │    │
│   ┌──────────────────────────────┐              │    │
│   │ Strategy 2: Shorter phrase   │              │    │
│   │ MATCH '"best of times"'      │──> Found? ──>│    │
│   └──────────────────────────────┘              │    │
│       │ No                                      │    │
│       v                                         v    │
│   Return "source not present"     Fetch next 5 lines │
│                                   from same book     │
│                                         │            │
│                                         v            │
│                                   Return result:     │
│                                   - book_title       │
│                                   - chapter          │
│                                   - matched_line     │
│                                   - next_5_lines[]   │
│                                   - confidence_score │
│                                                      │
└──────────────────────────────────────────────────────┘

Search Fallback Strategy:
  1. Try full 15-word phrase match
  2. If no result → try 10-word phrase
  3. If no result → try 7-word phrase
  4. If no result → try individual keyword match (NEAR operator)
  5. If no result → return "source not present"
```

### 3.4 Database Layer

```
Module: database.py

Responsibility: Store books, provide search and retrieval

File: data/library.db (SQLite)

┌──────────────────────────────────────────────────────┐
│                                                      │
│   TABLE: books                                       │
│   ┌──────────┬───────────┬──────────┬─────────────┐  │
│   │ book_id  │ title     │ author   │ ingested_at │  │
│   │ INTEGER  │ TEXT      │ TEXT     │ TIMESTAMP   │  │
│   │ PK       │ NOT NULL  │ NOT NULL │ AUTO        │  │
│   └──────────┴───────────┴──────────┴─────────────┘  │
│                                                      │
│   TABLE: lines                                       │
│   ┌──────────┬──────────┬─────────────┬───────────┐  │
│   │ line_id  │ book_id  │ line_number │ content   │  │
│   │ INTEGER  │ INTEGER  │ INTEGER     │ TEXT      │  │
│   │ PK       │ FK       │ NOT NULL    │ NOT NULL  │  │
│   └──────────┴──────────┴─────────────┴───────────┘  │
│                                                      │
│   VIRTUAL TABLE: lines_fts (FTS5)                    │
│   ┌───────────────────────────────────────────────┐   │
│   │ content    → indexed for full-text search     │   │
│   │ content_id → maps back to lines.line_id       │   │
│   └───────────────────────────────────────────────┘   │
│                                                      │
│   INDEX: idx_lines_book_linenum                      │
│   ON lines(book_id, line_number)                     │
│   → Fast retrieval of "next 5 lines after match"     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 3.5 API Layer (FastAPI)

```
Module: main.py

Endpoints:

  GET  /                    → Serve frontend HTML page
  WS   /ws                  → WebSocket for live updates to browser
  POST /api/ingest          → Upload and ingest a new book
  GET  /api/books           → List all ingested books
  GET  /api/search?q=...    → Manual text search (for testing)

WebSocket Flow:

  Browser ←──── WebSocket ────── FastAPI
                                    │
                    Pushes JSON every time a new match is found:
                    {
                      "status": "found" | "not_found",
                      "book_title": "The Great Novel",
                      "chapter": 1,
                      "matched_text": "it was the best of times",
                      "upcoming_lines": [
                        "it was the worst of times",
                        "it was the age of wisdom",
                        "it was the age of foolishness",
                        "it was the epoch of belief",
                        "it was the epoch of incredulity"
                      ],
                      "confidence": 0.95
                    }
```

### 3.6 Frontend Display

```
File: frontend/index.html + script.js + style.css

Layout:
┌─────────────────────────────────────────────────────┐
│                                                     │
│            LIVE READING PREDICTOR                    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  Book: The Great Novel                       │    │
│  │  Chapter: 1                                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  Currently reading:                          │    │
│  │  "it was the best of times"                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  Coming next:                                │    │
│  │                                              │    │
│  │  ► it was the worst of times                 │    │
│  │    it was the age of wisdom                  │    │
│  │    it was the age of foolishness             │    │
│  │    it was the epoch of belief                │    │
│  │    it was the epoch of incredulity           │    │
│  │                                              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  Status: ● Listening          Confidence: 95%       │
│                                                     │
└─────────────────────────────────────────────────────┘

WebSocket Client (script.js):
  - Connects to ws://localhost:8000/ws
  - On message: parse JSON, update DOM elements
  - On disconnect: show "Reconnecting..." status
  - Auto-reconnect with 1 second retry
```

---

## 4. Data Flow (End-to-End Sequence)

```
Time ──────────────────────────────────────────────────────────>

  │ Audio Capture    │  Whisper STT  │ Search Agent  │ Display │
  │                  │               │               │         │
  │ Capture 3s chunk │               │               │         │
  │ ────────────────>│               │               │         │
  │                  │ Transcribe    │               │         │
  │                  │ (~1000ms)     │               │         │
  │                  │ ─────────────>│               │         │
  │                  │               │ Build query   │         │
  │                  │               │ Search FTS5   │         │
  │                  │               │ (~10ms)       │         │
  │                  │               │ Fetch lines   │         │
  │                  │               │ (~5ms)        │         │
  │                  │               │ ─────────────>│         │
  │                  │               │               │ Update  │
  │                  │               │               │ DOM     │
  │                  │               │               │ (~1ms)  │
  │                  │               │               │         │
  │ Capture next     │               │               │         │
  │ chunk (parallel) │               │               │         │
  │ ────────────────>│               │               │         │
  │        ...       │     ...       │     ...       │  ...    │

Total latency per cycle: ~1000-2000ms (dominated by Whisper)
Pipeline is OVERLAPPED: audio capture runs in parallel with processing
```

---

## 5. Book Ingestion Pipeline

```
                    How books get into the database

  ┌──────────┐     ┌───────────────┐     ┌──────────────┐     ┌──────────┐
  │ Raw Book │     │ Text          │     │ Line         │     │ SQLite   │
  │ File     │────>│ Cleaner       │────>│ Splitter     │────>│ Insert   │
  │ (.txt)   │     │               │     │              │     │ + Index  │
  └──────────┘     └───────────────┘     └──────────────┘     └──────────┘

  Step 1: Place .txt file in data/books/
  Step 2: Run ingestion script or call POST /api/ingest
  Step 3: Cleaner:
           - Remove extra blank lines
           - Normalize unicode (smart quotes → straight quotes)
           - Strip headers/footers/page numbers
  Step 4: Splitter:
           - Split into individual lines/sentences
           - Assign sequential line_number
           - Detect chapter boundaries (optional)
  Step 5: Insert into 'lines' table + FTS5 index

  Processing time: ~1-5 seconds per book (one-time cost)
```

---

## 6. Configuration

```
File: config.py

WHISPER_MODEL       = "medium"        # tiny|base|small|medium|large-v3
AUDIO_CHUNK_SEC     = 3               # seconds per audio chunk
AUDIO_OVERLAP_SEC   = 1               # overlap between chunks
AUDIO_SAMPLE_RATE   = 16000           # Hz
ROLLING_BUFFER_WORDS = 20             # words kept in search buffer
SEARCH_PHRASE_LEN   = 15              # words used in search query
SEARCH_MIN_PHRASE   = 5               # minimum phrase length for fallback
UPCOMING_LINES      = 5               # lines to show after match
WEBSOCKET_PORT      = 8000            # backend port
DB_PATH             = "data/library.db"
BOOKS_DIR           = "data/books/"
```

---

## 7. Latency Budget

```
Component              Target       Max Acceptable
─────────────────────────────────────────────────
Audio capture          3000ms       3000ms (fixed chunk size)
Whisper transcription   800ms       2000ms
Text normalization        5ms         10ms
FTS5 search              10ms         50ms
Line retrieval            5ms         20ms
WebSocket push            1ms          5ms
DOM render                1ms          5ms
─────────────────────────────────────────────────
Total (processing)     ~822ms       ~2090ms
Total (with capture)   ~3822ms      ~5090ms

Note: Audio capture overlaps with processing,
so effective update rate = max(capture, processing)
                         = ~3 seconds between updates
```

---

## 8. Error Handling

| Error Condition | Handling |
|---|---|
| No mic detected | Show "No microphone found" on display |
| Whisper fails | Skip chunk, continue with next |
| No match found | Show "Source not present" on display |
| DB connection fail | Retry 3x, then show error |
| WebSocket drops | Auto-reconnect with 1s retry |
| Empty transcription | Ignore (silence), keep last result |
| Multiple matches | Return highest-ranked match |

---

## 9. File Manifest

```
live-reading-predictor/
│
├── backend/
│   ├── main.py              # FastAPI app, WebSocket, routes
│   ├── audio_capture.py     # Microphone capture with PyAudio
│   ├── speech.py            # Whisper transcription + text normalization
│   ├── search.py            # FTS5 query builder + fallback strategy
│   ├── database.py          # SQLite setup, ingestion, retrieval
│   └── config.py            # All configurable parameters
│
├── frontend/
│   ├── index.html           # Display layout
│   ├── style.css            # Dark theme, large readable text
│   └── script.js            # WebSocket client + DOM updates
│
├── data/
│   ├── books/               # Drop .txt book files here
│   └── library.db           # Auto-created SQLite database
│
├── scripts/
│   └── ingest_books.py      # Batch ingestion script
│
├── requirements.txt         # Python dependencies
└── README.md                # Setup and usage instructions
```

---

## 10. Dependencies

```
requirements.txt:

openai-whisper==20231117     # Speech-to-text
fastapi==0.104.1             # Web framework
uvicorn==0.24.0              # ASGI server
pyaudio==0.2.14              # Microphone access
websockets==12.0             # WebSocket support
numpy==1.26.2                # Audio processing (Whisper dependency)
```

---

## 11. Build Phases

| Phase | What | Deliverable | Test |
|---|---|---|---|
| 1 | Database + Ingestion | Books stored in SQLite | Query DB manually |
| 2 | Search Engine | FTS5 phrase matching | Type query, get results |
| 3 | API Layer | FastAPI endpoints | curl / browser test |
| 4 | Frontend Display | HTML page with WebSocket | See live updates |
| 5 | Whisper Integration | Audio → Text pipeline | Speak → see text |
| 6 | Full Pipeline | All components connected | Live demo |

---

## 12. Tech Stack Summary

| Component | Technology | Cost |
|---|---|---|
| Speech-to-Text | Whisper (local, medium model) | $0 |
| Database + Search | SQLite FTS5 | $0 |
| Backend | Python + FastAPI | $0 |
| Frontend | Vanilla JS + WebSocket | $0 |
| Hardware | HP ZBook 8 G1i (32 GB RAM) | $0 |
| **Total** | | **$0** |

---

## 13. Future Upgrades (Path A → Path B)

| Current (Prototype) | Future (Production) |
|---|---|
| SQLite FTS5 | Elasticsearch (better fuzzy matching) |
| Single machine | Client-server architecture |
| Vanilla JS frontend | React / Svelte |
| Local deployment | Cloud deployment |
| Manual book ingestion | Automated OCR + PDF pipeline |
