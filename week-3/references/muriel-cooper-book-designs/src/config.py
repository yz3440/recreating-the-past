from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
COVERS_DIR = DATA_DIR / "covers"
DB_PATH = DATA_DIR / "books.db"
STATIC_DIR = ROOT_DIR / "static"

MAX_ITERATIONS = 50
MODEL = "claude-sonnet-4-6"
