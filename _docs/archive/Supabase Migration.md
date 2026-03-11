# Supabase Migration Guide — Hands-On Implementation

## What We're Doing

Migrating from local PostgreSQL + Qdrant to Supabase PostgreSQL + pgvector + Supabase Storage. One hosted database for everything — relational data, vector embeddings, and image URLs.

**Before:** Local PG (179 MB, mostly base64 images) + Qdrant (2 vector collections)
**After:** Supabase PG (~19 MB) + pgvector (embeddings as columns) + Supabase Storage (~161 MB images)

---

# Project Setup and Data Migration
## Step 1: Supabase Project Setup

### 1.1 Enable pgvector

Go to Supabase Dashboard → SQL Editor, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.2 Create Image Storage Bucket

Dashboard → Storage → New Bucket:
- Name: `product-images`
- Public: **Yes**

Then in SQL Editor, create a read policy:

```sql
CREATE POLICY "Public read access" ON storage.objects
  FOR SELECT USING (bucket_id = 'product-images');
```

Images will be accessible at:
```
https://<your-project-ref>.supabase.co/storage/v1/object/public/product-images/{product_id}.jpg
```

### 1.3 Grab Your Credentials

From Dashboard → Settings → Database:
- **Connection string** (Session mode, port 5432): `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`

From Dashboard → Settings → API:
- **Project URL**: `https://<ref>.supabase.co`
- **Service role key**: (for Storage uploads — keep secret)

---

## Step 2: Migrate Relational Data

### 2.1 Dump your local database

```bash
pg_dump -Fc -f vintage_vestige.dump postgresql://localhost/vintage_vestige
```

This creates a compressed binary dump (~179 MB, mostly base64 image data).

### 2.2 Restore to Supabase

```bash
pg_restore --no-owner --no-acl \
  -d "postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres" \
  vintage_vestige.dump
```

If you get errors about existing objects, add `--clean --if-exists`.

### 2.3 Add vector columns

In Supabase SQL Editor:

```sql
-- Vector columns for embeddings
ALTER TABLE products ADD COLUMN text_embedding vector(384);
ALTER TABLE products ADD COLUMN image_embedding vector(512);

-- HNSW indexes for fast similarity search (cosine distance)
CREATE INDEX idx_products_text_embedding
  ON products USING hnsw (text_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_products_image_embedding
  ON products USING hnsw (image_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

### 2.4 Fix sequences

After pg_restore, auto-increment sequences may be wrong:

```sql
SELECT setval('products_id_seq', (SELECT COALESCE(MAX(id), 0) FROM products));
SELECT setval('style_bridges_id_seq', (SELECT COALESCE(MAX(id), 0) FROM style_bridges));
```

### 2.5 Verify

```sql
SELECT 'products' as tbl, COUNT(*) FROM products
UNION ALL
SELECT 'style_bridges', COUNT(*) FROM style_bridges;
-- Expected: 4234, 7324
```

---

## Step 3: Install Python Dependencies

```bash
pip install pgvector supabase
```

`pgvector` gives you the SQLAlchemy `Vector` column type.
`supabase` is the Python client for Storage uploads (used in migration script).

---

## Step 4: Update `.env`

```bash
# Database — swap local for Supabase
DATABASE_URL=postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# Supabase Storage (for image uploads)
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<your-service-role-key>
SUPABASE_STORAGE_BUCKET=product-images

# Keep these for now (needed during embedding migration), remove after Step 6
QDRANT_HOST=localhost
QDRANT_PORT=6333

