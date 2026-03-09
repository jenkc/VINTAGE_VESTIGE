# KG_PHASE3_DESIGN_ELEMENTS.md
# Phase 3 — Design Element Extraction

**Duration:** 2–3 days  
**Can run parallel with:** Phase 2 (AWS Setup)  
**Status:** 🔲 Not Started — begins after Phase 0 complete  
**Output:** `scripts/kg/design_elements_seed.py` + frequency report  
**Last Updated:** March 2026 (v2.0)

**v2.0 note:** Extract script now queries Supabase via SQLAlchemy Session,
not local Postgres via psycopg2. The `shared_attributes` column is a TEXT field
storing JSON strings (not JSONB) — parse with `json.loads()`.

---

## Purpose

DesignElement nodes are what make bridges meaningful. Without them, bridges are
scored connections. With them, bridges are arguments. A bridge that argues through
"empire waistline" is a different kind of knowledge than a bridge with a high
similarity score. This phase extracts that vocabulary from your existing data.

---

## Checklist

### Step 1 — Extract Vocabulary from shared_attributes
- [ ] Write and run `scripts/kg/extract_design_elements.py`
- [ ] Output: frequency-ranked list of (field, value, count) tuples
- [ ] Save output to `data/design_elements_frequency.csv`

**Run this after MMFashion pipeline is complete** — bridges will have been
recomputed with richer Fashionpedia fields, so `shared_attributes` will contain
more populated values. Running before MMFashion gives you sparser vocabulary.

```python
# scripts/kg/extract_design_elements.py
# Reads from Supabase via SQLAlchemy — no psycopg2 or local Postgres
import json
import csv
from collections import Counter
from storage.database import get_session, StyleBridge

def extract():
    element_counter = Counter()

    with get_session() as db:
        bridges = db.query(StyleBridge.shared_attributes)\
                    .filter(StyleBridge.shared_attributes.isnot(None))\
                    .all()

        for (attrs_text,) in bridges:
            if not attrs_text or attrs_text in ('{}', ''):
                continue
            try:
                attrs = json.loads(attrs_text)  # TEXT column, not JSONB
                for field, value in attrs.items():
                    if value and isinstance(value, str) and len(value) > 1:
                        element_counter[(field, value)] += 1
            except (json.JSONDecodeError, AttributeError):
                continue

    with open('data/design_elements_frequency.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['field', 'value', 'bridge_count', 'slug'])
        for (field, value), count in element_counter.most_common():
            slug = f"{field}_{value.lower().replace(' ', '_').replace('-', '_')}"
            writer.writerow([field, value, count, slug])

    print(f"Found {len(element_counter)} unique design elements")
    print("\nTop 20:")
    for (field, value), count in element_counter.most_common(20):
        print(f"  {field}: {value!r} — {count} bridges")

if __name__ == '__main__':
    extract()
```

### Step 1b — Extract Vocabulary from Products (mmfashion_tags + vibe fields)

A second extraction pass mines the `products` table directly. Post-MMFashion,
products have two additional vocabulary sources that `shared_attributes` doesn't
capture:

- `mmfashion_tags`: raw visual attribute terms from MMFashion inference
  (e.g. "dropped-waist", "sheer-overlay", "beaded") — these become DesignElement
  candidates in the `construction` and `decoration` categories
- `core_vibes` / `bridge_vibes`: controlled vocabulary terms assigned by Claude
  enrichment (e.g. "architectural", "romantic", "fluid") — these become
  DesignElement candidates in a new `vibe` category

These are higher-quality DesignElement sources than raw `shared_attributes` values
because they're already normalized — Claude used a controlled vocabulary list and
MMFashion outputs are from a fixed attribute set.

