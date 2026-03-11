# Vintage Vestige — Architecture

**As of: 2026-03-09**

---

## System Overview

Vintage Vestige is a 3-layer fashion intelligence platform:

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCT LAYER                        │
│                                                         │
│   Next.js 16 Frontend         FastAPI Backend           │
│   (vv-web/)                   (api/)                    │
│   [COMPLETE]                  [IMPLEMENTED]             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                  INTELLIGENCE LAYER                     │
│                                                         │
│   Claude Enrichment    Embedding Pipeline    Bridges    │
│   (enrichment/)        (embeddings/)         (tools/)   │
│   [WORKING]            [WORKING]             [WORKING]  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                      DATA LAYER                         │
│                                                         │
│   Supabase PostgreSQL + pgvector     Supabase Storage   │
│   (products, style_bridges,          (product-images    │
│    text_embedding 384d,               public bucket)    │
│    image_embedding 512d)                                │
│   [WORKING]                          [WORKING]          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Ingestion Pipeline

```
HuggingFace Datasets ─┐
Met Museum API ────────┤
Smithsonian API ───────┘
        │
        ▼
  load_data/*.py          # Parse, normalize, insert
        │
        ▼
  PostgreSQL:products     # 4,234 rows (raw metadata)
        │
        ▼
  enrichment/claude.py    # Claude Sonnet 4 enrichment
  enrichment/enrich_async.py  # Async concurrent (5x speedup)
        │                   (23 structured fields per product)
        ▼
  PostgreSQL:products     # Updated with enrichment fields
        │
        ├──► embeddings/generator.py  # all-MiniLM-L6-v2 (text)
        │         │
        │         ▼
        │    products.text_embedding  # 866 rows, vector(384), HNSW index
        │
        └──► embeddings/generator.py  # clip-ViT-B-32 (image)
                  │
                  ▼
             products.image_embedding # 866 rows, vector(512), HNSW index
```

### Bridge Discovery Pipeline

```
  products.text_embedding ──┐
  products.image_embedding ─┘
        │
        ▼
  analysis/compute_bridges.py
  │
  │  Pass 1: Open discovery (text + image similarity)
  │  Pass 2: Cross-culture (different culture)
  │
  │  For each candidate pair:
  │    text_similarity   ← cosine(text_a, text_b)
  │    image_similarity  ← cosine(img_a, img_b)  [if available]
  │    structural_score  ← weighted Jaccard over 12 Fashionpedia fields
  │    bridge_score      ← 0.40*text + 0.30*image + 0.30*structural
  │                        (or 0.55*text + 0.45*structural if no image)
  │
  ▼
  PostgreSQL:style_bridges  # 3,367 rows
        │
        ▼
  analysis/generate_narratives.py  # Async Claude calls
        │
        ▼
  PostgreSQL:style_bridges.bridge_narrative  # 3,367/3,367 (100%)
```

### Search Flow (UPDATED 2026-03-04 for pgvector)

```
  User Query (text or image)
        │
        ▼
  FastAPI (api/routers/search.py)       [IMPLEMENTED]
        │
        ├──► POST /search/text
        │     → EmbeddingGenerator.generate_text_embedding(query)
        │     → _build_filter_dict(SearchFilters) → SQL WHERE params
        │     → VectorSearch.search_text(vector, filters)  [pgvector <=> cosine]
        │     → Map SQL rows to SearchResult
        │
        └──► POST /search/image
              → base64 decode → PIL Image
              → EmbeddingGenerator.generate_image_embedding(pil_image)
              → VectorSearch.search_image(vector)  [pgvector <=> cosine]
              → Map SQL rows to SearchResult
                    │
                    ▼
              Next.js frontend renders    [COMPLETE]
```

Search uses pgvector cosine distance (`<=>`) with HNSW indexes. Filters are native SQL WHERE clauses — no separate vector database needed.

---

## Tech Stack

### Backend (Python 3.13.7)

