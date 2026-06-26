# Vintage Vestige — Knowledge Graph Implementation
## Master Index

**Project:** Vintage Vestige Knowledge Graph  
**Version:** 2.0 — Updated for current project state  
**Created:** March 2026  
**Last Revised:** March 2026  
**Status:** Waiting on Supabase migration completion (Steps 12–20)

---

## Document Set

| Document | Purpose | Audience |
|---|---|---|
| `KG_IMPLEMENTATION_INDEX.md` | This file — master index and overview | All |
| `KG_MASTER_PLAN.md` | Full implementation plan, all phases | Technical lead |
| `KG_PHASE0_PREREQUISITES.md` | Finish Supabase migration before KG work begins | Dev |
| `KG_PHASE1_SCHEMA_DESIGN.md` | Node/edge schema, property definitions | Technical lead |
| `KG_PHASE2_AWS_SETUP.md` | Neptune + S3 + IAM setup | Dev/ops |
| `KG_PHASE3_DESIGN_ELEMENTS.md` | Design element extraction + Getty AAT mapping | Dev + domain |
| `KG_PHASE4_EXPORT_SCRIPTS.md` | Supabase → Neptune CSV export pipeline | Dev |
| `KG_PHASE5_BULK_LOAD.md` | S3 upload + Neptune loader + validation | Dev |
| `KG_PHASE6_API_LAYER.md` | FastAPI graph endpoints + Neptune client | Dev |
| `KG_PHASE7_FRONTEND.md` | Influence chain + movement explorer UI | Dev/design |
| `KG_DECISIONS.md` | Architecture decisions log | All |
| `KG_SUCCESS_CRITERIA.md` | Definition of done for each phase | All |

**Note:** Phase 8 (Supabase Coexistence) has been removed. As of 2026-03-04,
Supabase is already the production database with pgvector columns on `products`.
The dual-database pattern (Supabase for relational/vector, Neptune for graph
traversal) is the current architecture, not future work. See KGD-009 for
the rationale for introducing Neptune as a deliberate second database.

---

## Foundation: What the Supabase Migration Delivered

Before the KG plan was written, a significant architectural consolidation happened.
Understanding this is essential context for everything that follows.

**Completed as of 2026-03-04 (Steps 1–11 of 20):**

| What changed | Detail |
|---|---|
| Qdrant eliminated | All vector storage consolidated into pgvector on `products` table |
| Embeddings on the row | `text_embedding vector(384)` + `image_embedding vector(512)` are columns on `products` — no separate table or DB |
| Images in Supabase Storage | 4,234 products migrated from base64 blobs → CDN URLs |
| Single operational database | Supabase PostgreSQL only; `storage/vector_search.py` replaced `storage/vector_db.py` |
| Search layer updated | `api/routers/search.py` rewrote to pgvector via `VectorSearch(db: Session)` |

**Steps 12–20 still pending** (this is the Phase 0 blocker):

| Step | File | What changes |
|---|---|---|
| 12 | `analysis/compute_bridges.py` | Swap Qdrant for pgvector queries — largest remaining file |
| 13 | `embeddings/generator.py` | Handle Supabase Storage URLs instead of base64 |
| 14 | `enrichment/claude.py` | Update for Supabase |
| 15 | enrichment scripts | Update |
| 16 | `storage/vector_db.py` + others | Delete obsolete files |
| 17 | `vv-web/next.config.ts` | Update image domains to Supabase Storage |
| 18 | tests | Update all references to Qdrant |
| 19–20 | — | Verify + cleanup |

Neptune is a deliberate second database being added *after* consolidation —
for graph traversal specifically. That's categorically different from why Qdrant
was eliminated (operational complexity without unique capability). See KGD-009.

---

## Executive Summary

The knowledge graph implementation promotes bridges from flat Supabase junction
table rows to first-class graph entities in Amazon Neptune. This makes the
following capabilities possible for the first time:

1. **Multi-step bridge traversal** — trace a silhouette argument 3+ generations
   across centuries in a single graph query; the specific feature that makes
   Neptune necessary and worth the operational cost of a second database
2. **Design movement emergence** — cluster bridges through shared design elements
   to surface aesthetic movements from evidence rather than assertion
3. **Cross-institutional queries** — connect Met Museum and Smithsonian pieces
   in a single traversal; impossible in any single institution's own database
4. **IIT substrate** — gives Integrated Information Theory a proper graph to
   measure; Φ scores over connected graph entities are more meaningful than
   Φ over flat search results

---

## Sequencing Decision

**The KG is not the next thing. It's the right thing at the right time.**

