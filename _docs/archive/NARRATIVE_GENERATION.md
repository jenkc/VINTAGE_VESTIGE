# Bridge Narrative Generation — Reference & Critique

## What It Does

Every style bridge connects two garments across time, culture, or category. The **bridge narrative** is a single AI-generated sentence that explains *why* these two items are connected — the human-readable story behind the numerical score.

Example: A 1920s Japanese kimono and a 2019 wrap dress might get:
> *"Both garments use the wrapped closure as both structural logic and cultural statement, separated by a century but united by the gesture of dressing."*

This is the only part of the bridge system where Vintage Vestige speaks in a human voice. Everything else — scores, classifications, shared attributes — is computed. The narrative is *authored*.

---

## Architecture

### Pipeline Order

```
compute_bridges.py          →  creates bridge rows (scores, shared_attributes)
classify_bridge_dimensions.py →  adds temporal_type, crossing_type, connection_mode, axes, contrast_pair
generate_narratives.py       →  fills bridge_narrative using Claude
```

Narratives run last because they consume classification data (connection_mode, contrast_pair) to shape the prompt.

### Files

| File | Role |
|------|------|
| `analysis/generate_narratives.py` | Orchestrator — async batched, semaphore-bounded |
| `enrichment/claude.py` (line 662) | `generate_bridge_narrative_async()` — prompt + API call |
| `enrichment/claude.py` (line 636) | `generate_bridge_narrative()` — sync version (legacy, unused by script) |
| `vv-web/src/components/bridge/NarrativeBlock.tsx` | Frontend display — italic blockquote |
| `vv-web/src/components/bridge/BridgeCardFull.tsx` | Shows narrative in full bridge cards |
| `vv-web/src/components/bridge/BridgeCardCompact.tsx` | Shows narrative inline in compact cards |

### Data Flow

```
Product A  ──┐
              ├──→  Claude prompt  ──→  1 sentence  ──→  style_bridges.bridge_narrative
Product B  ──┘
              ↑
     shared_attributes, connection_mode, contrast_pair
```

---

## The Prompt (async version)

### System Message
```
You are a fashion historian. Write exactly one sentence, max 30 words. No quotes, no preamble.
```

### User Message
```
These two fashion items share a style connection:

ITEM A: {title}
  Era: {era} | Culture: {culture}
  Material: {material} | Silhouette: {silhouette}
  Function: {social_function}

ITEM B: {title}
  Era: {era} | Culture: {culture}
  Material: {material} | Silhouette: {silhouette}
  Function: {social_function}

Shared attributes: {shared_attributes dict}
{mode_hint — varies by connection_mode}
Explain what connects them. Focus on the shared design DNA and how it transcends time.
```

### Mode Hints (appended conditionally)

| connection_mode | Hint added to prompt |
|-----------------|---------------------|
| `contrast` | "These items make OPPOSING arguments on the same axis: {contrast_pair}. Explain the tension." |
| `resonance` | "These items speak the same aesthetic language despite temporal distance. Explain what echoes." |
| `affinity` | *(none — default prompt)* |

### API Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| model | claude-sonnet-4-20250514 | Via `ClaudeEnricher.model` |
| max_tokens | 200 | Increased from 100→120→200 to prevent truncation |
| temperature | 0.6 | Moderate creativity — enough variation to avoid repetition |

---

## The Script

### Key Mechanics

- **Resume-safe**: Filters on `bridge_narrative IS NULL` — safe to interrupt and restart
- **Async concurrent**: Uses `asyncio.Semaphore(concurrency)` to cap parallel API calls (default: 5)
- **Batched DB writes**: Fetches `concurrency * 10` bridges per batch, commits after each batch
- **Pre-loaded products**: All products loaded as plain dicts before async loop (avoids SQLAlchemy session threading issues)
- **Priority order**: Processes highest `text_similarity` bridges first (most interesting connections get narratives first)
- **Progress tracking**: Prints rate and ETA after each batch

### CLI

```bash
venv/bin/python analysis/generate_narratives.py                    # all bridges
venv/bin/python analysis/generate_narratives.py --limit=100        # test run
venv/bin/python analysis/generate_narratives.py --concurrency=10   # faster (costs same)
```

---

## Critique

### What Works

1. **Mode-aware prompting** — Contrast bridges get a tension-focused prompt, resonance bridges get an echo-focused prompt. This means the narrative actually reflects the *type* of connection, not just a generic "these are similar."

2. **Resume safety** — You can kill the script and restart without reprocessing. Critical for a multi-hour run over thousands of bridges.

3. **Priority ordering** — High-similarity bridges get narratives first. If you stop early, the best connections have stories.

4. **Separation of concerns** — Classification runs before narrative generation, so the prompt has access to the full dimensional analysis.

### What Needs Attention

#### 1. The sync version is stale
`generate_bridge_narrative()` (line 636) still has the old prompt — no culture, no social_function, no mode hints, max_tokens=120. It's not used by the script, but it's dead weight that will confuse you later. Either update it to match the async version or delete it.

