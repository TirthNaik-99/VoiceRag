"""Batch book ingestion script — scans data/books/ and ingests all .txt files."""

import os
import sys

from backend.config import BOOKS_DIR
from backend.database import init_db, ingest_book


def _title_from_filename(filename: str) -> str:
    """Derive a human-readable title from a filename like 'a_tale_of_two_cities.txt'."""
    stem = os.path.splitext(filename)[0]
    return stem.replace("_", " ").title()


def main() -> None:
    init_db()

    txt_files = sorted(
        f for f in os.listdir(BOOKS_DIR)
        if f.endswith(".txt")
    )

    if not txt_files:
        print(f"No .txt files found in {BOOKS_DIR}")
        sys.exit(0)

    total_books = 0
    total_lines = 0

    for filename in txt_files:
        filepath = os.path.join(BOOKS_DIR, filename)
        title = _title_from_filename(filename)
        author = "Unknown"

        book_id = ingest_book(filepath, title, author)
        with open(filepath, encoding="utf-8", errors="replace") as fh:
            line_count = sum(1 for line in fh if line.strip())

        total_books += 1
        total_lines += line_count
        print(f"  Ingested: {title} (book_id={book_id}, lines={line_count})")

    print(f"\nSummary: {total_books} book(s) ingested, {total_lines} total lines.")


if __name__ == "__main__":
    main()