| Immediate priority | Why |
|---|---|
| Finish Supabase migration Steps 12–20 | KG exports read from Supabase — source must be complete |
| Data growth to ~1,500 enriched products | Richer chains; required before deploy anyway |
| Deploy (Railway + Vercel) | Live URL before building more infrastructure |
| `semantic_type` column on `style_bridges` | 2-hour win; immediate UI payoff, zero infrastructure cost |
| Build multi-step bridge UI concept | Validate the feature before building Neptune |
| Neptune when multi-step bridge UI is ready to ship | Neptune is load-bearing at this point |
| IIT after KG | Φ over a graph > Φ over flat rows |

**Full sequence:**
```
NOW ──────── Finish Supabase migration Steps 12-20
             └─ compute_bridges.py is the critical path

+1 week ──── Data growth to ~1,500 enriched products

+2 weeks ─── Deploy (Railway + Vercel)

QUICK WIN ── semantic_type column on style_bridges (~2 hours)
             └─ Classify from existing data; no infrastructure needed

TRIGGER ───── Start KG when multi-step bridge UI is planned
              └─ Schema design (1 week, no code)
              └─ AWS Setup + Design Elements (parallel, 1 week)
              └─ Export Scripts (1 week)
              └─ Bulk Load (2-3 days)
              └─ API Layer (1 week)
              └─ Frontend Graph Features (1 week)

AFTER KG ─── IIT Integration
PARALLEL ─── Academic paper
```

---

## Three Validation Queries

The KG implementation is complete when all three execute against live Neptune.

### Query 1 — Multi-Step Influence Chain
```cypher
MATCH path = (modern:Garment {platform: 'fashionpedia'})
  -[:CONNECTED_VIA]->(b1:Bridge {semantic_type: 'SILHOUETTE_TRANSMISSION'})
  -[:CONNECTS]->(g2:Garment)
  -[:CONNECTED_VIA]->(b2:Bridge {semantic_type: 'SILHOUETTE_TRANSMISSION'})
  -[:CONNECTS]->(g3:Garment {platform: 'met_museum'})
RETURN modern.title, b1.narrative, g2.title, b2.narrative, g3.title
LIMIT 5
```

### Query 2 — Design Movement
```cypher
MATCH (de:DesignElement {name: 'empire waistline'})
  <-[:ARGUES_THROUGH]-(b:Bridge)
  -[:CONNECTS]->(g:Garment)
  -[:FROM_ERA]->(era:Era)
WITH de, count(DISTINCT era) as era_count, collect(DISTINCT era.name) as eras,
     count(b) as bridge_count
WHERE era_count >= 3
RETURN de.name, era_count, eras, bridge_count
```

### Query 3 — Cross-Institutional Bridge
```cypher
MATCH (g1:Garment {platform: 'met_museum'})
  -[:CONNECTED_VIA]->(b:Bridge)
  -[:CONNECTS]->(g2:Garment {platform: 'smithsonian'})
WHERE b.score > 0.7
RETURN g1.title, b.narrative, g2.title, b.score
ORDER BY b.score DESC
LIMIT 10
```

---

## Quick Reference — Key Numbers

| Metric | Value |
|---|---|
| Total products in Supabase | 4,234 |
| Products with embeddings (current) | 866 |
| Target enriched products at KG time | ~1,500 |
| Current bridges | 7,324 |
| Bridge narratives generated | 22/7,324 |
| Cross-platform bridges | 1,134 (15.5%) |
| Cross-era bridges | 1,076 (14.7%) |
| Expected DesignElement nodes | ~150–300 |
| Expected KG Garment nodes | ~1,500 |
| Expected KG Bridge nodes | ~10,000–15,000 (post data growth + recompute) |
| Expected KG edge total | ~50,000–80,000 |
| Estimated Neptune cost | ~$10–30/month serverless |
| Estimated KG implementation time | 6 weeks from start |

---

## Current State Snapshot (as of 2026-03-04)

```
✅ 4,234 products in Supabase (images on CDN)
✅ 866 products enriched + embedded (pgvector on products table)
✅ 7,324 bridges computed (5 types, scored)
✅ Qdrant eliminated — pgvector in Supabase
✅ FastAPI search layer updated to pgvector
✅ Frontend COMPLETE (4 routes, error boundaries, SEO, mobile-ready)
✅ Frontend builds clean (tsc + npm run build pass)

⏳ Supabase migration Steps 12–20
   └─ compute_bridges.py is the current active task

🔲 Data growth to ~1,500 enriched products
🔲 Deploy (Railway + Vercel)
🔲 semantic_type column on style_bridges
🔲 7,302 bridge narratives remaining (~$13)
🔲 Knowledge graph (Neptune) — trigger: multi-step bridge UI
🔲 IIT integration — post-KG
```
