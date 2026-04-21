---
name: build-database
description: >-
  Builds the SQLite FTS5 database layer and book ingestion pipeline for the
  Live Reading Predictor. Creates database.py and ingest_books.py. Use when
  building or modifying the database schema, ingestion, or retrieval logic.
---

# Build Database

## Goal

Implement the database layer at `backend/database.py` and the ingestion script at `scripts/ingest_books.py` for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P1 — Core Data Layer** (depends on: build-project-scaffold; blocks: build-search-engine, build-api-layer)

The search engine and API layer depend on the function signatures this skill exports. If signatures change, downstream skills break.

## Guardrails

1. **Scope lock**: ONLY modify `backend/database.py` and `scripts/ingest_books.py`. Do NOT touch any other file.
2. **Interface contract**: The function signatures in "Required Exports" below are the contract. Do NOT rename functions, change parameter names/types, or alter return types. Other skills import these by exact name.
3. **Schema is frozen**: Use the exact table definitions below. Do NOT add columns, rename tables, or change types. Future schema changes require updating all dependent skills first.
4. **No ORM**: Use raw `sqlite3` only. Do NOT introduce SQLAlchemy, Peewee, or any ORM — the prototype must stay dependency-light.
5. **No auto-migration**: `init_db()` uses `CREATE TABLE IF NOT EXISTS`. Do NOT add migration logic, version tracking, or schema diffing.
6. **Config only**: Read all paths and constants from `backend.config`. Do NOT hardcode paths, database filenames, or magic numbers.
7. **No data loss**: `ingest_book()` must be idempotent-safe — if called twice with the same file, it should not crash (inserting duplicate is acceptable for the prototype; dedup is a future enhancement).
8. **Encoding safety**: Open text files with `encoding="utf-8"` and `errors="replace"` to avoid crashes on malformed input.

## Context

Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` sections 3.4 (Database Layer) and 5 (Book Ingestion Pipeline) for full specifications.

## Schema

### Table: books

| Column | Type | Constraints |
|---|---|---|
| book_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| ingested_at | TEXT | DEFAULT CURRENT_TIMESTAMP |

### Table: lines

| Column | Type | Constraints |
|---|---|---|
| line_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| book_id | INTEGER | FOREIGN KEY → books.book_id |
| line_number | INTEGER | NOT NULL |
| content | TEXT | NOT NULL |

Index: `idx_lines_book_linenum ON lines(book_id, line_number)`

### Virtual Table: lines_fts (FTS5)

```sql
CREATE VIRTUAL TABLE lines_fts USING fts5(
    content,
    content_rowid='line_id'
);
```

Populated by manual INSERT inside `ingest_book()` — do NOT use triggers.

## File: backend/database.py

### Required Exports

```python
def init_db() -> None:
    """Create tables, indexes, and FTS5 virtual table if not exist."""

def ingest_book(filepath: str, title: str, author: str) -> int:
    """Ingest a .txt book file. Returns book_id. Steps:
    1. Insert into books table
    2. Read file, clean text, split into lines
    3. Insert each line into lines table
    4. Insert each line into lines_fts
    Return the book_id.
    """

def get_lines_after(book_id: int, line_number: int, count: int = 5) -> list[str]:
    """Return `count` lines after the given line_number for the given book."""

def get_book_info(book_id: int) -> dict:
    """Return book metadata: {book_id, title, author, ingested_at}."""

def list_books() -> list[dict]:
    """Return list of all ingested books."""

def search_fts(query: str) -> list[dict]:
    """Run FTS5 MATCH query with JOIN to lines table.
    Query: SELECT l.line_id, l.book_id, l.line_number, l.content, f.rank
           FROM lines_fts f JOIN lines l ON f.rowid = l.line_id
           WHERE lines_fts MATCH ? ORDER BY f.rank LIMIT 10
    Return list of {line_id, book_id, line_number, content, rank}.
    """
```

### Text Cleaning (during ingestion)

- Strip leading/trailing whitespace per line
- Skip empty lines
- Normalize unicode: smart quotes → straight quotes, em-dash → hyphen
- Collapse multiple spaces into single space
- Do NOT lowercase during ingestion (preserve original case; lowercasing happens at search time)

### Database Connection

- Use `sqlite3.connect()` with the path from `config.DB_PATH`
- Enable WAL mode for better concurrent read performance: `PRAGMA journal_mode=WAL`
- Use `check_same_thread=False` for FastAPI compatibility

## File: scripts/ingest_books.py

A CLI script that:
1. Calls `init_db()`
2. Scans `config.BOOKS_DIR` for `.txt` files
3. For each file, derives title from filename (e.g., `a_tale_of_two_cities.txt` → `A Tale of Two Cities`)
4. Calls `ingest_book()` for each
5. Prints summary: number of books ingested, total lines

Usage: `python -m scripts.ingest_books` (run from project root)

## Verification

The sample book (`data/books/sample_book.txt`) is created by the `build-project-scaffold` skill. If it doesn't exist yet, create a minimal test file with at least 10 lines of known text before testing.

After building, the sub-agent MUST test by:
1. Running `init_db()` — confirm `data/library.db` is created with all tables
2. Ingesting `data/books/sample_book.txt` (or the minimal test file)
3. Querying: `SELECT COUNT(*) FROM lines` — confirm lines were inserted (count > 0)
4. Pick any line from the ingested content, search for a 3-4 word phrase from it via `search_fts()` — confirm FTS5 returns a result with correct `book_id` and `line_number`
5. Using the matched `book_id` and `line_number`, call `get_lines_after()` with `count=5` — confirm it returns up to 5 lines and content is correct
