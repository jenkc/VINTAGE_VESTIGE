# Vintage Vestige — Architecture

**As of: 2026-02-22 (end of day)**

---

## System Overview

Vintage Vestige is a 3-layer fashion intelligence platform:

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCT LAYER                        │
│                                                         │
│   Next.js 16 Frontend         FastAPI Backend           │
│   (vv-web/)                   (api/)                    │
│   [PARTIAL]                   [IMPLEMENTED]             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                  INTELLIGENCE LAYER                     │
│                                                         │
│   Claude Enrichment    Embedding Pipeline    Bridges    │
│   (enrichment/)        (embeddings/)         (scripts/) │
│   [WORKING]            [WORKING]             [WORKING]  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                      DATA LAYER                         │
│                                                         │
│   PostgreSQL            Qdrant Vector DB                │
│   (products,            (vintage_text 384d,             │
│    style_bridges)        vintage_images 512d)           │
│   [WORKING]             [WORKING]                       │
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
  PostgreSQL:products     # 866 rows (raw metadata)
        │
        ▼
  enrichment/claude.py    # Claude Sonnet 4 enrichment
        │                   (23 structured fields per product)
        ▼
  PostgreSQL:products     # Updated with enrichment fields
        │
        ├──► embeddings/generator.py  # all-MiniLM-L6-v2 (text)
        │         │
        │         ▼
        │    Qdrant:vintage_text      # 866 points, 384-dim
        │
        └──► embeddings/generator.py  # clip-ViT-B-32 (image)
                  │
                  ▼
             Qdrant:vintage_images    # 866 points, 512-dim
```

### Bridge Discovery Pipeline

```
  Qdrant:vintage_text ──┐
  Qdrant:vintage_images ┘
        │
        ▼
  analysis/compute_bridges.py
  │
  │  Pass 1: Open discovery (text + image similarity)
  │  Pass 2: Cross-category (different fp_category)
  │  Pass 3: Cross-vibe (different vibe)
  │
  │  For each candidate pair:
  │    text_similarity   ← cosine(text_a, text_b)
  │    image_similarity  ← cosine(img_a, img_b)  [if available]
  │    structural_score  ← weighted Jaccard over 12 Fashionpedia fields
  │    bridge_score      ← 0.40*text + 0.30*image + 0.30*structural
  │                        (or 0.55*text + 0.45*structural if no image)
  │
  ▼
  PostgreSQL:style_bridges  # 7,324 rows
        │
        ▼
  analysis/generate_narratives.py  # Async Claude calls
        │
        ▼
  PostgreSQL:style_bridges.bridge_narrative  # 22/7324 populated
```

### Search Flow (IMPLEMENTED 2026-02-22)

```
  User Query (text or image)
        │
        ▼
  FastAPI (api/routers/search.py)       [IMPLEMENTED]
        │
        ├──► POST /search/text
        │     → EmbeddingGenerator.generate_text_embedding(query)
        │     → _build_qdrant_filter(SearchFilters) → Qdrant Filter
        │     → VectorDB.search_similar(vintage_text, vector, query_filter)
        │     → Map hits to SearchResult (from Qdrant payload)
        │
        └──► POST /search/image
              → base64 decode → PIL Image
              → EmbeddingGenerator.generate_image_embedding(pil_image)
              → VectorDB.search_similar(vintage_images, vector)
              → Map hits to SearchResult (from Qdrant payload)
                    │
                    ▼
              Next.js frontend renders    [STUBS ONLY]
```

Both collections have identical 28-field payloads — no Postgres join needed for either search type.

---

## Tech Stack

### Backend (Python 3.13.7)

| Package | Version | Purpose |
|---------|---------|---------|
| SQLAlchemy | 2.0.36 | PostgreSQL ORM |
| psycopg | (via psycopg2) | PostgreSQL driver |
| qdrant-client | 1.12.1 | Vector database client |
| anthropic | 0.40.0 | Claude API (enrichment + narratives) |
| sentence-transformers | 3.3.1 | CLIP + MiniLM models |
| FastAPI | 0.104.1 | REST API (13 endpoints, 13 schemas) |
| Pillow | (bundled) | Image processing |
| python-dotenv | (bundled) | Environment variables |
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

| Service | Local Config | Purpose |
|---------|-------------|---------|
| PostgreSQL | `localhost/vintage_vestige` | Relational data |
| Qdrant | `localhost:6333` | Vector search |
| Claude API | `claude-sonnet-4-20250514` | AI enrichment |

---

## Database Schema

### PostgreSQL (confirmed via live query)

**Tables in database:** `products`, `style_bridges`

#### `products` table (866 rows)

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
primary_image   VARCHAR     -- URL or data URL
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

-- Timestamps
created_at      DATETIME    DEFAULT utcnow
updated_at      DATETIME    DEFAULT utcnow, on_update
embedded_at     DATETIME    nullable  -- 200/866 set (tracking gap)
enriched_at     DATETIME    nullable  -- 866/866 set
```

#### `style_bridges` table (7,324 rows)

```sql
-- storage/database.py:85-111
id                  INTEGER     PRIMARY KEY
source_id           INTEGER     FK → products.id, indexed
target_id           INTEGER     FK → products.id, indexed

text_similarity     FLOAT       NOT NULL
image_similarity    FLOAT       nullable  -- 2,243/7,324 have values
structural_score    FLOAT       NOT NULL
bridge_score        FLOAT       NOT NULL  -- range: 0.30–0.93

shared_attributes   TEXT        nullable  -- JSON string
bridge_type         VARCHAR     nullable  -- same_era, near_era, cross_era, cross_category, cross_vibe
bridge_narrative    TEXT        nullable  -- 22/7,324 populated

-- IIT 4.0 future columns (nullable, unused)
phi_score           FLOAT       nullable
cnn_structural_score FLOAT      nullable

created_at          DATETIME    DEFAULT utcnow

-- Constraints
UNIQUE (source_id, target_id)  -- canonical ordering: source_id < target_id
```

### Qdrant Collections (confirmed via live query)

#### `vintage_text` — 866 points

| Property | Value |
|----------|-------|
| Vector dimensions | 384 |
| Distance metric | Cosine |
| Points count | 866 |
| Payload fields | product_id, title, category, era, decade, style_tags, colors, material, pattern, garment_type, vibe, fit_style, occasion, ai_description, season, price, primary_image, culture, object_date, platform, fp_category |

#### `vintage_images` — 866 points

| Property | Value |
|----------|-------|
| Vector dimensions | 512 |
| Distance metric | Cosine |
| Points count | 866 |
| Payload fields | Same 28 fields as vintage_text (backfilled 2026-02-22) |

**Note:** Payloads were backfilled on 2026-02-22 to match `vintage_text`. Both collections have identical payload shapes.

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

```
With image:    bridge_score = 0.40 × text_sim + 0.30 × image_sim + 0.30 × structural
Without image: bridge_score = 0.55 × text_sim + 0.45 × structural
```

### Temporal Classification

Based on decade parsing with ERA_YEAR_MAP fallback:
- `same_era`: |year_a - year_b| ≤ 25
- `near_era`: |year_a - year_b| ≤ 75
- `cross_era`: |year_a - year_b| > 75

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
