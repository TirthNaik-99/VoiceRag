"""FTS5 search engine — phrase matching, fallback strategy, result assembly."""

import re
import string
from dataclasses import dataclass

from backend.config import SEARCH_MIN_PHRASE, SEARCH_PHRASE_LEN, UPCOMING_LINES
from backend.database import get_book_info, get_lines_after, search_fts

_FALLBACK_STEPS: list[tuple[int, float]] = [
    (15, 1.0),
    (10, 0.8),
    (7, 0.6),
    (SEARCH_MIN_PHRASE, 0.4),
]

_STRIP_PUNCT = str.maketrans("", "", string.punctuation.replace("'", ""))


@dataclass
class SearchResult:
    book_id: int
    book_title: str
    author: str
    line_number: int
    matched_text: str
    upcoming_lines: list[str]
    confidence: float


def _clean_query(raw: str) -> list[str]:
    """Lowercase, strip punctuation (keep apostrophes), return word list."""
    text = raw.lower().translate(_STRIP_PUNCT)
    return text.split()


def _build_fts_query(words: list[str]) -> str:
    """Wrap words in double quotes for FTS5 phrase matching."""
    phrase = " ".join(words)
    return f'"{phrase}"'


def _best_match(results: list[dict]) -> dict | None:
    """Return the result with the best (lowest) FTS5 rank, or None."""
    if not results:
        return None
    return min(results, key=lambda r: r["rank"])


def search_passage(query: str) -> SearchResult | None:
    """Search for a passage using progressively shorter phrase fallback.

    Returns a SearchResult on match, or None if no match / query too short.
    """
    try:
        words = _clean_query(query)

        if len(words) < SEARCH_MIN_PHRASE:
            return None

        for phrase_len, confidence in _FALLBACK_STEPS:
            if len(words) < phrase_len:
                continue

            tail = words[-phrase_len:]
            fts_query = _build_fts_query(tail)
            results = search_fts(fts_query)
            match = _best_match(results)

            if match is not None:
                book = get_book_info(match["book_id"])
                upcoming = get_lines_after(
                    match["book_id"], match["line_number"], UPCOMING_LINES
                )
                return SearchResult(
                    book_id=match["book_id"],
                    book_title=book.get("title", ""),
                    author=book.get("author", ""),
                    line_number=match["line_number"],
                    matched_text=match["content"],
                    upcoming_lines=upcoming,
                    confidence=confidence,
                )

        return None
    except Exception:
        return None
