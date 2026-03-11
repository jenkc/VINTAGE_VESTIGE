# Dev Diary: March 9, 2026 — The Great Reorganization (and Teaching an AI to Argue Better)

Today was a plumbing day. The kind of day where you move thirty files, fix twenty-three tests, and rewrite the guts of your AI narrator — and at the end, the application does exactly what it did before, except now it's ready to leave your laptop.

---

## What Actually Happened Today

### Moving Day: Scripts vs. Library Code

Vintage Vestige has been growing organically for three weeks. Scripts accumulate where they're written, not where they belong. The enrichment directory had both `claude.py` (a library that the API imports at runtime) and `enrich_async.py` (a CLI tool I run once to populate the database). The embeddings directory had both `generator.py` (runtime library) and `rebuild_embeddings.py` (one-time script). Storage had load scripts mixed in with the database ORM.

This matters because deployment is next. When I write a Dockerfile, I need to say "copy these five directories" and get exactly what the API needs — no data loading scripts, no migration tools, no one-time enrichment runners. If library code and scripts are mixed together, the Dockerfile either copies everything (bloated) or needs to exclude files from five different directories (fragile).

So I split them. Everything the API imports at runtime stays where it is: `api/`, `storage/`, `embeddings/`, `enrichment/`, `analysis/`. Everything you *run from the command line* moves to `tools/`:

```
tools/
├── analysis/          # compute_bridges, classify_bridge_dimensions, generate_narratives
├── enrichment/        # enrich_async, normalize_eras, backfill scripts
├── embeddings/        # generate_all_embeddings, rebuild_embeddings
├── data_loading/      # load_fashionpedia, load_met_vintage, load_va, etc.
├── data_quality/      # analyze_data_quality, classify_semantic_types
├── db_utils/          # view_database, wipe_database
└── migration/         # migrate_qdrant_to_pgvector, migrate_images_to_storage
```

The mechanical part: every script has a `sys.path.insert(0, project_root)` line that tells Python where the project root is, so `from storage.database import ...` works. Moving scripts one level deeper means changing `'..'` to `'..', '..'` — sixteen files, same change each time. Except three scripts in `db_utils/` that had *no* sys.path setup at all. Those just silently failed when you ran them from the wrong directory. Fixed.

### Temporal Classification: V&A Broke the Assumption

Here's a bug that only surfaces with the V&A Museum's collection. The temporal classifier had a fallback chain: if no era data exists, use the platform as a proxy. Met Museum = historical, Fashionpedia = modern. So `met_museum` vs `fashionpedia` → `transmission` (40+ year gap). Reasonable.

But the V&A has items from the 1600s *and* the 2000s. `va_museum` vs `va_museum` was returning `None` (unknown), which is technically correct but throws away the decade data we *do* have. And `va_museum` vs `met_museum` was returning... nothing useful, because "both historical" doesn't mean "same era."

The fix: before falling back to platform proxy, check if we have decade data. Parse "1870s" to 1875, "2010s" to 2015, compute the year gap, classify by distance. Only reach for the platform proxy when decades are also missing. And return `None` — honestly unknown — when two products share a platform and have no temporal data at all. Better to admit ignorance than guess wrong.

This also surfaced a code duplication issue. `classify_temporal_type` was defined in *both* `compute_bridges.py` and `classify_bridge_dimensions.py`, and they were starting to diverge. Deleted the duplicate, made `compute_bridges.py` the single source of truth.

### The SQL/Python Score Mismatch

This one was subtle. The bridge composite score in Python redistributes weights proportionally when image similarity is NULL. If a bridge has no image, the formula goes from `0.40*text + 0.30*image + 0.30*structural` to `(0.40/0.70)*text + (0.30/0.70)*structural` — the remaining weights absorb the missing component.

But the SQL in `bridge_queries.py` used `COALESCE(image_similarity, 0)`. That treats a missing image as "zero visual similarity" rather than "we don't know." A text-only bridge with excellent text and structural scores would rank below a mediocre bridge that happened to have an image, because 30% of its composite score was pinned to zero.

I rewrote the SQL as a 6-branch CASE statement: three connection modes (contrast, resonance, affinity) × two image states (present, null). Each branch uses the exact same weight redistribution as Python. The ordering now matches.

The other half of this fix: `text()` objects in SQLAlchemy don't support `.desc()` or comparison operators. I'd been using `text()` for the composite score expression, which broke when the routers tried to sort by it. Switched to `literal_column()` which wraps a raw SQL expression as if it were a column. Created a separate `_COMPOSITE_DESC` using `text()` specifically for ORDER BY clauses. Arcane SQLAlchemy distinction, but it matters.

