let's add a way to start execution at a specific pass, like this last time around connection kept dropping during pass 3
Read compute_bridges.py
Grep "def (main|run_pass|pass_\d|compute_pass)" (in /Users/jenkim/PROJECTS/VINTAGE_VESTIGE/tools/analysis/compute_bridges.py)
1 line of output
Grep "^def |if __name__|argparse|--rebuild|Pass [1234]" (in /Users/jenkim/PROJECTS/VINTAGE_VESTIGE/tools/analysis/compute_bridges.py)
2 lines of output
Let me read more of the file, focusing on the function definitions and main block.

Read compute_bridges.py (from line 401)
Now I have a clear picture. Let me write the plan.

Write memoized-noodling-hippo.md
37 lines
Claude’s Plan
Plan: Add --start-pass flag to compute_bridges.py
Context
When running bridge computation, the Supabase connection can drop during later passes (e.g., pass 3). Currently there's no way to skip already-completed passes and resume from a specific one — you have to re-run everything from pass 1. This wastes time and re-does work that's already persisted in the DB.

Changes
File: tools/analysis/compute_bridges.py

1. Add --start-pass=N CLI argument (lines ~1074-1086)
Parse a new --start-pass=N flag (default 1, valid 1-4) in the __main__ block and pass it to compute_bridges().

2. Add start_pass parameter to compute_bridges() (line ~824)
Add start_pass=1 parameter to the function signature.

3. Gate each pass on start_pass (lines ~896-1013)
Wrap Pass 1 (the per-product similarity loop, lines 912-972) in if start_pass <= 1:
Wrap Pass 2 (opposition, line 1002) in if start_pass <= 2:
Wrap Pass 3 (function, line 1007) in if start_pass <= 3:
Pass 4 (structural) always runs since it's the last pass
The shared setup code (loading products, product_map, embedding_cache, existing_pairs) must always run regardless of start_pass, since passes 2-4 need product_map and existing_pairs for dedup.

4. Adjust the "detach products" block
The expunge/bulk-load block (lines 982-999) should run whenever start_pass >= 2, since it's needed for passes 2-4. When skipping pass 1 entirely, we still need to load existing_pairs and embedding_cache.

5. Update usage docstring (line 17)

Usage:
  python analysis/compute_bridges.py [--rebuild] [--limit=N] [--start-pass=N]
Verification
python tools/analysis/compute_bridges.py --start-pass=3 should skip passes 1-2, load existing pairs for dedup, then run passes 3 and 4
python tools/analysis/compute_bridges.py (no flag) should behave identically to current behavior
python tools/analysis/compute_bridges.py --rebuild --start-pass=2 should clear all bridges then run passes 2-4 (edge case: warn that rebuild + start-pass > 1 will delete pass 1 results)
User approved the plan
Let me make the changes. I'll start with the docstring, function signature, and CLI parsing, then gate the passes.

Edit compute_bridges.py
Modified
Edit compute_bridges.py
Added 1 line
Now let me add the warning for --rebuild + --start-pass > 1, and gate the passes.

Edit compute_bridges.py
Added 2 lines
Now gate pass 1 (the per-product similarity loop):

Edit compute_bridges.py
Added 6 lines
Now gate passes 2-4:

Edit compute_bridges.py
Added 8 lines
Now add the CLI parsing for --start-pass:

Edit compute_bridges.py
Added 6 lines
Done. Here's what changed:

--start-pass=N CLI flag (1-4, default 1) — skips all passes before N
Each pass is gated with if start_pass <= N:, so --start-pass=3 skips passes 1-2 and runs 3+4
Shared setup (loading products, existing_pairs for dedup, embedding_cache) always runs so later passes have what they need
A warning prints if you combine --rebuild with --start-pass > 1 since rebuild deletes everything including earlier passes' results
Usage: python tools/analysis/compute_bridges.py --start-pass=3 to resume from the function pass.

