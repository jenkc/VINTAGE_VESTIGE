# KG_MASTER_PLAN.md
# Vintage Vestige — Knowledge Graph: Master Plan

**Status:** Waiting on prerequisites  
**Owner:** Jen / linuxgrrrl LLC  
**Target Start:** After Supabase migration complete + deploy + semantic_type column  
**Target Complete:** 6 weeks from start  
**Last Updated:** March 2026 (v2.0 — revised for current project state)

---

## What Changed in v2.0

The original plan was written when the project was at 866 products, Qdrant was
running, and the frontend had only stubs. The current state is substantially
different:

| Assumption in v1.0 | Reality in v2.0 |
|---|---|
| Frontend not built | Frontend is **complete** — 4 routes, builds clean |
| Qdrant as vector store | **Qdrant eliminated** — pgvector in Supabase |
| 866 products | **4,234 products** in Supabase (866 enriched) |
| Supabase migration = future work | **Steps 1–11 complete**, Steps 12–20 in progress |
| Phase 8 (Supabase Coexistence) needed | **Deleted** — already the current architecture |
| Export scripts read from Postgres + Qdrant | Export scripts read from **Supabase only** |
| KG is the next thing | KG starts after deploy + semantic_type column |

---

## Master Schedule

```
CURRENT ── Supabase migration Steps 12–20 (IN PROGRESS)
           └─ compute_bridges.py (Step 12 — current active task)
           └─ generator.py, enrichment, delete obsolete files, tests

+1 week ── Data growth to ~1,500 enriched products
           └─ .claude/plans/functional-hopping-barto.md

+2 weeks ─ Deploy (Railway + Vercel)
           └─ First live URL — required before building more infrastructure

QUICK WIN  semantic_type column on style_bridges
           └─ ~2 hours; classify from existing data; no infra cost
           └─ Immediate payoff: richer bridge UI, search filtering

─────────── KG TRIGGER: multi-step bridge UI planned ───────────

WEEK 1 ─── KG Phase 1: Schema Design
           └─ Node labels, edge types, property definitions
           └─ Bridge semantic type taxonomy
           └─ No code written this week

WEEK 2 ─── KG Phase 2: AWS Setup (days 1–3)
           KG Phase 3: Design Element Extraction (days 3–5)
           └─ Neptune Serverless cluster
           └─ S3 bucket + IAM role
           └─ Extract DesignElement vocabulary from shared_attributes
           └─ Getty AAT mapping for top 50 elements

WEEK 3 ─── KG Phase 4: Export Scripts
           └─ Read from Supabase (SQLAlchemy Session, NOT Qdrant)
           └─ All node + edge CSV files
           └─ Validation + integrity checks

WEEK 4 ─── KG Phase 5: Bulk Load + Validation
           └─ Upload to S3
           └─ Neptune bulk loader
           └─ Validation queries in Neptune Notebook

WEEK 5 ─── KG Phase 6: FastAPI Graph Layer
           └─ Neptune client (Gremlin/openCypher)
           └─ Dual connection pattern: Session (Supabase) + Gremlin (Neptune)
           └─ New /graph endpoints
           └─ Integration tests

WEEK 6 ─── KG Phase 7: Frontend Graph Features
           └─ Influence Chain Visualizer
           └─ Design Movement Explorer
           └─ Design Element Index

AFTER ───── IIT Integration (now over a proper graph)
PARALLEL ── Academic paper
```

---

## Phase Summary

