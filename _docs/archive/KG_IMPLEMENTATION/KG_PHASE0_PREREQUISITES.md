# KG_PHASE0_PREREQUISITES.md
# Phase 0 — Prerequisites

**Status:** ✅ Complete — All prerequisites met as of 2026-03-13
**Blocks:** Everything. Do not start schema design until all items here are complete.
**Last Updated:** 2026-03-13

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

### 1. Bridge Recomputation ✅ DONE (2026-03-13)

Four discovery passes complete. **14,223 bridges** computed on full 4,234-product dataset.

- Pass 1 (similarity): 4,202 cross_vibe + 2,744 transmission + 1,714 echo + 487 continuation
- Pass 2 (opposition): 1,322 bridges
- Pass 3 (shared purpose): 2,247 bridges
- Pass 4 (structural): 1,483 bridges

Enhancements: opposition composite sort score, near-duplicate detection, same-era vibe gate, 150-product group cap on Pass 3.

- [x] Full `--rebuild` run completes without errors
- [x] Bridge count recorded: 14,223
- [x] Bridge type distribution reviewed

### 2. Narrative Generation ✅ DONE (2026-03-13)

**ALL 14,223 bridges have `bridge_narrative`** populated. Mode-specific system prompts, classification context (temporal_type, crossing_type, primary_axis), vibe data, varied closings.

- [x] All bridges have `bridge_narrative` populated
- [x] Spot-check narrative quality (not truncated, contextually relevant)

### 3. Bridge Classification ✅ DONE (2026-03-13)

6-dimensional classification complete. **14,194/14,223** classified (24 have null temporal_type — products with no era/decade data).

- connection_mode: affinity 10,886 / contrast 3,314 / resonance 23
- crossing_type: cross_culture 6,277 / same_context 4,111 / cross_category_culture 2,430 / cross_category 1,405
- API schema: `BridgeResult` includes all 6 classification fields ✓
- Frontend: bridge cards can display connection_mode (frontend update planned but not blocking KG)

- [x] All bridges have classification dimensions populated
- [x] Distribution review: connection_mode breakdown looks reasonable
- [x] API schema updated: `BridgeResult` includes classification fields
- [ ] Frontend updated: classification shown on bridge cards *(planned, not yet implemented)*

### 4. Deploy (Railway + Vercel) — NEXT STEP

A live URL is required before adding more infrastructure. All data prerequisites are complete.

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
✅ 4,234 products enriched + embedded in Supabase (done 2026-03-07)

✅ Bridges recomputed on full dataset (4-pass discovery, 14,223 bridges) (done 2026-03-13)

✅ Bridge narratives generated for all bridges (14,223/14,223) (done 2026-03-13)

✅ Bridge classification dimensions populated (14,194/14,223) (done 2026-03-13)

⏳ Deployed: Railway URL + Vercel URL both live — NEXT STEP
```

Do not start Phase 1 (Schema Design) until all items are checked.
