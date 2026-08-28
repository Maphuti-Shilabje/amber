import logging
import math
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from fastembed import TextEmbedding

from backend.config import EMBEDDING_MODEL
from backend.db import get_db, get_all_embeddings, get_item

logger = logging.getLogger("mygoogle.search")

_embedding_model: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _embedding_model


def embed_text(text: str) -> np.ndarray:
    model = get_embedding_model()
    embeddings = list(model.embed([text]))
    vec = np.array(embeddings[0], dtype=np.float32)
    # Normalize vector for fast dot-product cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def sanitize_fts_query(query: str) -> str:
    """
    Sanitizes user input for SQLite FTS5 MATCH syntax.
    Replaces special FTS operators and tokenizes words into prefix queries.
    """
    tokens = re.findall(r"[A-Za-z0-9_\-\.\:\/]+", query)
    if not tokens:
        return ""
    # Use prefix matching on each token for responsive instant search
    fts_tokens = [f'"{token}"*' for token in tokens]
    return " ".join(fts_tokens)


def search_fts(query: str, limit: int = 40) -> List[Tuple[str, float, str]]:
    """
    Executes BM25 search over SQLite FTS5 table.
    Returns: list of (item_id, bm25_rank, highlight_snippet)
    """
    fts_query = sanitize_fts_query(query)
    if not fts_query:
        return []

    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # bm25(items_fts, 5.0, 10.0, 3.0, 2.0, 1.0) weights:
            # title=5.0, payload=10.0, tags=3.0, notes=2.0, raw_content=1.0
            cursor.execute("""
            SELECT 
                id,
                bm25(items_fts, 5.0, 10.0, 3.0, 2.0, 1.0) as rank,
                snippet(items_fts, 1, '<mark>', '</mark>', '...', 16) as title_snippet,
                snippet(items_fts, 2, '<mark>', '</mark>', '...', 24) as payload_snippet
            FROM items_fts
            WHERE items_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
            """, (fts_query, limit))
            
            for row in cursor.fetchall():
                snippet = row["payload_snippet"] or row["title_snippet"] or ""
                results.append((row["id"], float(row["rank"]), snippet))
        except Exception as e:
            logger.warning(f"FTS5 query failed for '{fts_query}': {e}")
            
    return results


def search_vectors(query_vec: np.ndarray, limit: int = 40) -> List[Tuple[str, float]]:
    """
    Computes cosine similarity between query vector and all stored embeddings in SQLite.
    Returns: list of (item_id, cosine_similarity_score)
    """
    stored_embeddings = get_all_embeddings(EMBEDDING_MODEL)
    if not stored_embeddings:
        return []

    item_ids = []
    matrix_rows = []

    for item_id, blob in stored_embeddings:
        vec = np.frombuffer(blob, dtype=np.float32)
        item_ids.append(item_id)
        matrix_rows.append(vec)

    if not matrix_rows:
        return []

    matrix = np.vstack(matrix_rows)
    # Cosine similarity is dot product when vectors are normalized
    scores = np.dot(matrix, query_vec)

    # Sort descending
    top_indices = np.argsort(scores)[::-1][:limit]
    # Filter out weak cosine scores (< 0.30)
    results = [(item_ids[idx], float(scores[idx])) for idx in top_indices if scores[idx] >= 0.30]
    return results


def hybrid_search(
    query: str,
    item_type: Optional[str] = None,
    limit: int = 20,
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Performs hybrid search combining BM25 keyword matching and vector semantic similarity
    using Reciprocal Rank Fusion (RRF).
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # 1. BM25 Search
    fts_results = search_fts(cleaned_query, limit=50)
    
    # 2. Vector Search
    try:
        query_vec = embed_text(cleaned_query)
        vector_results = search_vectors(query_vec, limit=50)
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        vector_results = []

    # 3. Reciprocal Rank Fusion
    rrf_scores: Dict[str, float] = {}
    snippets: Dict[str, str] = {}

    # BM25 RRF component
    for rank, (item_id, _, snippet) in enumerate(fts_results, start=1):
        rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + (1.0 / (k + rank))
        if snippet:
            snippets[item_id] = snippet

    # Vector RRF component
    for rank, (item_id, cos_score) in enumerate(vector_results, start=1):
        rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + (1.0 / (k + rank))

    if not rrf_scores:
        return []

    # 4. Fetch item details and apply domain boosts
    final_items = []
    q_lower = cleaned_query.lower()

    for item_id, base_score in rrf_scores.items():
        item = get_item(item_id)
        if not item:
            continue

        if item_type and item["type"] != item_type:
            continue

        score = base_score

        # Exact match bonus
        title_lower = (item["title"] or "").lower()
        payload_lower = (item["payload"] or "").lower()
        if q_lower in title_lower or q_lower in payload_lower:
            score += 0.04
        if title_lower == q_lower or payload_lower == q_lower:
            score += 0.08

        # Usage frequency bonus: + 0.015 * log(1 + use_count)
        use_count = item.get("use_count", 0) or 0
        if use_count > 0:
            score += 0.015 * math.log(1 + use_count)

        item_dict = dict(item)
        item_dict["score"] = round(score, 5)
        item_dict["highlight"] = snippets.get(item_id, "")
        final_items.append(item_dict)

    # Sort descending by final score
    final_items.sort(key=lambda x: x["score"], reverse=True)
    return final_items[:limit]
