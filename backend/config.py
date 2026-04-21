import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WHISPER_MODEL = "medium"
AUDIO_CHUNK_SEC = 3
AUDIO_OVERLAP_SEC = 1
AUDIO_SAMPLE_RATE = 16000
ROLLING_BUFFER_WORDS = 20
SEARCH_PHRASE_LEN = 15
SEARCH_MIN_PHRASE = 5
UPCOMING_LINES = 5
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 3690
DB_PATH = os.path.join(BASE_DIR, "data", "library.db")
BOOKS_DIR = os.path.join(BASE_DIR, "data", "books")
FILLER_WORDS = {"um", "uh", "like", "you know", "so", "well", "actually", "basically"}