| Package | Version | Purpose |
|---------|---------|---------|
| SQLAlchemy | 2.0.36 | PostgreSQL ORM |
| psycopg | (via psycopg2) | PostgreSQL driver |
| pgvector | latest | SQLAlchemy Vector column type + HNSW indexes |
| anthropic | 0.40.0 | Claude API (enrichment + narratives) |
| sentence-transformers | 3.3.1 | CLIP + MiniLM models |
| FastAPI | 0.104.1 | REST API (13 endpoints, 13 schemas) |
| Pillow | (bundled) | Image processing |
| python-dotenv | (bundled) | Environment variables |
| supabase | latest | Supabase Storage client (image uploads) |
| pytest | (dev) | Testing framework |

### Frontend (Node.js 25.2.0)

| Package | Version | Purpose |
|---------|---------|---------|
| Next.js | 16.1.6 | React framework |
| React | 19.2.3 | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| lucide-react | 0.564.0 | Icons |
| clsx + CVA | latest | Component utilities |

### Infrastructure

| Service | Config | Purpose |
|---------|--------|---------|
| Supabase PostgreSQL + pgvector | `db.tusswxlrdoamintvswjs.supabase.co:5432` | Relational data + vector search |
| Supabase Storage | `product-images` public bucket | Product image hosting |
| Claude API | `claude-sonnet-4-20250514` | AI enrichment |

---

## Database Schema

### Supabase PostgreSQL + pgvector (confirmed via live query 2026-03-04)

**Tables in database:** `products`, `style_bridges`

#### `products` table (4,234 rows, 1,490 enriched, 1,190 with text embeddings)

```sql
-- storage/database.py:16-83
id              INTEGER     PRIMARY KEY, auto-increment
external_id     VARCHAR     UNIQUE, indexed
platform        VARCHAR     indexed  -- 'fashionpedia', 'met_museum', 'smithsonian'

-- Basic info
title           VARCHAR
description     TEXT
price           FLOAT
currency        VARCHAR     DEFAULT 'USD'

-- Images
primary_image   VARCHAR     -- Supabase Storage HTTP URL
image_urls      TEXT        -- JSON array

-- Seller info
seller_name     VARCHAR
seller_url      VARCHAR
url             VARCHAR

-- Source metadata
color           VARCHAR     nullable  -- 0/866 populated
season          VARCHAR     nullable  -- 0/866 populated
year            FLOAT       nullable  -- 0/866 populated

-- Structured metadata
era             VARCHAR     nullable  -- 866/866 populated (from enrichment)
decade          VARCHAR     nullable  -- 865/866
category        VARCHAR     nullable  -- 866/866
style_tags      TEXT        nullable  -- 866/866 (JSON array)
material        VARCHAR     nullable  -- 866/866
pattern         VARCHAR     nullable  -- 0/866
garment_type    VARCHAR     nullable  -- 866/866
culture         VARCHAR     nullable  -- 344/866
period          VARCHAR     nullable  -- 0/866
object_date     VARCHAR     nullable  -- 158/866

-- AI enrichment fields
colors          TEXT        nullable  -- 866/866 (JSON array)
vibe            VARCHAR     nullable  -- 866/866
fit_style       VARCHAR     nullable  -- 866/866
occasion        VARCHAR     nullable  -- 866/866
ai_description  TEXT        nullable  -- 866/866
enriched_text   TEXT        nullable  -- 866/866

-- Fashionpedia taxonomy (from Claude enrichment)
fp_category        VARCHAR  nullable  -- 855/866
silhouette         VARCHAR  nullable  -- 753/866
neckline           VARCHAR  nullable  -- 135/866
waistline          VARCHAR  nullable  -- 697/866
length             VARCHAR  nullable  -- 656/866
sleeve_length      VARCHAR  nullable  -- 211/866
opening_type       VARCHAR  nullable  -- not counted
textile_pattern    VARCHAR  nullable  -- 845/866
textile_finishing  TEXT     nullable  -- 866/866 (JSON array)
nickname           VARCHAR  nullable  -- 508/866
garment_parts      TEXT     nullable  -- 866/866 (JSON array)
decorations        TEXT     nullable  -- 866/866 (JSON array)

-- Vector embeddings (pgvector)
text_embedding  vector(384) nullable  -- all-MiniLM-L6-v2, HNSW cosine index
image_embedding vector(512) nullable  -- clip-ViT-B-32, HNSW cosine index

-- Timestamps
created_at      DATETIME    DEFAULT utcnow
updated_at      DATETIME    DEFAULT utcnow, on_update
embedded_at     DATETIME    nullable  -- 200/866 set (tracking gap)
enriched_at     DATETIME    nullable  -- 866/866 set
```

