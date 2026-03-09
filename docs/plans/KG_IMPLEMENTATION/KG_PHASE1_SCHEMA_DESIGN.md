# KG_PHASE1_SCHEMA_DESIGN.md
# Phase 1 — Schema Design

**Duration:** 1 week (no code written this week)  
**Deliverable:** Finalized schema document, signed off before any export scripts begin  
**Status:** 🔲 Not Started — begins after Phase 0 complete  
**Blocks:** Phases 4, 5, 6, 7  
**Last Updated:** March 2026 (v2.0)

**v2.0 note:** `semantic_type` is now pre-populated on `style_bridges` in Supabase
(via the Phase 0 classifier script) before KG work begins. The Neptune Bridge node
reads this column directly — no re-classification needed in the export scripts.
The taxonomy below is the source of truth; the Postgres column is derived from it.

---

## Principle

Schema changes in Neptune are expensive. Unlike Postgres, there are no ALTER TABLE
statements — you reload data. Get it right before you load anything.

This phase is thinking work, not coding work. The output is this document,
completed and reviewed.

---

## Checklist

- [ ] All node labels defined with property lists
- [ ] All edge types defined with directionality and cardinality
- [ ] Bridge semantic type taxonomy finalized
- [ ] ID naming conventions agreed and documented
- [ ] Schema validated against 3 validation queries (can they be written against this schema?)
- [ ] Future-proofing review (IIT columns reserved, RDF federation hooks noted)
- [ ] Schema doc reviewed before Phase 4 begins

---

## Node Labels and Properties

### (:Garment)

Primary entity. Maps 1:1 to `products` table.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `garment_{products.id}` |
| `postgres_id` | Int | ✅ | Original products.id for joins |
| `title` | String | ✅ | |
| `platform` | String | ✅ | `met_museum` \| `smithsonian` \| `fashionpedia` |
| `era` | String | ✅ | e.g., "1920s", "Victorian" |
| `decade` | String | ✅ | e.g., "1920s" |
| `silhouette` | String | ❌ | Null for accessories |
| `fp_category` | String | ❌ | Fashionpedia category |
| `vibe` | String | ✅ | Enrichment field |
| `material` | String | ✅ | |
| `garment_type` | String | ✅ | |
| `culture` | String | ❌ | Museum items only |
| `image_url` | String | ✅ | Supabase Storage CDN URL (all images migrated from base64) |
| `text_embedding` | Float[] | ✅ | 384-dim MiniLM |
| `image_embedding` | Float[] | ❌ | 512-dim CLIP (null if no image) |
| `phi_score` | Float | ❌ | Reserved for IIT — null until Phase IIT |
| `enriched_text` | String | ✅ | Full enriched text blob |

**ID format:** `garment_{supabase_id}` e.g., `garment_1`, `garment_1500`

**Source:** Export reads only enriched products (`enriched_at IS NOT NULL`) from
Supabase. Total in DB is 4,234 but only ~1,500 will be enriched at KG time.

---

### (:Bridge)

The core innovation — promoted from junction table row to first-class entity.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `bridge_{style_bridges.id}` |
| `postgres_id` | Int | ✅ | Original style_bridges.id |
| `score` | Float | ✅ | Composite bridge score 0.0–1.0 |
| `text_similarity` | Float | ✅ | |
| `image_similarity` | Float | ❌ | Null if no image for either garment |
| `structural_score` | Float | ✅ | |
| `discovery_type` | String | ✅ | Original pass: `transmission` \| `continuation` \| `cross_category` \| `cross_culture` |
| `temporal_type` | String | ✅ | `transmission` \| `continuation` \| `contemporary` |
| `crossing_type` | String | ✅ | `same_context` \| `cross_category` \| `cross_culture` \| `cross_category_culture` |
| `connection_mode` | String | ✅ | `citation` \| `echo` \| `parallel` \| `contrast` \| `kinship` |
| `primary_axis` | String | ❌ | `volume` \| `ornament` \| `body` \| `register` |
| `secondary_axis` | String | ❌ | `volume` \| `ornament` \| `body` \| `register` |
| `contrast_pair` | String | ❌ | e.g. `"Exaggerated Volume <-> Column Minimalism"` (contrast only) |
| `semantic_type` | String | ❌ | **Deprecated** — kept for backward compat |
| `narrative` | String | ✅ | Claude-generated description |
| `shared_attributes` | String | ✅ | JSON string of shared fields |
| `confidence` | Float | ✅ | = score for algorithmic; curators set explicitly |
| `source` | String | ✅ | `algorithmic_v1` \| `curator` \| `documentary` |
| `contested` | Boolean | ✅ | Default false |
| `created_at` | String | ✅ | ISO datetime |
| `phi_score` | Float | ❌ | Reserved for IIT |

