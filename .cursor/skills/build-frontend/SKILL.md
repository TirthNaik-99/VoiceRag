---
name: build-frontend
description: >-
  Builds the browser-based live display frontend with WebSocket client for the
  Live Reading Predictor. Creates index.html, style.css, and script.js.
  Use when building or modifying the audience-facing display.
---

# Build Frontend

## Goal

Implement the frontend display at `frontend/index.html`, `frontend/style.css`, and `frontend/script.js` for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P1 — Display Layer** (depends on: build-project-scaffold; blocks: nothing)

Independent of all backend skills. Can be built in parallel with database, search, and speech skills. Only depends on the WebSocket JSON contract (defined below).

## Guardrails

1. **Scope lock**: ONLY modify `frontend/index.html`, `frontend/style.css`, and `frontend/script.js`. Do NOT touch any backend file.
2. **No frameworks**: Use vanilla HTML, CSS, and JavaScript only. Do NOT introduce React, Vue, Svelte, jQuery, Tailwind, Bootstrap, or any framework/library. This is a deliberate choice for zero-dependency speed.
3. **No CDN dependencies**: All code must be self-contained. Do NOT link to external CDNs, Google Fonts, or any remote resource. The app must work fully offline.
4. **No build tools**: No webpack, no Vite, no npm, no bundler. The files are served directly as static assets.
5. **WebSocket contract is frozen**: The JSON message format defined in "WebSocket Message Format" below is the contract with the backend. Do NOT expect fields not listed there. Do NOT rename or restructure fields.
6. **DOM IDs are the API**: The element IDs (`book-title`, `book-author`, `current-text`, `upcoming-lines`, `status`, `confidence`) are referenced by verification steps. Do NOT rename them.
7. **Dark theme only**: Do NOT add a theme toggle or light mode. The display is designed for projection in a dark venue.
8. **No user input**: The frontend is display-only. Do NOT add input fields, buttons, forms, or any interactive controls (except the auto-connecting WebSocket). The audience watches, they don't interact.
9. **Accessibility basics**: Use semantic HTML (`<header>`, `<main>`, `<footer>`, `<section>`). Include `lang="en"` on `<html>`. Use `<meta charset="UTF-8">`.

## Context

Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` section 3.6 (Frontend Display) for full specifications.

## Design Requirements

- **Dark theme** — this will be projected on a screen in a live event. Dark background, light text.
- **Large, highly readable text** — the audience needs to read from a distance.
- **Minimal, clean layout** — no clutter. Focus entirely on the text.
- **Real-time updates** — text updates smoothly without flashing or layout jumps.

## File: frontend/index.html

### Layout Structure

```html
<body>
  <header>
    <h1>Live Reading Predictor</h1>
  </header>

  <main>
    <!-- Book info section -->
    <section id="book-info">
      <span id="book-title">Waiting for input...</span>
      <span id="book-author"></span>
    </section>

    <!-- Currently reading section -->
    <section id="current-reading">
      <h2>Currently Reading</h2>
      <p id="current-text"></p>
    </section>

    <!-- Upcoming lines section -->
    <section id="upcoming">
      <h2>Coming Next</h2>
      <div id="upcoming-lines">
        <!-- Lines injected by JS -->
      </div>
    </section>
  </main>

  <footer>
    <span id="status">● Connecting...</span>
    <span id="confidence"></span>
  </footer>
</body>
```

- Link `style.css` and `script.js`
- No external CDN dependencies — everything self-contained

## File: frontend/style.css

### Theme

```
Background:    #0d1117 (GitHub dark)
Text:          #e6edf3 (soft white)
Accent:        #58a6ff (blue)
Current line:  #1f6feb background highlight
Upcoming text: #c9d1d9 (slightly dimmer)
Status green:  #3fb950
Status red:    #f85149
Status yellow: #d29922
```

### Typography

- Font: system font stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Current reading text: `2.5rem` (40px), bold
- Upcoming lines: `1.8rem` (28.8px), normal weight
- First upcoming line (next immediate line): slightly brighter, with a `►` prefix
- Status bar: `1rem`, fixed to bottom

### Layout

- Max width: `900px`, centered
- Generous padding: `2rem` on sides
- Sections separated by subtle borders or spacing
- Upcoming lines: each line on its own row, with `0.5rem` vertical spacing
- Smooth CSS transitions on text content changes (opacity fade)

### Responsive

- Should look good on both a laptop screen and a projector (1920x1080)
- No horizontal scrolling

## File: frontend/script.js

### WebSocket Client

```javascript
const WS_URL = `ws://${window.location.host}/ws`;

// State
let ws = null;
let reconnectTimer = null;

function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        updateStatus("listening", "Listening...");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        updateStatus("disconnected", "Disconnected. Reconnecting...");
        reconnectTimer = setTimeout(connect, 1000);
    };

    ws.onerror = () => {
        ws.close();
    };
}
```

### WebSocket Message Format

The backend sends JSON with this shape:

```json
{
  "status": "found | not_found | listening | error",
  "book_title": "string or null",
  "author": "string or null",
  "matched_text": "string or null",
  "upcoming_lines": ["line1", "line2", "..."] ,
  "confidence": 0.0,
  "transcript": "current transcribed text",
  "message": "error description (only when status=error)"
}
```

### Message Handler

```javascript
function handleMessage(data) {
    if (data.transcript) {
        updateCurrentText(data.transcript);
    }

    if (data.status === "found") {
        updateBookInfo(data.book_title, data.author);
        updateCurrentText(data.matched_text);
        updateUpcomingLines(data.upcoming_lines);
        updateConfidence(data.confidence);
        updateStatus("listening", "Listening...");
    } else if (data.status === "not_found") {
        updateBookInfo(null, null);
        updateUpcomingLines([]);
        updateConfidence(0);
        updateStatus("searching", "Source not present");
    } else if (data.status === "listening") {
        updateStatus("listening", "Listening...");
    } else if (data.status === "error") {
        updateStatus("error", data.message || "An error occurred");
    }
}
```

### DOM Update Functions

- `updateBookInfo(title, author)` — update header section
- `updateCurrentText(text)` — update the "currently reading" paragraph
- `updateUpcomingLines(lines)` — clear and rebuild the upcoming lines div
- `updateStatus(state, message)` — update the footer status indicator with colored dot
- `updateConfidence(value)` — show confidence as percentage

### Important Behaviors

- **No flashing**: use CSS transitions (opacity) when swapping text content
- **Auto-connect**: call `connect()` on page load
- **Auto-reconnect**: on close, retry every 1 second
- **Clean disconnect**: clear reconnect timer if user closes page (`beforeunload`)

## Verification

After building, the sub-agent MUST verify by:
1. Confirm all three files exist: `frontend/index.html`, `frontend/style.css`, `frontend/script.js`
2. Confirm `index.html` contains valid HTML structure: `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` tags
3. Confirm `index.html` links both `style.css` and `script.js`
4. Confirm `style.css` contains the dark theme background color `#0d1117`
5. Confirm `script.js` contains `new WebSocket`, `handleMessage`, `connect()` call on load
6. Confirm all DOM element IDs referenced in JS (`book-title`, `book-author`, `current-text`, `upcoming-lines`, `status`, `confidence`) exist in `index.html`