| Phase | Name | Duration | Status | Doc |
|---|---|---|---|---|
| 0 | Prerequisites | Until done | ⏳ In progress | `KG_PHASE0_PREREQUISITES.md` |
| 1 | Schema Design | 1 week | 🔲 Not started | `KG_PHASE1_SCHEMA_DESIGN.md` |
| 2 | AWS Setup | 2–3 days | 🔲 Not started | `KG_PHASE2_AWS_SETUP.md` |
| 3 | Design Element Extraction | 2–3 days | 🔲 Not started | `KG_PHASE3_DESIGN_ELEMENTS.md` |
| 4 | Export Scripts | 1 week | 🔲 Not started | `KG_PHASE4_EXPORT_SCRIPTS.md` |
| 5 | Bulk Load | 2–3 days | 🔲 Not started | `KG_PHASE5_BULK_LOAD.md` |
| 6 | API Layer | 1 week | 🔲 Not started | `KG_PHASE6_API_LAYER.md` |
| 7 | Frontend Features | 1 week | 🔲 Not started | `KG_PHASE7_FRONTEND.md` |
| ~~8~~ | ~~Supabase Coexistence~~ | ~~Ongoing~~ | ✅ Already done | ~~Deleted~~ |

---

## Master Checklist

### Phase 0 — Prerequisites (current focus)
- [ ] Step 12: `compute_bridges.py` updated for pgvector (no Qdrant references)
- [ ] Step 13: `embeddings/generator.py` handles Supabase Storage URLs
- [ ] Step 14: `enrichment/claude.py` updated
- [ ] Step 15: enrichment scripts updated
- [ ] Step 16: `storage/vector_db.py` deleted; other obsolete files removed
- [ ] Step 17: `vv-web/next.config.ts` image domains updated to Supabase Storage
- [ ] Step 18: all tests updated (no Qdrant references)
- [ ] Steps 19–20: verify + cleanup complete
- [ ] Data growth to ~1,500 enriched products executed
- [ ] Deployed to Railway (backend) + Vercel (frontend)
- [ ] `semantic_type` column added to `style_bridges`
- [ ] 7,302 bridge narratives generated (~$13)

### Phase 1 — Schema Design
- [ ] All node labels defined with full property lists
- [ ] All edge types defined with directionality
- [ ] Bridge semantic type taxonomy finalized (8 types)
- [ ] Node ID naming conventions documented
- [ ] Schema reviewed against 3 validation queries
- [ ] Schema doc signed off before any code written

### Phase 2 — AWS Setup
- [ ] AWS account created
- [ ] Billing alert set ($50/month)
- [ ] Neptune Serverless cluster created
- [ ] S3 bucket created (same region as Neptune)
- [ ] IAM role created (Neptune → S3 read access)
- [ ] Neptune Notebook environment working
- [ ] `.env` updated with Neptune endpoint (alongside existing Supabase env vars)

### Phase 3 — Design Element Extraction
- [ ] `extract_design_elements.py` written and run against Supabase
- [ ] Frequency-ranked element list generated
- [ ] Top 50 elements identified
- [ ] Getty AAT URIs manually mapped for top 50
- [ ] `design_elements_seed.py` populated
- [ ] DesignElement hierarchy sketched (subcategories)
- [ ] ≥70% bridge coverage confirmed

### Phase 4 — Export Scripts
- [ ] All scripts read from Supabase via SQLAlchemy Session (zero Qdrant references)
- [ ] `export_garment_nodes.py` — ~1,500 enriched rows
- [ ] `export_designer_nodes.py` — extracted from enrichment data
- [ ] `export_era_nodes.py` — ~15–20 unique eras
- [ ] `export_design_element_nodes.py` — from Phase 3 seed
- [ ] `export_bridge_nodes.py` — ~10,000–15,000 rows (post data growth recompute)
- [ ] `export_collection_nodes.py` — met_museum, smithsonian, fashionpedia + any added
- [ ] `export_garment_edges.py` — CREATED_BY, FROM_ERA, PART_OF, CONNECTED_VIA
- [ ] `export_bridge_edges.py` — CONNECTS, ARGUES_THROUGH, HAS_TYPE
- [ ] `export_element_edges.py` — SUBCATEGORY_OF
- [ ] `run_all_exports.py` — orchestrator
- [ ] `validate_exports.py` — count checks + referential integrity
- [ ] All CSVs validated (no nulls, no orphan edges)
- [ ] `LOAD_MANIFEST.json` written with final counts

