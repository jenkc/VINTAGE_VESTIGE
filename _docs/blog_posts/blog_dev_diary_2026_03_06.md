# Dev Diary: March 6, 2026 — Teaching an AI What a Dress Means

Today was about language. Not code language — the language a garment speaks. I spent the day building the vocabulary that Claude uses to describe *why* two pieces of clothing separated by centuries are making the same argument about the human body. Then I built the infrastructure to run that vocabulary through 3,368 museum objects overnight.

---

## What Actually Happened Today

### Replacing MMFashion with Claude Vision

The original plan called for MMFashion — a computer vision model from the academic fashion-AI world — to handle visual attribute extraction. Silhouettes, necklines, textile patterns, the Fashionpedia taxonomy fields. I'd written the integration plan, specced the pipeline, scoped the work.

Then I tried to install it.

`mmcv-full` depends on `pkg_resources` (deprecated), requires Python 3.8–3.10, and hasn't been maintained since 2023. My stack runs Python 3.13. The choice was: downgrade my entire environment for a model that does what Claude Vision already does, or just... ask Claude to look at the dress.

I chose the second thing.

`enrich_product()` already sends product images to Claude and returns structured JSON. The fix was expanding the prompt to cover all Fashionpedia taxonomy fields — silhouette, waistline, length, opening type, textile pattern, textile finishing, garment parts, decorations — and updating the merge logic to write them to the database.

No new dependencies. No model downloads. No separate batch process. One less moving part in the architecture.

### The Controlled Vibe Vocabulary

This is the decision I'm most interested to see play out.

The old enrichment prompt asked Claude for a `vibe` field — a 1-3 word free-text description. "Bohemian romantic." "Structured minimalism." "Punk adjacent." Every enrichment run produced slightly different language. You can't build a knowledge graph on vibes that shift with the wind.

The replacement is a controlled vocabulary of 20 terms organized across four aesthetic axes:

**Volume and Silhouette:** Exaggerated Volume, Column Minimalism, Empire Suspension, Constructed Armor, Draped Fluidity, Layered Accumulation

**Ornament and Surface:** Maximalist Ornament, Austere Restraint, Handcraft Visibility, Material Luxury, Pattern as Language

**Body Relationship:** Body Liberation, Body Transformation, Body Concealment, Body Display

**Cultural Register:** Pastoral Naturalism, Ceremonial Formalism, Dark Romanticism, Transgressive Subversion, Elite Distinction

Each term is an *argument*, not a label. "Body Liberation" isn't just a tag — it's the claim that the body should move freely, that fabric should follow rather than constrain. When Claude enriches a 1920s flapper dress and a 2024 jersey maxi dress, it can identify that both are making the same argument about the body even though they share almost nothing structurally.

A garment gets 1-3 `core_vibes` (its primary arguments) and 1-2 `bridge_vibes` (the arguments most likely to echo across centuries). The bridge vibes become nodes in the knowledge graph. A bridge that argues through "Body Liberation" connects garments across 500 years that are making the same ideological claim. That's a different kind of knowledge than a cosine similarity score.

### Building the Era Collection System

When Claude enriches a product, it assigns an era from our taxonomy of 54 canonical eras (Ancient Egyptian through Gorpcore). But Claude doesn't always use our exact names. It might return "Meiji Period" or "Tudor" or "Art Nouveau" — perfectly valid era descriptions that don't match our canonical list.

The old approach: print a warning on every single mismatch. Run 100 items, get 40 warnings scrolling past. Useless.

The new approach: silent collection during the run, structured report at the end.

`normalize_era()` now takes an optional `product_id` parameter. When an era string doesn't match any canonical name or alias, instead of printing a warning, it adds the raw string and the product ID to an in-memory collector. The collector is keyed on the lowercased era string, so `"Meiji Period"` and `"meiji period"` collapse into one entry.

At the end of the enrichment run, three things happen:
1. `report_unrecognized_eras()` prints a clean summary — each unique unrecognized era, how many products returned it, and the first 10 product IDs
2. `export_unrecognized_eras()` writes a CSV with the same data for review
3. After I add the new aliases to `ERA_ALIASES`, `fix_unrecognized_eras(db)` re-normalizes all those products in one pass