```python
# scripts/kg/extract_product_elements.py
# Runs AFTER extract_design_elements.py — supplements, doesn't replace it
import json
import csv
from collections import Counter
from storage.database import get_session, Product

def extract_product_vocabulary():
    vibe_counter = Counter()
    mmfashion_counter = Counter()

    with get_session() as db:
        products = db.query(
            Product.core_vibes,
            Product.bridge_vibes,
            Product.mmfashion_tags,
        ).filter(Product.enriched_at.isnot(None)).all()

        for core_vibes, bridge_vibes, mm_tags in products:
            # core_vibes and bridge_vibes are TEXT[] arrays (or None)
            for term in (core_vibes or []):
                if term:
                    vibe_counter[('vibe', term)] += 1
            for term in (bridge_vibes or []):
                if term:
                    vibe_counter[('bridge_vibe', term)] += 1
            for tag in (mm_tags or []):
                if tag:
                    mmfashion_counter[('mmfashion', tag)] += 1

    # Write vibe elements
    with open('data/vibe_elements_frequency.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['field', 'value', 'product_count', 'slug'])
        for (field, value), count in vibe_counter.most_common():
            slug = f"de_vibe_{value.lower().replace('-', '_').replace(' ', '_')}"
            writer.writerow([field, value, count, slug])

    # Write mmfashion elements
    with open('data/mmfashion_elements_frequency.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['field', 'value', 'product_count', 'slug'])
        for (field, value), count in mmfashion_counter.most_common():
            slug = f"de_visual_{value.lower().replace('-', '_').replace(' ', '_')}"
            writer.writerow([field, value, count, slug])

    print(f"Vibe vocabulary: {len(vibe_counter)} unique terms")
    print(f"MMFashion vocabulary: {len(mmfashion_counter)} unique terms")
    print("\nTop vibe terms:")
    for (field, value), count in vibe_counter.most_common(10):
        print(f"  {value!r} ({field}) — {count} products")
    print("\nTop MMFashion terms:")
    for (field, value), count in mmfashion_counter.most_common(10):
        print(f"  {value!r} — {count} products")

if __name__ == '__main__':
    extract_product_vocabulary()
```

```bash
venv/bin/python scripts/kg/extract_product_elements.py
```

- [ ] `data/vibe_elements_frequency.csv` generated and reviewed
- [ ] `data/mmfashion_elements_frequency.csv` generated and reviewed
- [ ] Vibe terms from controlled vocabulary (should be clean — ~15–20 distinct values)
- [ ] MMFashion terms reviewed for noise (low-confidence detections may be junk)

**Merge strategy:** Combine with `shared_attributes` results in Step 2 review.
Vibe terms go into a new `vibe` category in `design_elements_seed.py`.
MMFashion terms with product_count > 10 go into `construction` or `decoration`
category as appropriate. Terms with count < 5 are likely noise — skip them.

---

### Step 2 — Review and Curate Top 50
- [ ] Review `data/design_elements_frequency.csv` AND `data/vibe_elements_frequency.csv`
- [ ] Review `data/mmfashion_elements_frequency.csv` — apply product_count > 10 threshold
- [ ] Identify top 50 structural elements (from `shared_attributes`) by bridge count
- [ ] Identify all vibe terms with product_count > 5 (should be ~12–18 terms)
- [ ] Flag structural values that should be merged (e.g., "a-line" and "A-line")
- [ ] Flag MMFashion noise (terms with very low counts or clearly erroneous detections)
- [ ] Note which elements clearly correspond to Getty AAT concepts

### Step 3 — Getty AAT Mapping (top 50)
- [ ] Navigate to https://www.getty.edu/research/tools/vocabularies/aat/
- [ ] Search for each of the top 50 design elements
- [ ] Record URI in `design_elements_seed.py`
- [ ] Note: leave `aat_uri: null` for elements with no clear AAT match
- [ ] Target: 30+ of top 50 mapped to AAT URIs

**Key AAT searches to start with:**
- "bias cut" → search AAT
- "empire waistline" → search AAT
- "A-line" → search AAT silhouettes
- "cocoon silhouette" → search AAT
- "drop waist" → search AAT
- "floor length" → search AAT

### Step 4 — Build Seed File
- [ ] Create `scripts/kg/design_elements_seed.py`
- [ ] Include all structural elements with bridge_count > 5 (from `shared_attributes`)
- [ ] Include all vibe terms with product_count > 5 (from `core_vibes`/`bridge_vibes`)
- [ ] Include MMFashion terms with product_count > 10 (visual attributes as DesignElements)
- [ ] Include AAT URIs where mapped (structural terms — vibe terms likely have no AAT)
- [ ] Include category classification (silhouette | construction | material | cultural | vibe)
- [ ] Include subcategory relationships (for SUBCATEGORY_OF edges)

