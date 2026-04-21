"""Whisper speech-to-text — model loading, transcription, text normalization, rolling buffer."""

from __future__ import annotations

import re
import string
from collections import deque
from typing import TYPE_CHECKING, Optional

import numpy as np

from backend import config

if TYPE_CHECKING:
    import torch
    import whisper


def load_model(model_name: str = None) -> whisper.Whisper:
    """Load and return a Whisper model. Defaults to config.WHISPER_MODEL.

    Prints a message during loading since it takes a few seconds.
    """
    import torch as _torch
    import whisper as _whisper

    name = model_name or config.WHISPER_MODEL
    device = "cuda" if _torch.cuda.is_available() else "cpu"
    print(f"Loading Whisper model '{name}' on {device}…")
    model = _whisper.load_model(name, device=device)
    print(f"Whisper model '{name}' loaded.")
    return model


def transcribe_chunk(model: whisper.Whisper, audio_chunk: np.ndarray) -> str:
    """Transcribe a single audio chunk. Returns raw transcription text.

    Uses fp16=True if CUDA is available, fp16=False on CPU.
    """
    import torch as _torch

    use_fp16 = _torch.cuda.is_available()
    result = model.transcribe(audio_chunk, fp16=use_fp16)
    return result.get("text", "")


_punct_chars = string.punctuation.replace("'", "")
_PUNCT_EXCEPT_APOSTROPHE = re.compile(f"[{re.escape(_punct_chars)}]")
_MULTI_SPACE = re.compile(r"\s{2,}")


def _build_filler_pattern() -> re.Pattern:
    """Compile a single regex that matches any filler word/phrase from config."""
    sorted_fillers = sorted(config.FILLER_WORDS, key=len, reverse=True)
    alternatives = "|".join(re.escape(f) for f in sorted_fillers)
    return re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)


_FILLER_RE = _build_filler_pattern()


def normalize_text(raw: str) -> str:
    """Clean up raw transcription.

    Pipeline:
      1. Lowercase
      2. Remove filler words from config.FILLER_WORDS
      3. Remove punctuation except apostrophes
      4. Collapse multiple spaces
      5. Strip leading/trailing whitespace
    """
    text = raw.lower()
    text = _FILLER_RE.sub("", text)
    text = _PUNCT_EXCEPT_APOSTROPHE.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


class RollingBuffer:
    """Maintains a sliding window of the last N words spoken.

    Backed by ``collections.deque`` for thread-safe append/pop operations.
    """

    def __init__(self, max_words: int = None):
        self._max_words = max_words or config.ROLLING_BUFFER_WORDS
        self._buf: deque[str] = deque(maxlen=self._max_words)

    def add(self, text: str) -> None:
        """Add new transcribed words to the buffer. Oldest words are dropped
        automatically when the deque exceeds *max_words*."""
        words = text.split()
        for w in words:
            self._buf.append(w)

    def get_query(self, num_words: Optional[int] = None) -> str:
        """Return the last *num_words* as a single string.

        Defaults to all words currently in the buffer.
        """
        if num_words is None:
            return " ".join(self._buf)
        return " ".join(list(self._buf)[-num_words:])

    def clear(self) -> None:
        """Reset the buffer."""
        self._buf.clear()

    @property
    def word_count(self) -> int:
        """Current number of words in buffer."""
        return len(self._buf)