#### `style_bridges` table (3,367 rows)

```sql
-- storage/database.py:85-111
id                  INTEGER     PRIMARY KEY
source_id           INTEGER     FK → products.id, indexed
target_id           INTEGER     FK → products.id, indexed

text_similarity     FLOAT       NOT NULL
image_similarity    FLOAT       nullable
structural_score    FLOAT       NOT NULL
bridge_score        FLOAT       NOT NULL  -- range: 0.30–0.93

shared_attributes   TEXT        nullable  -- JSON string
bridge_type         VARCHAR     nullable  -- cross_era, near_era, cross_category, cross_vibe
bridge_narrative    TEXT        nullable  -- 3,367/3,367 (100%)

-- IIT 4.0 future columns (nullable, unused)
phi_score           FLOAT       nullable
cnn_structural_score FLOAT      nullable

created_at          DATETIME    DEFAULT utcnow

-- Constraints
UNIQUE (source_id, target_id)  -- canonical ordering: source_id < target_id
```

### pgvector Indexes

| Index | Column | Type | Params |
|-------|--------|------|--------|
| `idx_products_text_embedding` | `text_embedding` | HNSW | `vector_cosine_ops`, m=16, ef_construction=64 |
| `idx_products_image_embedding` | `image_embedding` | HNSW | `vector_cosine_ops`, m=16, ef_construction=64 |

1,190/4,234 products have text embeddings, 866/4,234 have image embeddings. Search uses cosine distance operator `<=>` with `1 - distance` for similarity scores.

**Note:** Qdrant was used prior to 2026-03-04 (`vintage_text` and `vintage_images` collections). All embeddings were migrated to pgvector columns and Qdrant has been removed.

---

## Embedding Pipeline

### Text Embeddings

- **Model:** `all-MiniLM-L6-v2` (384-dim, SentenceTransformers)
- **Input:** `enriched_text` field — natural language concatenation of:
  1. `ai_description` (richest content, first)
  2. Identity: era + decade + nickname + garment_type + material + colors
  3. Structural: silhouette + neckline + length + waistline + sleeve_length
  4. Style: style_tags + vibe
  5. Details: fit_style + textile_pattern + textile_finishing + occasion
  6. Decorations
