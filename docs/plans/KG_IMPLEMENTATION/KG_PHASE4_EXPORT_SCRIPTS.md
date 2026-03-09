# KG_PHASE4_EXPORT_SCRIPTS.md
# Phase 4 — Export Scripts

**Duration:** 1 week  
**Status:** 🔲 Not Started — begins after Phase 1 (schema) + Phase 3 (design elements)  
**Prerequisite:** Phase 0 complete (Supabase migration fully done, no Qdrant references)  
**Output:** `data/neptune/*.csv` — all node and edge files for bulk load  
**Last Updated:** March 2026 (v2.0)

---

## Critical Change from v1.0

**All export scripts read exclusively from Supabase via SQLAlchemy Session.**

There is no Qdrant. There is no local Postgres. There is no `psycopg2`. Every
script uses `get_session()` from `storage.database` and queries the `products`
and `style_bridges` tables in Supabase.

The embeddings (`text_embedding`, `image_embedding`) are pgvector columns on
the `products` table — read as numpy arrays via the SQLAlchemy Vector type.

**Post-MMFashion fields available at export time:**
- `products.core_vibes` — TEXT[] controlled vibe terms (replaces single `vibe` string)
- `products.bridge_vibes` — TEXT[] bridge-eligible vibe terms
- `products.mmfashion_tags` — TEXT[] raw MMFashion visual attributes
- `style_bridges.semantic_type` — pre-classified bridge type (populated by classifier script)

Garment nodes use `core_vibes[0]` as the primary `vibe` property, with `core_vibes`
and `bridge_vibes` stored as additional pipe-separated properties. The legacy `p.vibe`
string is only used as a fallback for products not yet re-enriched with MMFashion.

---

## Directory Structure

```
scripts/kg/
├── extract_design_elements.py    ← Phase 3 (already done)
├── design_elements_seed.py       ← Phase 3 (already done)
├── utils.py                      ← shared helpers
├── export_garment_nodes.py
├── export_designer_nodes.py
├── export_era_nodes.py
├── export_design_element_nodes.py
├── export_bridge_nodes.py        ← bridges-as-nodes; reads semantic_type from Supabase
├── export_collection_nodes.py
├── export_garment_edges.py
├── export_bridge_edges.py        ← CONNECTED_VIA + CONNECTS + ARGUES_THROUGH
├── export_element_edges.py
├── run_all_exports.py            ← orchestrator
└── validate_exports.py           ← integrity checker

data/neptune/
├── garment_nodes.csv
├── designer_nodes.csv
├── era_nodes.csv
├── design_element_nodes.csv
├── bridge_nodes.csv
├── collection_nodes.csv
├── garment_created_by_edges.csv
├── garment_from_era_edges.csv
├── garment_part_of_edges.csv
├── garment_connected_via_edges.csv
├── bridge_connects_edges.csv
├── bridge_argues_through_edges.csv
├── element_subcategory_edges.csv
└── LOAD_MANIFEST.json
```

---

## Checklist

### Utilities (`scripts/kg/utils.py`)
- [ ] `slugify(text)` — text → safe Neptune ID slug
- [ ] `get_db_session()` — returns SQLAlchemy Session to Supabase (wraps `get_session()`)
- [ ] `write_csv(path, headers, rows)` — writes Neptune bulk load CSV format
- [ ] `get_decade_year(decade_str)` — returns midpoint year (e.g., "1920s" → 1925)

### Node Exports

- [ ] **`export_garment_nodes.py`** — enriched products only (`enriched_at IS NOT NULL`)
  - [ ] Expected count: ~1,500 rows
  - [ ] `text_embedding` and `image_embedding` written as space-separated float strings
  - [ ] `image_url` is the Supabase Storage CDN URL (already a full HTTP URL)
  - [ ] `vibe` written from `core_vibes[0]` (first controlled term) — NOT the legacy `p.vibe` string
  - [ ] `core_vibes` and `bridge_vibes` written as pipe-separated strings for Neptune
  - [ ] `phi_score` column included but empty (reserved for IIT)

- [ ] **`export_designer_nodes.py`**
  - [ ] Extracted from `enrichment_data` JSON or `seller_name` field on products
  - [ ] Deduplication on slugified name (case-insensitive)

- [ ] **`export_era_nodes.py`**
  - [ ] Seeded from hardcoded era list (see schema doc — 15 eras)
  - [ ] `start_year` and `end_year` set for all

- [ ] **`export_design_element_nodes.py`**
  - [ ] Sources from `design_elements_seed.py` (Phase 3)
  - [ ] `bridge_count` populated from frequency analysis output

