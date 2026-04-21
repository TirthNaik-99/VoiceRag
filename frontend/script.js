// WebSocket connection
const WS_URL = `ws://${window.location.host}/ws`;

let ws = null;
let reconnectTimer = null;

// DOM references
const elBookTitle = document.getElementById("book-title");
const elBookAuthor = document.getElementById("book-author");
const elCurrentText = document.getElementById("current-text");
const elUpcomingLines = document.getElementById("upcoming-lines");
const elStatus = document.getElementById("status");
const elConfidence = document.getElementById("confidence");

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

function updateBookInfo(title, author) {
  elBookTitle.textContent = title || "Waiting for input...";
  elBookAuthor.textContent = author || "";
}

function updateCurrentText(text) {
  if (!text) return;
  elCurrentText.classList.add("fade-out");
  setTimeout(() => {
    elCurrentText.textContent = text;
    elCurrentText.classList.remove("fade-out");
  }, 150);
}

function updateUpcomingLines(lines) {
  elUpcomingLines.classList.add("fade-out");
  setTimeout(() => {
    elUpcomingLines.innerHTML = "";
    if (lines && lines.length) {
      lines.forEach((line) => {
        const p = document.createElement("p");
        p.className = "upcoming-line";
        p.textContent = line;
        elUpcomingLines.appendChild(p);
      });
    }
    elUpcomingLines.classList.remove("fade-out");
  }, 150);
}

function updateStatus(state, message) {
  elStatus.textContent = "● " + message;
  elStatus.className = state;
}

function updateConfidence(value) {
  if (value == null || value <= 0) {
    elConfidence.textContent = "";
    return;
  }
  elConfidence.textContent = Math.round(value * 100) + "% confidence";
}

window.addEventListener("beforeunload", () => {
  clearTimeout(reconnectTimer);
  if (ws) ws.close();
});

connect();
