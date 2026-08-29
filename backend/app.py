import logging
import uuid
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import (
    STATIC_DIR,
    EMBEDDING_MODEL,
    EMBED_TEXT_TRUNCATE_CHARS,
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    DEFAULT_ITEMS_LIMIT,
    MAX_ITEMS_LIMIT,
)
from backend.db import (
    init_db,
    upsert_item,
    get_item,
    delete_item,
    touch_item,
    list_items,
    save_embedding,
    get_db,
)
from backend.search import hybrid_search, embed_text
from backend.scraper import extract_url_content

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("amber.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    init_db()
    logger.info("Database initialized successfully.")
    yield


app = FastAPI(
    title="Amber",
    description="Personal local-first memory and command preservation hub",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for browser extensions and local tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Request & Response Models
class IngestRequest(BaseModel):
    id: Optional[str] = None
    type: str = Field(..., description="command | snippet | bookmark | highlight | ai_chat | note")
    title: str = Field(..., description="Title or summary")
    payload: str = Field(..., description="Actionable command, code snippet, or clipped quote")
    context: Optional[str] = Field(None, description="Directory, environment, OS, or tags")
    source_url: Optional[str] = Field(None, description="Original source link")
    notes: Optional[str] = Field(None, description="Explanations, cheat notes, or summary")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    raw_content: Optional[str] = Field(None, description="Full scraped content")
    auto_scrape: Optional[bool] = Field(True, description="Scrape web page text if source_url provided")


class TouchResponse(BaseModel):
    success: bool
    id: str


def process_and_index_item(item_id: str, payload_text: str, auto_scrape: bool, source_url: Optional[str]):
    """Background task to scrape url and compute vector embedding."""
    try:
        raw_text = ""
        if auto_scrape and source_url:
            scraped = extract_url_content(source_url)
            if scraped and scraped.get("content"):
                raw_text = scraped["content"]
                # Update item with scraped text
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE items SET raw_content = ? WHERE id = ?;", (raw_text, item_id))
        
        # Build text representation for vector indexing
        item = get_item(item_id)
        if item:
            embed_source = f"{item['title']}\n{item['payload']}\n{item.get('notes') or ''}\n{item.get('tags') or ''}"
            if raw_text:
                embed_source += f"\n{raw_text[:EMBED_TEXT_TRUNCATE_CHARS]}"
            vec = embed_text(embed_source)
            save_embedding(item_id, EMBEDDING_MODEL, vec.tobytes())
            logger.info(f"Vector embedding saved for item {item_id}")
    except Exception as e:
        logger.error(f"Error processing background index for {item_id}: {e}")


@app.post("/api/ingest")
async def ingest_item(req: IngestRequest, background_tasks: BackgroundTasks):
    item_id = req.id or str(uuid.uuid4())
    
    upsert_item(
        item_id=item_id,
        item_type=req.type,
        title=req.title,
        payload=req.payload,
        context=req.context,
        source_url=req.source_url,
        notes=req.notes,
        tags=req.tags,
        raw_content=req.raw_content,
    )
    
    # Process scraping and embeddings in background
    background_tasks.add_task(
        process_and_index_item,
        item_id=item_id,
        payload_text=req.payload,
        auto_scrape=req.auto_scrape if req.auto_scrape is not None else True,
        source_url=req.source_url
    )
    
    return {"status": "ok", "id": item_id, "message": "Item ingested and queued for indexing"}


@app.get("/api/search")
async def search_items(
    q: str = Query(..., min_length=1, description="Search query string"),
    type: Optional[str] = Query(None, description="Filter by item type"),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT)
):
    start = time.time()
    results = hybrid_search(query=q, item_type=type, limit=limit)
    elapsed_ms = round((time.time() - start) * 1000, 2)
    
    return {
        "query": q,
        "total_hits": len(results),
        "elapsed_ms": elapsed_ms,
        "results": results
    }


@app.get("/api/items")
async def get_items(
    limit: int = Query(DEFAULT_ITEMS_LIMIT, ge=1, le=MAX_ITEMS_LIMIT),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None)
):
    items = list_items(limit=limit, offset=offset, item_type=type)
    return {"items": items, "count": len(items)}


@app.get("/api/items/{item_id}")
async def get_item_by_id(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.delete("/api/items/{item_id}")
async def delete_item_by_id(item_id: str):
    success = delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "ok", "id": item_id}


@app.post("/api/items/{item_id}/touch")
async def touch_item_by_id(item_id: str):
    success = touch_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"success": True, "id": item_id}


@app.get("/api/stats")
async def get_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM items;")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT type, COUNT(*) as count FROM items GROUP BY type;")
        type_counts = {row["type"]: row["count"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) as total_embeddings FROM embeddings;")
        total_embeddings = cursor.fetchone()["total_embeddings"]
        
    return {
        "total_items": total,
        "type_counts": type_counts,
        "total_embeddings": total_embeddings,
        "model": EMBEDDING_MODEL
    }


# Static web UI routing
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.api_route("/favicon.ico", methods=["GET", "HEAD"])
    async def serve_favicon():
        ico_file = STATIC_DIR / "favicon.ico"
        if ico_file.exists():
            return FileResponse(str(ico_file), media_type="image/x-icon")
        svg_file = STATIC_DIR / "favicon.svg"
        if svg_file.exists():
            return FileResponse(str(svg_file), media_type="image/svg+xml")
        raise HTTPException(status_code=404)

    @app.get("/")
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"status": "ok", "message": "Amber daemon running. Web UI not found in static dir."}


def main():
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()


