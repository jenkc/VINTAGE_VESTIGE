# KG_SUCCESS_CRITERIA.md
# Knowledge Graph — Success Criteria

**Purpose:** Unambiguous exit gates for every phase. Before moving to the next
phase, every item in the current phase's criteria must be verified, not estimated.  
**Last Updated:** March 2026 (v2.0)

---

## Phase 0 — Prerequisites

Do not start schema design until all of the following are true.

### Supabase Migration Complete (Steps 12–20)

Verify by running in the project root:

```bash
# Zero Qdrant references in codebase
grep -r "qdrant\|QDRANT\|QdrantClient\|vector_db" . \
  --include="*.py" \
  --exclude-dir=".git" \
  --exclude-dir="venv"
# Must return: no output
```

```bash
# All tests pass
venv/bin/pytest
# Must return: 156+ passed, 0 failed
```

```bash
# API starts and responds
venv/bin/uvicorn api.main:app &
curl http://localhost:8000/health
# Must return: {"status": "ok"} or equivalent
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "1920s silk dress"}'
# Must return: results array with items
```

```bash
# QDRANT vars gone from .env
grep "QDRANT" .env
# Must return: no output
```

### Data Growth Complete

```sql
-- Run against Supabase
SELECT COUNT(*) FROM products WHERE enriched_at IS NOT NULL;
-- Must return: ≥ 1,500

SELECT COUNT(*) FROM style_bridges;
-- Must return: > 7,324 (recomputed after growth)

SELECT COUNT(*) FROM style_bridges WHERE bridge_narrative IS NOT NULL;
-- Must return: ≥ 7,000 (narratives generated)
```

### Deployed

```bash
# Both URLs must return HTTP 200
curl https://<railway-backend-url>/health     # FastAPI on Railway
curl https://<vercel-frontend-url>            # Next.js on Vercel
```

### semantic_type Column Populated

```sql
-- Run against Supabase
SELECT COUNT(*) FROM style_bridges WHERE semantic_type IS NULL;
-- Must return: 0

SELECT semantic_type, COUNT(*) 
FROM style_bridges 
GROUP BY semantic_type 
ORDER BY COUNT(*) DESC;
-- Must return: 8 distinct types, all with reasonable counts
```

---

## Phase 1 — Schema Design

Do not write any export code until all of the following are true.

- [ ] Every node label has a complete property table (no `TBD` fields)
- [ ] Every edge type has defined directionality, cardinality, and property list
- [ ] All 8 semantic bridge types defined with classification rules documented
- [ ] ID naming convention documented and applied consistently across all node types
- [ ] Schema reviewed against all 3 validation queries:
  - Can Validation Query 1 (Influence Chain) be written against this schema?
  - Can Validation Query 2 (Design Movement) be written against this schema?
  - Can Validation Query 3 (Cross-Institutional) be written against this schema?
- [ ] `KG_PHASE1_SCHEMA_DESIGN.md` has no `TBD` remaining
- [ ] Schema signed off before Phase 4 begins

---

## Phase 2 — AWS Setup

Do not begin export scripts until Neptune Notebook is working.

```python
# Run in Neptune Notebook — must succeed
%%oc
MATCH (n) RETURN count(n)
# Must return: 0 (empty graph — no data loaded yet, but query works)
```

```bash
# S3 bucket accessible
aws s3 ls s3://vintage-vestige-neptune-data/
# Must not return: access denied
```

- [ ] Billing alert set at $50/month
- [ ] Neptune cluster endpoint saved to `.env` as `NEPTUNE_ENDPOINT`
- [ ] Neptune load IAM role ARN saved to `.env` as `NEPTUNE_LOAD_ROLE_ARN`

---

## Phase 3 — Design Element Extraction

Do not write Neptune seed data until frequency analysis is reviewed.

```bash
# Frequency report exists and is populated
wc -l data/design_elements_frequency.csv
# Must return: > 50 lines (meaningful vocabulary exists)

head -20 data/design_elements_frequency.csv
# Review: do the top elements match fashion history vocabulary?
```

- [ ] `data/design_elements_frequency.csv` exists and reviewed
- [ ] Top 50 elements identified and curated (junk values removed)
- [ ] ≥ 30 Getty AAT URIs manually mapped
- [ ] `design_elements_seed.py` populated with curated list
- [ ] Coverage check: what % of bridge's `shared_attributes` contain at least one seeded element?

```sql
-- Run against Supabase
-- Must return: ≥ 70%
WITH bridge_coverage AS (
  SELECT 
    COUNT(*) FILTER (WHERE shared_attributes != '{}' AND shared_attributes IS NOT NULL) as has_attrs,
    COUNT(*) as total
  FROM style_bridges
)
SELECT ROUND(has_attrs::numeric / total * 100, 1) as coverage_pct
FROM bridge_coverage;
```

---

## Phase 4 — Export Scripts

Do not load Neptune until `validate_exports.py` exits clean.

```bash
venv/bin/python scripts/kg/validate_exports.py
# Must return:
#   ✅ garment_nodes.csv — N rows, no nulls
#   ✅ bridge_nodes.csv — N rows, no nulls
#   ✅ design_element_nodes.csv — N rows, no nulls
#   ✅ era_nodes.csv — 15 rows
#   ✅ All edge ~from IDs found in node files
#   ✅ All edge ~to IDs found in node files
#   ✅ No duplicate ~id values
#   0 errors total
```

