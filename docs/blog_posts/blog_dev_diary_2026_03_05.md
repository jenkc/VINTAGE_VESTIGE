# Dev Diary: March 5, 2026 — Migration Complete, Qdrant Is Dead, Long Live pgvector

Today I finished the Supabase migration. All twenty steps, done. Local Qdrant is gone. Every piece of the stack — API, bridge computation, enrichment scripts, embedding pipeline, tests — now runs against one hosted database. It feels like taking off a backpack after a long hike.

---

## What Actually Happened Today

### Steps 12-15: The Code Surgery (prior session, completed yesterday)

The hardest part of the migration was `compute_bridges.py`. This file had Qdrant woven through it like thread through fabric — six separate touchpoints. Qdrant filter objects became SQL WHERE fragments. Qdrant `scroll()` calls became `SELECT id FROM products WHERE text_embedding IS NOT NULL`. Vector retrieval that used to cross-reference two Qdrant collections became a single-row query pulling both embeddings at once.

The enrichment scripts were simpler but tedious. Six files, all following the same pattern: remove the `VectorDB` import, delete the giant payload dict, replace the Qdrant upsert with two lines:

```python
product.text_embedding = text_emb.tolist()
product.image_embedding = img_emb.tolist()
```

No more building a 28-field metadata dictionary to keep Qdrant payloads in sync with Postgres. The data just lives where it lives.

### Steps 16-17: Cleanup and Frontend

Moved the obsolete Qdrant backfill scripts into `scripts/` rather than deleting them. Old code has a way of being useful when you're debugging "wait, how did this work before?" Added the Supabase hostname to `next.config.ts` for Next.js image optimization.

### Step 18: Rewriting the Tests

This was more work than I expected. Every test file that touched the database or vector search needed updating:

- **conftest.py** — `vector_db` fixture became `vector_search`, backed by pgvector instead of Qdrant
- **integration/conftest.py** — `require_qdrant` became `require_vectors` (checks for pgvector embeddings)
- **test_vector_db.py** — Full rewrite. `TestVectorDBCollections` became `TestVectorEmbeddingsExist`. Tests that scrolled Qdrant collections now query SQL columns.
- **test_search_relevance.py** and **test_search_quality.py** — Global replace of the search helper function signature
- **test_data_quality.py** — Deleted the entire `TestQdrantPostgresConsistency` class. The class existed because we had to keep two databases in sync. Now there's nothing to sync. Replaced it with `TestEmbeddingConsistency` that just checks pgvector columns.
- **test_bridge_quality.py** — Deleted `TestQdrantPayloads`. Same reasoning.
- **test_embeddings.py** — `TestDecodeDataUrl` became `TestLoadImage` because `decode_data_url()` was renamed to `load_image()` during Step 13 (now handles HTTP URLs, not just base64).

The satisfying part: deleting test classes that tested Qdrant-Postgres sync. Those tests existed because of architectural complexity. Removing the complexity removed the tests. That's a good sign.

### Step 19: Verification

All tests pass:
- **134 unit tests** — no external services needed
- **70 integration tests** — hitting Supabase
- **3 expected failures** in data integrity — not migration bugs:
  - V&A museum data (3,368 products) loaded but not yet enriched
  - `same_era` bridge type is stale from old code runs
  - `va_museum` wasn't in the valid platforms set (fixed)

### Step 20: Documentation and Cleanup

Updated five docs. The interesting one was ARCHITECTURE.md — the temporal classification section was wrong. It described a year-distance algorithm (`same_era: |year_a - year_b| <= 25`) but the actual code uses era name comparison plus decade distance. `cross_era` means different named eras (Victorian vs. Art Deco), `cross_time` means same era but decades more than 30 years apart. The old `same_era` and `near_era` types were stale data from earlier code versions.

Deleted 3,957 `same_era` bridges. They were produced by code that no longer exists and don't match the current bridge classification logic. Kept 425 `near_era` bridges for now — they're questionable but not clearly wrong.

Created `storage/image_storage.py` — a Supabase Storage upload helper for future data loaders. Three functions, 35 lines. Now any new loader can call `upload_product_image(product_id, raw_bytes)` instead of base64-encoding into the database column.

---

## The Before and After

**Before (Feb 27):**
- Local PostgreSQL (179 MB, bloated with base64 images)
- Local Qdrant (2 collections, separate process, separate connection pool)
- `storage/vector_db.py` — Qdrant client with payload management
- Every enrichment script built a 28-field metadata dict to keep Qdrant in sync
- Test suite needed both PostgreSQL and Qdrant running
- Deployment plan: 4 services (Qdrant Cloud + Supabase + Railway + Vercel)

**After (Mar 5):**
- Supabase PostgreSQL + pgvector (~19 MB relational data)
- Supabase Storage (~161 MB images, CDN-served)
- `storage/vector_search.py` — shares the SQLAlchemy session, no separate connection
- Enrichment scripts write embeddings as column values. Two lines.
- Test suite needs only Supabase PostgreSQL
- Deployment plan: 3 services (Supabase + Railway + Vercel)

**Eliminated:** One entire database service, one Python client library, one connection pool, hundreds of lines of payload synchronization code, two test classes that only existed to verify cross-database consistency.

---

## Decisions Made Today

### Delete `same_era` bridges, keep `near_era`

The current `classify_temporal_type` function in compute_bridges.py produces three outcomes: `cross_era` (different named eras), `cross_time` (same era, decades 30+ years apart), or `None` (skip — not interesting). It never produces `same_era` or `near_era`. Those types came from an older version of the code.

3,957 `same_era` bridges were noise — products from the same era with no interesting temporal tension. Deleted. The 425 `near_era` bridges might be worth keeping or reclassifying. Left them for now.

### Documentation should match the code, not the plan

Found three places where docs described planned behavior instead of actual behavior (temporal classification, bridge type lists, Qdrant references). Fixed all of them. A lesson I keep relearning: documentation drifts the moment you stop treating it as source of truth.

---

## What's Next

The migration plan had an "Optional" section at the bottom: an image upload helper for future data loaders. Built that today as `storage/image_storage.py`. The next plan to implement is the next phase of the project — I'll be picking that up tomorrow.

Remaining cleanup: uninstall `qdrant-client` from the virtualenv. It's not in `requirements.txt` but it's still installed locally. One command, but I want to run the full test suite one more time first just to be sure nothing is importing it transitively.

The Supabase migration is the kind of work that doesn't feel exciting but makes everything after it easier. Every future feature — data growth, knowledge graph, deployment — is simpler because there's one database instead of two. Sometimes the best engineering decision is the one that deletes a box from the architecture diagram.

---

*Jen Kim / linuxgrrrl LLC*
*Building Vintage Vestige — where fashion history meets computational intelligence*