# These stay the same
ANTHROPIC_API_KEY=<unchanged>
SMITHSONIAN_API_KEY=<unchanged>
```

At this point, all your existing Python scripts that use `SessionLocal()` will connect to Supabase instead of local PG. Test it:

```bash
venv/bin/python -c "
from storage.database import SessionLocal, Product
db = SessionLocal()
print(f'Products: {db.query(Product).count()}')
db.close()
"
# Should print: Products: 4234
```

---

# Migration Scripts
## Step 5: Migrate Images to Supabase Storage

Create `scripts/migrate_images_to_storage.py`:

```python
"""
One-time migration: extract base64 images from products table,
upload to Supabase Storage, replace with public URLs.
"""
import os
import sys
import base64
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from storage.database import SessionLocal, Product

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'product-images')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
db = SessionLocal()

# Only migrate base64 images (skip products with HTTP URLs)
products = db.query(Product).filter(
    Product.primary_image.like('data:image%')
).all()

print(f"Found {len(products)} products with base64 images to migrate\n")

migrated = 0
failed = 0
batch_size = 50

for i, product in enumerate(products):
    try:
        # 1. Parse the data URL
        header, encoded = product.primary_image.split(',', 1)
        media_type = header.split(':')[1].split(';')[0]  # "image/jpeg"
        ext = 'jpg' if 'jpeg' in media_type else media_type.split('/')[1]

        # 2. Decode to bytes
        raw_bytes = base64.b64decode(encoded)

        # 3. Upload to Supabase Storage
        path = f"{product.id}.{ext}"
        result = supabase.storage.from_(BUCKET).upload(
            path,
            raw_bytes,
            {"content-type": media_type}
        )

        # 4. Build public URL and update product
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        product.primary_image = public_url

        migrated += 1

        if migrated % batch_size == 0:
            db.commit()
            print(f"  [{migrated}/{len(products)}] committed batch")

    except Exception as e:
        # If file already exists (re-run), just update the URL
        if 'Duplicate' in str(e) or 'already exists' in str(e):
            path = f"{product.id}.jpg"
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
            product.primary_image = public_url
            migrated += 1
        else:
            print(f"  FAILED product {product.id}: {e}")
            failed += 1

    # Gentle rate limiting
    if (i + 1) % 10 == 0:
        time.sleep(0.1)

db.commit()
db.close()

print(f"\nDone! Migrated: {migrated}, Failed: {failed}")
```

Run it:
```bash
venv/bin/python scripts/migrate_images_to_storage.py
```

**Verify:**
```sql
-- No base64 should remain
SELECT COUNT(*) FROM products WHERE primary_image LIKE 'data:image%';
-- Expected: 0

