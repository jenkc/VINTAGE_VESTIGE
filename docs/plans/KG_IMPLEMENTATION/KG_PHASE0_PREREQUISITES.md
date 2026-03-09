# KG_PHASE0_PREREQUISITES.md
# Phase 0 — Prerequisites

**Status:** ⏳ Active — Bridge recomputation in progress
**Blocks:** Everything. Do not start schema design until all items here are complete.
**Last Updated:** 2026-03-09

---

## What's Already Done (Do Not Redo)

| Item | Status | Notes |
|---|---|---|
| Frontend components (SearchBar, ProductCard, ImageUpload) | ✅ Done | All 5 phases complete |
| Product detail page with bridge panel | ✅ Done | `/product/[id]` route live |
| Qdrant → pgvector migration | ✅ Done | Steps 1–20 complete |
| Image migration to Supabase Storage | ✅ Done | All 4,234 products |
| Frontend build passes (tsc + npm run build) | ✅ Done | All 4 routes compile clean |
| Supabase migration Steps 12–20 | ✅ Done | Zero Qdrant references in codebase |
| Data growth to 4,234 products | ✅ Done | All enriched + embedded |
| Enrichment pipeline (Claude Sonnet 4) | ✅ Done | All 4,234 products enriched |
| Embedding pipeline (text + image) | ✅ Done | All products re-embedded with enriched_text |
| Pooler resilience (`ResilientSession`) | ✅ Done | Auto-retry on connection drops in `database.py` |

Do not include these in any "remaining work" list. They are done.

---

## Current Data

- **4,234 products** across 4 platforms:
  - va_museum: 1,856
  - fashionpedia: 1,000
  - smithsonian: 778
  - met_museum: 600
- **All enriched** with Fashionpedia taxonomy, cross-cultural fields, core_vibes, bridge_vibes
- **All embedded** with text (384d) + image (512d) vectors in pgvector
- **Bridge system**: 4-pass discovery (similarity, opposition, function, structural)

---

## What's Still Required Before KG Work Begins

### 1. Bridge Recomputation (IN PROGRESS)

Running `compute_bridges.py --rebuild` on full 4,234-product dataset.

Four discovery passes:
1. **Similarity** — pgvector proximity (affinity/resonance bridges)
2. **Opposition** — opposing core_vibes cross-join (contrast bridges)
3. **Shared Purpose** — shared social_function grouping (cross-cultural bridges)
4. **Parallel Form** — shared (category, silhouette) grouping (independent invention bridges)

- [ ] Full `--rebuild` run completes without errors
- [ ] Bridge count recorded
- [ ] Bridge type distribution reviewed

### 2. Narrative Generation

After bridges are computed, generate AI narratives for all bridges.

```bash
venv/bin/python analysis/generate_narratives.py
```

- [ ] All bridges have `bridge_narrative` populated
- [ ] Spot-check narrative quality (not truncated, contextually relevant)

### 3. Bridge Classification

Populate multi-dimensional classification columns on `style_bridges`:
- `temporal_type` (transmission | continuation | contemporary)
- `crossing_type` (same_context | cross_category | cross_culture | cross_category_culture)
- `connection_mode` (resonance | contrast | affinity)
- `primary_axis` / `secondary_axis` (volume | ornament | body | register)
- `contrast_pair` (e.g. "Exaggerated Volume <-> Column Minimalism")

```bash
venv/bin/python scripts/classify_bridge_dimensions.py --dry-run   # preview
venv/bin/python scripts/classify_bridge_dimensions.py             # commit
```

- [ ] All bridges have classification dimensions populated
- [ ] Distribution review: connection_mode breakdown looks reasonable
- [ ] API schema updated: `BridgeResult` includes classification fields
- [ ] Frontend updated: classification shown on bridge cards

### 4. Deploy (Railway + Vercel)

A live URL is required before adding more infrastructure.

- [ ] FastAPI deployed to Railway
  - [ ] Environment variables set: `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`
  - [ ] Health check: `GET /health` → 200
  - [ ] All endpoints reachable from public URL
- [ ] Next.js deployed to Vercel
  - [ ] `NEXT_PUBLIC_API_URL` set to Railway backend URL
  - [ ] All routes load without errors
  - [ ] Images load from Supabase Storage CDN
- [ ] End-to-end smoke test: search returns results, product detail shows bridges

---

## Exit Criteria

Phase 0 is complete when every item below is verified:

```
✅ 4,234 products enriched + embedded in Supabase

✅ Bridges recomputed on full dataset (4-pass discovery)

✅ Bridge narratives generated for all bridges

✅ Bridge classification dimensions populated

✅ Deployed: Railway URL + Vercel URL both live
```

Do not start Phase 1 (Schema Design) until all items are checked.
