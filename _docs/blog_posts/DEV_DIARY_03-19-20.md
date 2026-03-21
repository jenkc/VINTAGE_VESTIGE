# Dev Diary: March 19-20, 2026

**The one where we tore everything down and rebuilt it, again.**

Previous state: 14,223 bridges using 4-pass embedding-similarity system with 22 discrete vibes, axis-based contrast detection, and a "nice SaaS" frontend. All technically working. None of it interesting.

---

## Vibe System Rework

Scrapped 22 discrete vibe terms. Replaced with 6 axes, each a spectrum with two poles:

| Axis | Pole A | Pole B |
|------|--------|--------|
| Volume | Exaggerated Volume | Column Minimalism |
| Ornament | Maximalist Ornament | Bare Surface |
| Exposure | Body Display | Body Concealment |
| Gender | Gender Conforming | Gender Defiant |
| Register | Transgressive Subversion | Elite Distinction |
| Occasion | Pastoral Naturalism | Ceremonial Formalism |

Pick-a-pole + confidence scoring. Backfilled all 4,234 products.

Then discovered axes are useful for filtering but **not for defining bridges**. The contrast/opposition framing ("these two garments disagree about volume") produces boring results. Bridges are interesting as *paths*, not *debates*.

---

## Enrichment Overhaul

Rewrote the Claude enrichment prompt from scratch:

- **Image-first**: "Trust what you see in the image over any metadata"
- **Physical descriptions**: No vibe terms baked into `ai_description`. Concrete details only.
- **6 new KG fields**: `designer`, `influence_references`, `named_movements`, `production_mode`, `material_origin`, `garment_system`
- **`low_confidence_fields`**: Claude flags fields it's uncertain about
- **`display_title`**: Claude generates a descriptive 5-10 word title ("Black Silk Taffeta Bustle Afternoon Dress" instead of "Dress")
- **Cached system prompts**: Static template in system message (cacheable), per-item details in user message. ~30% API cost reduction.

Re-enriched all 4,234 products. Cost: ~$50. Time: ~18 min at concurrency 10.

---

## Embedding Upgrades

- **Text**: all-MiniLM-L6-v2 (384d) → **all-mpnet-base-v2 (768d)**
- **Image**: clip-ViT-B-32 (512d) → **clip-ViT-L-14 (768d)**
- `build_rich_text` now includes display_title, designer, influences, movements
- `enriched_text` no longer contaminated with old vibe vocabulary

Rebuilt both embedding sets. Had to ALTER TABLE the pgvector columns from 384d/512d to 768d.

---

## Bridge System: Complete Rewrite

### The Realization

After multiple iterations of the old 4-pass system (similarity, opposition, structural, visual echo), auditing the results, generating narratives, and viewing them in the frontend — we concluded:

**Bridges are only interesting as paths.** The axes, contrast pairs, and opposition framing don't produce interesting results. What's interesting is *why* two garments are connected: a shared designer, a shared movement, a construction technique that spans centuries, an explicit influence citation.

### Entity-Based Discovery (`better_bridges.py`)

Rewrote from scratch. Three passes:

**Pass 1: Shared Entities**
- Inverted index maps each entity value → product set
- IDF scoring: `log(N/count)` × entity type multiplier
- Multipliers: designer (3.0), influence (2.5), movement (2.0), garment_system (1.5), construction (1.0), social_function (1.0), motif (0.75)
- Common entities demoted: hand-sewing, machine-sewing, tailoring get 0.25× multiplier
- Blocklist: everyday-practical, status-signaling, geometric, floral, none — excluded from display, still scored
- Minimum: entity_score ≥ 5.0 (8.0 for same-era), at least one rare non-blocklisted entity (IDF ≥ 2.0)
- Per-era cap: max 300 same-era bridges
- Boundary: 30+ year gap OR different culture

**Pass 2: Lineage (directed)**
- Products with `influence_references` matched against corpus
- Era parsing: extracts decades ("1890s"), centuries, era keywords from influence strings
- Word index for fast matching + embedding fallback for unmatched
- Directed: source = older (the original), target = newer (the referencer)
- Lineage bonus: +5.0 to entity_score (the reference itself is a high-value entity)
- ~1,020 bridges, 460 via embedding fallback
- Only 323 unmatched (down from 2,597 before era parsing + embedding fallback)

