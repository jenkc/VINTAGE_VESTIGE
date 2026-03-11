# Dev Diary: March 7, 2026 — A Dress Doesn't Just Look Like Another Dress. It Argues With It.

Today I gave Vintage Vestige the ability to describe *how* two garments are connected, not just *that* they are. A bridge between a 1780s robe a la francaise and a 2022 Balenciaga couture gown used to be a number — 0.73, similar, trust us. Now it's a contrast on the volume axis: "Exaggerated Volume <-> Column Minimalism." The system knows they're making opposing arguments about the same question: how much space should a body occupy?

---

## What Actually Happened Today

### The Six-Dimensional Bridge Classification

Until today, every style bridge had a single `bridge_type` label: `cross_era`, `near_era`, `cross_category`, `cross_vibe`. One overloaded string trying to describe temporal distance, categorical crossing, and aesthetic connection all at once. You couldn't ask "show me all contrast bridges that are also cross-cultural transmissions" because those concepts were tangled into a single column.

I replaced it with six independent dimensions:

**Temporal type** — How far apart in time are these garments? A `transmission` bridges 40+ years across different eras. A `continuation` connects garments within the same era but different decades. `Contemporary` means they coexist.

**Crossing type** — What boundaries does this bridge cross? `same_context` means both garments live in the same category and culture. `cross_category` means a dress is talking to a coat. `cross_culture` means Japanese textile craft is talking to French couture. `cross_category_culture` means both boundaries are crossed at once.

**Connection mode** — This is the one I care most about. Three modes:

- **Contrast**: The garments make *opposing* arguments on the same aesthetic axis. They share enough structural DNA (structural_score > 0.4) that the opposition is meaningful — not random difference, but deliberate tension. Detected by checking 9 curated opposition pairs across the vibe vocabulary: "Exaggerated Volume vs. Column Minimalism," "Maximalist Ornament vs. Austere Restraint," "Transgressive Subversion vs. Elite Distinction."

- **Resonance**: The garments speak the same aesthetic language across significant temporal distance (text_similarity >= 0.85 and temporal_type is `transmission`). An 1890s Arts and Crafts dress and a 2020s cottagecore blouse that are almost eerily similar — that's resonance. The same idea resurfacing a century later.

- **Affinity**: Everything else. Two garments connected by shared material, shared structure, shared something. The `primary_axis` field tells you what the something is — volume, ornament, body, or register.

**Primary and secondary axis** — Which aesthetic axis dominates this connection? Derived from the shared attributes: silhouette maps to volume, material maps to ornament, neckline maps to body, occasion maps to register. Most bridges cluster on one or two axes.

**Contrast pair** — Only populated for contrast bridges. The literal opposition: "Body Liberation <-> Body Concealment." This string becomes a headline in the UI.

The classifier runs post-hoc as a standalone script (`scripts/classify_bridge_dimensions.py`), separate from bridge computation. This was a deliberate architectural decision — bridge discovery finds *what's connected*, classification describes *how*. Different concerns, different cadence. I can re-classify all 3,000+ bridges in seconds without recomputing similarity scores.

### Smarter Narratives

The AI-generated bridge narratives now know *how* a bridge connects, not just that it does.

When Claude generates a narrative for a contrast bridge, the prompt includes: "These items make OPPOSING arguments on the same axis: Exaggerated Volume <-> Column Minimalism. Explain the tension." For resonance bridges: "These items speak the same aesthetic language despite temporal distance. Explain what echoes."

Affinity bridges get the standard prompt — the axis information is there in the shared attributes, but I don't push Claude toward a specific frame. The result is narratives that match the bridge's character. Contrast narratives talk about tension and debate. Resonance narratives talk about persistence and revival. Affinity narratives find whatever thread connects the pair.

### The Social Function Explorer

This one came from a question I kept asking the data: "How do different cultures solve the same problem?"

A wedding dress in 1860s England and a wedding kimono in Edo-period Japan are both answering the question "what does a bride look like?" but arriving at completely different answers. The `social_function` field (a JSON array on each product — "wedding," "mourning," "status-signaling," "protection," "ceremony") lets us find these pairs.

I built two new API endpoints:

`GET /explore/functions` returns every social function in the database with product counts. It's the landing page: a grid of cards showing "wedding (142 products)," "status-signaling (98 products)," "ceremony (76 products)."