- **Construction:** [enrichment/claude.py:400-482](enrichment/claude.py#L400-L482) (`build_rich_text()`)
- **Target:** ~256 tokens (model's effective window)

### Image Embeddings

- **Model:** `clip-ViT-B-32` (512-dim, SentenceTransformers)
- **Input:** PIL Image (from URL or base64 data URL)
- **Processing:** Auto-converts to RGB if needed
- **Source:** [embeddings/models.py:38-65](embeddings/models.py#L38-L65)

### Singleton Pattern

Both models are loaded once via `EmbeddingModels` singleton ([embeddings/models.py:7-36](embeddings/models.py#L7-L36)). First load downloads ~500MB of model weights.

---

## Bridge Scoring Algorithm

Defined in [analysis/compute_bridges.py](analysis/compute_bridges.py).

### Structural Score (12 weighted fields)

```python
# Exact match fields (weight × (1.0 if match, else 0.0))
fp_category:       0.20
silhouette:        0.15
neckline:          0.08
waistline:         0.07
length:            0.07
sleeve_length:     0.05
opening_type:      0.03
textile_pattern:   0.05
nickname:          0.05

# Jaccard overlap fields (weight × |intersection|/|union|)
textile_finishing: 0.10
garment_parts:     0.05
decorations:       0.10
```

### Composite Bridge Score

Mode-dependent weights (proportionally redistributed when image is NULL):

```
Contrast:   0.20 × text_sim + 0.20 × image_sim + 0.60 × structural
Resonance:  0.60 × text_sim + 0.20 × image_sim + 0.20 × structural
Affinity:   0.40 × text_sim + 0.30 × image_sim + 0.30 × structural
```

### Multi-Dimensional Bridge Classification

After bridge computation, `tools/analysis/classify_bridge_dimensions.py` populates 6 orthogonal dimensions on each bridge:

| Column | Values | Source |
|--------|--------|--------|
| `temporal_type` | transmission \| continuation \| contemporary | Era/decade distance or platform proxy |
| `crossing_type` | same_context \| cross_category \| cross_culture \| cross_category_culture | Category group + culture comparison |
| `connection_mode` | contrast \| resonance \| affinity | Vibe opposition, text similarity, or fallback |
| `primary_axis` | volume \| ornament \| body \| register | Dominant axis from shared_attributes field mapping |
| `secondary_axis` | volume \| ornament \| body \| register | Second axis (if any) |
| `contrast_pair` | e.g. "Exaggerated Volume <-> Column Minimalism" | Only for contrast mode |

**Connection mode detection (priority order):**
1. **contrast** — opposing vibes from 9 opposition pairs + structural_score > 0.4
2. **resonance** — text_sim >= 0.85 + temporal_type == 'transmission'
3. **affinity** — everything else (primary_axis tells the story)

---

## Future Architecture (Designed, Not Built)

### IIT 4.0 Integration

Detailed in [docs/IIT_4.0_INTEGRATION_PLAN.md](IIT_4.0_INTEGRATION_PLAN.md) (78K, designed 2026-02-19).

4 approaches planned:
1. **Φ-Based Search Ranking** — Re-rank results by integrated information between modalities
2. **Maximal Attribute Selection** — Use Φ to identify which enrichment fields matter most
3. **Emergent Complex Discovery** — Find irreducible aesthetic archetypes in the data
4. **Adaptive Multi-Modal Weighting** — Dynamically adjust image vs. text weight per query

Implementation timeline: 6–10 weeks post-MVP. Requires new tables (`phi_scores`, `maximal_complexes`, `discovered_complexes`), new API endpoints, and frontend Φ visualization.

Quick-reference: [docs/IIT_REFERENCE.md](IIT_REFERENCE.md)

### CNN Visual Attribute Extraction

Detailed in [docs/CNN_INTEGRATION_SUMMARY.md](CNN_INTEGRATION_SUMMARY.md) (designed 2026-02-19).

4 phases:
1. Multi-Task Attribute CNN (ResNet50 backbone, 5 task heads)
2. CLIP Fine-Tuning (contrastive learning on rich_text/image pairs)
3. Era Classification network
4. Φ-Based Fusion (vision vs. text agreement scoring)

Adds 2–4 weeks to IIT timeline.

### Platform Expansion

Detailed in [docs/reference/fashion_intelligence_platform.md](reference/fashion_intelligence_platform.md).

- Phase 2: Style DNA API (B2B, months 3–6)
- Phase 3: Scale data layer to 10K+ items (V&A, Europeana, months 6–12)
- Phase 4: Trend Oracle analytics (months 9–15)
- Phase 5: Platform & marketplace (months 12+)

Target data sources: V&A, LACMA, Europeana Fashion, iDesigner, Etsy/Depop scraping. See [docs/reference/vintage_databases.md](reference/vintage_databases.md).
