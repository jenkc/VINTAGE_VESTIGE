# Dev Diary: March 4, 2026 — Burning Down the Vector Database & Sketching the Knowledge Graph

Today was a two-track day. In one window: the grunt work of finishing a major infrastructure migration. In the other: the much more exciting work of designing where this project goes next. Both felt necessary. You can't build a cathedral on top of scaffolding you're still welding together.

---

## Part 1: The Supabase Migration (Steps 5-11)

I've been migrating Vintage Vestige off local PostgreSQL + Qdrant and onto Supabase. Today I knocked out seven steps of a twenty-step migration plan, and the search layer is now fully running on pgvector.

### What actually happened

**Image migration (Step 5)** — All 4,234 product images were stored as base64-encoded strings directly in the database. That's ~163 MB of image data bloating the `primary_image` column. I uploaded everything to a Supabase Storage bucket and replaced the base64 blobs with HTTP URLs. Database went from ~179 MB to ~19 MB. Every image now loads from a CDN instead of being decoded from a text column.

**Qdrant to pgvector (Step 6)** — This was the scary one. Qdrant had been running locally with two collections: `vintage_text` (384-dim, all-MiniLM-L6-v2) and `vintage_images` (512-dim, CLIP). I wrote a migration script to scroll through both collections and write every vector into pgvector columns on the products table. 866 text embeddings, 866 image embeddings, all transferred. Created HNSW indexes with cosine ops. Ran a similarity query to verify. Then stopped Qdrant and deleted the env vars.

That felt surprisingly good — like removing a dependency that had been complicating every deployment conversation for weeks.

**ORM + search layer (Steps 7-11)** — Added `Vector(384)` and `Vector(512)` columns to the SQLAlchemy model. Wrote a new `VectorSearch` class that takes the request's SQLAlchemy session (no separate connection — everything in one database now). Rewrote the FastAPI search router and dependencies. Added JSON validators to handle `style_tags` and `colors` coming back as strings from SQL instead of pre-parsed lists from Qdrant payloads.

### The key decision: pgvector over Qdrant Cloud

I could have migrated to Qdrant Cloud (they have a free 1GB tier). Instead I chose to eliminate the vector database entirely. The reasoning:

1. **One database.** Supabase PostgreSQL handles relational data, vector search, and (via Storage) image hosting. No separate service to manage, monitor, or pay for.
2. **IIT simplification.** The IIT 4.0 integration plan needs cross-modal Phi calculations — measuring information integration between text and image embeddings for the same product. With pgvector, that's a single SQL query joining two columns. With Qdrant, it would have been cross-collection lookups with ID mapping.
3. **Shared sessions.** `VectorSearch` takes the same SQLAlchemy session that the rest of the request uses. Vector search and relational queries participate in the same transaction. No connection pool for a second database.

At 866 embedded products, pgvector HNSW is more than fast enough. If I hit 100K products, I'll revisit. But that's a good problem to have.

### Bugs I wrote and caught

- Forgot to add `column_name` as a parameter to the migration function but referenced it inside
- `if offset = None` instead of `==` (I blame late-night Python)
- `vintage_image` instead of `vintage_images` (collection name was plural)
- `pgvector.sqalchemy` instead of `pgvector.sqlalchemy` (missing an 'l')
- `b64dercode` instead of `b64decode`
- `.itemns()` instead of `.items()`

Six typos in one session. I'm writing all the code myself, Claude Code is checking my work, and it's catching things I absolutely would have spent 20 minutes debugging alone. The workflow is: I write, it reviews, I fix. Repeat.

---

## Part 2: The Knowledge Graph Decision

While the migration was running, I spent time in Claude Desktop designing the knowledge graph layer. This is the piece that transforms Vintage Vestige from "a search engine with bridges" into "a fashion intelligence platform."

### Why a knowledge graph at all?

Style bridges are powerful — they connect a Georgian-era empire waist dress to a modern reformation piece based on shared structural DNA. But bridges are **pairwise**. They tell you "A is related to B." They don't tell you:

- What design movement connects A, B, C, and D?
- Which specific design elements (empire waistline, A-line silhouette) recur across centuries?
- How did a decorative technique travel from one culture to another?

A knowledge graph makes these multi-hop questions answerable. Instead of just `Garment A --bridge--> Garment B`, you get:

```
Garment A --HAS_ELEMENT--> Empire Waistline --HAS_ELEMENT--> Garment B
                                    |
                           SUBCATEGORY_OF
                                    |
                              Waistline Types
```

That's the difference between "these two things are similar" and "here's *why* they're similar, and here's everything else that shares that reason."

### The architecture decision: AWS Neptune Serverless

I considered three options:

1. **Neo4j Aura (free tier)** — 200K nodes, nice query language (Cypher), great tooling. But the free tier is tiny and the jump to paid is steep.
2. **Storing graph edges in PostgreSQL** — No new infrastructure. But recursive CTEs for multi-hop traversals are ugly, slow, and hard to maintain. Postgres is great at many things; graph traversal isn't one of them.
3. **AWS Neptune Serverless** — Pay-per-query, scales to zero, supports both Gremlin and openCypher, S3 bulk loading.

