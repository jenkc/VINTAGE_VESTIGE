# Vintage Vestige — Session Handoff Document

**Last updated: 2026-03-20**
**Read this first in any new Claude Code session.**

---

## Current Priorities

1. **Frontend refactor** — Phase 0 (API schema updates) is first. See `_docs/FRONTEND_REFACTOR_PLAN.md` for full 6-phase plan with checklists.
2. **Generate more narratives** — only ~20 generated so far with new prompt. Lower score gate and run full batch after API is updated.
3. **Replace `compute_bridges.py` with `better_bridges.py`** — rename when confident.

## What to Work on Next

Start Phase 0 of `_docs/FRONTEND_REFACTOR_PLAN.md`:
- Update `api/schemas/bridge.py` and `api/schemas/product.py` for new bridge schema
- Update `api/routers/bridges.py` — new connection_mode values, remove primary_axis filter
- Update `analysis/bridge_queries.py` — new column names
- Verify with curl

## Known Bugs / Gaps

- 61 V&A products have broken image URLs (truncated at bucket path) — no image embeddings
- 2 products failed re-enrichment (id=1038 "Shirt", id=4134 "Dress fabric") — old data intact
- `compute_bridges.py` (old) still exists alongside `better_bridges.py` (new) — need to rename
- Tests (`tests/`) reference old bridge schema — will break until updated (Phase 5 of refactor)
- `backfill_bridge_scores.py` exists but wasn't needed (better_bridges.py applies lineage bonus + blocklist natively)

---

## Session Log: 2026-03-19/20 — Complete Pipeline Rework (Vibes, Enrichment, Embeddings, Bridges, Narratives)

### What Was Accomplished

**Vibe System Rework:**
- Scrapped 22 discrete vibe terms → 6 axes with pole pairs (Volume, Ornament, Exposure, Gender, Register, Occasion)
- Pick-a-pole + confidence scoring format
- Backfilled all 4,234 products with new format
- Later discovered: axes useful for filtering, NOT for defining bridges

**Enrichment Overhaul:**
- Rewrote enrichment prompt: image-first, physical descriptions, no vibe terms in `ai_description`
- Added 6 KG fields: `designer`, `influence_references`, `production_mode`, `material_origin`, `garment_system`, `named_movements`
- Added `low_confidence_fields`, `display_title`
- Cached system prompts (~30% API cost reduction)
- Re-enriched all 4,234 products (~$50, ~18 min)
- Backfilled display titles separately

**Embedding Upgrades:**
- Text: all-MiniLM-L6-v2 (384d) → all-mpnet-base-v2 (768d)
- Image: clip-ViT-B-32 (512d) → clip-ViT-L-14 (768d)
- ALTER TABLE pgvector columns from old dimensions to 768d
- `build_rich_text` updated: includes display_title, KG fields, new vibe format
- Rebuilt both embedding sets

**Bridge System — Complete Rewrite (`better_bridges.py`):**
- Entity-based discovery replaces embedding-similarity approach
- Pass 1: Shared Entities — inverted index, IDF scoring, entity multipliers, blocklist, rarity gate
- Pass 2: Lineage (directed) — influence_references matched to corpus, era parsing, embedding fallback, lineage bonus (+5.0)
- Pass 3: Visual Echo — pgvector image similarity for unconnected pairs, batch commits
- ~24,000 bridges with typed shared_entities JSON
- Saves after each pass (resilient to Supabase pooler drops)
- bridge_score: sigmoid-normalized (entity_score + context_score + embedding_bonus)

**Narrative Generation Rework:**
- One adaptive prompt replaces 6 mode-specific prompts
- Shared entities as substance, not vibes/axes
- Lineage note, visual echo fallback, distance line
- Quality gate + per-product cap (5)
- Ordering: lineage → visual_echo → shared_entity
- Generated 20 test narratives — all excellent

**Design & Planning:**
- Updated `FIGMA_DESIGN_HANDOFF_V2.md` — entity-based bridge display, Thread Pull, Bridge of the Day, Movement Trails
- Created `FRONTEND_REFACTOR_PLAN.md` — 6 phases, 15 days, 52 checkboxes
- Created HTML artifact reference (`vintage_vestige_ui.html`)
- Created `DEV_DIARY_03-19-20.md`

### Files Created

| File | Purpose |
|------|---------|
| `tools/analysis/better_bridges.py` | Entity-based bridge computation (replaces compute_bridges.py) |
| `tools/analysis/backfill_bridge_scores.py` | Patches existing bridges with lineage bonus + blocklist cleanup |
| `tools/analysis/generate_narratives.py` | Rewritten for entity-based bridges |
| `tools/enrichment/reenrich_creative_kg.py` | Targeted re-enrichment (creative + KG fields only) |
| `tools/enrichment/backfill_display_titles.py` | Display title backfill |
| `tools/enrichment/backfill_culture.py` | Culture field backfill (659 products) |
| `_docs/FRONTEND_REFACTOR_PLAN.md` | 6-phase frontend implementation plan with checklists |
| `_docs/DEV_DIARY_03-19-20.md` | Dev diary blog post |
| `vintage_vestige_ui.html` | HTML artifact for design reference |

### Files Modified

| File | Changes |
|------|---------|
| `storage/database.py` | StyleBridge model: added shared_entities, entity_score, directed; removed structural_score, bridge_type, primary_axis, secondary_axis, contrast_pair, shared_garment_fields, discovery_metadata, shared_designer, shared_movements, shared_influences |
| `enrichment/claude.py` | New enrichment prompt (image-first, KG fields, cached system prompt); new narrative method (one adaptive prompt); `_format_shared_entities`; `build_rich_text` updated with display_title + KG fields as @staticmethod |
| `tools/enrichment/enrich_async.py` | Updated for cached system prompt, new KG fields |
| `tools/embeddings/rebuild_embeddings.py` | Batched fetching, error handling, truncation warnings |
| `embeddings/generator.py` | Updated to all-mpnet-base-v2 (768d) |
| `_docs/FIGMA_DESIGN_HANDOFF_V2.md` | Fully updated for entity-based bridges, Thread Pull, new browse modes |
| `vv-web/src/app/layout.tsx` | Briefly had Figma capture script (added then removed) |

### Decisions Made

| Decision | Why |
|----------|-----|
| 6-axis vibes replace 22 discrete terms | Cleaner model, opposition built into structure, but ultimately useful for filtering not bridging |
| Entity-based bridges replace embedding-similarity | Every bridge has a typed "why" — shared designer, movement, technique. Not "these embeddings are close." |
| IDF scoring for entities | Rare entities (Japonisme) worth more than common ones (hand-sewing). Information retrieval standard. |
| Lineage bridges are directed (older → newer) | Time flows forward. The original is the source, the referencer is the target. |
| Lineage bonus +5.0 | The influence reference itself is a high-value entity connection, equivalent to sharing a rare movement. |
| ENTITY_BLOCKLIST | everyday-practical, status-signaling, hand-sewing etc. can tag along but can't be the sole reason for a bridge. |
| Same-era stricter gate (8.0 vs 5.0) | Two items from the same era need more specific shared entities to be interesting. |
| Per-era cap (300) | Prevents Victorian or Quiet Luxury from dominating. |
| Boundary year gap raised to 30 | 20 years same-culture wasn't enough distance to be interesting. |
| all-mpnet-base-v2 for text embeddings | 2x better than MiniLM, same library, minimal code change. |
| clip-ViT-L-14 for image embeddings | Catches fine-grained visual distinctions (silhouette subtleties, fabric texture). |
| One narrative prompt for all bridge types | Simpler, cacheable, entity data provides the substance. |
| Thread Pull as signature frontend interaction | Vertical scroll through entity-connected garments — the graph picks the path. |
| Scrapped Knowledge Graph for now | Outside Jen's expertise. Entity-based bridges are KG-ready when the time comes. |
| 3-week deployment target (April 10) | Aggressive but achievable with the refactor plan. |

### Problems Hit

| Problem | Resolution |
|---------|------------|
| Supabase ALTER TABLE timeout | Increased compute, restarted project, ran columns one at a time |
| Supabase pooler drops during CPU-bound work | ResilientSession retries; Pass 3 batch commits every 500 |
| Port 6543 vs 5432 confusion | 6543 is pooler (required), 5432 is direct (requires IPv6) |
| pgvector dimension mismatch on ALTER | NULL out old embeddings first, then ALTER TYPE |
| Pass 2 lineage: 87% below narrative gate | Added LINEAGE_BONUS (+5.0 to entity_score) |
| Top shared entities dominated by common terms | ENTITY_BLOCKLIST + demoted multipliers for common construction/garment_system |
| better_bridges.py saved all bridges at end (crash = lose everything) | Save after each pass |
| `_get_year` treats era midpoints same as decades | Added year_precision ('decade' vs 'era') with scoring discount |
| old compute_bridges.py import path | `sys.path.insert` hack at top of better_bridges.py |
| Figma MCP capture hung on pending | Abandoned, using Claude Desktop artifacts instead |

---

## Session Log: 2026-03-13 — Bridge Pipeline Completion + Test Suite Cleanup

### What Was Accomplished

