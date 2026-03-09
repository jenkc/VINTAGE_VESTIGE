"""
Smoke tests for the FastAPI API layer.

Hit every endpoint against live Postgres + pgvector and verify basic
response structure. Uses FastAPI TestClient (no uvicorn needed).
"""
import base64
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Module-scoped fixtures: fetch real IDs from the live DB once
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sample_ids(db_session):
    """Fetch a valid product_id, a bridged pair, and a bridge_id from live DB."""
    from storage.database import Product, StyleBridge

    product = db_session.query(Product).first()
    assert product, "No products in DB"

    bridge = db_session.query(StyleBridge).first()
    assert bridge, "No bridges in DB"

    return {
        "product_id": product.id,
        "bridge_id": bridge.id,
        "bridge_source": bridge.source_id,
        "bridge_target": bridge.target_id,
        "bridge_type": bridge.bridge_type,
    }


@pytest.fixture(scope="module")
def filter_options():
    """Fetch live filter values once for the module."""
    resp = client.get("/filters")
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. Filters
# ---------------------------------------------------------------------------
def test_filters(filter_options):
    for key in ("eras", "decades", "vibes", "garment_types",
                "occasions", "fit_styles", "cultures", "materials"):
        assert key in filter_options, f"Missing key: {key}"
        assert len(filter_options[key]) > 0, f"Empty list: {key}"


# ---------------------------------------------------------------------------
# 3. Search
# ---------------------------------------------------------------------------
def test_search_text():
    resp = client.post("/search/text", json={"query": "silk dress", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert len(data["results"]) <= 5
    for r in data["results"]:
        assert "id" in r
        assert 0 <= r["score"] <= 1


def test_search_text_with_filter(filter_options):
    era = filter_options["eras"][0]
    resp = client.post("/search/text", json={
        "query": "dress",
        "limit": 5,
        "filters": {"era": era},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 0


def test_search_image():
    # 4x4 red PNG — large enough that CLIP doesn't confuse channel dims
    from PIL import Image
    import io
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
    resp = client.post("/search/image", json={"image": data_url, "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert len(data["results"]) <= 3


# ---------------------------------------------------------------------------
# 4. Products
# ---------------------------------------------------------------------------
def test_get_product(sample_ids):
    pid = sample_ids["product_id"]
    resp = client.get(f"/products/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == pid
    assert "title" in data
    assert "era" in data
    assert "ai_description" in data


def test_get_product_not_found():
    resp = client.get("/products/99999999")
    assert resp.status_code == 404


def test_product_bridges(sample_ids):
    pid = sample_ids["product_id"]
    resp = client.get(f"/products/{pid}/bridges", params={"limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "bridges" in data
    assert "total" in data
    assert data["limit"] == 5


def test_product_modern_echoes(sample_ids):
    pid = sample_ids["product_id"]
    resp = client.get(f"/products/{pid}/modern-echoes")
    assert resp.status_code == 200
    data = resp.json()
    assert "bridges" in data
    assert "total" in data


def test_product_style_siblings(sample_ids):
    pid = sample_ids["product_id"]
    resp = client.get(f"/products/{pid}/style-siblings")
    assert resp.status_code == 200
    data = resp.json()
    assert "bridges" in data
    assert "total" in data


# ---------------------------------------------------------------------------
# 5. Bridges
# ---------------------------------------------------------------------------
def test_bridges_top():
    resp = client.get("/bridges/top", params={"limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bridges"]) > 0
    assert len(data["bridges"]) <= 5
    # Verify descending score order
    scores = [b["bridge_score"] for b in data["bridges"]]
    assert scores == sorted(scores, reverse=True)


def test_bridges_top_filtered(sample_ids):
    btype = sample_ids["bridge_type"]
    resp = client.get("/bridges/top", params={"bridge_type": btype, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    for b in data["bridges"]:
        assert b["bridge_type"] == btype


def test_bridges_top_limit():
    resp = client.get("/bridges/top", params={"limit": 3})
    assert resp.status_code == 200
    assert len(resp.json()["bridges"]) <= 3


def test_bridges_stats():
    resp = client.get("/bridges/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bridges"] > 0
    assert data["total_products_with_bridges"] > 0
    assert len(data["by_type"]) > 0
    assert len(data["score_histogram"]) == 10
    for bucket in data["score_histogram"]:
        assert "bucket" in bucket
        assert "count" in bucket


def test_bridge_between(sample_ids):
    a, b = sample_ids["bridge_source"], sample_ids["bridge_target"]
    resp = client.get(f"/bridges/between/{a}/{b}")
    assert resp.status_code == 200
    data = resp.json()
    assert "source" in data
    assert "target" in data
    assert data["bridge_score"] > 0


def test_bridge_between_not_found():
    # Product 1 and 2 are unlikely to have a bridge; if they do, 99999999 won't exist
    resp = client.get("/bridges/between/99999999/99999998")
    assert resp.status_code == 404


def test_bridge_detail(sample_ids):
    bid = sample_ids["bridge_id"]
    resp = client.get(f"/bridges/{bid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == bid
    assert "source" in data
    assert "target" in data
    assert data["bridge_score"] > 0
