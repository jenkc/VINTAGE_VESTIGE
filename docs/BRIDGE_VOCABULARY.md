# Bridge Vocabulary: Vibes vs. Cross-Cultural Fields

Two different vocabulary systems power the bridge pipeline. They work at different stages and answer different questions.

---

## Vibe Vocabulary (Discovery Layer)

**What it is:** Aesthetic descriptors assigned during enrichment.

**Fields:**
- `core_vibes` — 1-3 terms from a controlled list (e.g., romantic, minimalist, punk, bohemian)
- `bridge_vibes` — 1-2 terms most likely to connect across eras
- `vibe_scores` — confidence scores for each assigned vibe

**Where it lives:** On each product, written during enrichment.

**How it works:** Vibes get baked into the `enriched_text` string, which is what the MiniLM embedding model encodes into a 384-dimensional vector. When two products share vibes like "romantic" or "punk," their vectors end up closer together in embedding space.

**What it does in the pipeline:** Vibes shape which candidates the vector search *finds*. A 1920s beaded flapper dress and a 2020s festival top might both carry "glamorous" and "bohemian" vibes, so their embeddings cluster together, and the vector search surfaces them as candidates.

**Analogy:** Vibes are the *casting call*. They decide who shows up to the audition.

---

## Cross-Cultural Fields (Filtering Layer)

**What it is:** Material, functional, and visual DNA of a garment.

**Fields:**
- `construction_technique` — how it was made (e.g., resist-dyeing, hand-embroidery, pleating, batik, lacework)
- `social_function` — why it existed (e.g., wedding, mourning, workwear, status-signaling, festival-celebration)
- `motif_family` — its visual language (e.g., geometric, floral, paisley, tree-of-life, chevron-zigzag)

**Where it lives:** On each product, written during enrichment (or backfilled for products enriched before these fields existed).

**How it works:** These fields are checked *after* vector search finds candidates, specifically during the **cross-category pass** in `compute_bridges.py`. The `shares_cross_cultural_field()` function checks whether two products share at least one value in any of these three fields. If they don't, the bridge is rejected.

**What it does in the pipeline:** Cross-cultural fields act as a **substance gate**. They prevent shallow bridges. A coat and a skirt might have similar embeddings (both "elegant," both "structured"), but unless they share something concrete — both use hand-embroidery, both serve a wedding function, both carry geometric motifs — the cross-category bridge is rejected.

**Analogy:** Cross-cultural fields are the *callback criteria*. Just because you showed up to the audition doesn't mean you get the part. You need to prove you belong.

---

## How They Work Together

```
Product A (1890s Victorian corset)
  vibes: romantic, structured, feminine
  construction_technique: ["hand-sewing", "boning"]
  social_function: ["status-signaling"]
  motif_family: ["floral"]

Product B (2020s structured bustier top)
  vibes: romantic, edgy, feminine
  construction_technique: ["boning", "machine-sewing"]
  social_function: ["everyday-practical"]
  motif_family: ["floral"]
```

### Step 1: Discovery (vibes → embeddings → vector search)
Both products share "romantic" and "feminine" vibes. Their enriched text embeddings are close in vector space. The pgvector search surfaces Product B as a candidate for Product A.

### Step 2: Filtering (cross-cultural fields → substance gate)
The cross-category pass checks: do they share a cross-cultural field?
- construction_technique: both have "boning" → **yes, shared**
- motif_family: both have "floral" → **yes, shared**

The bridge passes the substance gate. It gets scored and stored.

### Step 3: Scoring (structural weights → bridge score)
The structural score is computed from all Fashionpedia taxonomy fields (silhouette, neckline, etc.) plus the cross-cultural fields. The final bridge score blends:
- 40% text similarity (from vibes + enriched text)
- 30% image similarity (from CLIP embeddings)
- 30% structural score (from taxonomy + cross-cultural fields)

---

## Summary Table

| | Vibe Vocabulary | Cross-Cultural Fields |
|---|---|---|
| **Question** | What does this *feel* like? | What is this *made of* and *for*? |
| **Stage** | Discovery (vector search) | Filtering (substance gate) |
| **Mechanism** | Encoded into embeddings | Checked as set intersection |
| **Effect** | Determines which candidates surface | Determines which candidates survive |
| **Used in** | All three passes | Cross-category pass only |
| **Example** | "romantic," "punk," "minimalist" | "resist-dyeing," "wedding," "geometric" |

---

## Why Both Are Necessary

Without vibes, the vector search would only find items that share literal keywords. Two garments from different eras might use completely different terminology but evoke the same aesthetic — vibes capture that.

Without cross-cultural fields, cross-category bridges would be shallow. A dress and a jacket might both feel "bohemian," but that's not enough to justify a bridge. Shared construction techniques or social functions give the bridge a real story — something a narrative can be written about, something a user can learn from.

Vibes cast the net wide. Cross-cultural fields make sure what you catch is worth keeping.
