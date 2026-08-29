import os
import tempfile
import pytest

# Use a temporary database for tests
temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
os.environ["AMBER_DB_PATH"] = temp_db.name

from backend.db import init_db, upsert_item, get_item, touch_item, delete_item, list_items, save_embedding
from backend.search import search_fts, hybrid_search, embed_text
from backend.config import EMBEDDING_MODEL


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()
    yield
    if os.path.exists(temp_db.name):
        os.remove(temp_db.name)


def test_upsert_and_get():
    item_id = "test-1"
    upsert_item(
        item_id=item_id,
        item_type="command",
        title="Create Python venv",
        payload="python -m venv .venv && source .venv/bin/activate",
        context="Ubuntu 24.04",
        notes="Standard virtual environment activation command",
        tags="python,venv,virtualenv"
    )
    
    item = get_item(item_id)
    assert item is not None
    assert item["title"] == "Create Python venv"
    assert "source .venv/bin/activate" in item["payload"]
    assert item["use_count"] == 0


def test_fts_search():
    # Test exact and keyword matching
    results = search_fts("venv")
    assert len(results) >= 1
    assert results[0][0] == "test-1"

    # Test prefix matching
    results_prefix = search_fts("virt")
    assert len(results_prefix) >= 1


def test_hybrid_search_with_embeddings():
    # Insert another item for coffee site test
    coffee_id = "coffee-1"
    upsert_item(
        item_id=coffee_id,
        item_type="bookmark",
        title="Onyx Coffee Lab",
        payload="https://onyxcoffeelab.com",
        context="Roastery",
        source_url="https://onyxcoffeelab.com",
        notes="Artisan Ethiopian beans with blueberry notes and clean acidity",
        tags="coffee,roastery,ethiopian"
    )

    # Embed both items
    item1 = get_item("test-1")
    vec1 = embed_text(f"{item1['title']}\n{item1['payload']}\n{item1['notes']}")
    save_embedding("test-1", EMBEDDING_MODEL, vec1.tobytes())

    item2 = get_item(coffee_id)
    vec2 = embed_text(f"{item2['title']}\n{item2['payload']}\n{item2['notes']}")
    save_embedding(coffee_id, EMBEDDING_MODEL, vec2.tobytes())

    # Search for semantic query without direct keyword match in title
    results = hybrid_search("isolated python environment setup")
    assert len(results) > 0
    assert results[0]["id"] == "test-1"

    # Search for coffee query
    coffee_results = hybrid_search("blueberry roaster beans")
    assert len(coffee_results) > 0
    assert coffee_results[0]["id"] == "coffee-1"


def test_touch_and_delete():
    assert touch_item("test-1") is True
    item = get_item("test-1")
    assert item["use_count"] == 1

    assert delete_item("test-1") is True
    assert get_item("test-1") is None


def test_non_matching_query_returns_empty():
    # Searching for non-existent unrelated terms must return 0 results
    results = hybrid_search("quantum astronaut telescope moon")
    assert len(results) == 0

    results_oov = hybrid_search("xyzabc123nonexistent")
    assert len(results_oov) == 0

