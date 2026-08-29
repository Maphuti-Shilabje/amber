# Amber Configuration & Hyperparameter Guide

This document describes all configuration variables, scoring hyperparameters, data limits, and ranking dials in `Amber`, including their types, default values, valid ranges, and operational impacts.

---

## 1. Search & Ranking Hyperparameters

These variables control the hybrid ranking algorithm combining SQLite FTS5 (BM25) and FastEmbed (dense ONNX vector embeddings) via Reciprocal Rank Fusion (RRF).

| Environment Variable | Type | Default | Valid / Recommended Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `AMBER_MIN_SIMILARITY` | float | `0.62` | `0.40` - `0.85` | **Semantic Similarity Floor.** Minimum cosine similarity required for a vector candidate to be retained. Higher values (e.g. `0.70`) eliminate false positive noise. Lower values (e.g. `0.50`) increase recall. |
| `AMBER_RRF_K` | int | `60` | `10` - `100` | **RRF Smoothing Constant.** Dampens rank disparity ($1 / (k + \text{rank})$). Lower values (e.g. `20`) give massive priority to rank #1 results over lower ranks. |
| `AMBER_VECTOR_EXPONENT` | float | `2.0` | `1.0` - `3.0` | **Vector Score Weighting Exponent.** Applied as $(\text{cosine\_score})^{\text{exponent}}$ before multiplying by RRF rank. Values $> 1.0$ exponentially penalize marginal vector matches. |
| `AMBER_EXACT_MATCH_BONUS` | float | `0.08` | `0.00` - `0.20` | **Exact Match Boost.** Flat score bonus added when the user's query exactly matches the full item title or command payload. |
| `AMBER_SUBSTRING_MATCH_BONUS` | float | `0.04` | `0.00` - `0.10` | **Substring Match Boost.** Flat score bonus added when the user's query is contained as a substring within the title or payload. |
| `AMBER_USAGE_BOOST` | float | `0.015` | `0.00` - `0.05` | **Usage Frequency Multiplier.** Controls the logarithmic reward for frequently executed or copied items: $\text{score} += \text{USAGE\_BOOST} \times \ln(1 + \text{use\_count})$. |
| `AMBER_BM25_W_TITLE` | float | `5.0` | `1.0` - `20.0` | **BM25 Title Weight.** Importance of keyword matches in the item title. |
| `AMBER_BM25_W_PAYLOAD` | float | `10.0` | `1.0` - `20.0` | **BM25 Payload Weight.** Importance of keyword matches in the actual command or code snippet. |
| `AMBER_BM25_W_TAGS` | float | `3.0` | `1.0` - `10.0` | **BM25 Tags Weight.** Importance of keyword matches in user tags. |
| `AMBER_BM25_W_NOTES` | float | `2.0` | `1.0` - `10.0` | **BM25 Notes Weight.** Importance of keyword matches in explanations or summaries. |
| `AMBER_BM25_W_RAW` | float | `1.0` | `0.1` - `5.0` | **BM25 Raw Content Weight.** Importance of keyword matches in deep scraped web text. |
| `AMBER_FTS_CANDIDATE_LIMIT` | int | `50` | `10` - `200` | Maximum number of keyword candidates pulled from SQLite FTS5 into the RRF pool. |
| `AMBER_VECTOR_CANDIDATE_LIMIT` | int | `50` | `10` - `200` | Maximum number of semantic candidates pulled from vector search into the RRF pool. |
| `AMBER_SNIPPET_WORDS_TITLE` | int | `16` | `5` - `50` | Number of context words surrounding matched keywords in the title preview snippet. |
| `AMBER_SNIPPET_WORDS_PAYLOAD` | int | `24` | `5` - `100` | Number of context words surrounding matched keywords in the payload preview snippet. |

---

## 2. Embedding Model & Ingestion Settings

| Environment Variable | Type | Default | Valid / Recommended Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `AMBER_EMBED_MODEL` | string | `BAAI/bge-small-en-v1.5` | Any FastEmbed model | Pre-trained ONNX embedding model. `bge-small-en-v1.5` produces 384-dimensional vectors with minimal CPU/RAM overhead (~115MB model weights). |
| `AMBER_EMBED_DIM` | int | `384` | Model-dependent | Dimensionality of the embedding vectors. Must match the chosen model. |
| `AMBER_EMBED_TRUNCATE_CHARS` | int | `2000` | `500` - `10000` | Character limit for scraped text passed to the embedding generator. |
| `AMBER_MODEL_IDLE_TIMEOUT_SEC` | int | `300` | `0` (immediate), `-1` (never), `30`–`3600` | Seconds of inactivity before unloading the ONNX model from RAM to drop daemon memory footprint back down to ~45MB. |

---

## 3. Database & Network Settings

| Environment Variable | Type | Default | Valid / Recommended Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `AMBER_HOST` | string | `127.0.0.1` | IP address | Host interface the FastAPI daemon binds to. Default is localhost only for security. |
| `AMBER_PORT` | int | `7474` | `1024` - `65535` | Port number for the HTTP backend daemon. |
| `AMBER_DATA_DIR` | path | `~/.local/share/amber` | Valid directory path | Directory where `db.sqlite` is stored. |
| `AMBER_DB_PATH` | path | `~/.local/share/amber/db.sqlite` | Valid file path | Explicit path to the SQLite database file. |
| `AMBER_DB_TIMEOUT_SEC` | float | `10.0` | `1.0` - `60.0` | SQLite connection timeout in seconds before throwing an error. |
| `AMBER_DB_BUSY_TIMEOUT_MS` | int | `5000` | `1000` - `30000` | SQLite WAL mode busy handler timeout in milliseconds. |
| `AMBER_DEFAULT_SEARCH_LIMIT` | int | `20` | `1` - `100` | Default number of items returned by `GET /api/search` if not specified in the request. |
| `AMBER_MAX_SEARCH_LIMIT` | int | `100` | `10` - `500` | Upper bound for the `limit` query parameter on search endpoints. |
| `AMBER_DEFAULT_ITEMS_LIMIT` | int | `50` | `1` - `200` | Default number of items returned by `GET /api/items`. |
| `AMBER_MAX_ITEMS_LIMIT` | int | `200` | `50` - `1000` | Upper bound for the `limit` query parameter on list items endpoints. |

---

## 4. Practical Tuning Recipes

### Recipe A: High Precision (Strict Exact Matching)
If you prefer exact syntax and commands over fuzzy semantic suggestions:
```bash
export AMBER_MIN_SIMILARITY=0.72
export AMBER_EXACT_MATCH_BONUS=0.15
export AMBER_BM25_W_PAYLOAD=15.0
```

### Recipe B: High Recall (Exploratory & Conceptual)
If you frequently search for concepts without remembering exact keywords:
```bash
export AMBER_MIN_SIMILARITY=0.55
export AMBER_VECTOR_EXPONENT=1.5
export AMBER_RRF_K=40
```

### Recipe C: Habit-Driven (Heavy Usage Weight)
If you want commands you run often to dominate search results:
```bash
export AMBER_USAGE_BOOST=0.040
```
