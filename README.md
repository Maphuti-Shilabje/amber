# mygoogle

Personal local-first search engine, command hub, and memory cache.

## Architecture
- Storage: SQLite with FTS5 full-text search and vector embeddings.
- Backend: FastAPI daemon with hybrid search (BM25 + FastEmbed + Reciprocal Rank Fusion).
- CLI: Interactive terminal search using fzf.
- Web: Lightweight omnibox interface with action cards.
- Extension: Manifest V3 browser capture for single-click saving.
