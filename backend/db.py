import sqlite3
import time
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from backend.config import DB_PATH, DB_CONNECT_TIMEOUT_SEC, DB_BUSY_TIMEOUT_MS

logger = logging.getLogger("mygoogle.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=DB_CONNECT_TIMEOUT_SEC)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS};")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Primary items table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            context TEXT,
            source_url TEXT,
            notes TEXT,
            tags TEXT,
            raw_content TEXT,
            use_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            last_used_at INTEGER
        );
        """)

        # 2. FTS5 Virtual Table for full-text search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            id UNINDEXED,
            title,
            payload,
            tags,
            notes,
            raw_content,
            tokenize = 'porter unicode61'
        );
        """)

        # 3. Vector Embeddings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            item_id TEXT PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
            model TEXT NOT NULL,
            embedding BLOB NOT NULL
        );
        """)

        # 4. Triggers to keep items_fts in sync with items table
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
            INSERT INTO items_fts(id, title, payload, tags, notes, raw_content)
            VALUES (new.id, new.title, new.payload, new.tags, new.notes, new.raw_content);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
            DELETE FROM items_fts WHERE id = old.id;
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
            DELETE FROM items_fts WHERE id = old.id;
            INSERT INTO items_fts(id, title, payload, tags, notes, raw_content)
            VALUES (new.id, new.title, new.payload, new.tags, new.notes, new.raw_content);
        END;
        """)

        # Indexes for fast filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_last_used ON items(last_used_at DESC);")


def upsert_item(
    item_id: str,
    item_type: str,
    title: str,
    payload: str,
    context: Optional[str] = None,
    source_url: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[str] = None,
    raw_content: Optional[str] = None,
    created_at: Optional[int] = None,
) -> str:
    now = int(time.time() * 1000)
    c_at = created_at if created_at is not None else now
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO items (
            id, type, title, payload, context, source_url, notes, tags, raw_content, created_at, last_used_at, use_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(id) DO UPDATE SET
            type = excluded.type,
            title = excluded.title,
            payload = excluded.payload,
            context = excluded.context,
            source_url = excluded.source_url,
            notes = excluded.notes,
            tags = excluded.tags,
            raw_content = CASE 
                WHEN excluded.raw_content IS NOT NULL AND excluded.raw_content != '' 
                THEN excluded.raw_content 
                ELSE items.raw_content 
            END;
        """, (item_id, item_type, title, payload, context, source_url, notes, tags, raw_content, c_at, now))
    return item_id


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?;", (item_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def delete_item(item_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?;", (item_id,))
        return cursor.rowcount > 0


def touch_item(item_id: str) -> bool:
    now = int(time.time() * 1000)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE items 
        SET use_count = use_count + 1, last_used_at = ?
        WHERE id = ?;
        """, (now, item_id))
        return cursor.rowcount > 0


def list_items(limit: int = 50, offset: int = 0, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        if item_type:
            cursor.execute("""
            SELECT * FROM items 
            WHERE type = ? 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?;
            """, (item_type, limit, offset))
        else:
            cursor.execute("""
            SELECT * FROM items 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?;
            """, (limit, offset))
        return [dict(r) for r in cursor.fetchall()]


def save_embedding(item_id: str, model: str, embedding_bytes: bytes):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO embeddings (item_id, model, embedding)
        VALUES (?, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            model = excluded.model,
            embedding = excluded.embedding;
        """, (item_id, model, embedding_bytes))


def get_all_embeddings(model: str) -> List[Tuple[str, bytes]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, embedding FROM embeddings WHERE model = ?;", (model,))
        return cursor.fetchall()