**ID format:** `bridge_{supabase_id}` e.g., `bridge_1`, `bridge_10000`

**Note on bridge classification:** Six classification columns are read directly from
`style_bridges` in Supabase, pre-populated by `scripts/classify_bridge_dimensions.py`
during Phase 0. The export script does NOT re-classify — it trusts the Postgres values.
See "Multi-Dimensional Bridge Classification" section below for the full taxonomy.

---

### (:DesignElement)

What actually travels through a bridge. The vocabulary of fashion's argument structure.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `de_{field}_{value_slug}` |
| `name` | String | ✅ | e.g., "empire waistline", "bias cut" |
| `field` | String | ✅ | Which Fashionpedia field: silhouette, construction, etc. |
| `category` | String | ✅ | `silhouette` \| `construction` \| `material` \| `cultural` |
| `aat_uri` | String | ❌ | Getty AAT URI — null until mapped |
| `description` | String | ❌ | Human-readable description |
| `bridge_count` | Int | ✅ | How many bridges argue through this element |

**ID format:** `de_silhouette_empire_waistline` (field + slugified value)

---

### (:Era)

Time period nodes. Enables era-level traversal and movement detection.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `era_{slug}` |
| `name` | String | ✅ | e.g., "1920s", "Victorian", "Belle Époque" |
| `start_year` | Int | ✅ | |
| `end_year` | Int | ✅ | |
| `decade` | String | ❌ | For decade-level eras |

**ID format:** `era_1920s`, `era_victorian`, `era_belle_epoque`

**Seed data:**
```
era_1800s_early:  1800–1830  (Empire/Regency)
era_victorian:    1837–1901
era_edwardian:    1901–1910
era_1910s:        1910–1919
era_1920s:        1920–1929
era_1930s:        1930–1939
era_1940s:        1940–1949
era_1950s:        1950–1959
era_1960s:        1960–1969
era_1970s:        1970–1979
era_1980s:        1980–1989
era_1990s:        1990–1999
era_2000s:        2000–2009
era_2010s:        2010–2019
era_2020s:        2020–present
```

---

### (:Designer)

Fashion designers and houses. Extracted from enrichment data where available.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `designer_{slug}` |
| `name` | String | ✅ | |
| `type` | String | ✅ | `person` \| `house` |
| `nationality` | String | ❌ | |
| `active_start` | Int | ❌ | Year |
| `active_end` | Int | ❌ | Year |
| `wikidata_uri` | String | ❌ | For future LOD federation |

---

### (:Collection)

Museum collections and fashion house seasons.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `collection_{slug}` |
| `name` | String | ✅ | "The Metropolitan Museum of Art Costume Institute" |
| `type` | String | ✅ | `museum` \| `fashion_house` |
| `institution` | String | ✅ | |
| `sparql_endpoint` | String | ❌ | For future SPARQL federation |

---

### (:MuseumRecord)

External LOD references. Populated when federating with museum SPARQL endpoints.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | String | ✅ | `mr_{accession}` |
| `institution` | String | ✅ | |
| `accession` | String | ✅ | |
| `uri` | String | ✅ | LOD URI |

*Note: MuseumRecord nodes are mostly empty in Phase 1 — populated during Phase 3 data
expansion (V&A, Europeana integration). Reserve the node type now.*

---

## Edge Types

### Garment Edges