-- Check a few URLs
SELECT id, LEFT(primary_image, 80) FROM products LIMIT 5;
```

Open a few URLs in your browser to confirm images render.

---

## Step 6: Migrate Embeddings from Qdrant to pgvector

Make sure your local Qdrant is still running for this step.

Create `scripts/migrate_qdrant_to_pgvector.py`:

```python
"""
One-time migration: read embeddings from local Qdrant,
write them to pgvector columns in Supabase PostgreSQL.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from storage.database import SessionLocal, Product
from sqlalchemy import text

# Connect to local Qdrant (still running)
qdrant = QdrantClient(
    host=os.getenv('QDRANT_HOST', 'localhost'),
    port=int(os.getenv('QDRANT_PORT', '6333'))
)

db = SessionLocal()  # now pointing at Supabase

def migrate_collection(collection_name, column_name):
    """Scroll through a Qdrant collection and write vectors to pgvector column."""
    print(f"\nMigrating {collection_name} → {column_name}...")
    migrated = 0
    offset = None

    while True:
        points, offset = qdrant.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_vectors=True,
            with_payload=False,
        )

        for point in points:
            vec_str = str(point.vector)  # pgvector accepts '[0.1, 0.2, ...]' format
            db.execute(
                text(f"UPDATE products SET {column_name} = :vec WHERE id = :id"),
                {"vec": vec_str, "id": point.id}
            )
            migrated += 1

        db.commit()
        print(f"  Migrated {migrated} embeddings so far...")

        if offset is None:
            break

    print(f"  Done: {migrated} total")
    return migrated

# Migrate both collections
text_count = migrate_collection('vintage_text', 'text_embedding')
image_count = migrate_collection('vintage_images', 'image_embedding')

db.close()

print(f"\nMigration complete!")
print(f"  Text embeddings: {text_count}")
print(f"  Image embeddings: {image_count}")
```

Run it:
```bash
venv/bin/python scripts/migrate_qdrant_to_pgvector.py
```

**Verify:**
```sql
SELECT
  COUNT(*) FILTER (WHERE text_embedding IS NOT NULL) as has_text,
  COUNT(*) FILTER (WHERE image_embedding IS NOT NULL) as has_image,
  COUNT(*) as total
FROM products;
-- Expected: ~866 text, ~866 image, 4234 total

-- Test a similarity query works
SELECT id, title,
  1 - (text_embedding <=> (SELECT text_embedding FROM products WHERE id = 1)) as similarity
FROM products
WHERE text_embedding IS NOT NULL AND id != 1
ORDER BY text_embedding <=> (SELECT text_embedding FROM products WHERE id = 1)
LIMIT 5;
```

After this works, you can stop local Qdrant and remove `QDRANT_HOST`/`QDRANT_PORT` from `.env`.

---

# Core Code Changes
## Step 7: Update the ORM Model

**File:** `storage/database.py`

Add the pgvector import at the top:
```python
from pgvector.sqlalchemy import Vector
```

Add two columns to the `Product` class (after the `enriched_at` line):
```python
    # Vector embeddings (pgvector)
    text_embedding = Column(Vector(384), nullable=True)
    image_embedding = Column(Vector(512), nullable=True)
```

Nothing else changes in this file. `engine`, `SessionLocal`, `get_db`, `StyleBridge` all work as-is.

---

## Step 8: Create the Vector Search Module

**Create:** `storage/vector_search.py` (replaces `storage/vector_db.py`)

```python
"""
Vector similarity search using pgvector in PostgreSQL.
Replaces the Qdrant-based VectorDB class.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np


class VectorSearch:
    """Vector similarity search backed by pgvector columns on the products table."""

    def __init__(self, db: Session):
        self.db = db

    def search_text(self, query_vector, limit=10, filters=None):
        """
        Search products by text embedding cosine similarity.

        Args:
            query_vector: numpy array (384-dim)
            limit: max results
            filters: optional dict like {"platform": "met_museum", "fp_category": "dress"}
        Returns:
            list of dicts with product fields + score
        """
        where_parts = ["text_embedding IS NOT NULL"]
        params = {"vec": str(query_vector.tolist()), "limit": limit}

        if filters:
            for key, value in filters.items():
                if value is not None:
                    safe_key = key  # column name from SearchFilters schema
                    where_parts.append(f"{safe_key} = :{safe_key}")
                    params[safe_key] = value

        where_sql = " AND ".join(where_parts)

        rows = self.db.execute(text(f"""
            SELECT id, title, platform, category, primary_image,
                   era, decade, style_tags, colors, material,
                   garment_type, vibe, fit_style, occasion,
                   ai_description, culture, object_date, price,
                   fp_category,
                   1 - (text_embedding <=> :vec) as score
            FROM products
            WHERE {where_sql}
            ORDER BY text_embedding <=> :vec
            LIMIT :limit
        """), params).fetchall()

        return [dict(row._mapping) for row in rows]

    def search_image(self, query_vector, limit=10):
        """Search products by image embedding cosine similarity."""
        rows = self.db.execute(text("""
            SELECT id, title, platform, category, primary_image,
                   era, decade, style_tags, colors, material,
                   garment_type, vibe, fit_style, occasion,
                   ai_description, culture, object_date, price,
                   1 - (image_embedding <=> :vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL
            ORDER BY image_embedding <=> :vec
            LIMIT :limit
        """), {"vec": str(query_vector.tolist()), "limit": limit}).fetchall()

        return [dict(row._mapping) for row in rows]

    def get_embedding(self, product_id, embedding_type='text'):
        """Retrieve a product's embedding as a numpy array."""
        col = 'text_embedding' if embedding_type == 'text' else 'image_embedding'
        row = self.db.execute(
            text(f"SELECT {col} FROM products WHERE id = :id"),
            {"id": product_id}
        ).fetchone()
        if row and row[0]:
            return np.array(row[0])
        return None

    def upsert_embedding(self, product_id, text_vec=None, image_vec=None):
        """Write embeddings to product columns."""
        updates = []
        params = {"id": product_id}
        if text_vec is not None:
            updates.append("text_embedding = :text_vec")
            params["text_vec"] = str(text_vec.tolist())
        if image_vec is not None:
            updates.append("image_embedding = :image_vec")
            params["image_vec"] = str(image_vec.tolist())
        if updates:
            self.db.execute(
                text(f"UPDATE products SET {', '.join(updates)} WHERE id = :id"),
                params
            )
            self.db.commit()
