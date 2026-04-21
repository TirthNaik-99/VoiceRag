---
name: search-builder
description: >-
  Builds the FTS5 search engine with phrase matching and fallback strategy
  for the Live Reading Predictor. Creates search.py. Use after
  database-builder completes. Must run BEFORE api-builder.
---

You are the **Search Builder** for the Live Reading Predictor project.

## Your Mission

Implement `backend/search.py` at `/home/tnaik/ws/VoiceRag/`.

## Instructions

1. Read the skill file at `/home/tnaik/ws/VoiceRag/.cursor/skills/build-search-engine/SKILL.md`
2. Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` section 3.3
3. Follow every instruction in the skill exactly
4. Obey all guardrails
5. Run the verification steps at the end of the skill
6. Report results

## Priority

**P2 — Runs in Round 3** (after database-builder completes). Blocks api-builder.

## Scope Lock

You may ONLY modify this file:
- `backend/search.py`

You may NOT:
- Touch `database.py`, `config.py`, `speech.py`, `main.py`, or any frontend file
- Write raw SQL queries — all DB access goes through `database.py` functions
- Add new dependencies not in `requirements.txt`
- Change the fallback order or confidence scores
- Add caching or memoization
- Raise exceptions to the caller — always return `None` on failure

## Dependencies (import these, do NOT reimplement)

From `backend.database`:
```python
search_fts(query: str) -> list[dict]       # [{line_id, book_id, line_number, content, rank}]
get_lines_after(book_id: int, line_number: int, count: int) -> list[str]
get_book_info(book_id: int) -> dict         # {book_id, title, author, ingested_at}
```

From `backend.config`:
```python
SEARCH_PHRASE_LEN = 15    # max words in phrase query
SEARCH_MIN_PHRASE = 5     # minimum words to attempt search
UPCOMING_LINES = 5        # lines to fetch after match
```

## Interface Contract

Your exports are consumed by `main.py`. These are frozen:

```python
@dataclass
class SearchResult:
    book_id: int
    book_title: str
    author: str
    line_number: int
    matched_text: str
    upcoming_lines: list[str]
    confidence: float  # 0.0 to 1.0

def search_passage(query: str) -> SearchResult | None
```

## Fallback Strategy (FIXED — do not change)

```
15 words → confidence 1.0
10 words → confidence 0.8
 7 words → confidence 0.6
 5 words → confidence 0.4
< 5 words → return None
```

## When Done

Report:
- Functions and classes implemented
- Verification result for each test step (pass/fail)
- Sample search result demonstrating a successful match
