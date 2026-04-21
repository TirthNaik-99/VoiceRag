---
name: build-search-engine
description: >-
  Builds the FTS5 search engine with phrase matching and fallback strategy
  for the Live Reading Predictor. Creates search.py. Use when building or
  modifying the text search and passage retrieval logic.
---

# Build Search Engine

## Goal

Implement the search agent at `backend/search.py` for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P2 — Search Logic** (depends on: build-database; blocks: build-api-layer)

This skill consumes `database.py` exports and is consumed by `main.py`. It sits in the middle of the dependency chain.

## Guardrails

1. **Scope lock**: ONLY modify `backend/search.py`. Do NOT touch `database.py`, `config.py`, or any other file.
2. **Interface contract**: Export exactly `SearchResult` (dataclass) and `search_passage(query: str) -> SearchResult | None`. Do NOT rename, add extra parameters, or change the return type. The API layer imports these by exact name.
3. **Use database.py as-is**: Call `search_fts()`, `get_lines_after()`, `get_book_info()` exactly as defined in the database skill. Do NOT write raw SQL queries directly — all DB access goes through `database.py`.
4. **No new dependencies**: Do NOT import any package not already in `requirements.txt`. No nltk, no spacy, no regex library. Use only Python stdlib + what's listed.
5. **Fallback order is fixed**: The phrase length fallback (15 → 10 → 7 → 5) and confidence scores (1.0 → 0.8 → 0.6 → 0.4) are specified below. Do NOT change these values, reorder them, or add extra steps without updating this skill doc first.
6. **No caching**: Do NOT add result caching, memoization, or any state between calls. `search_passage()` must be a pure stateless function for this prototype.
7. **Fail safe**: If anything unexpected happens (DB error, malformed data), return `None` — never raise an exception to the caller.

## Context

Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` section 3.3 (Search Agent) for full specifications.

## Dependencies

This module imports from `backend/database.py`:
- `search_fts(query: str) -> list[dict]`
- `get_lines_after(book_id: int, line_number: int, count: int) -> list[str]`
- `get_book_info(book_id: int) -> dict`

And from `backend/config.py`:
- `SEARCH_PHRASE_LEN`, `SEARCH_MIN_PHRASE`, `UPCOMING_LINES`

## File: backend/search.py

### Data Class

```python
from dataclasses import dataclass

@dataclass
class SearchResult:
    book_id: int
    book_title: str
    author: str
    line_number: int
    matched_text: str
    upcoming_lines: list[str]
    confidence: float  # 0.0 to 1.0
```

### Required Exports

```python
def search_passage(query: str) -> SearchResult | None:
    """Main entry point. Takes a query string (from rolling buffer),
    runs the fallback search strategy, and returns a SearchResult or None.
    """
```

### Fallback Search Strategy

The search must try progressively shorter phrase queries:

```
Input query (20 words): "it was the best of times it was the worst of times it was the age of wisdom it was"

Step 1: Extract last SEARCH_PHRASE_LEN (15) words
        → "the worst of times it was the age of wisdom it was"
        (counted from the end: words 6-20)

Step 2: Try exact phrase match with all 15 words
        FTS5: MATCH '"the worst of times it was the age of wisdom it was"'
        → If found → return result with confidence=1.0

Step 3: If not found, try last 10 words
        → "the age of wisdom it was"
        FTS5: MATCH '"it was the age of wisdom it was"'
        → If found → return result with confidence=0.8

Step 4: If not found, try last 7 words
        → "of wisdom it was"
        FTS5: MATCH '"age of wisdom it was"'
        → If found → return result with confidence=0.6

Step 5: If not found, try last SEARCH_MIN_PHRASE (5) words
        → "wisdom it was"
        FTS5: MATCH '"of wisdom it was"'
        → If found → return result with confidence=0.4

Step 6: If still not found → return None
```

### Query Building

- Lowercase the query before searching
- Remove punctuation except apostrophes (for contractions like "don't")
- Wrap in double quotes for FTS5 phrase matching: `'"word1 word2 word3"'`
- Escape any special FTS5 characters

### Result Assembly

When a match is found:
1. Get the matching `line_id`, `book_id`, `line_number` from FTS5 result
2. Call `get_book_info(book_id)` for title and author
3. Call `get_lines_after(book_id, line_number, UPCOMING_LINES)` for next lines
4. Build and return `SearchResult`

### Edge Cases

- If query has fewer words than `SEARCH_MIN_PHRASE`, return None immediately
- If multiple FTS5 matches exist, use the one with the best rank (FTS5 `rank` column)
- If `get_lines_after` returns fewer lines than requested (near end of book), return what's available

## Verification

The sample book is created by the `build-project-scaffold` skill and ingested by the `build-database` skill. If the DB doesn't exist yet, run `init_db()` and ingest any available `.txt` file from `data/books/` (or create a minimal 10-line test file) before testing.

After building, the sub-agent MUST test by:
1. Ensure `data/library.db` exists with at least one ingested book
2. Pick a known phrase (5+ words) from the ingested content, call `search_passage()` with it — confirm it returns a SearchResult with correct `book_title` and non-empty `upcoming_lines`
3. Call `search_passage("xyzzy qwert asdfg hjklz mnbvc")` — confirm it returns None (no match)
4. Call `search_passage("of")` — confirm it returns None (below minimum phrase length)
