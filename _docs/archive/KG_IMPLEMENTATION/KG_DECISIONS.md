# KG_DECISIONS.md
# Knowledge Graph — Architecture Decisions Log

**Format:** Decision number | Date | Status | Decision | Rationale  
**Status options:** Active | Superseded | Under Review  
**Owner:** Jen / linuxgrrrl LLC  
**Last Updated:** March 2026 (v2.0)

---

## How to Use This Document

When you make an architectural choice during implementation, log it here before
moving on. Future-you will thank present-you. The format is lightweight on
purpose — write enough to explain the decision to someone who wasn't in the room.

Log a decision when you:
- Choose between two real alternatives
- Discover a constraint that changes the approach
- Decide *not* to implement something that was in the plan
- Change something from what this document set specified

---

## Decisions

---

### KGD-001 — Knowledge Graph Before IIT

**Date:** March 2026  
**Status:** Active  
**Decision:** Implement the knowledge graph before IIT (Integrated Information Theory) integration.

**Rationale:**  
The KG changes data architecture. IIT changes scoring algorithm. Architecture changes
are expensive to retrofit; scoring changes are cheap to add. IIT needs a stable graph
substrate to be meaningful — Φ scores over connected graph entities are a fundamentally
different (and better) measurement than Φ over flat search results. The academic paper
also benefits from this order: the KG is the methodological argument, IIT is the
measurement layer on top of it.

**Alternatives considered:**  
- Implement basic Φ in parallel with KG (rejected: scope creep, no baseline to measure against)
- Skip KG and go straight to IIT (rejected: IIT over flat data is technically interesting but academically weaker)

---

### KGD-002 — Neptune Serverless, Not Provisioned

**Date:** March 2026  
**Status:** Active  
**Decision:** Use Amazon Neptune Serverless with 1–8 NCU range, not a provisioned instance.

**Rationale:**  
At ~1,500 garments and ~10,000–15,000 bridges (post data growth), query load is
low and irregular. Provisioned instances cost ~$200–400/month for a single writer.
Serverless scales to near-zero between sessions and costs ~$10–30/month at dev
usage. The 8 NCU cap is sufficient for the current dataset; increase the cap if
query times degrade after expansion to 10K+ items.

**Alternatives considered:**  
- Neo4j Aura Free (rejected: 50K node limit, no SPARQL for future LOD federation)
- Self-hosted Neo4j on Railway (rejected: operational burden, no managed failover)
- Provisioned Neptune (rejected: cost-prohibitive at this scale)

---

### KGD-003 — Bridges as Nodes, Not Edges

**Date:** March 2026  
**Status:** Active  
**Decision:** Promote bridges from Supabase junction table rows to first-class Neptune nodes.  
Bridge traversal uses: `(:Garment)-[:CONNECTED_VIA]->(:Bridge)-[:CONNECTS]->(:Garment)`

**Rationale:**  
If bridges are edges, they can't have their own relationships. A bridge that is an
edge can't `ARGUES_THROUGH` a DesignElement. It can't be the target of curatorial
validation. Bridge-as-edge is structurally correct for a database; bridge-as-node is
epistemologically correct for a knowledge graph that claims bridges are arguments.
The 2-hop cost (`CONNECTED_VIA` + `CONNECTS`) is worth it.

**Alternatives considered:**  
- Bridge as edge with rich properties (rejected: can't have its own relationships; can't ARGUES_THROUGH)
- Hybrid: edge for simple queries, node for rich traversal (rejected: two representations of same entity)

---

### KGD-004 — LPG (openCypher), Not RDF

**Date:** March 2026  
**Status:** Active  
**Decision:** Use Labeled Property Graph with openCypher as primary query language. SPARQL reserved for future LOD federation only.

**Rationale:**  
The operational graph is an application graph — it needs fast traversal, rich
properties on edges, and developer-friendly queries. LPG is purpose-built for this.
RDF's triple decomposition makes edge properties painful (requires reification).
Neptune supports both on the same cluster, so SPARQL remains available for future
museum LOD federation without any migration.