git push error:
(venv) jenkim@Mac-3201 VINTAGE_VESTIGE % git push
Enumerating objects: 396, done.
Counting objects: 100% (392/392), done.
Delta compression using up to 8 threads
Compressing objects: 100% (299/299), done.
Writing objects: 100% (307/307), 508.97 KiB | 13.05 MiB/s, done.
Total 307 (delta 118), reused 0 (delta 0), pack-reused 0 (from 0)
error: RPC failed; HTTP 408 curl 22 The requested URL returned error: 408
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly
Everything up-to-date
compute_bridges keeps having resilient-session reporting the connection dropped.
That "HTTP 408" is a request timeout from the remote — likely GitHub timing out on a large push. The "Everything up-to-date" at the end is misleading (it prints after the failure).

A few things to try:

Increase the HTTP post buffer — your push is ~509KB which shouldn't be huge, but this often helps:


git config http.postBuffer 524288000
Then retry the push:


git push
If it still fails, try pushing over SSH instead of HTTPS — SSH doesn't have the same HTTP timeout issues. You can check your remote with git remote -v and switch to SSH if needed.

As a last resort, you could push in smaller chunks by pushing specific commits rather than all at once — but given the size (~509KB), the buffer fix usually does it.

Let me check the current database session config to see what resilience settings are in place.

Grep "SessionLocal|create_engine|pool|prepare_threshold" (in /Users/jenkim/PROJECTS/VINTAGE_VESTIGE/storage/database.py)
2 lines of output
Read database.py
The issue is that the ResilientSession only retries once. During long-running passes like pass 3 (function matching), the Supabase pooler drops idle connections, and a single retry may not be enough — or the retry itself can fail if the connection pool is exhausted.

Here's what I'd suggest changing in storage/database.py:

Retry with a small loop (e.g., 3 attempts with a brief sleep) instead of just one retry
Dispose the engine's connection pool on failure so it forces fresh connections
Here are the changes:

Edit database.py
Added 1 line
Edit database.py
Added 13 lines
Here's what changed:

3 retries instead of 1, with escalating delays (1s, 3s, 5s)
engine.dispose() on each failure — this clears the stale connection pool so the next attempt gets a truly fresh connection from Supabase's pooler
If all 3 retries fail, it re-raises the original error so you know something bigger is wrong
This should handle the Supabase pooler dropping idle connections during the long pass 3 function-matching loops. Combined with your new --start-pass=3 flag, you've got a safety net either way.

is my internet connection decent?
That's outside what I can check — I don't have access to your network or any way to run diagnostics on your internet connection.

But the git push 408 and Supabase pooler drops are both consistent with either:

Flaky connection (packet loss, high latency)
Supabase pooler idle timeouts (which happen regardless of your connection quality)
Quick way to test from your terminal:


ping -c 10 google.com
If you're seeing low packet loss and <50ms latency, your connection is probably fine and it's the Supabase pooler doing its thing. The retry changes we just made should handle that.

what is the pooler actually doing?
The Supabase connection pooler (PgBouncer) sits between your app and the actual PostgreSQL database. It manages a shared pool of persistent DB connections so that every SessionLocal() call doesn't have to open a brand new TCP connection + TLS handshake + Postgres auth from scratch.

How it works:

Your app connects to pooler.supabase.com:6543
PgBouncer accepts that connection and assigns it one of its pre-opened connections to the real Postgres
When your session goes idle, PgBouncer can reclaim that backend connection and give it to someone else
Why connections drop:

