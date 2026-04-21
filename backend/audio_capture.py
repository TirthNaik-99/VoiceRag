"""Audio capture — microphone input via PyAudio in configurable chunks with overlap."""

from __future__ import annotations

import queue
import threading
from typing import Optional

import numpy as np

_pyaudio = None
_pyaudio_import_error: Optional[str] = None

try:
    import pyaudio as _pyaudio
except ImportError:
    _pyaudio_import_error = (
        "PyAudio is required for audio capture but is not installed.\n"
        "Install it with:\n"
        "  pip install pyaudio\n"
        "On Debian/Ubuntu you may also need:\n"
        "  sudo apt-get install portaudio19-dev python3-pyaudio"
    )


def _require_pyaudio():
    if _pyaudio is None:
        raise ImportError(_pyaudio_import_error)


class AudioCapture:
    """Captures audio from microphone in configurable chunks with overlap."""

    def __init__(self, sample_rate: int, chunk_duration: float, overlap: float):
        _require_pyaudio()

        self._sample_rate = sample_rate
        self._chunk_duration = chunk_duration
        self._overlap = overlap

        self._frames_per_chunk = int(sample_rate * chunk_duration)
        self._frames_overlap = int(sample_rate * overlap)
        self._read_size = 1024

        self._pa = None
        self._stream = None
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._overlap_buffer: Optional[np.ndarray] = None

    def start(self) -> None:
        """Begin capturing audio in a background thread."""
        if self._running:
            return

        self._pa = _pyaudio.PyAudio()

        try:
            self._pa.get_default_input_device_info()
        except (IOError, OSError):
            self._pa.terminate()
            raise RuntimeError(
                "No microphone found. Please connect a microphone and try again."
            )

        self._stream = self._pa.open(
            format=_pyaudio.paInt16,
            channels=1,
            rate=self._sample_rate,
            input=True,
            frames_per_buffer=self._read_size,
        )

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        """Read raw frames from the mic stream and enqueue them."""
        while self._running:
            try:
                data = self._stream.read(self._read_size, exception_on_overflow=False)
                self._queue.put(data)
            except Exception:
                if not self._running:
                    break

    def stop(self) -> None:
        """Stop capture and release resources."""
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pa is not None:
            self._pa.terminate()
            self._pa = None

    def get_chunk(self) -> np.ndarray:
        """Return the next audio chunk as float32 numpy array normalized to [-1, 1].

        Blocking call — waits until chunk_duration seconds of audio are captured.
        Raises RuntimeError if capture is not active.
        """
        if not self._running:
            raise RuntimeError("Audio capture is not active. Call start() first.")

        frames_needed = self._frames_per_chunk
        if self._overlap_buffer is not None:
            frames_needed -= len(self._overlap_buffer)

        raw_frames: list[bytes] = []
        collected = 0
        while collected < frames_needed:
            try:
                data = self._queue.get(timeout=self._chunk_duration + 1.0)
            except queue.Empty:
                raise RuntimeError("Timed out waiting for audio data.")
            raw_frames.append(data)
            collected += len(data) // 2  # 2 bytes per int16 sample

        raw = b"".join(raw_frames)
        pcm = np.frombuffer(raw, dtype=np.int16)[:frames_needed]
        audio = pcm.astype(np.float32) / 32768.0

        if self._overlap_buffer is not None:
            audio = np.concatenate([self._overlap_buffer, audio])

        if self._frames_overlap > 0:
            self._overlap_buffer = audio[-self._frames_overlap:]
        else:
            self._overlap_buffer = None

        return audio

    def is_active(self) -> bool:
        """Return True if capture is running."""
        return self._running