### Narrative Generation Overhaul

The narrative system got a complete rewrite. Seven specific changes:

**1. Deleted the sync version.** `generate_bridge_narrative` (sync) had been dead code since the async version was built. Carrying two implementations of the same prompt is a maintenance liability — they inevitably diverge.

**2. Fixed whitespace.** The old prompt was built with f-string indentation inside a method body, which meant the actual prompt sent to Claude had random leading spaces from Python indentation. Switched to list-based construction: build prompt lines as a list, join them at the end.

**3. Varied closing instructions.** Instead of the same generic "Write a brief explanation" for every bridge, the closing now varies based on classification. An `echo` temporal type with `cross_culture` crossing gets: "Focus on how this aesthetic idea traveled across cultures and centuries." A `contrast` on the `body` axis gets: "Focus on the tension between these opposing approaches to the body." Eight distinct closings mapped from the classification dimensions.

**4. Added vibe data.** The prompt now includes both items' `core_vibes` — the controlled vocabulary of aesthetic tendencies ("Exaggerated Volume," "Transgressive Subversion," "Pastoral Naturalism"). This gives Claude the language to describe the connection in terms the system already understands.

**5. Formatted shared attributes.** Instead of dumping `{"fp_category": "dress", "silhouette": "a-line", "material": "silk"}` into the prompt, a new `_format_shared_attributes()` method converts it to readable text: "category: dress, silhouette: a-line, material: silk." Small thing, but Claude writes better narratives when the input reads like English.

**6. Differentiated length.** Contrast bridges get 2 sentences and 60 words. Resonance and affinity bridges get 1 sentence and 40 words. Contrasts need the space — sentence one establishes shared ground, sentence two describes the divergence. Affinity bridges can say what they need to say in one sentence because there's only one relationship to describe.

**7. Mode-specific system prompts.** The system message changes per mode:
- Contrast: "Write exactly two sentences, max 60 words total. First sentence: what they share. Second sentence: how they diverge."
- Resonance/affinity: "Write exactly one sentence, max 40 words."

### 228 Tests, All Passing

The reorganization broke 23 tests across 5 files. Each had a different cause:

- Wrong function signatures (classification tests called `classify_temporal_type(bridge, src, tgt)` but the function now takes individual fields)
- Stale assertions (same era + close decades used to return `None`, now correctly returns `'contemporary'`)
- Missing mock fields (MockBridge didn't have the 5 new classification columns)
- Wrong field count (enrichment test expected 23 fields, model now has 29)
- A `SyntaxWarning` from using `is 'contemporary'` instead of `== 'contemporary'` with a string literal

Fixed all of them. 158 unit tests pass, 70 integration tests pass. 5 remaining errors in `test_database_model.py` are SQLite ARRAY incompatibility — a separate issue, not related to today's changes.

---

## What I Learned

Reorganization work doesn't feel productive while you're doing it. You're not building features or fixing visible bugs. You're moving files, updating paths, and fixing tests that broke because you moved files and updated paths. It's the software equivalent of organizing your closet — necessary, invisible, thankless.

But it changes what's *possible*. Before today, writing a Dockerfile would have required listing every file to exclude. Now it's five COPY lines and a one-line .dockerignore. Before today, the narrative prompt was a frozen artifact from two weeks ago that didn't know about connection modes or classification. Now it speaks the same language as the rest of the system.

The temporal classification fix was a good reminder that assumptions baked into code have a way of becoming invisible. "Same platform means roughly same era" was true for Met + Fashionpedia. It was never true for V&A. The data tells you when your abstractions are wrong, if you listen to the test failures instead of working around them.

---

## What's Next

`compute_bridges.py --rebuild` is still crunching through 4,234 products. Once it finishes:

1. Run the classifier: `venv/bin/python tools/analysis/classify_bridge_dimensions.py`
2. Generate narratives: `venv/bin/python tools/analysis/generate_narratives.py`
3. Review 20-30 sample narratives across modes — do contrast narratives actually describe tension? Do resonance narratives describe echoes? Do affinity narratives find the thread?
4. Continue reorganization: docs cleanup (Phase 3), deployment files (Phase 4), verification (Phase 5)

Then deployment. Railway for the API, Vercel for the frontend, Supabase already running. The whole point of today's reorganization was to make that step trivial.

---

*Jen Kim / linuxgrrrl LLC*
*Building Vintage Vestige — where fashion history meets computational intelligence*