PgBouncer has an idle timeout (~300s on Supabase's free/pro tier). If your session holds a connection but doesn't send any queries for that long — which happens in compute_bridges when:

Pass 3 is doing a ton of in-memory Python work (nested loops, structural scoring, cosine sim) between DB writes
The db.commit() only happens after processing an entire function group
...PgBouncer says "you're idle, I'm taking this connection back" and your next db.execute() or db.commit() hits a dead socket.

What your current config does about it:

pool_pre_ping=True — SQLAlchemy pings before checkout, but that only helps on new checkouts from the pool, not mid-session drops
pool_recycle=280 — recycles connections before the 300s timeout, but again only on checkout
ResilientSession — catches the OperationalError and retries with a fresh connection (now up to 3 times)
The core tension is that passes 2-4 do heavy Python computation between DB calls, so the connection sits idle long enough for PgBouncer to kill it. The retry logic patches over it; --start-pass gives you a manual escape hatch if retries aren't enough.

can we do db calls when python finishes its computations
Good idea. Right now passes 2-4 do all the Python computation (structural scoring, cosine sim), accumulate bridges in memory, then only hit the DB at the end for batch inserts + commit. But the DB session is opened at the start of each pass and sits idle the whole time.

The fix: don't open the session until it's time to write. The _get_embeddings calls in passes 2-4 already read from the in-memory embedding_cache (bulk-loaded before passes start), so they don't need a live DB connection either — the db param is just a fallback that never triggers after bulk load.

Let me refactor the three pass functions to only open a session for the insert phase.

Read compute_bridges.py (lines 564-643)
The _get_embeddings calls pass db but after bulk load they only read from embedding_cache. I need to make those calls not require db at all, then restructure each pass to compute in-memory first and only open a DB session for the insert batch.

Edit compute_bridges.py
Added 9 lines
Now pass 3:

Edit compute_bridges.py
Added 8 lines
Now pass 4:

Edit compute_bridges.py
Added 10 lines
Now update the call sites in compute_bridges() — they no longer pass db:

Edit compute_bridges.py
Removed 5 lines
Now each pass function manages its own DB session internally — opened only for the insert phase. Let me verify the summary section still works (it opens its own session):

Read compute_bridges.py (lines 1031-1050)
Read compute_bridges.py (lines 1051-1070)
Good — the summary opens its own SessionLocal(). Everything looks clean.

Here's what changed:

Passes 2-4 no longer hold a DB session during computation. Each pass now has two phases:

Compute phase — all Python work (structural scoring, cosine sim from embedding_cache, filtering) runs with zero DB connections open
Insert phase — opens a fresh SessionLocal(), batch-inserts the results, commits, closes
_get_embeddings(db, id, cache) replaced with embedding_cache.get(id, (None, None)) — since bulk load already populated the cache, the DB fallback was never triggering anyway

This means the connection can't go idle during the heavy computation loops — it simply doesn't exist yet. The DB session only lives for the brief insert+commit at the end of each pass.

---

## Session: 2026-03-10 — Bridge tuning & blazer domination fix

### Context
Ran compute_bridges.py through all 4 passes for the first time. Multiple crashes and issues along the way.

### Bugs fixed
- **DetachedInstanceError on Pass 2**: `fresh_db()` closed the session but `product_map` objects were still bound. Fixed by eager-loading all 15+ fields then `db.expunge(p)` before closing session.
- **Missing structural fields in eager-load**: Initial touch list missed 10 fields (nickname, neckline, length, waistline, sleeve_length, textile_pattern, opening_type, garment_parts, decorations, textile_finishing). Added all STRUCTURAL_WEIGHTS fields.
- **Summary queries using closed session**: Added `db = SessionLocal()` before summary section.
- **Empty existing_pairs on resume**: Loaded all existing `(source_id, target_id)` from DB at startup for dedup.

### Performance improvements
- **bulk_load_embeddings()**: Loads all embeddings in one query into a dict, replacing thousands of individual DB fetches during passes 2-4.
- **Session cycling**: Each pass gets its own `SessionLocal()` → close cycle to avoid pooler timeouts.

### Caps increased
- Opposition (Pass 2): `top_per_pair` 20 → 150
- Function (Pass 3): `top_per_function` 15 → 150 (was 50 briefly)
- Structural (Pass 4): `top_per_group` 10 → 30

### Blazer domination problem
After all passes completed, queried opposition bridges and found one "Hip Blazer" from Fashionpedia appeared in 10+ of top 30 bridges. Root cause: `fp_category` at 0.16 weight is the heaviest single field — two blazers trivially hit 0.28 from category + silhouette alone.

### Decided changes (not yet applied to code)

**1. Rebalance structural weights** — shift weight from basic taxonomy to cross-cultural fields:
- `fp_category`: 0.16 → 0.06 (table stakes, not interesting)
- `construction_technique`: 0.10 → 0.14
- `social_function`: 0.07 → 0.12
- `motif_family`: 0.07 → 0.12
- Other minor adjustments to sum to 1.0

**2. Per-product participation cap** — greedy diversified selection loop:
- Track `product_appearances` dict across all pairs/groups within a pass
- Skip bridges where either product exceeds `max_appearances` (suggested 8)
- Apply to passes 2, 3, and 4

**3. Lower gate thresholds** (discussed, optional):
- Opposition structural gate: 0.30 → 0.20
- Function average gate: 0.25 → 0.18
- Structural floor: 0.40 → 0.30

### Plan
User will apply weight changes + participation caps, then run `--rebuild` overnight to recompute all bridges from scratch with new scoring.

---

## Session: 2026-03-12 — Rebuild run + opposition composite score

### Changes applied to code
- **Structural weights rebalanced** — fp_category 0.16→0.06, cross-cultural fields up to 0.38 combined
- **Per-product participation caps** — `max_appearances=8` in passes 2-4 with greedy selection
- **top_per_function** bumped to 150
- **Rebuild block restored** — was missing, `--rebuild` now properly deletes existing bridges
- **Startup session cycling** — products loaded on throwaway session with eager-load + expunge, separate sessions for embeddings/existing_pairs
- **Pre-parsed JSON set fields** — `preparse_set_fields()` runs at startup, `compute_structural_score` uses cached sets
- **Group size cap** — Pass 4 caps groups at 100 products (Pass 3 still needs this added)
- **Removed duplicate expunge block** before passes 2-4 (products already detached at startup)
- **Fixed missing `embedding_cache={}` and `start_time`** — lost during reorganization

### Rebuild results (15,619 total bridges)
- Pass 1 (similarity): 10,243 bridges (cross_vibe 4161, transmission 3416, echo 2107, continuation 533, null 26)
- Pass 2 (opposition): 1,317 bridges
- Pass 3 (function): 2,545 bridges
- Pass 4 (structural): 1,514 bridges
- Runtime: 1486.6s (~25 min)

### Remaining issue: opposition sort key
Top opposition bridges dominated by "Constructed Armor <-> Body Liberation" axis (18/20 top results) and suited garments. Sorting by structural_score rewards garment types with the most populated fields.

### Next: opposition composite sort score
Proposed formula (not yet implemented):
```
opposition_sort_score = (
    0.40 * cross_cultural_score_norm   # Jaccard on 3 cross-cultural fields, normalized
  + 0.35 * temporal_distance_norm      # era gap / 200, capped at 1.0
  + 0.25 * structural_score            # full structural score
)
```
Also: add group cap to Pass 3 (same pattern as Pass 4).

---

still dropping connection, do we need to do this in batches
Yeah, the insert phase is probably sending hundreds of individual INSERT statements on a single session, which can still take long enough to trigger issues. Let's batch them.

Read compute_bridges.py (lines 375-389)
I'll add a batch insert helper and update each pass to use it — open a fresh session per batch of ~100, commit, close, repeat.

Edit compute_bridges.py
Added 25 lines
Now let me update the three pass functions to use _batch_insert_bridges instead of managing their own sessions.

Edit compute_bridges.py
Added 3 lines
Edit compute_bridges.py
Removed 1 line
Edit compute_bridges.py
Removed 1 line
Now each pass:

Computes everything in memory with no DB connection
Hands all bridges to _batch_insert_bridges which opens a fresh session per 100 inserts, commits, closes
Each batch session lives for just a few seconds max — well under the pooler's 300s timeout. Give it another run.