I went with Neptune. The key factor: **serverless means I'm not paying for idle capacity.** This is a portfolio project. It might get traffic during demo weeks and zero traffic otherwise. Neptune Serverless handles that pattern perfectly — 1-8 NCU scaling with a $50/month billing alert as a safety net.

### The dual-connection pattern

This was the trickiest architectural decision. The API already uses SQLAlchemy sessions for Supabase. Neptune uses Gremlin (or openCypher). How do they coexist?

The answer: **separate dependency injection, same request.**

```python
# Existing (unchanged)
def get_db() -> Session:           # SQLAlchemy → Supabase

# New
def get_neptune_client() -> Client: # Gremlin → Neptune
```

Endpoints that need both (e.g., "get product detail from Supabase + influence chain from Neptune") inject both dependencies. They're independent connections to independent databases. No ORM trying to bridge two query languages.

### What I'm NOT building yet

The KG has a trigger condition: **it starts after the Supabase migration is complete, the app is deployed, and a `semantic_type` column exists on `style_bridges`.** That last one is a quick win (~2 hours) that classifies bridges into types like `material_echo`, `silhouette_revival`, `cultural_fusion` based on which shared attributes scored highest. It's immediately useful in the bridge UI and becomes an edge property in the graph.

I'm also not starting the KG until the dataset has grown to ~1,500 products. A knowledge graph over 866 items is a toy. Over 1,500 with cross-institutional bridges, it starts showing real patterns.

### The phase plan

Seven phases, six weeks:

1. **Schema Design** (week 1) — Node labels, edge types, property definitions. No code. Just design.
2. **AWS Setup** (week 2, days 1-3) — Neptune cluster, S3 bucket, IAM roles.
3. **Design Element Extraction** (week 2, days 3-5) — Pull the shared attribute vocabulary from existing bridge data. Map top 50 elements to Getty AAT URIs for art-historical authority.
4. **Export Scripts** (week 3) — CSV generators reading from Supabase (not Qdrant — it's gone now).
5. **Bulk Load** (week 4) — S3 upload, Neptune bulk loader, validation queries.
6. **API Layer** (week 5) — `/graph` endpoints with the dual-connection pattern.
7. **Frontend** (week 6) — Influence Chain Visualizer, Design Movement Explorer, Design Element Index.

The original plan had a Phase 8 for "Supabase Coexistence" — I deleted it. That's already the architecture after today's migration work.

### The Getty AAT mapping

This is the decision I'm most excited about. The [Getty Art & Architecture Thesaurus](http://www.getty.edu/research/tools/vocabularies/aat/) is the standard vocabulary for describing art objects in museum collections. By mapping our top 50 design elements (empire waistline, A-line silhouette, lace appliqué, etc.) to AAT URIs, we get:

- **Authority.** These aren't made-up terms — they're the same vocabulary used by the Met, the V&A, the Smithsonian.
- **Interoperability.** If I ever want to federate with museum APIs, we speak the same language.
- **Hierarchy.** AAT gives us subcategory relationships for free (empire waistline → waistline types → garment construction).

I'll do the initial mapping manually for the top 50 elements. After that, lower-frequency elements can be mapped incrementally or left unmapped (`aat_uri: null`).

---

## Part 3: Documentation Cleanup

Updated five docs to reflect the Supabase migration:

- **ARCHITECTURE.md** — Replaced all Qdrant references with pgvector. Data layer diagram, data flow, search flow, tech stack, infrastructure, database schema all updated.
- **API_SPEC.md** — Search endpoints now reference pgvector cosine distance instead of Qdrant pre-filtering. Dependencies table updated.
- **DATA_INVENTORY.md** — Connection string, product counts, vector storage section rewritten for pgvector.
- **DECISIONS.md** — Added decisions 27-29 (pgvector over Qdrant, Supabase Storage for images, VectorSearch shares SQLAlchemy session).
- **SESSION_LOG.md** — Full session record with files created/modified, decisions, bugs, resume point.

---

## What's Next

**Tomorrow:** Step 12 of the Supabase migration — updating `compute_bridges.py`. This is the biggest single-file change. It touches Qdrant in six places: imports, ID fetching, vector retrieval, candidate search, filter builders, and the main function. Every one of those needs to become a pgvector SQL query.

**This week:** Steps 12-20 to finish the migration. Then data growth to 1,500 products.

**After deploy:** The `semantic_type` column, then the knowledge graph.

The project is at an interesting inflection point. The MVP is built — search works, bridges work, the frontend is polished. Everything from here is about depth: richer data, graph structure, IIT integration. The kind of work that turns a portfolio piece into a research platform.

---

*Jen Kim / linuxgrrrl LLC*
*Building Vintage Vestige — where fashion history meets computational intelligence*