#### 2. The prompt says "transcends time" for every bridge
The closing instruction "Focus on the shared design DNA and how it transcends time" makes sense for transmission/echo bridges but is misleading for contemporary bridges (same era) or cross-culture bridges where time isn't the interesting axis. The prompt should vary by temporal_type and crossing_type, not just connection_mode.

Suggested approach:
- **echo/transmission**: "how it transcends time"
- **contemporary**: "how the same era produced different expressions"
- **cross_culture**: "how different cultures arrived at the same solution"
- **cross_category**: "how the same design logic appears in different garment types"

#### 3. "Exactly one sentence, max 30 words" — is that what you actually want?
The system message constrains to 30 words, but max_tokens is 200 (roughly 50-70 words). The constraint is fighting itself. More importantly: is one sentence enough for the "Same Question, Different Answers" view? Those contrast pairs might benefit from 2 sentences — one describing the tension, one noting what they still share.

Consider whether different connection_modes warrant different lengths:
- **affinity**: 1 sentence, ~25 words (simple family resemblance)
- **resonance**: 1-2 sentences, ~40 words (echo needs a bit more space)
- **contrast**: 2 sentences, ~50 words (tension + what unifies)

#### 4. shared_attributes is a raw dict dump
The prompt passes `{shared_attributes}` which renders as something like `{'silhouette': 'A-line', 'material': 'silk', 'neckline': 'V-neck'}`. Claude handles this fine, but a formatted version would give better results:

```python
shared_str = ", ".join(f"{k}: {v}" for k, v in shared_attributes.items())
```

This is minor but reduces cognitive load on the model.

#### 5. No vibe data in the prompt
The product dict includes `vibe` but it's never passed to the prompt. For contrast bridges especially, knowing that Item A has "Exaggerated Volume" and Item B has "Column Minimalism" would let Claude write much more specific narratives. The contrast_pair string gives the pair names, but Claude doesn't know which item has which vibe.

Consider adding:
```
  Vibes: {item_a.get('vibe', 'unknown')}
```

#### 6. No quality gate
Every narrative gets stored, even if Claude produces something generic like "Both items share similar design elements across eras." There's no validation that the narrative is actually interesting or specific. Options:
- Post-hoc: Query for narratives containing generic phrases ("share similar", "both feature", "connected by") and re-generate with a stricter prompt
- Inline: Check word count / reject if under 15 words (usually means Claude punted)

#### 7. Prompt whitespace
The async prompt (lines 672-684) has 8 spaces of indentation on every line because it's inside a class method. This gets sent to Claude as literal whitespace. It works but wastes tokens. Strip it or use `textwrap.dedent()`.

---

## How Narratives Serve the Project Goals

### The core thesis
Vintage Vestige's argument is that fashion doesn't just repeat — it *rhymes*. The bridge system proves this computationally (scores, shared attributes, classifications). But proof isn't persuasion. **The narrative is where the proof becomes a story.**

### For the user
A bridge score of 0.78 means nothing to someone browsing. "Both garments weaponize structured shoulders to project authority — one for a 1940s boardroom, the other for a 2023 runway" means everything. The narrative is the bridge's elevator pitch.

### For the "Same Question, Different Answers" view
This is where narratives matter most. The contrast bridges show that the same human need (protection, status, mourning, celebration) produces wildly different aesthetic solutions. Without a narrative, you're just looking at two pictures side by side. With one, you understand *why* the difference is interesting.

### For differentiation
Any fashion database can show "similar items." The narrative is what makes Vintage Vestige a *curatorial* experience rather than a search engine. It's the difference between "these match" and "here's why this matters."

### Cost and scale
At ~4,000-8,000 bridges, Sonnet at ~$0.003/narrative = roughly $12-24 total. Cheap enough to regenerate if you change the prompt strategy. This is an advantage — you can iterate on narrative quality without worrying about cost.

---

## Suggested Improvements (Priority Order)

### Now (before running generate_narratives.py)

1. **Delete or update the sync version** of `generate_bridge_narrative` — it's diverged from async
2. **Strip prompt whitespace** — `textwrap.dedent()` or unindent the f-string

### Soon (after first narrative run, review quality)

3. **Vary the closing instruction by temporal_type/crossing_type** — not everything "transcends time"
4. **Add vibe data to the prompt** — especially for contrast bridges
5. **Format shared_attributes** as readable text instead of raw dict
6. **Review a sample of 20-30 narratives** across connection modes — check for generic language, truncation, factual errors

### Later (if narrative quality needs leveling up)

7. **Differentiate length by connection_mode** — contrasts deserve 2 sentences
8. **Quality gate** — flag/regenerate generic narratives
9. **A/B test temperature** — try 0.7 or 0.8 for more distinctive voice
10. **Consider few-shot examples** — add 2-3 example narratives to the system prompt so Claude matches your preferred style