### Phase 5 — Bulk Load
- [ ] All CSVs uploaded to S3
- [ ] Neptune bulk loader invoked
- [ ] Load completed without critical errors
- [ ] Node counts verified (Garments, Bridges, DesignElements, Eras)
- [ ] Edge counts verified
- [ ] 3 validation queries execute successfully
- [ ] Spot-check: 5 random bridges traversable in Neptune Notebook
- [ ] Performance baseline: simple traversal < 500ms

### Phase 6 — API Layer
- [ ] `api/graph/neptune.py` — Neptune Gremlin client
- [ ] Dual connection pattern documented and implemented:
  - `get_db()` → SQLAlchemy Session → Supabase (existing)
  - `get_neptune_client()` → Gremlin client → Neptune (new)
- [ ] `get_influence_chain()` function
- [ ] `get_design_movement()` function
- [ ] `get_style_ancestry()` function (graph version)
- [ ] `get_modern_echoes_graph()` function
- [ ] `get_design_elements()` function
- [ ] `api/routers/graph.py` — all /graph endpoints
- [ ] Integration tests for all graph endpoints
- [ ] Error handling: Neptune down → 503 (not 500)
- [ ] Response time < 800ms for all graph endpoints

### Phase 7 — Frontend
- [ ] Influence Chain Visualizer component (integrates with existing product detail page)
- [ ] Design Movement Explorer (D3 force-directed graph)
- [ ] Design Element Index page
- [ ] `/explore` route added to Next.js app
- [ ] Bridge panel updated with semantic_type display and DesignElement chips
- [ ] Navigation updated (Explore link in Header)
- [ ] Mobile-responsive: force graph falls back to list view at <768px
- [ ] Loading skeletons for all async graph queries

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Neptune VPC setup complexity | Medium | High | Use Neptune Notebooks; avoids bastion host |
| Bridge semantic_type accuracy | Medium | Medium | Rule-based classifier; source = `algorithmic_v1`; curators correct over time |
| Getty AAT mapping gaps | High | Low | Leave `aat_uri` null; populate incrementally |
| Neptune cost overrun | Low | Medium | Serverless 1–8 NCU cap; billing alert at $50/month |
| CSV referential integrity errors | Medium | Medium | `validate_exports.py` catches before load |
| Gremlin + SQLAlchemy dual-connection complexity | Medium | Medium | Document pattern explicitly in Phase 6; separate `Depends()` per database |
| KG start delayed by data growth / deploy | Low | Low | Timeline is intentional — KG waits for trigger point |
| Bridge count change after data growth recompute | Medium | Low | Rerun `compute_bridges.py` after growth; export scripts handle any count |

---

## Dependencies

```
Supabase migration (Steps 12-20) ────────────────┐
                                                   ▼
Data growth to ~1,500 products ───────────────────┐
                                                   ▼
Deploy (Railway + Vercel) ────────────────────────┐
                                                   ▼
semantic_type column on style_bridges ────────────┐
                                                   ▼
              [TRIGGER: multi-step bridge UI planned]
                                                   │
                          KG Phase 1 (Schema) ─────┘
                                    │
               ┌────────────────────┘
               ▼                    ▼
     KG Phase 2 (AWS)    KG Phase 3 (Elements)
               └────────────────────┐
                                    ▼
                          KG Phase 4 (Exports)
                                    │
                                    ▼
                          KG Phase 5 (Bulk Load)
                                    │
                                    ▼
                          KG Phase 6 (API Layer)
                                    │
                                    ▼
                          KG Phase 7 (Frontend)
                                    │
                                    ▼
                           IIT Integration
```

---

## Definition of Done

The knowledge graph implementation is **done** when:

1. All three validation queries return coherent results in production Neptune
2. `/graph/influence-chain/{id}` returns a 3-hop traversable chain
3. `/graph/design-movement/{element}` returns garments spanning 3+ eras
4. Cross-institutional bridges visible in the frontend `/explore` route
5. All phase checklists 100% complete
6. `KG_DECISIONS.md` reflects all architectural choices made
7. `PROJECT_STATE.md` updated to reflect Neptune in the architecture
8. `SESSION_LOG.md` updated with final implementation state