**Pass 3: Visual Echo**
- pgvector image similarity for pairs NOT already connected
- Batch commits every 500 bridges (survives Supabase pooler timeouts)
- Only finds "surprises that metadata missed"
- ~2,800 bridges

**Results: ~24,000 total bridges.** Every bridge has a typed, weighted reason stored in `shared_entities` JSON.

### Scoring

```
bridge_score = sigmoid(entity_score + context_score + embedding_bonus)

entity_score: IDF × type_multiplier per shared entity
context_score: year_gap bonus (decade precision > era midpoint) + culture/category crossing
embedding_bonus: small confirmation boost from text/image similarity
```

### Schema Changes

StyleBridge simplified:
- Added: `shared_entities` (JSON), `entity_score`, `directed`
- Removed: `structural_score`, `bridge_type`, `primary_axis`, `secondary_axis`, `contrast_pair`, `shared_garment_fields`, `discovery_metadata`, `shared_designer`, `shared_movements`, `shared_influences`
- Connection modes: `shared_entity`, `lineage`, `visual_echo` (replaces contrast/echo/parallel/visual/affinity)

---

## Narrative Generation Rework

One adaptive prompt for all bridge types (replaces 6 mode-specific prompts):

- Shared entities formatted with human-readable labels (Designer, Movement, Technique, etc.)
- Distance line: "45 years apart · different cultures"
- Lineage note: 'Item B references "Japanese kimono draping" — Item A is that tradition.'
- Visual echo: "visual form — see the images" when no entity overlap
- Images sent as vision content to Claude
- Quality gate: bridge_score ≥ 0.55 (0.45 for visual echo)
- Per-product narrative cap: 5
- Ordering: lineage first, then visual_echo, then shared_entity

Sample narrative (lineage bridge):
> "These tattered socks trace the arc of punk's domestication — from Westwood and McLaren's original anarchic unraveling to the movement's gentler offspring where rebellion gets packaged into turquoise stripes and controlled fraying."

---

## ERA Taxonomy

Expanded ERA_MIDPOINTS from 32 to 38 eras. Added: Punk, Minimalism, Indie Sleaze, Belle Epoque, Dark Academia, Dopamine Dressing, Cottagecore, Gorpcore, World War I Transition, Italian Renaissance, Late Medieval, Restoration, Gothic/High Medieval, Rave/Club Kid.

---

## Design Handoff Update

Updated `FIGMA_DESIGN_HANDOFF_V2.md` for entity-based bridges:
- Killed: axis slider, opposition theater, "What Argues With This?", vibe trails, all contrast/axis UI
- Added: Thread Pull (signature interaction), Bridge of the Day, Movement Trails, Influence Map
- Bridge display: shared entities as headline tags, lineage arrows, distance labels
- Browse modes: Era, Culture, Movement, Function (replaces Vibe, Axis)
- Filter presets: Same Maker, Longest Echoes, Lineage, Visual Surprises, Cross-Culture

---

## Frontend Refactor Plan

Created `FRONTEND_REFACTOR_PLAN.md` — 6 phases, 15 days, 52 checkboxes:

1. **Phase 0**: Backend API schema updates (Day 1-2)
2. **Phase 1**: TypeScript types + design tokens (Day 2-3)
3. **Phase 2**: Bridge components rewrite (Day 3-5)
4. **Phase 3**: All pages updated (Day 5-9)
5. **Phase 4**: Thread Pull + Bridge of the Day (Day 9-12)
6. **Phase 5**: Polish + tests + deploy (Day 12-15)

Target: deployed by April 10.

---

## Supabase War Stories

- Pooler timeout (~30s) kills connections during CPU-bound work (embedding generation, bridge scoring)
- ResilientSession retries handle it but it's noisy
- ALTER TABLE on 4,234 rows timed out multiple times — had to increase compute, restart project
- Pass 3 batch commits (500 bridges) survive pooler drops mid-visual-echo-pass
- Port 6543 (pooler) not 5432 (direct) — direct requires IPv6 or paid IPv4 add-on

---

## What's Next

Tomorrow: Phase 0 of the frontend refactor. Update API schemas, then start rebuilding components with entity-based bridge data. Thread Pull is the wow feature. Ship in 3 weeks.