It's a feedback loop. Run enrichment, review the CSV, add aliases, fix the products. Each batch run teaches the taxonomy something new. The era dictionary grows from the data instead of being prescribed upfront.

### The Deployment Plan

With the Supabase migration done and the enrichment pipeline ready, I wrote the full deployment plan. Seven phases, 25 deliverables, dependency graph:

- **Phase 0 (Data):** Enrich all 3,368 remaining products, generate embeddings, recompute bridges, generate narratives
- **Phase 1 (Environment):** `.env.example`, CORS lockdown, frontend API URL as env var
- **Phase 2 (Frontend Testing):** Vitest + Testing Library, 7 component smoke tests, 3 page integration tests
- **Phase 3 (API Hardening):** Error handling audit, rate limiting
- **Phase 4 (Containerization):** Dockerfile, `.dockerignore`, local Docker verification
- **Phase 5 (Deploy):** Railway (API) + Vercel (frontend), 8-point end-to-end smoke test
- **Phase 6 (CI/CD):** GitHub Actions for lint, build, test on every push

The critical path runs through the data — enrichment takes ~5.5 hours — but everything else can be done in parallel.

---

## Decisions Made Today

### Claude Vision over MMFashion

Not a close call. MMFashion would have required a Python environment downgrade, a 2GB model download, a separate batch pipeline, and ongoing maintenance of a model last updated in 2023. Claude Vision does the same job inside the existing enrichment pipeline. The only cost is API tokens (~$0.025/item), and we're already paying that for the rest of enrichment.

### Controlled vocabulary over free-text vibes

This is a bet. Free-text vibes are richer in the individual case — "punk-inflected Edwardian revival" tells you more about one garment than "Transgressive Subversion, Dark Romanticism" does. But controlled terms are comparable across 4,234 garments and queryable in a knowledge graph. I chose the system that scales.

I'm keeping the free-text `vibe` field out of the prompts entirely for now. I want to see how bridges perform with just the controlled vocabulary. If the bridge narratives are weaker without the color of free text, I'll add it back. But I suspect the structured terms will produce *better* bridges because they force Claude to identify the actual aesthetic argument rather than reaching for evocative adjectives.

### Silent collection over loud warnings

A small infrastructure decision that changes the development workflow. When you're running 3,368 enrichments overnight, you don't want 800 warnings — you want a summary at the end. The era collection system turns a wall of noise into a CSV you can review over coffee. More importantly, it creates a path to resolution: review, alias, fix, repeat.

---

## What I Learned

The MMFashion decision crystallized something I've been circling around: the gap between "the right tool for the job" and "the tool that fits the system." MMFashion is probably more accurate at detecting neckline types than Claude Vision. But it doesn't fit the system — wrong Python version, wrong deployment model, wrong maintenance trajectory. Claude Vision is good enough at neckline detection and *it's already in the pipeline*. "Good enough and already integrated" beats "slightly better but requires a separate infrastructure."

The vibe vocabulary is a different kind of lesson. Controlled vocabularies feel reductive when you're looking at one garment. They feel powerful when you're looking at four thousand. The question is always: are you building for the individual case or the system? Fashion scholarship works in the individual case. Computational fashion intelligence works in the system.

---

## What's Next

Tonight: kick off the first batch of 100 enrichments, review the unrecognized eras CSV, add aliases, repeat. The full 3,368-product run will happen in batches over the next day or two (~$85 in API costs, ~5.5 hours of compute time).

After enrichment is complete: generate embeddings for all new products, recompute bridges with the full 4,234-product dataset, run the semantic type classifier, and generate bridge narratives. Then the deployment plan kicks in.

The part I'm most looking forward to: seeing what bridges emerge when the dataset is 5x larger. The original 866 products were mostly Met Museum and Fashionpedia — heavy on Western fashion history. The V&A collection adds 1,856 objects with broader cultural and geographic range. The cross-culture bridges should get a lot more interesting.

---

*Jen Kim / linuxgrrrl LLC*
*Building Vintage Vestige — where fashion history meets computational intelligence*