**Alternatives considered:**  
- RDF-first from the start (rejected: developer velocity cost, reification complexity for bridge properties)
- Pure LPG with no SPARQL ever (rejected: forecloses museum federation, which is the paper's long-term goal)

---

### KGD-005 — Bridge Classification Pre-Computed in Supabase, Not in Export Scripts

**Date:** March 2026 (updated 2026-03-13)
**Status:** Active (revised — COMPLETE)
**Decision:** Classify bridges across **6 orthogonal dimensions** in a standalone script
(`tools/analysis/classify_bridge_dimensions.py`) during Phase 0 — before KG work begins —
and store the results as columns on `style_bridges` in Supabase. Neptune export
scripts read these columns directly; they do not re-classify.

The 6 dimensions replace the old single `semantic_type` column:
- `temporal_type` — transmission / continuation / echo / cross_vibe / contemporary
- `crossing_type` — same_context / cross_category / cross_culture / cross_category_culture
- `connection_mode` — **contrast / resonance / affinity** (simplified from 5 modes to 3 sharp ones; see Decision #35)
- `primary_axis` — volume / ornament / body / register
- `secondary_axis` — volume / ornament / body / register
- `contrast_pair` — e.g. "Exaggerated Volume <-> Column Minimalism" (contrast only)

**Status as of 2026-03-13:** COMPLETE. 14,194/14,223 bridges classified.
Distribution: affinity 10,886 / contrast 3,314 / resonance 23.

**Rationale:**
The original single `semantic_type` conflated temporal distance, categorical crossing,
and aesthetic connection into one if/elif chain. This made it impossible to query
"all contrast bridges that are also cross-cultural transmissions." The 6-dimension
model decomposes bridge meaning into independent axes, enabling precise filtering in
the API/frontend and giving the narrative generator a rich scaffold. Running in Phase 0
means the values are immediately useful in the Supabase-backed API — no Neptune required.
The rule-based classifier is transparent, reviewable, and correctable.

**Alternatives considered:**
- Keep single semantic_type (rejected: too coarse, conflates orthogonal concerns)
- Classify only during Neptune export (rejected: loses the immediate UI benefit)
- Claude re-enrichment for classification on all bridges (rejected: ~$50–100 cost; rule-based is sufficient)
- No classification until KG is live (rejected: classification is the academic contribution; should be visible ASAP)

---

### KGD-006 — Supabase + Neptune Permanently (Not a Transitional State)

**Date:** March 2026  
**Status:** Active  
**Decision:** Two databases permanently. Supabase for relational/vector data; Neptune for graph traversal. Not a migration path toward one database.

**Rationale:**  
These databases excel at fundamentally different tasks. Postgres is the right tool
for: display data, auth, flat lookups, pgvector similarity search, bridge table
storage. Neptune is the right tool for: multi-hop traversal, relationship-first
queries, emergent cluster discovery. Trying to consolidate to one means either:
(a) Postgres for graph traversal — painful recursive CTEs that degrade at 3+ hops,
or (b) Neptune for everything — no auth, no RLS, no pgvector, no simple flat queries.
The dual-database pattern with shared Supabase integer IDs and application-layer
joins is the correct architecture.

**Alternatives considered:**  
- Postgres + recursive CTEs for graph (rejected: performance degrades badly at 3+ hops)
- Neptune for everything (rejected: no auth, no pgvector, no simple flat queries)
- Neo4j for everything (rejected: no vector search, no auth, no PostgREST)

---

### KGD-007 — Getty AAT Mapping is Manual, Not Automated

**Date:** March 2026  
**Status:** Active  
**Decision:** Getty AAT URI mapping for DesignElements is done manually for top 50 elements, not via automated lookup.

**Rationale:**  
Getty AAT has no reliable free API for bulk lookup. The vocabulary is specialized
enough that fuzzy string matching produces bad results. Manual mapping of 50 elements
takes 4–6 hours and produces authoritative, defensible URIs for the academic paper.
Elements outside the top 50 are left with `aat_uri: null` and populated incrementally.

**Alternatives considered:**  
- Automated string matching against AAT (rejected: too many false positives in fashion vocabulary)
- Skip AAT entirely (rejected: forecloses museum LOD federation; AAT is the lingua franca of museum KGs)
- Map all 150–300 elements manually (rejected: scope creep; top 50 covers the meaningful ones)

---

### KGD-008 — Phase 1 Skips InfluenceChain and DesignMovement Nodes

**Date:** March 2026  
**Status:** Active  
**Decision:** `(:InfluenceChain)` and `(:DesignMovement)` node types deferred to Phase 2.
Phase 1 derives movements and chains via traversal queries, not stored nodes.

**Rationale:**  
Named InfluenceChains require curatorial judgment. DesignMovements require cluster
analysis on top of a populated graph. Neither can be meaningfully populated during
bulk load. Both can be *queried* in Phase 1 through Cypher traversal, which is
sufficient to validate the concept and power the frontend.

**Alternatives considered:**  
- Generate algorithmic names for chains in Phase 1 (deferred: Claude generation is possible but adds scope)
- Include empty nodes as placeholders (rejected: empty nodes add noise without value)

---

### KGD-009 — Neptune as Intentional Second Database (Not Contradicting Qdrant Elimination)

**Date:** March 2026  
**Status:** Active  
**Decision:** Introducing Neptune as a second database is the right choice even after
consolidating Qdrant → Supabase pgvector in March 2026. These decisions are not
in conflict.

**Rationale:**  
Qdrant was eliminated because it added operational complexity without providing a
unique capability — pgvector in Supabase does the same vector similarity job with
zero additional infrastructure. That consolidation was the right call.

Neptune is different. Graph traversal — specifically multi-step bridge traversal
at 3+ hops with semantic type filtering — is a category of query that Postgres
cannot do well. Recursive CTEs work at depth 2; at depth 3+ with filtered paths
they degrade badly and the code becomes unmaintainable. Neptune is the right tool
for this specific capability. The operational cost of a second database is justified
because Neptune provides something pgvector cannot: pointer-based traversal that
doesn't slow down with dataset size.

The rule for this project's database decisions:
- One database can do the job comparably → consolidate (Qdrant → pgvector)
- Only a specialized tool can do the job → add the tool (Neptune for graph traversal)

**Alternatives considered:**  
- Postgres recursive CTEs for multi-step bridges (rejected: degrade at depth 3+; complex to write and maintain)
- Skip multi-step bridges entirely (rejected: this is the core academic and product differentiation)
- Build Neptune before deploying (rejected: deploy first; Neptune when multi-step bridge UI is planned)

---

## Template for New Decisions

Copy this block when logging a new decision:

```
### KGD-XXX — [Short Title]

**Date:** [Date]  
**Status:** Active  
**Decision:** [One sentence: what was decided]

**Rationale:**  
[Why this, not something else. Be honest about tradeoffs.]

**Alternatives considered:**  
- [Alt 1] (rejected: reason)
- [Alt 2] (rejected: reason)
```