`GET /explore/functions/{function}` returns all products tagged with that function, filterable by culture and era. Pick "wedding," filter to Japanese and Victorian, and you're looking at two cultures' answers to the same question side by side.

Then I added a `shared_function` filter to the existing `GET /bridges/top` endpoint. Ask for `?shared_function=wedding&connection_mode=contrast` and you get bridges between garments that both serve a wedding function but make opposing aesthetic arguments. A minimal 1920s flapper wedding dress vs. a maximalist Victorian bridal gown, both answering "what does a bride wear?" with completely different logic.

The PostgreSQL query uses jsonb containment operators — `social_function::jsonb @> '["wedding"]'::jsonb` — which is fast and correct on JSON array columns without any parsing overhead.

### Bridge Recomputation

While I was building all of the above, `compute_bridges.py --rebuild` was running in the background over the full 4,234-product corpus. The previous bridge set was computed over 866 products. Now every enriched, embedded product participates in bridge discovery. The cross-culture bridges should be dramatically richer with the V&A collection's 1,856 objects in the mix — that's Japanese textiles, Indian saris, Chinese court robes, African wax prints, all finding connections to Western fashion history.

---

## Decisions Made Today

### Three connection modes, not five

The original plan had five modes: citation, echo, parallel, contrast, kinship. After thinking it through, I collapsed to three: contrast, resonance, affinity. Citation and echo were too similar — both describe temporal re-emergence. Parallel was too rare (the triple condition almost never fired). Three modes is enough to tell the story: are these garments arguing with each other, echoing each other, or just... kin?

The simplification also means each mode has a clear narrative frame. Contrast = tension. Resonance = echo. Affinity = the primary_axis tells the story. Five modes would have meant five different narrative strategies, and the distinctions between "citation" and "echo" narratives would have been hair-splitting.

### Post-hoc classification over inline classification

The classifier is a separate script, not embedded in bridge computation. This means I can change classification logic — adjust thresholds, add new opposition pairs, redefine what "resonance" means — without recomputing bridges. Bridge computation is expensive (similarity calculations over thousands of product pairs). Classification is cheap (read existing scores, apply rules, write labels). Decoupling them respects the different cost profiles.

### jsonb containment over application-level filtering

The social function queries use PostgreSQL's native jsonb operators instead of pulling all products and filtering in Python. `@>` containment is indexed, handles array membership correctly, and pushes the work to the database where it belongs. This matters when the dataset grows — at 4,234 products it's fast either way, but at 40,000 it won't be.

---

## What I Learned

The six-dimension classification started as an engineering task — decompose one overloaded column into orthogonal dimensions, make things filterable. But as I built it, I realized it's actually a *theory* of how garments relate. Every bridge is a temporal relationship (how far apart?), a categorical relationship (what boundaries are crossed?), an aesthetic relationship (tension, echo, or kinship?), and it operates on a specific axis (volume, ornament, body, cultural register).

That's not a database schema. That's a framework for thinking about fashion history.

The contrast bridges are what I'm most excited about. Most recommendation systems find similarity — "you liked this, here's more of it." Vintage Vestige now finds *meaningful opposition*. Two garments that share enough structural DNA that their differences become an argument rather than noise. A Comme des Garcons deconstructed jacket and a Dior Bar jacket share silhouette, neckline, construction — but one argues for "Transgressive Subversion" and the other for "Elite Distinction." They're having a conversation across decades about what a jacket *means*.

That's not a search result. That's a thesis.

---

## What's Next

The bridge recomputation should finish overnight. Then:

1. Run the classifier: `scripts/classify_bridge_dimensions.py` — populate all six dimensions on every bridge
2. Generate narratives: `analysis/generate_narratives.py` — new bridges get mode-specific prompts
3. Normalize the remaining 35 unrecognized era strings (Rococo, Space Age, Supermodel Era, etc.) — add aliases to `era_taxonomy.py` and run `normalize_eras.py --apply`
4. Start building the frontend: social function explorer, bridge card enhancements with mode badges and contrast pair callouts, bridge filtering UI

The part I'm most looking forward to: opening the contrast bridges in a browser for the first time and seeing which garments the system thinks are arguing with each other.

---

*Jen Kim / linuxgrrrl LLC*
*Building Vintage Vestige — where fashion history meets computational intelligence*
