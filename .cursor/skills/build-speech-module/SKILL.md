---
name: build-speech-module
description: >-
  Builds the Whisper speech-to-text module, audio capture, text normalization,
  and rolling buffer for the Live Reading Predictor. Creates speech.py and
  audio_capture.py. Use when building or modifying the speech recognition pipeline.
---

# Build Speech Module

## Goal

Implement the speech-to-text pipeline at `backend/speech.py` and `backend/audio_capture.py` for the Live Reading Predictor project at `/home/tnaik/ws/VoiceRag/`.

## Priority Level

**P1 — Audio Pipeline** (depends on: build-project-scaffold; blocks: build-api-layer)

Independent of database and search skills. Can be built in parallel with build-database. The API layer depends on the class/function signatures this skill exports.

## Guardrails

1. **Scope lock**: ONLY modify `backend/speech.py` and `backend/audio_capture.py`. Do NOT touch any other file.
2. **Interface contract**: Export exactly these names — `load_model()`, `transcribe_chunk()`, `normalize_text()`, `RollingBuffer` from `speech.py`, and `AudioCapture` from `audio_capture.py`. Do NOT rename or change signatures.
3. **No alternative STT engines**: Use OpenAI Whisper only. Do NOT substitute with Google STT, Deepgram, Vosk, or any other engine. Swapping engines is a future upgrade.
4. **No streaming Whisper**: Use the standard `whisper.transcribe()` batch API on chunks. Do NOT implement streaming/real-time Whisper — it's not stable enough for the prototype.
5. **Config only**: All tunable values (model name, chunk duration, buffer size, filler words) come from `backend.config`. Do NOT hardcode values.
6. **Thread safety**: `RollingBuffer` may be accessed from multiple async contexts. Use a `collections.deque` (thread-safe for append/pop) as the backing store, NOT a plain list.
7. **No network calls**: Whisper model download happens during setup, NOT at runtime inside these modules. `load_model()` loads from local cache. Do NOT add any internet-fetching logic.
8. **Graceful degradation**: If PyAudio is not installed, `audio_capture.py` must raise a clear `ImportError` with install instructions, not a cryptic traceback.

## Context

Read the system design at `/home/tnaik/ws/VoiceRag/prototype/1st_PROTO_SYSTEM_DESIGN.md` sections 3.1 (Audio Capture) and 3.2 (Speech-to-Text) for full specifications.

## Dependencies

From `backend/config.py`:
- `WHISPER_MODEL`, `AUDIO_CHUNK_SEC`, `AUDIO_OVERLAP_SEC`, `AUDIO_SAMPLE_RATE`
- `ROLLING_BUFFER_WORDS`, `FILLER_WORDS`

External packages:
- `whisper` (openai-whisper)
- `torch` (installed as whisper dependency — used for `torch.cuda.is_available()`)
- `pyaudio`
- `numpy`

## File: backend/audio_capture.py

### Class: AudioCapture

```python
class AudioCapture:
    """Captures audio from microphone in configurable chunks with overlap."""

    def __init__(self, sample_rate: int, chunk_duration: float, overlap: float):
        """Initialize PyAudio stream."""

    def start(self) -> None:
        """Begin capturing audio in a background thread."""

    def stop(self) -> None:
        """Stop capture and release resources."""

    def get_chunk(self) -> np.ndarray:
        """Return the next audio chunk as float32 numpy array normalized to [-1, 1].
        Blocking call — waits until chunk_duration seconds of audio are captured.
        Raises RuntimeError if capture is not active.
        """

    def is_active(self) -> bool:
        """Return True if capture is running."""
```

### Implementation Details

- Use PyAudio with `paInt16` format, mono channel, at `AUDIO_SAMPLE_RATE` Hz
- Capture runs in a background thread, pushing frames into a `queue.Queue`
- `get_chunk()` pulls frames from the queue, assembles `chunk_duration` seconds of audio
- Overlap: retain last `overlap` seconds of the previous chunk and prepend to the current chunk
- Convert int16 PCM to float32 normalized to [-1.0, 1.0] (Whisper expects this format)
- Handle gracefully: no microphone found → raise descriptive error

## File: backend/speech.py

### Required Exports

```python
def load_model(model_name: str = None) -> whisper.Whisper:
    """Load and return a Whisper model. Defaults to config.WHISPER_MODEL.
    Prints a message during loading since it takes a few seconds.
    """

def transcribe_chunk(model: whisper.Whisper, audio_chunk: np.ndarray) -> str:
    """Transcribe a single audio chunk. Returns raw transcription text.
    Uses fp16=False on CPU, fp16=True if CUDA is available.
    """

def normalize_text(raw: str) -> str:
    """Clean up raw transcription:
    1. Lowercase
    2. Remove filler words from config.FILLER_WORDS
    3. Remove punctuation except apostrophes
    4. Collapse multiple spaces
    5. Strip leading/trailing whitespace
    """

class RollingBuffer:
    """Maintains a sliding window of the last N words spoken."""

    def __init__(self, max_words: int):
        """Initialize with max_words from config.ROLLING_BUFFER_WORDS."""

    def add(self, text: str) -> None:
        """Add new transcribed words to the buffer. Drop oldest if over max_words."""

    def get_query(self, num_words: int = None) -> str:
        """Return the last num_words as a single string.
        Defaults to all words in buffer.
        """

    def clear(self) -> None:
        """Reset the buffer."""

    @property
    def word_count(self) -> int:
        """Current number of words in buffer."""
```

### Rolling Buffer Behavior

```
Buffer max_words = 20

add("it was the best of times")         → buffer: [it, was, the, best, of, times]
add("it was the worst of times")        → buffer: [it, was, the, best, of, times, it, was, the, worst, of, times]
add("it was the age of wisdom it was")  → buffer: [of, times, it, was, the, worst, of, times, it, was, the, age, of, wisdom, it, was]
                                          (oldest words dropped to stay ≤ 20)

get_query(10) → "the worst of times it was the age of wisdom it was"
```

## Important Notes

- PyAudio may not be available in all environments. Wrap import in try/except and provide a clear error message with install instructions if missing.
- Whisper model loading is slow (5-15 seconds). Load once at startup, reuse for all chunks.
- Detect CUDA availability: `torch.cuda.is_available()` — use GPU if available for faster transcription.
- The audio capture and transcription should be designed to run in separate threads/async tasks so capture doesn't block on transcription.

## Verification

After building, the sub-agent MUST verify by:
1. Confirm `speech.py` and `audio_capture.py` have no syntax errors: `python -c "from backend import speech, audio_capture"`
2. Test `normalize_text("  Um, it was THE best of, uh, times!  ")` → returns `"it was the best of times"`
3. Test `RollingBuffer(10)`: add 15 words, confirm `word_count` is 10 and oldest words were dropped
4. Do NOT attempt to actually run audio capture or Whisper transcription (requires mic and model download) — just verify the code is syntactically correct and importable