Verify counts against Supabase:

```sql
-- Supabase: source of truth for garment and bridge counts
SELECT COUNT(*) FROM products WHERE enriched_at IS NOT NULL;  -- must match garment_nodes.csv
SELECT COUNT(*) FROM style_bridges;                            -- must match bridge_nodes.csv
```

- [ ] `LOAD_MANIFEST.json` written with final counts
- [ ] All CSV files open in a text editor without encoding errors
- [ ] No Qdrant, no psycopg2, no local Postgres references in any export script

---

## Phase 5 — Bulk Load

Do not build the API layer until all 3 validation queries pass.

```cypher
-- Run in Neptune Notebook after load

-- Node counts
MATCH (g:Garment) RETURN count(g)
-- Must match garment_nodes.csv row count (~1,500)

MATCH (b:Bridge) RETURN count(b)
-- Must match bridge_nodes.csv row count (~10,000–15,000)

MATCH (de:DesignElement) RETURN count(de)
-- Must match design_elements_seed.py count

MATCH (e:Era) RETURN count(e)
-- Must return: 15

-- Validation Query 1 — Influence Chain
MATCH path = (modern:Garment {platform: 'fashionpedia'})
  -[:CONNECTED_VIA]->(b1:Bridge)
  -[:CONNECTS]->(g2:Garment)
  -[:CONNECTED_VIA]->(b2:Bridge)
  -[:CONNECTS]->(historical:Garment)
WHERE historical.platform IN ['met_museum', 'smithsonian']
  AND b1.score > 0.6 AND b2.score > 0.6
RETURN modern.title, b1.narrative, g2.title, b2.narrative, historical.title
LIMIT 5
-- Must return: ≥ 1 result

-- Validation Query 2 — Design Movement
MATCH (de:DesignElement)
  <-[:ARGUES_THROUGH]-(b:Bridge)
  -[:CONNECTS]->(g:Garment)
  -[:FROM_ERA]->(era:Era)
WITH de, count(DISTINCT era) as era_count, count(b) as bridge_count
WHERE era_count >= 2
RETURN de.name, era_count, bridge_count
ORDER BY bridge_count DESC
LIMIT 10
-- Must return: ≥ 1 result

-- Validation Query 3 — Cross-Institutional
MATCH (g1:Garment {platform: 'met_museum'})
  -[:CONNECTED_VIA]->(b:Bridge)
  -[:CONNECTS]->(g2:Garment {platform: 'smithsonian'})
WHERE b.score > 0.6
RETURN g1.title, b.narrative, g2.title, b.score
ORDER BY b.score DESC
LIMIT 10
-- Must return: ≥ 1 result
```

Performance baseline:
```cypher
-- Simple 2-hop query must complete < 500ms
MATCH (g:Garment {id: 'garment_1'})
  -[:CONNECTED_VIA]->(b:Bridge)
  -[:CONNECTS]->(related:Garment)
RETURN related.title, b.score
LIMIT 10
```

---

## Phase 6 — API Layer

Do not build frontend graph features until all endpoints pass tests.

```bash
# All integration tests pass
venv/bin/pytest tests/integration/test_graph_endpoints.py -v
# Must return: all tests passed

# All 7 graph endpoints visible in auto-docs
curl http://localhost:8000/openapi.json | python -m json.tool | grep '"/graph/'
# Must return: 7 paths

# Neptune unavailable returns 503 not 500
# Test by temporarily setting NEPTUNE_ENDPOINT to invalid value
```

- [ ] Response times meet targets (measured, not estimated):
  - `/graph/style-ancestry` < 300ms
  - `/graph/influence-chain` < 800ms
  - `/graph/design-movement` < 1000ms
- [ ] Dual-connection pattern documented in `ARCHITECTURE.md`

---

## Phase 7 — Frontend Graph Features

Do not call the KG implementation complete until all QA items pass.

- [ ] Influence Chain Visualizer renders on product detail page for fashionpedia items
- [ ] At least one 3-hop chain displays correctly end-to-end
- [ ] Design Movement Explorer loads for ≥ 3 design elements
- [ ] Design Element Index page shows all seeded elements
- [ ] `/explore` route accessible from navigation
- [ ] All graph features have loading skeletons (no layout shift while loading)
- [ ] All graph features degrade gracefully when Neptune returns empty results
- [ ] Mobile: force-directed graph falls back to list view at < 768px viewport
- [ ] `npm run build` still passes after all new components added

---

## Overall Done

The knowledge graph implementation is **complete** when:

1. All three validation queries return coherent results in production Neptune
2. `/graph/influence-chain/{id}` returns a 3-hop traversable chain in < 800ms
3. `/graph/design-movement/{element}` returns garments spanning ≥ 2 eras
4. Cross-institutional bridges visible in the `/explore` frontend route
5. All phase checklists 100% checked off
6. `KG_DECISIONS.md` has entries for every significant choice made during implementation
7. `PROJECT_STATE.md` updated: Neptune added to database layer
8. `SESSION_LOG.md` updated: KG implementation marked complete
9. `ARCHITECTURE.md` updated: dual-connection pattern documented
