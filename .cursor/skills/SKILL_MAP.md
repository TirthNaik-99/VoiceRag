# Skill Map & Parallelization Strategy

## Skill Inventory

| # | Skill | Priority | Files Owned | Lines |
|---|---|---|---|---|
| 1 | `build-project-scaffold` | **P0** — Foundation | `config.py`, `requirements.txt`, `.gitignore`, `README.md`, `sample_book.txt`, all placeholders | 147 |
| 2 | `build-database` | **P1** — Core Data | `backend/database.py`, `scripts/ingest_books.py` | 138 |
| 3 | `build-speech-module` | **P1** — Audio Pipeline | `backend/speech.py`, `backend/audio_capture.py` | 156 |
| 4 | `build-frontend` | **P1** — Display Layer | `frontend/index.html`, `frontend/style.css`, `frontend/script.js` | 223 |
| 5 | `build-search-engine` | **P2** — Search Logic | `backend/search.py` | 134 |
| 6 | `build-api-layer` | **P3** — Integration | `backend/main.py` | 172 |

---

## Dependency Graph

```
                    ┌──────────────────────────┐
                    │  P0: build-project-      │
                    │      scaffold             │
                    │  (foundation — run first) │
                    └────────────┬─────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            v                    v                    v
 ┌────────────────────┐ ┌─────────────────┐ ┌────────────────┐
 │ P1: build-database │ │ P1: build-      │ │ P1: build-     │
 │                    │ │     speech-      │ │     frontend   │
 │ Exports:           │ │     module       │ │                │
 │ - init_db()        │ │                  │ │ Consumes:      │
 │ - ingest_book()    │ │ Exports:         │ │ - WS JSON      │
 │ - search_fts()     │ │ - load_model()   │ │   contract     │
 │ - get_lines_after()│ │ - transcribe()   │ │                │
 │ - get_book_info()  │ │ - normalize()    │ │ No backend     │
 │ - list_books()     │ │ - RollingBuffer  │ │ dependency     │
 │                    │ │ - AudioCapture   │ │                │
 └────────┬───────────┘ └────────┬────────┘ └────────────────┘
          │                      │
          v                      │
 ┌────────────────────┐          │
 │ P2: build-search-  │          │
 │     engine          │          │
 │                     │          │
 │ Imports from:       │          │
 │ - database.py       │          │
 │ - config.py         │          │
 │                     │          │
 │ Exports:            │          │
 │ - SearchResult      │          │
 │ - search_passage()  │          │
 └────────┬────────────┘          │
          │                       │
          └───────────┬───────────┘
                      │
                      v
           ┌──────────────────┐
           │ P3: build-api-   │
           │     layer         │
           │                   │
           │ Imports from:     │
           │ - database.py     │
           │ - search.py       │
           │ - speech.py       │
           │ - audio_capture.py│
           │ - config.py       │
           │                   │
           │ Wires everything  │
           │ together           │
           └──────────────────┘
```

---

## Execution Rounds

### Round 1 — Foundation (sequential, single agent)

| Agent | Skill | What It Does |
|---|---|---|
| Agent 0 | `build-project-scaffold` | Creates all directories, `config.py`, `requirements.txt`, `.gitignore`, `README.md`, sample book, placeholder files |

**Must complete before Round 2 starts.** All other skills depend on the directory structure and `config.py` this creates.

### Round 2 — Core Components (parallel, 3 agents)

| Agent | Skill | What It Does | Independent? |
|---|---|---|---|
| Agent 1 | `build-database` | SQLite schema, FTS5, ingestion pipeline | Yes — no backend dependencies |
| Agent 2 | `build-speech-module` | Whisper STT, audio capture, rolling buffer | Yes — no backend dependencies |
| Agent 3 | `build-frontend` | HTML display, CSS theme, WebSocket client | Yes — only needs JSON contract (in skill) |

**All 3 run simultaneously.** They touch different files and have no cross-dependencies.

### Round 3 — Search Logic (sequential, single agent)

| Agent | Skill | What It Does | Depends On |
|---|---|---|---|
| Agent 4 | `build-search-engine` | FTS5 query builder, fallback strategy | `database.py` from Round 2 |

**Must wait for Round 2 Agent 1 (database) to complete.** Imports `search_fts()`, `get_lines_after()`, `get_book_info()` from `database.py`.

### Round 4 — Integration (sequential, single agent)