```
(:Garment)-[:CREATED_BY]->(:Designer)
  Properties: none
  Cardinality: many garments → one designer

(:Garment)-[:FROM_ERA]->(:Era)
  Properties: none
  Cardinality: many garments → one era

(:Garment)-[:PART_OF]->(:Collection)
  Properties: none
  Cardinality: many garments → one collection

(:Garment)-[:CONNECTED_VIA]->(:Bridge)
  Properties: none
  Cardinality: one garment → many bridges (one per connection)
  Note: This edge goes Garment → Bridge (garment is the "source side")
```

### Bridge Edges

```
(:Bridge)-[:CONNECTS]->(:Garment)
  Properties: none
  Cardinality: one bridge → one garment (the "target side")
  Note: Together, CONNECTED_VIA + CONNECTS create the full bridge traversal

(:Bridge)-[:ARGUES_THROUGH]->(:DesignElement)
  Properties: none
  Cardinality: one bridge → many design elements
  Note: One ARGUES_THROUGH edge per shared attribute

(:Bridge)-[:HAS_TYPE]->(:BridgeType)
  Properties: none
  Note: Optional taxonomy node; semantic_type property on Bridge is sufficient
        for Phase 1 — skip BridgeType nodes initially

(:Bridge)-[:EVIDENCE_FROM]->(:MuseumRecord)
  Properties: none
  Note: Empty in Phase 1; populated with LOD federation in Phase 3+

(:Bridge)-[:CONTRADICTED_BY]->(:Bridge)
  Properties: { reason: String, created_by: String }
  Note: Rare; for explicitly contested bridges — skip in Phase 1
```

### DesignElement Edges

```
(:DesignElement)-[:SUBCATEGORY_OF]->(:DesignElement)
  Properties: none
  Example: "empire waistline" -[:SUBCATEGORY_OF]-> "waistline"
  Note: Build this hierarchy from Fashionpedia taxonomy

(:DesignElement)-[:GETTY_AAT_MATCH]->(:ExternalConcept)
  Properties: { confidence: Float }
  Note: Future RDF federation hook — skip in Phase 1, but reserve concept
```

---

## Multi-Dimensional Bridge Classification

This is the key intellectual contribution of the schema. The old single `semantic_type`
column has been replaced by **6 orthogonal dimensions** that decompose bridge meaning
into independent, filterable axes.

### Dimension 1: Temporal Distance (`temporal_type`)

| Value | Definition |
|---|---|
| `transmission` | 40+ year midpoint gap — ideas traveling through time |
| `continuation` | Same era or adjacent, 20+ year decade gap |
| `contemporary` | Same decade or very close |

### Dimension 2: Contextual Crossing (`crossing_type`)

| Value | Definition |
|---|---|
| `same_context` | Same category group + same culture |
| `cross_category` | Different garment types (e.g. dress ↔ jacket) |
| `cross_culture` | Different cultural origins |
| `cross_category_culture` | Both (richest bridges) |

### Dimension 3: Connection Mode (`connection_mode`)

| Mode | Detection Signal | Definition | Example |
|---|---|---|---|
| `contrast` | Vibe axis opposition + structural > 0.4 | Opposite aesthetic arguments grounded in shared DNA | Kawakubo deconstruction vs Chanel construction |
| `resonance` | text_sim >= 0.85 + transmission | Same aesthetic language across 40+ years | 1870s mourning dress ↔ 2020s Dark Academia blazer |
| `affinity` | Everything else | Family resemblance — the axis tells the story | Shared ornament DNA (material), shared volume DNA (silhouette) |

Priority: contrast > resonance > affinity. The axis columns carry the specific story for affinity bridges.

### Dimension 4–5: Aesthetic Axis (`primary_axis`, `secondary_axis`)

| Axis | Structural fields | Vibe terms |
|---|---|---|
| `volume` | silhouette, fit_style | Exaggerated Volume, Column Minimalism, Empire Suspension, Constructed Armor, Draped Fluidity, Layered Accumulation |
| `ornament` | material, colors, textile_pattern, textile_finishing, decorations | Maximalist Ornament, Austere Restraint, Handcraft Visibility, Material Luxury, Pattern as Language, Transparency and Revelation |
| `body` | garment_type, neckline, sleeve_length, waistline, length | Body Liberation, Body Transformation, Body Concealment, Body Display |
| `register` | occasion, social_function, culture | Pastoral Naturalism, Ceremonial Formalism, Dark Romanticism, Transgressive Subversion, Nostalgic Revival, Elite Distinction |