**Bridge Pipeline — Fully Complete:**
- **Opposition composite sort score** implemented in Pass 2: `0.40 * cc_norm + 0.35 * temporal_norm + 0.25 * structural_score` — rewards temporal distance and cross-cultural overlap over raw structural match
- **Near-duplicate detection** added to all passes: (1) exact title match → always skip, (2) same-era + text_sim ≥ 0.95 → skip; Pass 1 extended to catch cross-platform near-duplicates
- **Same-era vibe gate** added to passes 3 and 4: same-era pairs only included if `_vibes_diverge()` returns True
- **Pass 3 group cap** set at 150 products per shared purpose (matching the cap in Pass 4)
- **Social function consolidation** — 101 fragmented `social_function` values mapped to ~20 canonical clusters (`tools/analysis/consolidate_social_function.py` with `--apply`). Multi-cluster support (e.g. "wedding" → `["wedding-ceremonial"]`). Compute_bridges updated to handle `social_function` as array for all passes.
- **Backfill core_vibes** — 866 enriched products missing `core_vibes` re-enriched via `enrichment/backfill_vibes.py` (targeted, uses existing enriched fields, safe to resume)
- **Invalid vibe terms cleanup** — inline SQL stripped any term not in the 22-term controlled vocabulary; 72 products updated
- **Bridge classifier** (`tools/analysis/classify_bridge_dimensions.py`) — ran successfully on all 14,223 bridges. 14,194/14,223 classified. Distribution: affinity 10,886 / contrast 3,314 / resonance 23
- **Narrative generation** (`tools/analysis/generate_narratives.py`) — **ALL 14,223 bridges now have narratives**. Mode-specific prompts, classification context, varied closings.

**Database State (post-pipeline):**
- 14,223 style bridges (4 passes: cross_vibe 4,202, transmission 2,744, function 2,247, echo 1,714, structural 1,483, opposition 1,322, continuation 487, null 24)
- crossing_type: cross_culture 6,277, same_context 4,111, cross_category_culture 2,430, cross_category 1,405
- connection_mode: affinity 10,886, contrast 3,314, resonance 23
- ALL 14,223 bridges have `bridge_narrative`

**Data Integrity Tests — Created and Passing:**
- Created `tests/data_integrity/test_db_integrity.py` — 35 tests across: TestProductCompleteness, TestVibeVocabulary, TestSocialFunction, TestBridgeInvariants, TestBridgeClassification, TestNarratives, TestNearDuplicates, TestPlatformDistribution