```

**Key difference from old VectorDB:** This takes a SQLAlchemy `Session` — no separate connection. Vector search and relational queries share the same session.

---

## Step 9: Update API Dependencies

**File:** `api/dependencies.py`

Replace the entire file:

```python
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session

from storage.database import get_db
from storage.vector_search import VectorSearch
from embeddings.generator import EmbeddingGenerator


def get_vector_search(db: Session = Depends(get_db)) -> VectorSearch:
    """VectorSearch using the request's DB session."""
    return VectorSearch(db)


@lru_cache(maxsize=1)
def get_embedding_generator() -> EmbeddingGenerator:
    """Create EmbeddingGenerator once, reuse for all requests."""
    return EmbeddingGenerator()
```

---

## Step 10: Rewrite Search Router

**File:** `api/routers/search.py`

Complete rewrite — remove all Qdrant imports, use VectorSearch:

```python
from fastapi import APIRouter, Depends
import base64
from io import BytesIO
from PIL import Image

from embeddings.generator import EmbeddingGenerator
from storage.vector_search import VectorSearch
from api.dependencies import get_vector_search, get_embedding_generator
from api.schemas.search import (
    TextSearchRequest, ImageSearchRequest,
    SearchResult, SearchResponse, SearchFilters,
)

router = APIRouter(prefix="/search", tags=["search"])


def _build_filter_dict(filters: SearchFilters | None) -> dict | None:
    if not filters:
        return None
    d = {k: v for k, v in filters.model_dump(exclude_none=True).items()}
    return d if d else None