### Dimension 6: Contrast Pair (`contrast_pair`) — 9 opposition pairs

| # | Pair | Axis | The shared question |
|---|------|------|---------------------|
| 1 | Exaggerated Volume ↔ Column Minimalism | volume | How much space should a body claim? |
| 2 | Constructed Armor ↔ Draped Fluidity | volume | Should fabric impose or follow? |
| 3 | Constructed Armor ↔ Body Liberation | volume | Should the garment control or free? |
| 4 | Maximalist Ornament ↔ Austere Restraint | ornament | Excess or absence? |
| 5 | Transparency and Revelation ↔ Body Concealment | ornament | Show or hide what's beneath? |
| 6 | Body Liberation ↔ Body Transformation | body | Accept the body or reshape it? |
| 7 | Body Display ↔ Body Concealment | body | Is the body public or private? |
| 8 | Transgressive Subversion ↔ Elite Distinction | register | Reject norms or embody them? |
| 9 | Pastoral Naturalism ↔ Ceremonial Formalism | register | Nature or ritual? |

### Classification Script

**Important:** Classification runs in Phase 0 via `scripts/classify_bridge_dimensions.py`,
not inside the Neptune export scripts. By the time Phase 4 runs, every bridge already
has all 6 columns populated in Supabase. The export script reads them directly.

---

## ID Naming Conventions

| Node Type | Format | Example |
|---|---|---|
| Garment | `garment_{supabase_id}` | `garment_42` |
| Bridge | `bridge_{supabase_id}` | `bridge_1337` |
| DesignElement | `de_{field}_{value_slug}` | `de_silhouette_a_line` |
| Era | `era_{slug}` | `era_1920s` |
| Designer | `designer_{slug}` | `designer_madeleine_vionnet` |
| Collection | `collection_{slug}` | `collection_met_costume_institute` |
| MuseumRecord | `mr_{institution}_{accession}` | `mr_met_1987_400` |

**Slug rules:**
- Lowercase
- Spaces → underscores
- Remove special characters
- Max 64 chars

---

## Future-Proofing Notes

These are NOT implemented in Phase 1. They are schema slots reserved for future phases.

| Slot | Phase | Purpose |
|---|---|---|
| `phi_score` on Garment and Bridge | IIT | Φ measurement for integrated information |
| `cnn_structural_score` on Bridge | IIT/CNN | Visual attribute extraction score |
| `aat_uri` on DesignElement | Phase 3 | Getty AAT federation |
| `wikidata_uri` on Designer | Phase 3 | Wikidata LOD federation |
| `sparql_endpoint` on Collection | Phase 3 | Museum SPARQL federation |
| `CONTRADICTED_BY` edge on Bridge | Post-MVP | Academic contestation layer |
| `MuseumRecord` nodes | Phase 3 | External LOD citation |
| `(:InfluenceChain)` nodes | Phase 2 | Named sequences of bridges |
| `(:DesignMovement)` nodes | Phase 2 | Emergent movement clusters |

---

## Schema Validation Against 3 Queries

Before finalizing, verify this schema can express all three validation queries.

**Query 1 (Influence Chain):** Requires `CONNECTED_VIA` + `CONNECTS` edges with
`semantic_type` on Bridge and `platform` on Garment. ✅ Schema supports this.

**Query 2 (Design Movement):** Requires `ARGUES_THROUGH` edges from Bridge to
DesignElement, `FROM_ERA` from Garment to Era. ✅ Schema supports this.

**Query 3 (Cross-Institutional):** Requires `platform` on Garment, `score` on
Bridge, `CONNECTED_VIA` + `CONNECTS` traversal. ✅ Schema supports this.

---

## Sign-Off Checklist

- [ ] Schema reviewed against all three validation queries
- [ ] ID naming conventions agreed
- [ ] Bridge semantic type taxonomy reviewed for completeness
- [ ] Future-proofing columns noted but not implemented
- [ ] No schema elements left ambiguous before export scripts begin