- [ ] **`export_bridge_nodes.py`** — the novel export; ~10,000–15,000 rows
  - [ ] Reads 6 classification columns directly from `style_bridges` (pre-populated by `scripts/classify_bridge_dimensions.py`):
    - `temporal_type`, `crossing_type`, `connection_mode`, `primary_axis`, `secondary_axis`, `contrast_pair`
  - [ ] Also reads legacy `semantic_type` for backward compat (deprecated)
  - [ ] Does NOT re-classify — trusts the Postgres values
  - [ ] `narrative` from `style_bridges.bridge_narrative`
  - [ ] `source` = `"algorithmic_v1"` for all
  - [ ] `contested` = `false` for all

- [ ] **`export_collection_nodes.py`**
  - [ ] Covers all platforms currently in Supabase (met_museum, smithsonian,
    fashionpedia + any added during data growth)
  - [ ] Query distinct platforms: `SELECT DISTINCT platform FROM products`

### Edge Exports

- [ ] **`export_garment_edges.py`** — produces 4 files:
  - [ ] `garment_created_by_edges.csv` — Garment → Designer
  - [ ] `garment_from_era_edges.csv` — Garment → Era
  - [ ] `garment_part_of_edges.csv` — Garment → Collection
  - [ ] `garment_connected_via_edges.csv` — Garment → Bridge (source side)

- [ ] **`export_bridge_edges.py`** — produces 2 files:
  - [ ] `bridge_connects_edges.csv` — Bridge → Garment (target side)
  - [ ] `bridge_argues_through_edges.csv` — Bridge → DesignElement

- [ ] **`export_element_edges.py`**
  - [ ] `element_subcategory_edges.csv` — DesignElement → DesignElement

### Orchestration + Validation
- [ ] `run_all_exports.py` — runs all scripts in correct dependency order
- [ ] `validate_exports.py` checks:
  - [ ] Row counts match expected (cross-check against Supabase counts)
  - [ ] No null `~id` values
  - [ ] No null `~label` values
  - [ ] All edge `~from` IDs exist in node files
  - [ ] All edge `~to` IDs exist in node files
  - [ ] No duplicate `~id` values within any file
- [ ] `LOAD_MANIFEST.json` written with final counts
- [ ] All CSVs open cleanly (check for encoding issues)

---

## Implementation Reference

### Shared Session Pattern

Every export script follows this pattern — no direct DB connections:

```python
# scripts/kg/utils.py
from storage.database import get_session  # existing project utility
from contextlib import contextmanager

@contextmanager
def get_db_session():
    """Yields a Supabase SQLAlchemy session."""
    with get_session() as session:
        yield session
```

### Key Export: Bridge Nodes (reads semantic_type from Supabase)

```python
# scripts/kg/export_bridge_nodes.py
import json, csv
from storage.database import get_session, StyleBridge, Product
from sqlalchemy.orm import aliased
from utils import slugify, write_csv

def export():
    rows = []

    with get_session() as db:
        # Join bridges with both garments to get year data for validation
        Source = aliased(Product)
        Target = aliased(Product)

        bridges = db.query(
            StyleBridge,
            Source.decade.label('source_decade'),
            Target.decade.label('target_decade')
        ).join(Source, StyleBridge.source_id == Source.id)\
         .join(Target, StyleBridge.target_id == Target.id)\
         .all()

        for bridge, source_decade, target_decade in bridges:
            rows.append([
                f"bridge_{bridge.id}",             # ~id
                'Bridge',                           # ~label
                round(bridge.bridge_score, 4),
                round(bridge.text_similarity, 4),
                round(bridge.image_similarity, 4) if bridge.image_similarity else '',
                round(bridge.structural_score, 4),
                bridge.bridge_type or '',
                bridge.semantic_type or 'STRUCTURAL_SIBLING',  # read from Supabase
                (bridge.bridge_narrative or '').replace('\n', ' ').replace('"', "'"),
                (bridge.shared_attributes or '{}').replace('\n', ''),
                round(bridge.bridge_score, 4),     # confidence = score
                'algorithmic_v1',
                'false',
                str(bridge.created_at) if bridge.created_at else '',
                ''                                  # phi_score reserved
            ])

    headers = [
        '~id', '~label',
        'score:Double', 'text_similarity:Double',
        'image_similarity:Double', 'structural_score:Double',
        'discovery_type:String', 'semantic_type:String',
        'narrative:String', 'shared_attributes:String',
        'confidence:Double', 'source:String',
        'contested:Bool', 'created_at:String',
        'phi_score:Double'
    ]

    write_csv('data/neptune/bridge_nodes.csv', headers, rows)
    print(f"Exported {len(rows)} bridge nodes")
    return len(rows)

if __name__ == '__main__':
    export()
```

### Garment Node Export (pgvector embeddings)