@router.post("/text", response_model=SearchResponse)
def search_text(
    body: TextSearchRequest,
    vs: VectorSearch = Depends(get_vector_search),
    emb: EmbeddingGenerator = Depends(get_embedding_generator),
):
    """Search products by text query."""
    text_vector = emb.generate_text_embedding(body.query)
    filters = _build_filter_dict(body.filters)
    hits = vs.search_text(text_vector, limit=body.limit, filters=filters)

    results = [SearchResult(
        id=hit["id"],
        score=hit["score"],
        title=hit.get("title", ""),
        category=hit.get("category"),
        primary_image=hit.get("primary_image"),
        era=hit.get("era"),
        decade=hit.get("decade"),
        style_tags=hit.get("style_tags", []),
        colors=hit.get("colors", []),
        material=hit.get("material"),
        garment_type=hit.get("garment_type"),
        vibe=hit.get("vibe"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
    ) for hit in hits]

    return SearchResponse(results=results, query=body.query, total=len(results))


@router.post("/image", response_model=SearchResponse)
def search_image(
    body: ImageSearchRequest,
    vs: VectorSearch = Depends(get_vector_search),
    emb: EmbeddingGenerator = Depends(get_embedding_generator),
):
    """Search products by image upload."""
    header, b64data = body.image.split(",", 1)
    raw = base64.b64decode(b64data)
    pil_image = Image.open(BytesIO(raw))

    vector = emb.generate_image_embedding(pil_image)
    hits = vs.search_image(vector, limit=body.limit)

    results = [SearchResult(
        id=hit["id"],
        score=hit["score"],
        title=hit.get("title", ""),
        category=hit.get("category"),
        primary_image=hit.get("primary_image"),
        era=hit.get("era"),
        decade=hit.get("decade"),
        style_tags=hit.get("style_tags", []),
        colors=hit.get("colors", []),
        material=hit.get("material"),
        garment_type=hit.get("garment_type"),
        vibe=hit.get("vibe"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
    ) for hit in hits]

    return SearchResponse(results=results, query="[image]", total=len(results))
```

**Important:** `style_tags` and `colors` come back as JSON strings from SQL (they're `Text` columns). The old Qdrant payload had these pre-parsed. Add validators to `SearchResult` — see Step 11.

---

## Step 11: Add JSON Validators to Search Schema

**File:** `api/schemas/search.py`

Add to the `SearchResult` class:

```python
import json
from pydantic import field_validator

class SearchResult(BaseModel):
    # ... existing fields ...

    @field_validator("style_tags", "colors", mode="before")
    @classmethod
    def parse_json_lists(cls, v):
        """Handle JSON strings coming from SQL vs lists from old Qdrant."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v if isinstance(v, list) else []
```

---

# Convert Bridge Computation from Qdrant to pgvector
## Step 12: Update compute_bridges.py

This is the biggest single-file change. Here's what to replace conceptually:

**File:** `analysis/compute_bridges.py`

### 12.1 Imports — remove Qdrant, add pgvector helpers
```python
# REMOVE these:
from storage.vector_db import VectorDB
from qdrant_client.models import Filter, FieldCondition, MatchValue, HasIdCondition

# KEEP these:
from storage.database import SessionLocal, Product, StyleBridge
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func, text
```

### 12.2 Replace the ID-fetching functions

Old pattern (scrolls Qdrant collections):
```python
text_ids = set of IDs from qdrant vintage_text collection
image_ids = set of IDs from qdrant vintage_images collection
```

New pattern (query products table):
```python
text_ids = {r[0] for r in db.execute(
    text("SELECT id FROM products WHERE text_embedding IS NOT NULL")
).fetchall()}

image_ids = {r[0] for r in db.execute(
    text("SELECT id FROM products WHERE image_embedding IS NOT NULL")
).fetchall()}
```

### 12.3 Replace vector retrieval per product

Old: `vdb.client.retrieve(collection_name='vintage_text', ids=[product.id])`

New:
```python
row = db.execute(
    text("SELECT text_embedding, image_embedding FROM products WHERE id = :id"),
    {"id": product.id}
).fetchone()

text_vector = row[0] if row else None  # pgvector returns as list
image_vector = row[1] if row else None
```

### 12.4 Replace candidate search

Old pattern used `vdb.client.search()` with Qdrant filters.

New pattern — a helper function:
```python
def search_candidates_pgvector(db, product_id, text_vector, image_vector,
                                exclude_sql, exclude_params, top_k):
    """Search for bridge candidates using pgvector."""
    candidates = {}
    params = {"pid": product_id, "top_k": top_k, **exclude_params}

    if text_vector is not None:
        params["text_vec"] = str(list(text_vector))
        rows = db.execute(text(f"""
            SELECT id, 1 - (text_embedding <=> :text_vec) as score
            FROM products
            WHERE text_embedding IS NOT NULL
              AND id != :pid
              {exclude_sql}
            ORDER BY text_embedding <=> :text_vec
            LIMIT :top_k
        """), params).fetchall()
        for row in rows:
            candidates[row[0]] = {'text_score': row[1], 'image_score': None}

    if image_vector is not None:
        params["img_vec"] = str(list(image_vector))
        rows = db.execute(text(f"""
            SELECT id, 1 - (image_embedding <=> :img_vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL
              AND id != :pid
              {exclude_sql}
            ORDER BY image_embedding <=> :img_vec
            LIMIT :top_k
        """), params).fetchall()
        for row in rows:
            if row[0] in candidates:
                candidates[row[0]]['image_score'] = row[1]
            else:
                candidates[row[0]] = {'text_score': None, 'image_score': row[1]}

    return candidates
```

### 12.5 Replace Qdrant filter builders with SQL WHERE fragments

Old: `Filter(must_not=[FieldCondition(key="fp_category", match=MatchValue(value=cat))])`

New:
```python
# Open discovery — no exclusions
def build_open_filter(product):
    return "", {}

# Cross-category — exclude same fp_category
def build_cross_category_filter(product):
    if not product.fp_category:
        return None, None
    return "AND fp_category != :excl_cat", {"excl_cat": product.fp_category}

# Cross-vibe — exclude same vibe
def build_cross_vibe_filter(product):
    if not product.vibe:
        return None, None
    return "AND vibe != :excl_vibe", {"excl_vibe": product.vibe}

# Cross-culture — exclude same culture
def build_cross_culture_filter(product):
    if not product.culture:
        return None, None
    return "AND culture != :excl_culture", {"excl_culture": product.culture}
```

### 12.6 Update `build_cross_vibe_filter` for the new vibe vocabulary:
After MMFashion re-enrichment, the meaningful vibe data moves from the single
`vibe` string to the `core_vibes` array. Update the filter to use `core_vibes[1]`
(Postgres arrays are 1-indexed) with a fallback to `vibe` for products not yet
re-enriched:
```python
def build_cross_vibe_filter(product):
    # Use core_vibes[0] if available (post-MMFashion), fall back to legacy vibe
    primary_vibe = (product.core_vibes[0] if product.core_vibes else product.vibe)
    if not primary_vibe:
        return None, None
    if product.core_vibes:
        return "AND (core_vibes[1] IS NULL OR core_vibes[1] != :excl_vibe)", \
               {"excl_vibe": primary_vibe}
    else:
        return "AND vibe != :excl_vibe", {"excl_vibe": primary_vibe}
```

The fallback is essential — when you first run `compute_bridges.py` after Step 12
but before MMFashion re-enrichment, `core_vibes` is null on all products. Without
it the cross_vibe pass produces nothing. After MMFashion runs and you recompute
bridges in Phase 7, all products will have `core_vibes` and the fallback is never
hit.
### 12.7 Remove VectorDB initialization

In the main function, remove `vdb = VectorDB()`. Everything goes through `db` (the SQLAlchemy session).

**Everything else in compute_bridges.py stays the same:** score_candidates(), compute_structural_score(), bridge_type classification, pg_insert upsert, etc.

---

# Update Embedding and Enrichment Scripts
## Step 13: Update embeddings/generator.py

### 13.1 Handle URL images (not just base64)

Replace `decode_data_url()` with a more general loader:

```python
import requests

def load_image(image_ref):
    """Load image from data URL, HTTP URL, or PIL Image."""
    if not image_ref:
        return None
    if isinstance(image_ref, Image.Image):
        return image_ref
    if isinstance(image_ref, str):
        if image_ref.startswith('data:image'):
            header, encoded = image_ref.split(',', 1)
            return Image.open(BytesIO(base64.b64decode(encoded)))
        elif image_ref.startswith('http'):
            resp = requests.get(image_ref, timeout=15)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content))
    return None
```

Update `generate_product_embeddings()` to use `load_image()` instead of `decode_data_url()`.

### 13.2 Write embeddings to product columns (not Qdrant)

In `generate_embeddings_for_database()`, replace the Qdrant storage block (lines 147-161):

```python
# OLD: store in Qdrant
# vector_db = VectorDB()
# for item in embeddings_data:
#     vector_db.upsert_product(...)

# NEW: write to product columns
for item in embeddings_data:
    product = db.query(Product).filter(
        Product.id == int(item['product_id'])
    ).first()
    if product:
        if item.get('text_embedding') is not None:
            product.text_embedding = item['text_embedding'].tolist()
        if item.get('image_embedding') is not None:
            product.image_embedding = item['image_embedding'].tolist()
db.commit()
```

Remove the `from storage.vector_db import VectorDB` import.

---

## Step 14: Update enrichment/claude.py

The Claude API supports both base64 and URL image sources. Update the image block builder (appears in `enrich_product` and `generate_bridge_narrative_async`):

```python
# Where you build the image content block:
if image_data:
    if image_data.startswith('data:image'):
        # Legacy base64 data URL
        header, encoded = image_data.split(',', 1)
        media_type = header.split(':')[1].split(';')[0]
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            }
        })
    elif image_data.startswith('http'):
        # Supabase Storage URL (or any HTTP URL)
        content.append({
            "type": "image",
            "source": {
                "type": "url",
                "url": image_data,
            }
        })
```

This is backward-compatible — existing base64 still works, new URLs work too.

---

## Step 15: Update Enrichment + Embedding Scripts

All 6 files follow the same pattern. In each one:

1. Remove `from storage.vector_db import VectorDB`
2. Remove any `from qdrant_client.models import PointStruct` etc.
3. Replace Qdrant upsert blocks with direct column updates

**Files to update:**

| File | What to change |
|------|----------------|
| `enrichment/scripts/enrich_and_reembed_all.py` | Replace `vector_db.upsert_product(...)` with `product.text_embedding = vec.tolist()` |
| `enrichment/scripts/enrich_remaining.py` | Same pattern |
| `enrichment/scripts/reenrich_fashionpedia.py` | Same pattern |
| `embeddings/scripts/rebuild_embeddings.py` | Same pattern |
| `embeddings/scripts/generate_all_embeddings.py` | Same pattern |
| `embeddings/scripts/generate_image_embeddings.py` | Same pattern |

The pattern in every case:

```python
# OLD
vector_db.upsert_product(
    product_id=str(product.id),
    embeddings={'text_embedding': text_emb, 'image_embedding': img_emb},
    metadata={...big dict of product fields...}
)

# NEW (so much simpler!)
product.text_embedding = text_emb.tolist() if text_emb is not None else None
product.image_embedding = img_emb.tolist() if img_emb is not None else None
db.commit()
```

No more building payload dicts. No more keeping Qdrant in sync with PostgreSQL.

---

# Cleanup, Frontend, Tests, Verification
## Step 16: Delete Obsolete Files

These are no longer needed:
- `storage/load_data/backfill_qdrant_platform.py` — was for fixing Qdrant payloads
- `embeddings/scripts/backfill_image_payloads.py` — same

Keep `storage/vector_db.py` for reference until you've verified everything works, then delete it.

---

## Step 17: Update Frontend

**File:** `vv-web/next.config.ts`

Add your Supabase project hostname:

```typescript
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.metmuseum.org" },
      { protocol: "https", hostname: "ids.si.edu" },
      { protocol: "https", hostname: "*.etsy.com" },
      { protocol: "https", hostname: "i.etsystatic.com" },
      { protocol: "https", hostname: "<your-project-ref>.supabase.co" },
    ],
  },
};
```

No changes needed in `ImageWithFallback.tsx` or `ProductCard.tsx` — they already handle regular URLs.

---

## Step 18: Update Tests

**`tests/conftest.py`:**
- Remove any `vector_db` fixture that creates a `VectorDB()` instance
- Add a `vector_search` fixture:
  ```python
  @pytest.fixture(scope="session")
  def vector_search(db_session):
      from storage.vector_search import VectorSearch
      return VectorSearch(db_session)
  ```

**Integration tests:** Update any that import `VectorDB` or `qdrant_client` to use `VectorSearch` instead.

**Unit tests:** Should pass unchanged (they don't touch the DB).

---

## Step 19: Verify Everything

### Quick checks
```bash
# Unit tests (no DB needed)
venv/bin/python -m pytest tests/unit/ -v

# Integration tests (hits Supabase)
venv/bin/python -m pytest tests/integration/ -v

# Data integrity
venv/bin/python -m pytest tests/data_integrity/ -v
```

### Manual API test
```bash
# Start the API
cd /Users/jenkim/PROJECTS/VINTAGE_VESTIGE
uvicorn api.main:app --reload

# Test text search
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "silk evening gown", "limit": 5}'

# Test product detail (check image URL renders)
curl http://localhost:8000/products/1
```

### Bridge computation test
```bash
venv/bin/python analysis/compute_bridges.py --limit=5
```

### Frontend test
```bash
cd vv-web && npm run dev
```
Open localhost:3000, verify images load in ProductCards.

---

## Step 20: Cleanup

1. Remove `qdrant-client` from `requirements.txt`
2. Delete `storage/vector_db.py`
3. Remove `QDRANT_HOST` and `QDRANT_PORT` from `.env`
4. Stop local Qdrant server
5. Archive `vintage_vestige.dump`
6. Update docs: `ARCHITECTURE.md`, `API_SPEC.md`, `PROJECT_STATE.md`

---

## Optional: Image Upload Helper for Future Loaders

After migration, new data loaders should upload images to Supabase Storage directly instead of base64-encoding into the DB. Create a shared helper:

**Create:** `storage/image_storage.py`

```python
"""Upload images to Supabase Storage."""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
    return _client

def upload_product_image(product_id, image_bytes, content_type="image/jpeg"):
    """
    Upload image bytes to Supabase Storage.
    Returns the public URL.
    """
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'product-images')
    ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[1]
    path = f"{product_id}.{ext}"

    client = _get_client()
    client.storage.from_(bucket).upload(path, image_bytes, {"content-type": content_type})

    return f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{bucket}/{path}"
```

Then in loaders, replace `base64.b64encode(...)` → `upload_product_image(product_id, raw_bytes)`. This can be done incrementally — existing loaders still work, they'll just store slightly longer URLs.

---

## Summary of All File Changes

| # | File | Action | Difficulty |
|---|------|--------|------------|
| 1 | `.env` | Modify — Supabase credentials | Easy |
| 2 | `storage/database.py` | Modify — add 2 Vector columns | Easy |
| 3 | `storage/vector_search.py` | **Create** — pgvector search class | Medium |
| 4 | `storage/image_storage.py` | **Create** — Supabase Storage helper | Easy |
| 5 | `api/dependencies.py` | Modify — swap VectorDB → VectorSearch | Easy |
| 6 | `api/routers/search.py` | Rewrite — pgvector search | Medium |
| 7 | `api/schemas/search.py` | Modify — add JSON validators | Easy |
| 8 | `analysis/compute_bridges.py` | Modify — replace Qdrant with pgvector SQL | Hard |
| 9 | `embeddings/generator.py` | Modify — write to columns, URL images | Medium |
| 10 | `enrichment/claude.py` | Modify — URL image support | Easy |
| 11 | 6 enrichment/embedding scripts | Modify — replace Qdrant upserts | Easy (repetitive) |
| 12 | `scripts/migrate_images_to_storage.py` | **Create** — one-time migration | Medium |
| 13 | `scripts/migrate_qdrant_to_pgvector.py` | **Create** — one-time migration | Easy |
| 14 | `vv-web/next.config.ts` | Modify — add Supabase hostname | Easy |
| 15 | `tests/conftest.py` | Modify — swap fixtures | Easy |
| 16 | 2 backfill scripts | **Delete** | — |
| 17 | `storage/vector_db.py` | **Delete** (after verification) | — |
