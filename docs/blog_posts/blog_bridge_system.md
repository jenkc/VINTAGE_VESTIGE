# Building the Bridge: Connecting Fashion Across Centuries

Two days of debugging, refactoring, and building something that actually works.

---

Vintage Vestige started as a question: what if you could search for "dark academia aesthetic" and get results from the Met Museum alongside modern fashion datasets? The search works. The enrichment pipeline works. But this week I tackled the next layer — **style bridges**, the system that finds hidden connections between garments across eras and categories.

It did not go smoothly.

## The problem with pairing things with themselves

The first sign of trouble was the bridge report showing duplicate images. The same Smithsonian gown, paired with itself, scoring 0.964. Of course it's a strong match — it's literally the same item.

Five self-referencing bridges had slipped through from an earlier pipeline run. The Qdrant vector search uses a `HasIdCondition` filter to exclude the query item from its own results, and that works fine — but these ghosts were from before that filter existed. I deleted them from the database and added a guard at insert time so it can't happen again.

While investigating, I also discovered that Qdrant's payload fields for `platform` and `fp_category` were empty for most products. This meant the cross-category filter in the bridge engine was silently matching nothing — it was searching with conditions on fields that didn't exist. A backfill script across all 866 products fixed that.

## The bidirectional bridge problem

With self-matches cleaned up, the next issue was subtler. The system was storing bridges in both directions: A→B and B→A, each as a separate row. ~15,000 bridges became 7,324 after introducing canonical ordering — always store `min(id)` as source, `max(id)` as target, with a unique constraint to catch duplicates at the database level.

This is the kind of thing that's obvious in retrospect but easy to miss when you're focused on making the scoring logic work. The fix was a few lines of code. The investigation took considerably longer.

## A broken narrative generator

The project had two files related to bridge narratives: `generate_bridge_narrative()` in `claude.py` (the method that actually calls Claude), and `generate_narratives.py` (a standalone script meant to batch-process all bridges). Both were broken.

The method had an indentation bug — it was outside the class body, so calling `self.client` would fail at runtime. The script was a 20-line stub referencing a column name that didn't exist (`narrative` instead of `bridge_narrative`) and had no processing loop.

I fixed the method, rewrote the script from scratch, and bumped `max_tokens` from 100 to 200 because narratives were getting cut off mid-word. The rate limiter (a 0.3-second sleep between API calls) was also unnecessary — with ~4 seconds of natural API latency per call, the sleep was doing nothing useful. Removed it, added async concurrency with a semaphore, and went from 0.25 requests/second to about 2.1/second.

## What the bridges actually found

The highest-scoring bridge (0.935) connects a Met Museum robe to a fashion plate — both embodying the Georgian shift toward neoclassical simplicity, with empire waistlines and lightweight cotton muslin. The narrative Claude generated for it genuinely reads well.

Other strong connections: a Fruit of Islam uniform and its jacket (shared military tailoring DNA), Mary Lincoln's dress and her purple velvet evening bodice (Victorian fit-and-flare with off-the-shoulder necklines), and a pair of Women's US Army Service garments spanning decades but sharing the same precise silhouette language.

The bridge type distribution is healthy: 54% same-era, 24% cross-category, 15% cross-era, 6% near-era, 1% cross-vibe. The cross-era bridges are the most interesting from a product perspective — connecting a Regency-era muslin dress to a modern cottagecore garment through shared structural DNA.

## Testing everything

I wrote 37 new tests across two files. The unit tests cover structural scoring (Jaccard similarity for set fields, weighted field matching), temporal classification (boundary conditions at exactly 10, 11, and 31 years), and date extraction from formats like "ca. 1920", "late 19th century", and "1860-1870". The data integrity tests verify bridge invariants against the live database: no self-references, canonical ordering, no orphaned references, valid score ranges, parseable JSON in shared_attributes.

All 156 tests pass. Zero failures.

## Current state

- **866 products** across Fashionpedia (500), Met Museum (200), and Smithsonian (166)
- **7,324 unique bridges** with canonical ordering and deduplication
- **22 narratives generated** (7,302 remaining — about a 30-minute run at ~$13)
- **156 tests passing** across unit, integration, data integrity, and search quality suites
- Bridge scores range from 0.300 to 0.935, averaging 0.556

The scoring formula combines text similarity (0.40), image similarity (0.30), and structural matching (0.30) using the Fashionpedia taxonomy — silhouette, neckline, waistline, sleeve length, textile pattern, and more. When image embeddings aren't available, the weights shift to 0.55 text / 0.45 structural.

## What I learned

Debug the data before debugging the code. Half the issues this week were data problems masquerading as logic bugs — missing Qdrant payloads, stale bridge rows from old pipeline runs, a column name mismatch between the code and the schema. The actual algorithms were fine. The plumbing around them needed work.

Also: canonical ordering for undirected relationships is one of those patterns that should be the default, not an afterthought. If A connecting to B is the same as B connecting to A, enforce that at the data layer from day one.

---

*Next up: generating the remaining 7,300 narratives, and building the web interface that lets people actually explore these connections.*