```python
# scripts/kg/design_elements_seed.py
# Generated from extract_design_elements.py output + manual curation

DESIGN_ELEMENTS = [
    # SILHOUETTE category
    {
        "id": "de_silhouette_a_line",
        "name": "A-line silhouette",
        "field": "silhouette",
        "category": "silhouette",
        "aat_uri": None,  # TODO: map
        "description": "Fitted at top, flaring gradually to hemline",
        "subcategory_of": None,
        "bridge_count": 0  # populated by export script
    },
    {
        "id": "de_silhouette_empire",
        "name": "empire waistline",
        "field": "silhouette",
        "category": "silhouette",
        "aat_uri": "http://vocab.getty.edu/aat/300209894",
        "description": "Waistline positioned just below the bust, characteristic of Regency/Empire period",
        "subcategory_of": "de_silhouette_fitted_bodice",
        "bridge_count": 0
    },
    # ... add all top 100+ elements from shared_attributes

    # VIBE category (from controlled vocabulary in claude.py)
    {
        "id": "de_vibe_architectural",
        "name": "architectural",
        "field": "core_vibes",
        "category": "vibe",
        "aat_uri": None,
        "description": "Strong geometric form; structure independent of the body",
        "subcategory_of": None,
        "bridge_count": 0
    },
    {
        "id": "de_vibe_romantic",
        "name": "romantic",
        "field": "core_vibes",
        "category": "vibe",
        "aat_uri": None,
        "description": "Soft, decorative; associated with sentiment and femininity",
        "subcategory_of": None,
        "bridge_count": 0
    },
    # ... add all vibe terms from VIBE_VOCABULARY in enrichment/claude.py
]

# Subcategory hierarchy
SUBCATEGORIES = [
    # silhouette subtypes
    ("de_silhouette_a_line", "de_silhouette_general"),
    ("de_silhouette_empire", "de_silhouette_general"),
    ("de_silhouette_drop_waist", "de_silhouette_general"),
    # construction subtypes
    ("de_construction_bias_cut", "de_construction_general"),
    # material subtypes
    ("de_material_silk", "de_material_natural"),
    ("de_material_wool", "de_material_natural"),
]
```

### Step 5 — Validate Coverage
- [ ] Count: what % of bridges have at least one ARGUES_THROUGH edge (via `shared_attributes`)?
- [ ] Minimum target: 70% of bridges connected to at least one structural DesignElement
- [ ] Bonus: count what % of garments have at least one vibe DesignElement (via `core_vibes`)
- [ ] Expected: ~95%+ of enriched garments have core_vibes populated post-MMFashion

```python
# Quick validation
total_bridges = 7324
covered = sum(1 for b in bridges if any(
    attr in ELEMENT_FIELD_SET for attr in json.loads(b['shared_attributes'] or '{}')
))
print(f"Coverage: {covered}/{total_bridges} = {covered/total_bridges:.1%}")
```

---

## Deliverables

| File | Description |
|---|---|
| `data/design_elements_frequency.csv` | Frequency report from `shared_attributes` |
| `data/vibe_elements_frequency.csv` | Frequency report from `core_vibes`/`bridge_vibes` |
| `data/mmfashion_elements_frequency.csv` | Frequency report from `mmfashion_tags` |
| `scripts/kg/design_elements_seed.py` | Curated DesignElement definitions (all three sources) |
| `data/design_elements_aat_mapping.csv` | Getty AAT URI mapping for review |

---

## Expected Output Size

Combining all three sources:

From `shared_attributes` (bridge-level):
- ~150–300 unique (field, value) pairs across 7,324+ bridges
- ~50–80 elements with bridge_count > 10 (the meaningful ones)

From `core_vibes`/`bridge_vibes` (product-level, controlled vocabulary):
- ~15–20 distinct vibe terms (controlled vocabulary — should be clean)
- All terms with product_count > 5 are likely meaningful DesignElements

From `mmfashion_tags` (product-level, MMFashion output):
- ~30–60 distinct visual attribute terms
- Use product_count > 10 as noise threshold

Total expected DesignElement nodes: ~200–350
Getty AAT URIs: ~30–40 mapped in Phase 1 (Fashionpedia/structural terms map cleanly;
vibe terms may not have AAT equivalents — leave `aat_uri: null` for those)
