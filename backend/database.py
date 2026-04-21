"""SQLite FTS5 database layer — schema, ingestion, search, retrieval."""

import re
import sqlite3
import unicodedata

from backend.config import DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables, indexes, and FTS5 virtual table if not exist."""
    conn = _get_conn()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS lines (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books(book_id)
            )"""
        )
        conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_lines_book_linenum
               ON lines(book_id, line_number)"""
        )
        conn.execute(
            """CREATE VIRTUAL TABLE IF NOT EXISTS lines_fts USING fts5(
                content,
                content_rowid='line_id'
            )"""
        )
        conn.commit()
    finally:
        conn.close()


_SMART_QUOTES = str.maketrans({
    "\u2018": "'",   # left single
    "\u2019": "'",   # right single
    "\u201c": '"',   # left double
    "\u201d": '"',   # right double
    "\u2014": "-",   # em-dash
    "\u2013": "-",   # en-dash
})

_MULTI_SPACE = re.compile(r" {2,}")


def _clean_line(raw: str) -> str | None:
    """Strip, normalize unicode, collapse spaces. Returns None for blank lines."""
    line = raw.strip()
    if not line:
        return None
    line = line.translate(_SMART_QUOTES)
    line = unicodedata.normalize("NFC", line)
    line = _MULTI_SPACE.sub(" ", line)
    return line


def ingest_book(filepath: str, title: str, author: str) -> int:
    """Ingest a .txt book file. Returns book_id."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (title, author),
        )
        book_id: int = cur.lastrowid  # type: ignore[assignment]

        with open(filepath, encoding="utf-8", errors="replace") as fh:
            raw_lines = fh.readlines()

        line_num = 0
        for raw in raw_lines:
            cleaned = _clean_line(raw)
            if cleaned is None:
                continue
            line_num += 1
            cur = conn.execute(
                "INSERT INTO lines (book_id, line_number, content) VALUES (?, ?, ?)",
                (book_id, line_num, cleaned),
            )
            line_id = cur.lastrowid
            conn.execute(
                "INSERT INTO lines_fts (rowid, content) VALUES (?, ?)",
                (line_id, cleaned),
            )

        conn.commit()
        return book_id
    finally:
        conn.close()


def get_lines_after(book_id: int, line_number: int, count: int = 5) -> list[str]:
    """Return `count` lines after the given line_number for the given book."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT content FROM lines
               WHERE book_id = ? AND line_number > ?
               ORDER BY line_number ASC
               LIMIT ?""",
            (book_id, line_number, count),
        ).fetchall()
        return [row["content"] for row in rows]
    finally:
        conn.close()


def get_book_info(book_id: int) -> dict:
    """Return book metadata: {book_id, title, author, ingested_at}."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT book_id, title, author, ingested_at FROM books WHERE book_id = ?",
            (book_id,),
        ).fetchone()
        if row is None:
            return {}
        return dict(row)
    finally:
        conn.close()


def list_books() -> list[dict]:
    """Return list of all ingested books."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT book_id, title, author, ingested_at FROM books"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_fts(query: str) -> list[dict]:
    """Run FTS5 MATCH query with JOIN to lines table."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT l.line_id, l.book_id, l.line_number, l.content, f.rank
               FROM lines_fts f
               JOIN lines l ON f.rowid = l.line_id
               WHERE lines_fts MATCH ?
               ORDER BY f.rank
               LIMIT 10""",
            (query,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