```python
# scripts/kg/export_garment_nodes.py
import json
from storage.database import get_session, Product
from utils import write_csv

def export():
    rows = []

    with get_session() as db:
        # Only enriched products go into the KG
        products = db.query(Product)\
                     .filter(Product.enriched_at.isnot(None))\
                     .order_by(Product.id)\
                     .all()

        for p in products:
            # pgvector returns numpy array — convert to space-separated string
            text_emb = ''
            if p.text_embedding is not None:
                text_emb = ' '.join(str(x) for x in p.text_embedding)

            image_emb = ''
            if p.image_embedding is not None:
                image_emb = ' '.join(str(x) for x in p.image_embedding)

            # vibe: use first core_vibe from controlled vocabulary if available;
            # fall back to legacy p.vibe string for products not yet re-enriched
            primary_vibe = ''
            if p.core_vibes:
                primary_vibe = p.core_vibes[0]
            elif p.vibe:
                primary_vibe = p.vibe

            # core_vibes / bridge_vibes as pipe-separated strings (Neptune property)
            core_vibes_str  = '|'.join(p.core_vibes  or [])
            bridge_vibes_str = '|'.join(p.bridge_vibes or [])

            rows.append([
                f"garment_{p.id}",     # ~id
                'Garment',             # ~label
                p.id,                  # supabase_id (for join back to Supabase)
                p.title or '',
                p.platform or '',
                p.era or '',
                p.decade or '',
                p.silhouette or '',
                p.fp_category or '',
                primary_vibe,          # first core_vibe, or legacy vibe fallback
                core_vibes_str,        # all controlled vibe terms (pipe-separated)
                bridge_vibes_str,      # bridge-eligible vibe terms (pipe-separated)
                p.material or '',
                p.garment_type or '',
                p.culture or '',
                p.primary_image or '', # Supabase Storage CDN URL
                text_emb,
                image_emb,
                '',                    # phi_score reserved
                (p.enriched_text or '').replace('\n', ' ')[:2000]
            ])

    headers = [
        '~id', '~label',
        'supabase_id:Int',
        'title:String', 'platform:String',
        'era:String', 'decade:String',
        'silhouette:String', 'fp_category:String',
        'vibe:String',          # primary vibe term (core_vibes[0] or legacy)
        'core_vibes:String',    # all controlled vibe terms, pipe-separated
        'bridge_vibes:String',  # bridge-eligible vibe terms, pipe-separated
        'material:String', 'garment_type:String',
        'culture:String', 'image_url:String',
        'text_embedding:String',   # stored as string; Neptune doesn't index these
        'image_embedding:String',  # stored for reference only
        'phi_score:Double',
        'enriched_text:String'
    ]

    write_csv('data/neptune/garment_nodes.csv', headers, rows)
    print(f"Exported {len(rows)} garment nodes")
    return len(rows)

if __name__ == '__main__':
    export()
```

**Note on embeddings in Neptune:** Embeddings are stored as string properties for
reference and potential future use, but Neptune is not used for vector search —
that stays in Supabase pgvector. Neptune is for graph traversal only.

---

## Expected Row Counts

These reflect post-data-growth numbers (~1,500 enriched products, bridges recomputed):

| File | Expected Rows | Notes |
|---|---|---|
| `garment_nodes.csv` | ~1,500 | Enriched products only (`enriched_at IS NOT NULL`) |
| `designer_nodes.csv` | ~50–200 | After deduplication |
| `era_nodes.csv` | 15 | Seeded from hardcoded list |
| `design_element_nodes.csv` | ~150–300 | From Phase 3 seed |
| `bridge_nodes.csv` | ~10,000–15,000 | Recomputed after data growth |
| `collection_nodes.csv` | 3+ | All distinct platforms in Supabase |
| `garment_connected_via_edges.csv` | ~20,000–30,000 | 2× bridge count (source side) |
| `bridge_connects_edges.csv` | ~10,000–15,000 | 1× bridge count (target side) |
| `bridge_argues_through_edges.csv` | ~30,000–60,000 | N edges per bridge |
| `garment_from_era_edges.csv` | ~1,500 | All enriched garments have era |
| `garment_part_of_edges.csv` | ~1,500 | All enriched garments have collection |
| `garment_created_by_edges.csv` | ~500–1,000 | Garments with designer data |
| `element_subcategory_edges.csv` | ~50–100 | Hierarchy edges |
| **TOTAL EDGES** | **~65,000–110,000** | |

---

## Estimated Effort

| Task | Time |
|---|---|
| `utils.py` | 1 hour |
| Node export scripts (6 files) | 6 hours |
| Edge export scripts (3 files) | 4 hours |
| Orchestrator + validator | 2 hours |
| Debug + fix validation errors | 3 hours |
| **Total** | **~16 hours** |