| Agent | Skill | What It Does | Depends On |
|---|---|---|---|
| Agent 5 | `build-api-layer` | FastAPI app, WebSocket handler, wires all modules | ALL Round 2 + Round 3 skills |

**Must wait for ALL previous rounds to complete.** Imports from every backend module.

---

## Execution Timeline

```
Time ─────────────────────────────────────────────────────────>

Round 1:  ██████ build-project-scaffold
          │
Round 2:  ├── ████████████ build-database        ──┐
          ├── ████████████ build-speech-module     ──┤ parallel
          └── ████████████ build-frontend          ──┘
                                                    │
Round 3:                   ████████ build-search-engine
                                                    │
Round 4:                            ████████████ build-api-layer

Total agents: 6 (1 + 3 parallel + 1 + 1)
```

---

## File Ownership Map

Each file is owned by exactly ONE skill. No two skills may modify the same file.

| File | Owner Skill | Consumers |
|---|---|---|
| `backend/config.py` | build-project-scaffold | ALL skills (read-only) |
| `backend/__init__.py` | build-project-scaffold | — |
| `backend/database.py` | **build-database** | build-search-engine, build-api-layer |
| `backend/search.py` | **build-search-engine** | build-api-layer |
| `backend/speech.py` | **build-speech-module** | build-api-layer |
| `backend/audio_capture.py` | **build-speech-module** | build-api-layer |
| `backend/main.py` | **build-api-layer** | — |
| `frontend/index.html` | **build-frontend** | — |
| `frontend/style.css` | **build-frontend** | — |
| `frontend/script.js` | **build-frontend** | — |
| `scripts/__init__.py` | build-project-scaffold | — |
| `scripts/ingest_books.py` | **build-database** | — |
| `data/books/sample_book.txt` | build-project-scaffold | build-database (ingest) |
| `data/library.db` | build-database (auto-created) | build-search-engine |
| `requirements.txt` | build-project-scaffold | — |
| `.gitignore` | build-project-scaffold | — |
| `README.md` | build-project-scaffold | — |

---

## Interface Contracts (Cross-Skill API)

These are the exact function/class signatures that form the contract between skills. Changing any of these requires updating ALL consuming skills.

### database.py → search.py, main.py

```python
def init_db() -> None
def ingest_book(filepath: str, title: str, author: str) -> int
def get_lines_after(book_id: int, line_number: int, count: int = 5) -> list[str]
def get_book_info(book_id: int) -> dict  # {book_id, title, author, ingested_at}
def list_books() -> list[dict]
def search_fts(query: str) -> list[dict]  # [{line_id, book_id, line_number, content, rank}]
```

### search.py → main.py

```python
@dataclass
class SearchResult:
    book_id: int
    book_title: str
    author: str
    line_number: int
    matched_text: str
    upcoming_lines: list[str]
    confidence: float

def search_passage(query: str) -> SearchResult | None
```

### speech.py → main.py

```python
def load_model(model_name: str = None) -> whisper.Whisper
def transcribe_chunk(model, audio_chunk: np.ndarray) -> str
def normalize_text(raw: str) -> str

class RollingBuffer:
    def __init__(self, max_words: int)
    def add(self, text: str) -> None
    def get_query(self, num_words: int = None) -> str
    def clear(self) -> None
    word_count: int  # property
```

### audio_capture.py → main.py

```python
class AudioCapture:
    def __init__(self, sample_rate: int, chunk_duration: float, overlap: float)
    def start(self) -> None
    def stop(self) -> None
    def get_chunk(self) -> np.ndarray
    def is_active(self) -> bool
```

### main.py → frontend (WebSocket JSON)

```json
{
  "status": "found | not_found | listening | error",
  "book_title": "string or null",
  "author": "string or null",
  "matched_text": "string or null",
  "upcoming_lines": ["string"],
  "confidence": 0.0,
  "transcript": "string",
  "message": "string (only when status=error)"
}
```

---

## Rules for Adding New Skills

1. **Check the file ownership map** — never create a skill that modifies files owned by another skill
2. **Assign a priority level** — based on dependencies in the graph above
3. **Define interface contracts** — if the new skill exports functions consumed by others, document exact signatures here
4. **Add guardrails** — every skill must have scope lock, interface contract, and no-new-dependencies rules
5. **Update this map** — add the new skill to the inventory, dependency graph, and execution rounds