**Full Test Suite — Clean:**
- Fixed 8 test failures + 5 errors → **309 passed, 5 skipped, 0 failures**
- `test_bridge_quality.py` — updated valid_types (added: opposition, function, structural, echo, contemporary) and expected_types (updated to actual pipeline passes)
- `test_data_quality.py` — JSON field integrity handles native PostgreSQL arrays + null JSON; added `jewelry`, `ensemble`, `necklace` to valid fp_categories
- `test_bridge_logic.py` — score threshold adjusted 0.5→0.4 (8 non-set fields weight to 0.49); set_fields test now pre-populates `_garment_parts_set` to match preparse pattern
- `test_database_model.py` — in_memory_db tests skipped (SQLite can't compile pgvector ARRAY types); non-DB tests still run

### Files Modified This Session

| File | Changes |
|------|---------|
| `tools/analysis/compute_bridges.py` | Opposition composite sort score, near-duplicate detection (all passes), same-era vibe gate (passes 3+4), Pass 3 group cap 150, social_function as array, `preparse_set_fields` moved to module level |
| `tools/analysis/consolidate_social_function.py` | New: maps 101 social_function values → ~20 canonical clusters |
| `enrichment/backfill_vibes.py` | New: targeted re-enrichment for products missing core_vibes |
| `tools/analysis/generate_narratives.py` | Fixed social_function deserialization |
| `enrichment/claude.py` | Fixed social_function rendering (comma-sep string), added primary_axis to narrative prompt |
| `tests/data_integrity/test_db_integrity.py` | New: 35 data integrity tests |
| `tests/data_integrity/test_bridge_quality.py` | Updated valid_types and expected_types for new bridge type system |
| `tests/data_integrity/test_data_quality.py` | JSON field test handles native arrays + null; added jewelry/ensemble/necklace to fp_categories |
| `tests/unit/test_bridge_logic.py` | Score threshold 0.5→0.4; set_fields test pre-populates `_garment_parts_set` |
| `tests/unit/test_database_model.py` | Skipped in_memory_db fixture (SQLite ARRAY incompatibility) |

### Decisions Made

| Decision | Why |
|----------|-----|
| Opposition composite sort score | Raw structural_score rewards generic same-category garments; composite rewards temporal distance + cross-cultural field overlap |
| Near-duplicate detection cross-platform | Cross-platform pairs with same title + same era + text_sim ≥ 0.95 are effectively duplicates — shouldn't waste bridge slots |
| Same-era vibe gate on passes 3+4 | Same-era items without divergent vibes produce low-insight bridges in function/structural passes |
| 150-product group cap on Pass 3 | Matches Pass 4 cap; prevents any single social function from dominating |
| Social function as multi-value | Old single-value `social_function` conflated mixed-purpose garments; array supports multi-cluster (e.g. `["wedding-ceremonial", "status-display"]`) |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `_sort_score` key in bridge dict → `CompileError: Unconsumed column names` | Pop `_sort_score` before passing bridge dict to `_batch_insert_bridges` |
| `preparse_set_fields` NameError — function nested inside `compute_bridges()` | Moved to module level above `compute_bridges()` |
| `ModuleNotFoundError` in `consolidate_social_function.py` | Added `sys.path.insert` with `os.path.dirname(os.path.dirname(...))` |
| `test_bridge_type_values_valid` FAILED ('echo', 'opposition', 'function', 'structural' unknown) | Added all 4 new bridge types to valid_types set |
| `test_json_fields_are_valid_json_arrays` FAILED (NoneType) | PostgreSQL ARRAY fields return Python lists; null JSON → None. Updated test to handle both |
| SQLite ARRAY ERRORs in test_database_model.py | Skipped in_memory_db fixture; those tests are covered by data_integrity/ suite |

### What's Left Open

- **`_sort_score` CompileError** — still needs the pop-before-insert fix if Pass 2 is re-run
- **Anthropic API monthly cap** — hit for March 2026; resets April 1. Narratives are done for now (all 14,223 complete).
- **Frontend updates** — social function explorer page, bridge card connection mode badges, bridge filtering UI

### Current State

**Pipeline: COMPLETE.** All 4,234 products enriched + embedded. 14,223 bridges computed (4 passes). All bridges classified (6 dimensions) and have narratives. Full test suite passes (309/309 non-skipped). Ready for deployment.

RESUME POINT: Deployment next. Phase 4 of reorg plan (Dockerfile, .dockerignore, .env.example) → Railway (API) + Vercel (frontend). See `_docs/DEPLOYMENT_PLAN.md`.

---

## Session Log: 2026-03-10 → 2026-03-12 — Bridge Rebuild + Tuning + Optimization

### What Was Accomplished

**Bridge Pipeline Debugging & Session Management:**
- Fixed DetachedInstanceError on Pass 2 — eager-load all 15+ fields then `db.expunge(p)` before closing session
- Fixed missing structural fields in eager-load (10 fields were missing from touch list)
- Fixed summary queries using closed session
- Fixed empty `existing_pairs` on resume — loads all existing `(source_id, target_id)` from DB at startup
- Added `--start-pass=N` CLI flag to resume from a specific pass
- ResilientSession upgraded to 3 retries with escalating delays (1s, 3s, 5s) + `engine.dispose()`
- Refactored passes 2-4 to compute entirely in-memory, then batch-insert with fresh sessions (100 per batch)
- Startup session cycling — each query uses its own throwaway session

**Performance Improvements:**
- `bulk_load_embeddings()` — loads all embeddings in one query into memory dict
- `preparse_set_fields()` — pre-parses JSON array fields into Python sets at startup, eliminating millions of `json.loads()` calls during structural scoring
- Group size cap of 100 products per group in Pass 4 (Pass 3 still needs this)

**Structural Weight Rebalance:**
- `fp_category` demoted from 0.16 → 0.06 (table stakes, not interesting)
- Cross-cultural fields promoted: `construction_technique` 0.10→0.14, `social_function` 0.07→0.12, `motif_family` 0.07→0.12
- Total cross-cultural weight: 0.24 → 0.38

**Bridge Diversity:**
- Per-product participation cap (`max_appearances=8`) with greedy diversified selection in passes 2-4
- `top_per_pair` increased 20→150, `top_per_function` 15→150, `top_per_group` 10→30

**Rebuild Results (15,619 total bridges):**
- Pass 1 (similarity): 10,243 bridges (cross_vibe 4161, transmission 3416, echo 2107, continuation 533, null 26)
- Pass 2 (opposition): 1,317 bridges
- Pass 3 (function): 2,545 bridges
- Pass 4 (structural): 1,514 bridges
- Runtime: 1486.6s (~25 min)

**Supabase Pro Upgrade:**
- Upgraded from free tier to Pro ($25/mo) — egress cap was hit from repeated test runs

### Files Modified

| File | Changes |
|------|---------|
| `tools/analysis/compute_bridges.py` | Structural weight rebalance, participation caps, pre-parsed set fields, group size cap, batch inserts, session cycling, `--start-pass` flag, rebuild block restored, bulk embedding load |
| `storage/database.py` | ResilientSession: 3 retries with escalating delays + `engine.dispose()` |

### Decisions Made

| Decision | Why |
|----------|-----|
| Demote `fp_category` weight from 0.16→0.06 | Two blazers trivially score 0.28 from category+silhouette alone — rewards "boring" matches |
| Cross-cultural fields get 0.38 combined weight | `construction_technique`, `social_function`, `motif_family` are the interesting bridge signals |
| Per-product participation cap of 8 | Prevents any single product from dominating top bridges |
| Pre-parse JSON set fields at startup | Eliminates millions of redundant `json.loads()` calls during O(n²) passes |
| Batch inserts (100 per batch, fresh session each) | Prevents pooler timeout during large insert phases |
| Supabase Pro upgrade | Free tier egress limit hit from repeated bridge computation runs |

### Problems Hit

| Problem | Fix |
|---------|-----|
| DetachedInstanceError after session close | Eager-load all fields then `db.expunge(p)` before closing |
| Connection drops during startup queries | Split into throwaway sessions per query |
| `--rebuild` didn't actually delete bridges | Rebuild block was missing — restored it |
| `embedding_cache` and `start_time` undefined | Lost during reorganization — re-added |
| Duplicate expunge block crashed (products already detached) | Removed duplicate — startup already handles expunge |
| Blazer domination in opposition bridges | Weight rebalance + participation caps |
| Pass 1 counter shows 0 in summary | Logging bug: `total_by_pass['similarity']` not incremented (data is correct) |

### What's Left Open

- **Opposition composite sort score** — sorting by structural_score rewards generic garments. Proposed formula: `0.40 * cross_cultural_score_norm + 0.35 * temporal_distance_norm + 0.25 * structural_score`
- **Pass 3 group cap** — needs same 100-product cap as Pass 4
- **Pass 1 counter logging bug** — `total_by_pass['similarity']` not being incremented
- **Classifier run** — `tools/analysis/classify_bridge_dimensions.py` (after opposition sort is fixed)
- **Narrative generation** — `tools/analysis/generate_narratives.py` (after classifier)

RESUME POINT: Implement opposition composite sort score (reward temporal distance + cross-cultural field overlap instead of raw structural score). Then add group cap to Pass 3. Then run classifier → generate narratives.

---

## Session Log: 2026-03-09 — Project Reorganization + Test Fixes + Narrative Overhaul

### What Was Accomplished

**Project Reorganization (Phase 2 of deployment prep):**
- Moved all runnable scripts into `tools/` directory, keeping only library code in package dirs
- Created `tools/analysis/`, `tools/enrichment/`, `tools/embeddings/`, `tools/data_loading/`, `tools/data_quality/`, `tools/db_utils/`, `tools/migration/`
- Updated `sys.path.insert(0, project_root)` in 16+ scripts from `'..'` to `'..', '..'` (one extra level for `tools/*/` nesting)
- Added missing `sys.path` setup to 3 scripts in `tools/db_utils/` that had none (`view_database.py`, `wipe_database.py`, `reclassify_bridge_eras.py`)

**Temporal Classification Fix:**
- Fixed platform fallback in `classify_temporal_type` — same platform no longer implies same era (V&A spans centuries)
- Added decade-based fallback before platform proxy: parse decades → compute year gap → classify by distance
- Platform proxy now only fires when one platform is historical and the other modern
- Returns `None` (unknown) when truly no temporal data exists for same-platform pairs

**Consolidated Duplicate `classify_temporal_type`:**
- Deleted duplicate function from `tools/analysis/classify_bridge_dimensions.py`
- Now imports single source of truth from `tools/analysis/compute_bridges.py`
- Moved `classify_bridge_dimensions.py` from `tools/data_quality/` to `tools/analysis/` (where it belongs with the rest of the bridge pipeline)

**SQL/Python Score Mismatch Fix:**
- Rewrote `_COMPOSITE_SQL` in `analysis/bridge_queries.py` — old SQL used `COALESCE(image_similarity, 0)` while Python redistributed weights proportionally when image is NULL
- New SQL uses a 6-branch CASE statement matching Python's weight redistribution for all 3 connection modes (contrast: 0.20/0.20/0.60, resonance: 0.60/0.20/0.20, affinity: 0.40/0.30/0.30)
- Changed from `text()` to `literal_column()` for `_COMPOSITE_SQL` (supports `.desc()` and comparison operators)
- Created `_COMPOSITE_DESC` with `text()` for ORDER BY clauses

**Narrative Generation Overhaul (7 items):**
1. Deleted stale sync `generate_bridge_narrative` method from `enrichment/claude.py`
2. Rewrote prompt construction as list-based building (no whitespace issues from f-string indentation)
3. Added `_narrative_closing()` static method — 8 closing variations based on temporal_type, crossing_type, connection_mode
4. Added vibe data to prompts (`core_vibes` for both items)
5. Added `_format_shared_attributes()` static method — converts shared dict to readable text
6. Differentiated length: contrast bridges get 2 sentences / 60 words, others get 1 sentence / 40 words
7. Mode-specific system prompts: contrast explains tension, resonance explains echoes, affinity finds the thread

**Narrative Pipeline Update:**
- `tools/analysis/generate_narratives.py` now fetches all classification fields (`temporal_type`, `crossing_type`, `primary_axis`)
- Product map now includes `core_vibes` for narrative prompts
- Passes all classification fields through to `generate_bridge_narrative_async()`

**Test Fixes (158 unit tests passing, 70 integration tests passing):**
- Removed stale `REVIVAL_STRUCTURAL_THRESHOLD` import and `TestRevivalClassification` class from `test_bridge_logic.py`
- Updated 6 assertions in `test_bridge_logic.py`: `None` → `'contemporary'` for same-era/close-decade cases
- Rewrote all `classify_temporal_type` calls in `test_bridge_classification.py` from 3-arg `(bridge, src, tgt)` to individual field signature
- Updated import path from `tools.data_quality` to `tools.analysis` in classification tests
- Fixed expected values in temporal tests (Victorian→Quiet Luxury is 'echo' not 'transmission')
- Added `temporal_type`, `crossing_type`, `primary_axis`, `secondary_axis`, `contrast_pair` to MockBridge defaults in `test_bridge_queries.py`
- Updated `test_enrichment.py` expected field count from 23 to 29 (added core_vibes, bridge_vibes, vibe_scores, construction_technique, social_function, motif_family)
- Fixed `is 'contemporary'` → `== 'contemporary'` SyntaxWarning in `compute_bridges.py`

### Files Modified This Session

| File | Changes |
|------|---------|
| `tools/analysis/compute_bridges.py` | Fixed temporal fallback (decade-based before platform proxy), fixed `is` → `==` |
| `tools/analysis/classify_bridge_dimensions.py` | Moved from `tools/data_quality/`, deleted duplicate `classify_temporal_type`, imports from `compute_bridges` |
| `tools/analysis/generate_narratives.py` | Updated to fetch/pass all classification fields, include `core_vibes` in product map |
| `analysis/bridge_queries.py` | Rewrote composite SQL (6-branch CASE), `text()` → `literal_column()`, added `_COMPOSITE_DESC` |
| `enrichment/claude.py` | Deleted sync `generate_bridge_narrative`, added `_format_shared_attributes()`, `_narrative_closing()`, rewrote async narrative method with list-based prompt, mode-specific system prompts, differentiated length |
| 16+ scripts in `tools/` | Updated `sys.path` from `'..'` to `'..', '..'` |
| 3 scripts in `tools/db_utils/` | Added missing `sys.path` setup |
| `tests/unit/test_bridge_logic.py` | Removed stale imports/tests, updated assertions |
| `tests/unit/test_bridge_classification.py` | Rewrote for new function signatures, updated import path |
| `tests/unit/test_bridge_queries.py` | Added 5 new fields to MockBridge defaults |
| `tests/unit/test_enrichment.py` | Updated expected field count 23 → 29 |

### Decisions Made

| Decision | Why |
|----------|-----|
| Decade-based fallback before platform proxy in temporal classification | V&A spans many eras — same platform ≠ same time period |
| Return `None` for truly unknown temporal data | Better to admit ignorance than guess wrong |
| Single `classify_temporal_type` in `compute_bridges.py` | Was duplicated in `classify_bridge_dimensions.py` — consolidated to single source of truth |
| `classify_bridge_dimensions.py` lives in `tools/analysis/` not `tools/data_quality/` | It's part of the bridge pipeline (compute → classify → narrate), not data quality |
| `literal_column()` for composite SQL | `text()` objects don't support `.desc()` or comparison operators in SQLAlchemy |
| 6-branch CASE for composite scores | Must match Python's proportional weight redistribution when image is NULL, per connection mode |
| Contrast narratives get 2 sentences / 60 words, others get 1 / 40 | Contrasts need space to explain both the shared ground and the divergence |
| List-based prompt construction | Eliminates whitespace bugs from f-string indentation in multi-line prompts |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` in `tools/db_utils/view_database.py` | Script had no `sys.path` setup — added it. Found 2 more scripts with same issue |
| `ImportError: REVIVAL_STRUCTURAL_THRESHOLD` removed from `compute_bridges` | Deleted stale import and `TestRevivalClassification` class from tests |
| `SyntaxWarning: "is" with str literal` | Changed `is 'contemporary'` to `== 'contemporary'` |
| 23 test failures across 5 files | Multiple causes: wrong function signatures, stale assertions, missing MockBridge fields, wrong field counts — fixed all systematically |
| 11 integration failures from `text().desc()` | `text()` objects don't support `.desc()` — switched to `literal_column()` |
| SQL sort order wrong (1 remaining test) | SQL used `COALESCE(image_similarity, 0)` but Python redistributed weights proportionally — rewrote SQL to match |

### What's Left Open

- **5 test errors in `test_database_model.py`** — SQLite ARRAY incompatibility (separate issue, not blocking)
- **`compute_bridges.py --rebuild`** was still running at end of session
- After bridges finish: run `tools/analysis/classify_bridge_dimensions.py` → `tools/analysis/generate_narratives.py`
- Review 20-30 sample narratives across connection modes
- Phase 3 of reorg plan: docs cleanup (rename `old/` → `archive/`)
- Phase 4 of reorg plan: deployment files (Dockerfile, .dockerignore, .env.example)

RESUME POINT: Check if compute_bridges finished → run classifier → run narrative generation → review samples. Then continue with reorg Phases 3-5.

---

## Session Log: 2026-03-07 — Multi-Dimensional Bridge Classification + Social Function Explorer API

### What Was Accomplished

**Multi-Dimensional Bridge Classification (replaces `semantic_type`):**
- Designed and implemented 6-column classification system replacing the single overloaded `semantic_type` column on StyleBridge
- 6 new columns: `temporal_type`, `crossing_type`, `connection_mode`, `primary_axis`, `secondary_axis`, `contrast_pair`
- Started with 5 connection modes (citation/echo/parallel/contrast/kinship), then **simplified to 3 sharp modes**: contrast, resonance, affinity — after critique identified echo was too broad, parallel too rare, and citation couldn't detect intentionality
- 9 opposition pairs across 4 aesthetic axes (volume, ornament, body, register) for contrast detection
- Classifier script built, tested, and ready to run post-bridge-computation

**Social Function Explorer API:**
- New `/explore` router with 2 endpoints for browsing products by social function
- `shared_function` filter added to existing `/bridges/top` endpoint for "Same Question, Different Answers" view
- Uses PostgreSQL `jsonb` containment operators for efficient JSON array querying

**Narrative Pipeline Update:**
- `generate_bridge_narrative_async()` now accepts `connection_mode` and `contrast_pair`
- Mode-specific prompt hints: contrast bridges explain tension, resonance bridges explain echoes, affinity bridges use existing generic prompt
- `generate_narratives.py` fetches and threads the new fields through

**Test Updates:**
- Updated `test_bridge_classification.py` for 3-mode system (deleted echo/parallel/kinship tests, added resonance/affinity/contrast-beats-resonance tests)

**KG Plan Updates:**
- Updated 5 KG implementation plan docs to reflect 6-dimension model

### Files Created This Session

| File | Purpose |
|------|---------|
| `scripts/classify_bridge_dimensions.py` | Multi-dimensional bridge classifier (330 lines) |
| `tests/unit/test_bridge_classification.py` | Unit tests for classifier (414 lines) |
| `analysis/product_queries.py` | Social function query helpers (JSON containment queries) |
| `api/routers/explore.py` | Explore router (`/explore/functions`, `/explore/functions/{fn}`) |
| `api/schemas/explore.py` | Pydantic schemas for explore endpoints |
| `docs/plans/FRONTEND_UPDATES.md` | Proposed frontend changes for new API endpoints |

### Files Modified This Session

| File | Changes |
|------|---------|
| `storage/database.py` | Added 6 new columns to StyleBridge model |
| `analysis/bridge_queries.py` | Added 6 fields to BridgeResult/build/filters + `shared_function` filter with jsonb query + `text` import |
| `api/routers/bridges.py` | Added `temporal_type`, `crossing_type`, `connection_mode`, `primary_axis`, `shared_function` query params |
| `api/schemas/bridge.py` | Added 6 new optional fields to BridgeResult Pydantic schema |
| `enrichment/claude.py` | Added `connection_mode`/`contrast_pair` params to `generate_bridge_narrative_async()` with mode hint logic |
| `analysis/generate_narratives.py` | Fetches `connection_mode`/`contrast_pair` from bridges, passes through to enricher |
| `api/main.py` | Registered explore router |
| `docs/plans/KG_IMPLEMENTATION/KG_PHASE1_SCHEMA_DESIGN.md` | Replaced semantic_type with 6-dimension model |
| `docs/plans/KG_IMPLEMENTATION/KG_PHASE0_PREREQUISITES.md` | Updated classifier reference |
| `docs/plans/KG_IMPLEMENTATION/KG_PHASE4_EXPORT_SCRIPTS.md` | Updated export to 6 columns |
| `docs/plans/KG_IMPLEMENTATION/KG_PHASE7_FRONTEND.md` | Updated color coding to 3 modes |
| `docs/plans/KG_IMPLEMENTATION/KG_DECISIONS.md` | Rewrote KGD-005 for 6-dimension model |

### Decisions Made

| Decision | Why |
|----------|-----|
| 6 orthogonal dimensions over single `semantic_type` | Can't filter "all contrast bridges that are also cross-cultural transmissions" with a single column |
| 3 connection modes (contrast/resonance/affinity) over 5 | Echo was "not kinship" rather than something specific; parallel was too rare; citation can't detect intentionality from embeddings |
| Contrast priority over resonance | Opposing vibes on same structural axis is more interesting than high text similarity |
| Post-hoc classifier (not integrated into compute_bridges) | Bridge computation is already complex; classification is a separate concern that runs after |
| Include bridge_vibes in contrast/resonance detection | bridge_vibes are "secondary aesthetic tendencies" — excluding them misses valid oppositions |
| New `/explore` router (not extending `/products`) | Social function exploration is conceptually different from single-product CRUD; will grow with technique/motif explorers |
| `jsonb` containment for social_function queries | `social_function::jsonb @> '["wedding"]'::jsonb` is efficient and indexable |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `classify_crossing_type` signature had 3 args but tests expected 2 | Dropped `bridge` param — function doesn't use it |
| Mode hint code placed inside f-string | Moved logic above the f-string, interpolate `{mode_hint}` variable |
| `bindparams()` closing paren misaligned in shared_function filter | Fixed indentation so bindparams closes before filter |

### What's Left Open

- **`compute_bridges.py --rebuild` still running** — classifier can't run until it finishes
- **Classifier dry-run** — `venv/bin/python scripts/classify_bridge_dimensions.py --dry-run` (pending bridge completion)
- **Generate narratives** — after classifier populates connection_mode, new narratives will get mode-specific hints
- **Supabase ALTER TABLE** — 6 new columns added to style_bridges (done this session)
- **Frontend updates** — documented in `docs/plans/FRONTEND_UPDATES.md`, not yet implemented

RESUME POINT: Wait for `compute_bridges.py` to finish → run classifier dry-run → review distribution → full classifier run → generate narratives. Frontend updates are planned but not started.

---

## Session Log: 2026-03-06 — Async Enrichment Pipeline + Embedding Script Fixes + Bug Fixes

### What Was Accomplished

**Bug Fixes:**
- **f-string bug in `enrichment/claude.py`** — `{"term": confidence_float}` inside f-strings on lines 332 and 405 was being parsed as a format specifier. Fixed by doubling braces: `{{"term": confidence_float}}`. This was causing most enrichment calls to fail (only 70/3298 succeeded before fix).
- **Stale print/docstrings in `analysis/compute_bridges.py`** — Updated "3 passes" → "2 passes" after the cross_category pass was removed in a prior session. Updated module docstring, function docstring, and runtime print.

**New Enrichment Scripts:**
- **`enrichment/enrich_async.py`** — Async concurrent enrichment using `asyncio.Semaphore` for bounded concurrency. 5x speedup over sequential. Supports `--limit=N`, `--concurrency=N`, `--yes`. Prints progress every 10 completions with rate and ETA. Does NOT generate embeddings (user runs those separately).
- **`enrichment/enrich_batch.py`** — Message Batches API enrichment (50% cost reduction). Submit/poll workflow. Ultimately user chose async approach for real-time feedback.

**Embedding Script Updates:**
- **`embeddings/generator.py`** — `generate_embeddings_for_database()` now uses `enriched_text` (with fallback to title+description) instead of raw title+description. Filter changed from `embedded_at == None` to `enriched_at != None, text_embedding == None`. Also generates image embeddings inline if missing.

**Enrichment Progress:**
- User ran multiple batches of 300 products using `enrich_async.py`
- Enrichment count: 866 → **1,490** (624 new products enriched this session)
- Text embeddings: 866 → **1,190** (324 new)
- 624 products now have `core_vibes` (new vibe vocabulary fields)

**Architecture Discussion:**
- Discussed multimodal embedding fusion approaches (early fusion, concatenation, learned projection)
- Decided to keep current late fusion approach (separate text + image vectors, combined at bridge scoring) — better for fashion domain because "looks similar" and "means similar" are different signals

### Files Created This Session

| File | Purpose |
|------|---------|
| `enrichment/enrich_async.py` | Async concurrent enrichment (asyncio, semaphore-bounded) |
| `enrichment/enrich_batch.py` | Message Batches API enrichment (50% cost, submit/poll) |

### Files Modified This Session

| File | Changes |
|------|---------|
| `enrichment/claude.py` | Fixed f-string bug: `{}` → `{{}}` for vibe_scores on lines 332, 405 |
| `analysis/compute_bridges.py` | Updated docstrings + print: "3 passes" → "2 passes" |
| `embeddings/generator.py` | `generate_embeddings_for_database()`: use enriched_text, changed filter, inline image embedding |

### Decisions Made

| Decision | Why |
|----------|-----|
| Keep separate text + image embeddings (no fusion) | Late fusion at bridge scoring preserves MiniLM semantic richness + CLIP visual similarity as independent signals |
| Async concurrent over Batch API for enrichment | User prefers real-time feedback; async is 5x faster; batch saves 50% cost but has 24hr turnaround |
| Embedding generation stays separate from enrichment | User's established workflow — enrich first, embed after |
| Use enriched_text for text embeddings (not title+description) | enriched_text contains 23 enrichment fields → richer semantic signal |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `Invalid format specifier ' confidence_float'` in f-string | Doubled braces: `{{"term": confidence_float}}` in claude.py |
| No progress output from async script | Added shared counter dict, prints every 10 completions with rate/ETA |
| Old embeddings used title+description, not enriched_text | Updated `generate_embeddings_for_database()` filter and text source |

### What's Left Open

- **~2,744 products still unenriched** (1,490/4,234 done)
- **~3,044 products missing text embeddings** (1,190/4,234 done)
- **~3,368 products missing image embeddings** (866/4,234 done)
- **Old 866 products** embedded from title+description (not enriched_text) — should be re-embedded
- **Bridges need recomputation** after enrichment + embedding completes (`compute_bridges.py --rebuild`)
- **Unrecognized eras** — review CSV after enrichment completes, add aliases

RESUME POINT: User is running enrichment batches of 300 via `enrich_async.py`. After enrichment completes: run embedding generation → recompute bridges → review era taxonomy.

---

## Session Log: 2026-03-04 — Supabase Migration (Steps 5-11 of 20) + IIT Todoist CSV

### What Was Accomplished

**Supabase Migration Progress (Steps 5-11 complete):**

Continuing the Supabase migration plan at `.claude/plans/zazzy-seeking-falcon.md`. Steps 1-4 were completed in a prior session (enable pgvector, create storage bucket, pg_dump/restore, update .env). This session completed:

- **Step 5: Image migration** — All 4,234 products migrated from base64 `data:image/...` → Supabase Storage URLs (`https://tusswxlrdoamintvswjs.supabase.co/storage/v1/object/public/product-images/{id}.jpg`). Zero base64 remaining.
- **Step 6: Qdrant → pgvector embedding migration** — 866 text embeddings + 866 image embeddings migrated from local Qdrant to pgvector columns. HNSW indexes created. Verified similarity queries work. Local Qdrant stopped and `QDRANT_HOST`/`QDRANT_PORT` removed from `.env`.
- **Step 7: ORM model update** — Added `from pgvector.sqlalchemy import Vector` and two columns (`text_embedding Vector(384)`, `image_embedding Vector(512)`) to Product class in `storage/database.py`.
- **Step 8: Vector search module** — Created `storage/vector_search.py` with `VectorSearch` class (4 methods: `search_text`, `search_image`, `get_embedding`, `upsert_embedding`). Takes SQLAlchemy Session instead of managing Qdrant connection.
- **Step 9: API dependencies** — Rewrote `api/dependencies.py` to use `VectorSearch` instead of old `VectorDB`.
- **Step 10: Search router** — Rewrote `api/routers/search.py` to use `VectorSearch` + pgvector instead of Qdrant.
- **Step 11: Search schema validators** — Added `@field_validator` to `SearchResult` in `api/schemas/search.py` to parse JSON strings from SQL for `style_tags` and `colors` fields.

**IIT 4.0 Todoist CSV:**
- Created comprehensive task list at `docs/IIT_4.0_TODOIST_TASKS.csv` with ~130 tasks across 8 sections, 3 indent levels, ready for Todoist CSV import.

### Files Created This Session

| File | Purpose |
|------|---------|
| `storage/vector_search.py` | pgvector-backed VectorSearch class (replaces `storage/vector_db.py`) |
| `docs/IIT_4.0_TODOIST_TASKS.csv` | 130-task Todoist import file for IIT 4.0 implementation |

### Files Modified This Session

| File | Changes |
|------|---------|
| `storage/database.py` | Added pgvector Vector import + text_embedding/image_embedding columns |
| `api/dependencies.py` | Swapped VectorDB → VectorSearch, removed Qdrant dependency |
| `api/routers/search.py` | Full rewrite: Qdrant → pgvector VectorSearch |
| `api/schemas/search.py` | Added `parse_json_lists` field_validator for style_tags/colors |
| `scripts/migrate_qdrant_to_pgvector.py` | User-written migration script (fixed: function signature, `==` vs `=`, collection name `vintage_images` plural) |
| `.env` | Removed QDRANT_HOST, QDRANT_PORT |

### Decisions Made

| Decision | Why |
|----------|-----|
| pgvector over Qdrant Cloud | Single database (Supabase) for everything — simpler ops, both embeddings on same row simplifies Φ calculation |
| VectorSearch takes Session (not own connection) | Shares request's DB session — no separate vector DB connection to manage |
| Keep `storage/vector_db.py` for now | Will delete in Step 16 after all references are updated |

### Problems Hit

| Problem | Fix |
|---------|-----|
| Qdrant collection name mismatch: `vintage_image` vs `vintage_images` | Collection was `vintage_images` (plural) — fixed in migration script |
| `_build_filter_dict` logic inverted (`if not filters:` then used `filters`) | Fixed: early return `None` when no filters |
| Typo `pgvector.sqalchemy` (missing 'l') | Fixed to `pgvector.sqlalchemy` |
| Typo `b64dercode` | Fixed to `b64decode` |
| Typo `.itemns()` | Fixed to `.items()` |
| Similarity query returned no rows | Product ID 1 didn't exist — used subquery to find any product with embeddings |

### What's Left Open

- **Steps 12-20 of Supabase migration** remain:
  - Step 12: Update compute_bridges.py (biggest remaining file — swap Qdrant for pgvector queries)
  - Step 13: Update embeddings/generator.py (handle URL images)
  - Step 14: Update enrichment/claude.py
  - Step 15: Update enrichment scripts
  - Step 16: Delete obsolete files (vector_db.py, etc.)
  - Step 17: Update frontend (next.config.ts image domains)
  - Step 18: Update tests
  - Step 19-20: Verify + cleanup

RESUME POINT: Start Step 12 (compute_bridges.py). User is writing all code themselves — walk through each step, check their work, flag bugs.

---

## Session Log: 2026-02-27 — Frontend Polish COMPLETE + Database Growth Plan + Deployment Discussion

### What Was Accomplished

**Frontend Polish (Step 10 — COMPLETE):**

All polish items finished. TypeScript check and `npm run build` both pass clean. All 4 routes compile:
- `/` — static, revalidates every hour
- `/about` — static
- `/search` — static (client-side data fetching)
- `/product/[id]` — dynamic (server-rendered per request)

Polish items completed:
- **Error boundaries**: `global-error.tsx` (root-level, with `<html>`/`<body>` tags), `error.tsx` (page-level for home), `product/[id]/loading.tsx` already existed
- **ImageWithFallback swap**: Replaced `next/image` with `ImageWithFallback` in BridgeCardFull, BridgeCardCompact, ProductCard. Kept ternary fallbacks as belt-and-suspenders.
- **Search error handling**: Added `error` state, catch block, and error display to search page
- **Home data caching**: `export const revalidate = 3600` (1-hour ISR)
- **Scroll snap**: `snap-x snap-mandatory` on carousels (home + product detail), `snap-start` on BridgeCardCompact
- **Mobile touch targets**: Search submit button enlarged to `size-11` (44px) for WCAG 2.5.5
- **Mobile search UX**: `autoFocus={!searchParams.get("q")}` — focuses input only when no existing query
- **SEO metadata**: Static `metadata` export on about page, dynamic `generateMetadata` on product detail page (title, description, OpenGraph image)
- **Accessibility**: `role="img" aria-label` on ScoreCircle, `role="search" aria-label` on search form, `aria-label="Submit search"` on button, `role="region" aria-label` on carousel containers
- **Loading skeleton**: Created `loading.tsx` for home page (hero + how-it-works shimmer)
- **CSS cleanup**: Confirmed no legacy `vintage-*` classes remain

**Database Growth Plan (866 → 1,500 products):**
- Analyzed all 3 data loaders and enrichment pipeline to plan growth
- Created 6-phase plan at `.claude/plans/functional-hopping-barto.md`
- Strategy: maximize free API data before Claude enrichment
- Target distribution: Fashionpedia 750, Met 400, Smithsonian 350
- Estimated cost: ~$27 (~$14 with Batch API)
- Bridge scaling analysis: confirmed linear growth due to `top_n` caps per product

**Backend Deployment Discussion:**
- Covered deployment options: Railway (all-in-one), Vercel+Render+Supabase+Qdrant Cloud (mix-and-match), Fly.io
- Explained key deployment concepts: env vars, build vs runtime, health checks, cold starts, CORS
- Recommended starting with: Qdrant Cloud (free 1GB) + Supabase (free Postgres) + Railway (FastAPI) + Vercel (Next.js)
- User decided to grow dataset before deploying (richer content = better first impression)

### Files Created This Session

| File | Purpose |
|------|---------|
| `vv-web/src/app/global-error.tsx` | Root-level error boundary (replaces root layout) |
| `vv-web/src/app/error.tsx` | Home page error boundary |
| `vv-web/src/app/loading.tsx` | Home page loading skeleton (Skeleton shimmer) |
| `.claude/plans/functional-hopping-barto.md` | Database growth plan: 866 → 1,500 products |

### Files Modified This Session

| File | Changes |
|------|---------|
| `vv-web/src/app/page.tsx` | Added `revalidate = 3600`, `snap-x snap-mandatory`, `role="region" aria-label` |
| `vv-web/src/app/search/page.tsx` | Added error state + display, 44px touch target, autoFocus, `role="search"`, `aria-label` |
| `vv-web/src/app/product/[id]/page.tsx` | Added `generateMetadata` (title, description, OG image), `snap-x snap-mandatory`, `role="region" aria-label` |
| `vv-web/src/app/about/page.tsx` | Added static `metadata` export (title + description) |
| `vv-web/src/components/bridge/BridgeCardFull.tsx` | Swapped `Image` → `ImageWithFallback` |
| `vv-web/src/components/bridge/BridgeCardCompact.tsx` | Swapped `Image` → `ImageWithFallback`, added `snap-start` |
| `vv-web/src/components/bridge/ScoreCircle.tsx` | Added `role="img"` + `aria-label` |
| `vv-web/src/components/search/ProductCard.tsx` | Swapped `Image` → `ImageWithFallback` |

### Decisions Made

| Decision | Why |
|----------|-----|
| Keep ternary fallbacks alongside ImageWithFallback | Belt-and-suspenders: ImageWithFallback handles load errors, ternary handles missing URLs |
| Search page doesn't need `loading.tsx` | Client component manages its own loading state with `useState` |
| `revalidate = 3600` for home page | 1-hour ISR cache — bridges don't change often, avoids per-request DB calls |
| 44px touch targets (`size-11`) | WCAG 2.5.5 minimum target size for mobile accessibility |
| `autoFocus` only when no existing query | Prevents keyboard popping up when returning to search with results |
| Grow dataset before deploying | Sparse data = empty pages = bad first impression |
| Target 1,500 products for growth | Balances content density vs Claude API cost (~$27) |
| Fashionpedia-heavy distribution (750/1500) | Expert-annotated taxonomy = cheaper enrichment ($0.015 vs $0.03/item) |
| `"use client"` pages can't export `metadata` | Next.js constraint — root layout's default title applies instead |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `npx tsc --noEmit` failed — `npx` not found | Prepended PATH: `export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.nvm/versions/node/*/bin:$PATH"` |
| Port 8000 already in use | Backend was already running from a previous session (PID 17312) |

### What's Left Open

- **Database growth**: Plan documented at `.claude/plans/functional-hopping-barto.md` — user will implement themselves
- **Deployment**: Discussed options but not started — user wants data density first
- **Image search frontend**: Backend API exists but no frontend implementation yet
- **Bridge narratives**: Still 22/7,324 generated — will be addressed during Phase 6 of growth plan

RESUME POINT: User is implementing the database growth plan (Phase 1: load data from all 3 sources, then Phases 2-6). After data growth, deployment is next.

---

## Session Log: 2026-02-25 (cont.) — Frontend Phase 3B Search + Phase 3C Bridge Components (1-7)

### What Was Accomplished

**Frontend Phase 3B — Search Components (COMPLETE):**
- **3B.1 SearchBar.tsx** — `"use client"`, debounced text input (400ms), Enter for immediate search, clear button (X/Search icon swap), large/compact variants
- **3B.2 ImageUpload.tsx** — `"use client"`, drag-and-drop + file picker, FileReader base64 conversion, preview with X overlay, mobile Camera/desktop Upload icons
- **3B.3 ProductCard.tsx** — Server component, union type `CardData = SearchResult | ProductSummary`, next/Image with `fill` + `sizes`, platform badge with inline color, era badge, match %, gradient placeholder for missing images, `group-hover:scale-105` image zoom

**Frontend Phase 3C — Bridge Components (7 of 10 done):**
- **3C.1 PlatformBadge.tsx** — Frosted-glass pill, runtime platform color from PLATFORM_COLORS
- **3C.2 EraBadge.tsx** — Dark translucent pill, "Era · date" format with middle dot separator
- **3C.3 ScoreCircle.tsx** — Circular match display (44px mobile / 52px desktop), color from `scoreColorByValue()`
- **3C.4 BridgeConnector.tsx** — Gold circle with ArrowLeftRight icon, full/compact variants
- **3C.5 AttributePill.tsx** — Shared DNA pill with two-tone label/value typography, sage color scheme
- **3C.6 NarrativeBlock.tsx** — Blockquote with gold left border, italic serif text
- **3C.7 ScoreBreakdown.tsx** — Three horizontal bars (semantic/visual/structural), `BARS` array with `.map()`, skips null image similarity, 60% opacity fills

**Type fix:**
- Added `platform: string` to `SearchResult` interface in `types/index.ts` — was missing, causing TS error in ProductCard union type

### Files Created This Session

| File | Purpose |
|------|---------|
| `vv-web/src/components/bridge/PlatformBadge.tsx` | Frosted-glass platform pill |
| `vv-web/src/components/bridge/EraBadge.tsx` | Dark translucent era pill |
| `vv-web/src/components/bridge/ScoreCircle.tsx` | Circular match percentage |
| `vv-web/src/components/bridge/BridgeConnector.tsx` | Gold exchange icon circle |
| `vv-web/src/components/bridge/AttributePill.tsx` | Shared DNA attribute pill |
| `vv-web/src/components/bridge/NarrativeBlock.tsx` | AI narrative quote block |
| `vv-web/src/components/bridge/ScoreBreakdown.tsx` | Three-bar score visualization |

### Files Modified This Session

| File | Changes |
|------|---------|
| `vv-web/src/components/search/SearchBar.tsx` | Populated: debounced search with large/compact variants |
| `vv-web/src/components/search/ImageUpload.tsx` | Populated: drag-drop + file picker with base64 conversion |
| `vv-web/src/components/search/ProductCard.tsx` | Populated: product card with image, platform badge, era, score |
| `vv-web/src/types/index.ts` | Added `platform: string` to SearchResult |

### Decisions Made

| Decision | Why |
|----------|-----|
| ProductCard accepts `SearchResult \| ProductSummary` union | Reusable in both search results and bridge displays |
| ProductCard uses `hasScore()` type guard | Distinguishes SearchResult (has `score`) from ProductSummary at runtime |
| Platform badge uses inline `style` not Tailwind class | Color comes from JS object at runtime — can't be a static class |
| ScoreBreakdown appends `99` hex to color for 60% opacity | `${bar.color}99` is simpler than a separate opacity layer |
| ProductCard is server component (no `"use client"`) | Purely presentational — no hooks or state needed |
| `ArrowLeftRight` from lucide-react for BridgeConnector | Matches the spec's double-arrow icon without custom SVG |
| Frontend page route `/product/[id]` (singular) | URL slug convention for viewing one resource; API uses plural `/products/` per REST |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `product.name` doesn't exist on types | Changed to `product.title` |
| `import { match } from "assert"` auto-inserted | Removed — VS Code autocomplete artifact |
| `defalultValue` typo in SearchBar | Fixed to `defaultValue` |
| `debouncedSearch` missing setTimeout body | Added `debounceRef.current = setTimeout(() => onSearch(query), 400)` |
| `SearchResult` missing `platform` field | Added `platform: string` to SearchResult interface |
| ScoreBreakdown inner div missing `h-full rounded-full` | Added classes — without them, fill bar has zero height |
| ScoreBreakdown `/ >` syntax error | Fixed to `/>` |

### What's Left Open

- **BridgeCardFull.tsx** — empty stub, next to implement
- **BridgeCardCompact.tsx** — empty stub
- **bridge/index.ts** — barrel export file not yet created
- **Phase 3D** — Skeleton.tsx, ImageWithFallback.tsx
- **Phases 4-5** — Pages + polish

RESUME POINT: Start Phase 3C.8 BridgeCardFull (the big composition component), then BridgeCardCompact, index.ts barrel, then 3D utilities.

---

## Session Log: 2026-02-25 — MID-SESSION SAVE — API Smoke Tests + Frontend Phase 1-3A

### What Was Accomplished

**API Smoke Tests (17/17 passing):**
- Wrote `tests/integration/test_api_smoke.py` with 17 smoke tests covering all 14 API endpoints
- Fixed `httpx` 0.28 incompatibility with `starlette` 0.27 — downgraded to `httpx==0.27.0`
- Fixed `test_search_image` — 1x1 PNG caused CLIP channel confusion; replaced with 4x4 PIL-generated PNG
- All 17 tests green

**Frontend Phase 1 — Design System Alignment (COMPLETE):**
- **1.1** Swapped Playfair Display → Cormorant Garamond in `layout.tsx`, fixed CSS variable to `--font-serif`
- **1.2** Replaced entire Tailwind color palette: `vintage.*` → flat tokens (terracotta, gold, sage, cream, charcoal, etc.) + custom shadows + border radii
- **1.3** Populated `theme.ts` with PLATFORM_COLORS, PLATFORM_NAMES, SCORE_COLORS, scoreColorByValue()
- **1.4** Updated `globals.css`: `vintage-*` classes → new tokens, added gold scrollbar styles
- **1.5** Updated all 4 UI primitives (Button, Card, Badge, Input) to new color tokens
- **1.6** Added `images.remotePatterns` in `next.config.ts` for Met Museum, Smithsonian, Etsy CDNs
- Also fixed `tailwind.config.ts` line 41: `var(--font-cormorant)` → `var(--font-serif)`
- `npm run build` passes clean

**Frontend Phase 2 — Types & API Client (COMPLETE):**
- **2.1** Reconciled Product type: removed dead fields (color, season, year, period, pattern), added Fashionpedia taxonomy (12 fields)
- **2.2** Added 6 bridge interfaces: ProductSummary, BridgeResult, BridgeListResponse, BridgeTypeStats, ScoreHistogramBucket, BridgeStats
- **2.3** Added 8 API functions: getProductBridges, getModernEchoes, getStyleAncestry, getStyleSiblings, getTopBridges, getBridgeStats, getBridgeBetween, getBridgeDetail
- **2.4** Added DEFAULT_BRIDGE_LIMIT and FEATURED_BRIDGES_LIMIT constants
- `npx tsc --noEmit` passes with zero errors

**Frontend Phase 3A — Layout Components (COMPLETE):**
- **3A.1** Header: sticky, frosted glass, mobile hamburger / desktop nav links, `"use client"` for menu state
- **3A.2** Footer: 3-column grid (mobile: stacked), brand + nav + tech stack + copyright
- **3A.3** Navigation: skipped — Header already handles mobile nav
- **3A.4** Root layout: added Header/Footer imports, fixed `--font-serif` variable, updated metadata title/description
- `npm run build` passes clean

### Files Modified This Session

| File | Changes |
|------|---------|
| `tests/integration/test_api_smoke.py` | Wrote 17 smoke tests, fixed image test |
| `vv-web/src/app/layout.tsx` | Font swap, Header/Footer, metadata, removed old color classes |
| `vv-web/tailwind.config.ts` | Full color palette replacement, shadows, border radii, font-serif variable |
| `vv-web/src/styles/theme.ts` | Populated with platform colors, score colors, scoreColorByValue |
| `vv-web/src/app/globals.css` | New color tokens, scrollbar styles |
| `vv-web/src/components/ui/Button.tsx` | vintage-* → terracotta/cream/border |
| `vv-web/src/components/ui/Card.tsx` | vintage-* → warm-white/border/muted |
| `vv-web/src/components/ui/Badge.tsx` | vintage-* → terracotta/sage/border |
| `vv-web/src/components/ui/Input.tsx` | vintage-* → border/muted/terracotta |
| `vv-web/next.config.ts` | Added remotePatterns for museum CDNs |
| `vv-web/src/types/index.ts` | Reconciled Product, added 6 bridge interfaces |
| `vv-web/src/lib/api.ts` | Added 8 bridge API functions |
| `vv-web/src/lib/constants.ts` | Added bridge limit constants |
| `vv-web/src/components/layout/Header.tsx` | Populated: sticky header with mobile/desktop nav |
| `vv-web/src/components/layout/Footer.tsx` | Populated: 3-column responsive footer |

### Decisions Made

| Decision | Why |
|----------|-----|
| Downgrade httpx to 0.27.0 | httpx 0.28 removed `app` kwarg that starlette 0.27 TestClient needs |
| 4x4 PIL PNG instead of hand-crafted 1x1 | CLIP misinterprets 1x1x3 as 1-channel image |
| Skip Navigation.tsx | Header already handles mobile nav dropdown; can upgrade to slide-in later |
| Flat color tokens (not nested) | `bg-terracotta` is shorter than `bg-vintage-burgundy` and matches Figma tokens |
| `--font-serif` not `--font-cormorant` | Standard convention; Tailwind's `font-serif` maps directly |

### Problems Hit

| Problem | Fix |
|---------|-----|
| `httpx` 0.28 broke TestClient | `pip install httpx==0.27.0` |
| CLIP ValueError on 1x1 PNG | Used PIL to generate 4x4 RGB PNG |
| `--font-cormorant` in layout vs `--font-serif` in tailwind config | Standardized on `--font-serif` everywhere |
| `bg-vintage-cream` still in layout.tsx body | Removed (already set in globals.css) |

RESUME POINT: Start implementing Phase 3B — search components (SearchBar.tsx, ImageUpload.tsx, ProductCard.tsx)

---

## Session Log: 2026-02-23 — Figma Design Capture + Frontend Implementation Plan

### What Was Accomplished

**Figma Design Population:**
- Created 5 standalone HTML pages in `figma-pages/` that visually match the design handoff (`docs/FIGMA_DESIGN_HANDOFF.md`)
- Served pages via Python HTTP server on port 8888
- Captured all 5 into Figma file `3AXCKfChPdugtQOQ5629BP` using `generate_figma_design` MCP tool
- Files created:
  - `figma-pages/design-system.html` — Color swatches, typography scale, spacing, radii, shadows
  - `figma-pages/components.html` — All UI components (badges, cards, search, buttons, layout)
  - `figma-pages/home-desktop.html` — Full home page at 1440px
  - `figma-pages/search-results-desktop.html` — Search results with 4-col product grid
  - `figma-pages/product-detail-desktop.html` — Product hero + bridge sections

**Frontend Implementation Plan:**
- Explored all 14 FastAPI backend endpoints and Pydantic schemas
- Explored all existing Next.js frontend files (types, API client, components, stubs)
- Created comprehensive mobile-first implementation plan: `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md`
- Plan covers 5 phases, 41 files (13 modify, 6 populate, 22 create), with checklists and deliverables
- **User will implement this plan themselves** — not Claude

### Decisions Made

| Decision | Why |
|----------|-----|
| Mobile-first design (390px base) | Primary audience is Gen Z / younger Millennials on phones |
| Cormorant Garamond replaces Playfair Display | Per Figma design handoff — more editorial, vintage-appropriate |
| New color tokens replace `vintage.*` namespace | Handoff specifies specific palette (terracotta, gold, sage, platform colors, score colors) |
| BridgeCardFull: stacked on mobile, side-by-side on desktop | Images need to be large enough to see detail on small screens |
| BridgeCardCompact: 240px mobile, 280px desktop | 240px allows peek effect in carousel (1.5 cards visible at 390px) |
| No code implementation by Claude | User explicitly said "i was going to do the implementation. i just need the plan" |

### Files Created This Session

| File | Purpose |
|------|---------|
| `figma-pages/design-system.html` | Design system showcase for Figma capture |
| `figma-pages/components.html` | Component library showcase for Figma capture |
| `figma-pages/home-desktop.html` | Home page mock for Figma capture |
| `figma-pages/search-results-desktop.html` | Search results mock for Figma capture |
| `figma-pages/product-detail-desktop.html` | Product detail mock for Figma capture |
| `docs/plans/FRONTEND_IMPLEMENTATION_PLAN.md` | 5-phase mobile-first frontend implementation plan |

### Files Read But Not Modified

- `docs/FIGMA_DESIGN_HANDOFF.md` — Design tokens, components, page layouts
- `vv-web/src/lib/api.ts` — 4 existing API functions
- `vv-web/src/types/index.ts` — Product, SearchFilters, SearchResult types
- `vv-web/src/app/layout.tsx` — Playfair Display + Inter fonts
- `vv-web/tailwind.config.ts` — vintage.* color palette
- `vv-web/src/app/globals.css` — Base styles with vintage-* classes
- `vv-web/next.config.ts` — Empty config
- All existing component stubs in `vv-web/src/components/`

### What's Left Open

- **Frontend implementation** — User is doing this themselves using the plan doc
- **Figma refinement** — User said they're still refining the design
- **Bridge narratives** — Still 22/7,324 generated (needs `analysis/generate_narratives.py` run)
- **API smoke testing** — Endpoints still not tested against live services

---

## Session Log: 2026-02-21 + 2026-02-22 — FastAPI Backend Implementation

### What Was Accomplished

**Schemas (Day 1 — Feb 21):**
- Created `api/schemas/product.py` — `ProductSummary` (13 fields), `ProductDetail` (34 fields), `_parse_json_list()` helper
- Rewrote `api/schemas/search.py` — fixed syntax bugs, created `SearchFilters`, `TextSearchRequest`, `ImageSearchRequest`, `SearchResult`, `SearchResponse`
- Created `api/schemas/bridge.py` — `BridgeResult`, `BridgeListResponse`, `BridgeTypeStats`, `ScoreHistogramBucket`, `BridgeStats`
- Created `api/schemas/filters.py` — `FilterOptions` (8 list fields)
- Created `api/schemas/__init__.py` — re-exports all 13 schemas
- Fixed `api/__init__.py` — replaced broken `=` with empty file
- Fixed `tests/unit/test_bridge_logic.py` — updated stale import `scripts.analysis.compute_bridges` → `analysis.compute_bridges`

**Routers (Day 2 — Feb 22):**
- Wrote `api/routers/products.py` — 5 endpoints (get_product, product_bridges, modern_echoes, style_ancestry, style_siblings)
- Wrote `api/routers/bridges.py` — 4 endpoints (top_bridges, bridge_stats, bridge_between, bridge_detail)
- Wrote `api/routers/filters.py` — 1 endpoint (get_filters with 8 SELECT DISTINCT queries)
- Wrote `api/routers/search.py` — 2 endpoints (search_text with Qdrant filtering, search_image with base64 decode + CLIP)
- Wrote `api/dependencies.py` — `get_vector_db()` and `get_embedding_generator()` with `@lru_cache`
- Wrote `api/main.py` — FastAPI app wiring (CORS, 4 router includes, health endpoint)

**Infrastructure (Day 2 — Feb 22):**
- Modified `storage/vector_db.py` — added `query_filter` param to `search_similar()` for native Qdrant filtering
- Created `embeddings/scripts/backfill_image_payloads.py` — backfilled `vintage_images` payloads from 12 → 28 fields using `set_payload()`
- Modified `embeddings/scripts/generate_image_embeddings.py` — imports `build_full_payload()` so future runs include full payload
- Ran backfill script — both Qdrant collections now have identical payload shapes

**Documentation (Day 2 — Feb 22):**
- Created `docs/blog_first_api.md` — dev diary covering both days

### Decisions Made

| Decision | Why |
|----------|-----|
| Aligned SearchFilters and FilterOptions to 8 identical fields | 1:1 mapping means filter dropdowns match exactly what search accepts |
| Removed 5 dead columns from all schemas (color, season, year, pattern, period) | 0/866 populated, superseded by enrichment fields |
| Native Qdrant filtering (Option B) over Python post-filtering | Cleaner, faster — Qdrant prunes before vector comparison |
| Backfilled vintage_images payloads instead of Postgres join in image search | Eliminates per-request DB join; both collections now identical |
| No lifespan function in main.py | Qdrant/embedding singletons handled by lru_cache in dependencies.py |
| No /api/v1 prefix on routes | Frontend calls endpoints directly (http://localhost:8000/search/text) |

### Problems Encountered

| Problem | Resolution |
|---------|------------|
| `api/__init__.py` contained just `=` | Replaced with empty file |
| `api/schemas/search.py` had syntax bugs (`query = str`) | Rewrote from scratch |
| `tests/unit/test_bridge_logic.py` stale import path | Fixed `scripts.analysis.compute_bridges` → `analysis.compute_bridges` |
| `vintage_images` had 12 payload fields vs 28 in `vintage_text` | Wrote backfill script using `set_payload()` — no re-embedding needed |
| Route ordering — `/{bridge_id}` would match `/top` | Put `/top`, `/stats`, `/between/{a}/{b}` before `/{bridge_id}` |
| Function name shadowing in bridges router | Renamed endpoint functions (e.g., `top_bridges` not `get_top_bridges`) |
| bridge_queries functions use keyword-only args (`*`) | Must pass named params, not positional |

### What's Left Open
- Tests not yet run against the live API (user was running tests at end of session)
- `embedded_at` column still only set for 200/866 products (tracking gap, not data gap)
- 22/7,324 bridge narratives generated (need to run `generate_narratives.py`)
- Frontend search components are still stubs

---

## Environment Setup

### Prerequisites

- Python 3.13+ with venv
- Node.js 25+ with npm
- Supabase project (PostgreSQL + pgvector + Storage)
- Anthropic API key (for Claude enrichment/narratives)

### Python Environment

```bash
# Always use the venv — never system python
source venv/bin/activate
# Or reference directly:
venv/bin/python <script>
venv/bin/pytest tests/
```

### Environment Variables

File: `.env` (exists in project root)

```
DATABASE_URL=postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_STORAGE_BUCKET=product-images
ANTHROPIC_API_KEY=sk-ant-...  # Required for enrichment/narratives
```

### Frontend

```bash
cd vv-web
npm install    # First time only
npm run dev    # http://localhost:3000
```

### Run Tests

```bash
venv/bin/pytest tests/                    # Full suite
venv/bin/pytest tests/unit/               # Unit only (no DB needed)
venv/bin/pytest tests/integration/        # Needs Supabase PostgreSQL
venv/bin/pytest tests/data_integrity/     # Needs Supabase PostgreSQL
venv/bin/pytest tests/search_quality/     # Needs Supabase PostgreSQL
venv/bin/pytest -m "not slow"             # Skip slow tests
```

---

## Current State (2026-03-12)

### What Works

- **4,234 products** in Supabase PostgreSQL across 4 platforms (va_museum 1,856, fashionpedia 1,000, smithsonian 778, met_museum 600)
- **ALL 4,234 enriched** by Claude Sonnet 4 with 23 structured fields + core_vibes/bridge_vibes
- **ALL 4,234 text embeddings** + **ALL 4,234 image embeddings** in pgvector columns (HNSW indexed)
- **15,619 bridges computed** — 4 passes complete with rebalanced weights + participation caps
- **Supabase Pro** — upgraded from free tier
- **6-dimensional bridge classification** designed and coded (pending classifier run)
- **Bridge query library** (`analysis/bridge_queries.py`) — supports 6 new dimension filters + `shared_function`
- **FastAPI backend** — 16 endpoints across 5 routers, 16 Pydantic schemas, pgvector search
- **Social Function Explorer API** — `/explore/functions` + `/explore/functions/{fn}`
- **Frontend COMPLETE** — Next.js 16 app: design system, layout, search, bridge components, 4 pages, polish
- **Supabase migration COMPLETE** — PostgreSQL + pgvector + Supabase Storage (all 20 steps done)

### What's In Progress

- **Opposition composite sort score** — current sort by structural_score rewards generic garments; implementing composite that rewards temporal distance + cross-cultural fields

### What's Incomplete

- **Opposition sort score** — implement composite formula, re-run Pass 2
- **Pass 3 group cap** — needs same 100-product cap as Pass 4
- **Classifier run** — `tools/analysis/classify_bridge_dimensions.py`
- **Narrative generation** — `tools/analysis/generate_narratives.py` (with mode hints)
- **Frontend updates** — social function explorer page, bridge card connection mode badges, bridge filtering UI
- **Image search frontend** — Backend API exists, frontend not yet implemented

### What's Not Started

- **Deployment** — Supabase + Railway + Vercel
- **Knowledge Graph** — plans written, prerequisites partly done

---

## Key File Locations

### Core Data Layer
| File | Purpose |
|------|---------|
| [storage/database.py](../storage/database.py) | Product + StyleBridge ORM models (6 new classification columns) |
| [storage/vector_search.py](../storage/vector_search.py) | pgvector search module |
| [analysis/bridge_queries.py](../analysis/bridge_queries.py) | Bridge query functions (6 dimension filters + shared_function) |
| [analysis/product_queries.py](../analysis/product_queries.py) | Social function query helpers (jsonb containment) |

### Intelligence Layer
| File | Purpose |
|------|---------|
| [enrichment/claude.py](../enrichment/claude.py) | ClaudeEnricher (sync + async, enrichment + narratives with mode hints) |
| [enrichment/fashionpedia_taxonomy.py](../enrichment/fashionpedia_taxonomy.py) | Full Fashionpedia ontology (27 cat, 294 attr) |
| [embeddings/generator.py](../embeddings/generator.py) | EmbeddingGenerator (text + image) |
| [embeddings/models.py](../embeddings/models.py) | Singleton model loader (MiniLM + CLIP) |

### Scripts
| File | Purpose |
|------|---------|
| [analysis/compute_bridges.py](../analysis/compute_bridges.py) | 2-pass bridge discovery (open + cross-culture) |
| [analysis/generate_narratives.py](../analysis/generate_narratives.py) | Async narrative generation (with connection_mode hints) |
| [scripts/classify_bridge_dimensions.py](../scripts/classify_bridge_dimensions.py) | 6-dimension bridge classifier |

### API
| File | Purpose | Endpoints |
|------|---------|-----------|
| [api/main.py](../api/main.py) | FastAPI app entry point | CORS, 5 router includes, /health |
| [api/routers/search.py](../api/routers/search.py) | Search endpoints | POST /search/text, POST /search/image |
| [api/routers/products.py](../api/routers/products.py) | Product endpoints | GET /products/{id}, /bridges, /modern-echoes, /style-ancestry, /style-siblings |
| [api/routers/bridges.py](../api/routers/bridges.py) | Bridge endpoints | GET /bridges/top (+ 6 dimension filters + shared_function), /stats, /between/{a}/{b}, /{id} |
| [api/routers/explore.py](../api/routers/explore.py) | Explore endpoints | GET /explore/functions, /explore/functions/{fn} |
| [api/routers/filters.py](../api/routers/filters.py) | Filter endpoint | GET /filters |
| [api/schemas/](../api/schemas/) | Pydantic models | 16 schemas across 5 files |

### Frontend
| File | Purpose |
|------|---------|
| [vv-web/src/app/page.tsx](../vv-web/src/app/page.tsx) | Homepage (hero + how it works) |
| [vv-web/src/app/layout.tsx](../vv-web/src/app/layout.tsx) | Root layout (fonts, metadata) |
| [vv-web/src/lib/api.ts](../vv-web/src/lib/api.ts) | API client (12 functions) |
| [vv-web/src/types/index.ts](../vv-web/src/types/index.ts) | TypeScript types |

---

## Known Gotchas

1. **Always use `venv/bin/python`** — system Python won't have the packages.

2. **`embedded_at` is misleading** — only 200/4,234 products have this timestamp, but all 4,234 have pgvector embeddings. Don't filter by `embedded_at IS NOT NULL` to find "embedded" products.

3. **Bridge canonical ordering** — `source_id < target_id` always. When looking up a bridge between products A and B, use `min(A,B)` as source and `max(A,B)` as target.

4. **`bridge_narrative` not `narrative`** — The column is `bridge_narrative`. Earlier code/docs may reference just `narrative`.

5. **Embedding model loading is slow** — First import of `embeddings.models` downloads ~500MB of model weights. Subsequent loads are cached.

6. **JSON fields in Postgres** — `style_tags`, `colors`, `textile_finishing`, `garment_parts`, `decorations`, `image_urls` are all `Text` columns storing JSON strings, not JSONB. Parse with `json.loads()`. But `social_function`, `construction_technique`, `motif_family` are `ARRAY(String)` — no parsing needed.

7. **Score distribution is tight** — Fashion corpus items cluster closely in embedding space. The minimum bridge score threshold is 0.30. Don't expect scores as spread out as general-purpose search.

8. **`generate_bridge_narrative_async` max_tokens=200** — Was 100 originally, caused truncation. Sync version has been deleted; only async remains.

9. **Scripts live in `tools/`** — All runnable scripts are under `tools/` (analysis, enrichment, embeddings, data_loading, data_quality, db_utils, migration). Library code stays in package dirs (api/, storage/, embeddings/, enrichment/, analysis/).

10. **5 test errors in `test_database_model.py`** — SQLite ARRAY incompatibility. Not blocking; separate issue from the main test suite.

11. **Composite SQL uses literal_column, not text()** — `_COMPOSITE_SQL` in `bridge_queries.py` uses `literal_column()` which supports `.desc()` and comparison operators. `_COMPOSITE_DESC` uses `text()` for ORDER BY. Don't mix them up.

12. **Classifier path updated** — `tools/analysis/classify_bridge_dimensions.py` (was `tools/data_quality/`). Imports `classify_temporal_type` from `tools/analysis/compute_bridges`.

---

## Priorities for Next Session

### Immediate (Bridge Pipeline Completion)

1. **Check if `compute_bridges.py --rebuild`** finished (was still running end of last session)
2. **Run classifier** — `venv/bin/python tools/analysis/classify_bridge_dimensions.py` — populate 6 dimension columns
3. **Generate narratives** — `venv/bin/python tools/analysis/generate_narratives.py` — new narratives use full classification context
4. **Review 20-30 sample narratives** across connection modes (contrast, resonance, affinity) — check quality

### Project Reorganization (Remaining)

5. **Phase 3: Docs cleanup** — rename `_docs/old/` → `_docs/archive/`, move completed plans
6. **Phase 4: Deployment files** — Dockerfile, .dockerignore, .env.example, CORS tightening
7. **Phase 5: Verify** — API starts, scripts run from new locations, tests pass, frontend builds

### Frontend Updates

8. **Social Function Explorer page** — `/explore/functions` (landing + detail views)
9. **Bridge card enhancements** — connection mode badges (contrast/resonance/affinity), axis pills
10. **Bridge filtering UI** — dimension toggles on bridges/top view
11. **Frontend TypeScript types** — add new bridge fields + explore API types

### After Pipeline + Reorg Complete

12. **Deployment** — Supabase + Railway + Vercel
13. **Knowledge Graph implementation** — plans in `_docs/plans/KG_IMPLEMENTATION/`
14. **Image search frontend** — Connect `searchByImage` API to frontend UI
