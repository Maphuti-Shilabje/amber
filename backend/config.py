import os
from pathlib import Path

# Paths
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "mygoogle"
DATA_DIR = Path(os.environ.get("MYGOOGLE_DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("MYGOOGLE_DB_PATH", str(DATA_DIR / "db.sqlite")))

# Server config
HOST = os.environ.get("MYGOOGLE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MYGOOGLE_PORT", "7474"))

# Embedding Model
EMBEDDING_MODEL = os.environ.get("MYGOOGLE_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = 384

# Static UI directory
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web" / "static"
