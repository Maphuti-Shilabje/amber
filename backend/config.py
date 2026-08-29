import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Storage and Paths
# -----------------------------------------------------------------------------
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "amber"
DATA_DIR = Path(os.environ.get("AMBER_DATA_DIR", str(DEFAULT_DATA_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("AMBER_DB_PATH", str(DATA_DIR / "db.sqlite")))

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_STATIC = PACKAGE_DIR.parent / "web" / "static"
PKG_STATIC = PACKAGE_DIR / "static"
STATIC_DIR = REPO_STATIC if REPO_STATIC.exists() else PKG_STATIC

# -----------------------------------------------------------------------------
# Server Settings
# -----------------------------------------------------------------------------
HOST = os.environ.get("AMBER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AMBER_PORT", "7474"))

# -----------------------------------------------------------------------------
# Database Engine Settings
# -----------------------------------------------------------------------------
DB_CONNECT_TIMEOUT_SEC = float(os.environ.get("AMBER_DB_TIMEOUT_SEC", "10.0"))
DB_BUSY_TIMEOUT_MS = int(os.environ.get("AMBER_DB_BUSY_TIMEOUT_MS", "5000"))

# -----------------------------------------------------------------------------
# Embedding Model Settings
# -----------------------------------------------------------------------------
EMBEDDING_MODEL = os.environ.get("AMBER_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = int(os.environ.get("AMBER_EMBED_DIM", "384"))
EMBED_TEXT_TRUNCATE_CHARS = int(os.environ.get("AMBER_EMBED_TRUNCATE_CHARS", "2000"))

# Idle memory management: seconds before unloading model from RAM (300=5m, 0=immediate, -1=never)
MODEL_IDLE_TIMEOUT_SEC = int(os.environ.get("AMBER_MODEL_IDLE_TIMEOUT_SEC", "300"))

# -----------------------------------------------------------------------------
# Hybrid Search and Ranking Hyperparameters
# -----------------------------------------------------------------------------
# Minimum cosine similarity required for vector search match (rejects ambient noise)
MIN_VECTOR_SIMILARITY = float(os.environ.get("AMBER_MIN_SIMILARITY", "0.62"))

# Reciprocal Rank Fusion smoothing constant k (lower gives higher weight to rank 1)
RRF_K = int(os.environ.get("AMBER_RRF_K", "60"))

# Exponent applied to vector cosine similarity in RRF weighting (penalizes marginal scores)
VECTOR_SCORE_EXPONENT = float(os.environ.get("AMBER_VECTOR_EXPONENT", "2.0"))

# Score bonuses for exact and substring query matches in title or payload
EXACT_MATCH_BONUS = float(os.environ.get("AMBER_EXACT_MATCH_BONUS", "0.08"))
SUBSTRING_MATCH_BONUS = float(os.environ.get("AMBER_SUBSTRING_MATCH_BONUS", "0.04"))

# Usage frequency boost multiplier: score += USAGE_BOOST * ln(1 + use_count)
USAGE_BOOST_MULTIPLIER = float(os.environ.get("AMBER_USAGE_BOOST", "0.015"))

# FTS5 BM25 Field Weights (title, payload, tags, notes, raw_content)
BM25_WEIGHT_TITLE = float(os.environ.get("AMBER_BM25_W_TITLE", "5.0"))
BM25_WEIGHT_PAYLOAD = float(os.environ.get("AMBER_BM25_W_PAYLOAD", "10.0"))
BM25_WEIGHT_TAGS = float(os.environ.get("AMBER_BM25_W_TAGS", "3.0"))
BM25_WEIGHT_NOTES = float(os.environ.get("AMBER_BM25_W_NOTES", "2.0"))
BM25_WEIGHT_RAW = float(os.environ.get("AMBER_BM25_W_RAW", "1.0"))

# Candidate Retrieval Limits
FTS_CANDIDATE_LIMIT = int(os.environ.get("AMBER_FTS_CANDIDATE_LIMIT", "50"))
VECTOR_CANDIDATE_LIMIT = int(os.environ.get("AMBER_VECTOR_CANDIDATE_LIMIT", "50"))

# Snippet Token Lengths
FTS_SNIPPET_WORDS_TITLE = int(os.environ.get("AMBER_SNIPPET_WORDS_TITLE", "16"))
FTS_SNIPPET_WORDS_PAYLOAD = int(os.environ.get("AMBER_SNIPPET_WORDS_PAYLOAD", "24"))

# -----------------------------------------------------------------------------
# API Pagination Defaults and Bounds
# -----------------------------------------------------------------------------
DEFAULT_SEARCH_LIMIT = int(os.environ.get("AMBER_DEFAULT_SEARCH_LIMIT", "20"))
MAX_SEARCH_LIMIT = int(os.environ.get("AMBER_MAX_SEARCH_LIMIT", "100"))
DEFAULT_ITEMS_LIMIT = int(os.environ.get("AMBER_DEFAULT_ITEMS_LIMIT", "50"))
MAX_ITEMS_LIMIT = int(os.environ.get("AMBER_MAX_ITEMS_LIMIT", "200"))
