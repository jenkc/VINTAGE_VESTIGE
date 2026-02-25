# Fashion Intelligence Platform — Product Strategy

## The Core Thesis

Fashion is one of the last creative industries without a structured intelligence
layer. Music has MusicBrainz, Spotify's audio fingerprinting, and Gracenote. Film
has IMDb and TMDb. Food has flavor compound databases. But fashion? Designers,
retailers, stylists, and historians all work from vibes, mood boards, and tribal
knowledge. There is no structured, queryable map of how garments relate across
time, culture, and construction.

**We're building that map.**

The underlying asset is a **fashion knowledge graph** that connects garments across
eras, sources, and design DNA — powered by museum archives, modern datasets,
AI enrichment, and dual-space embeddings (visual + semantic). Every item in the
graph has structured taxonomy (silhouette, neckline, textile, construction),
creative metadata (vibe, style movement, occasion), and embedding vectors that
capture both how it looks and what it means.

---

## What We Have Today

| Asset | Scale | Status |
|-------|-------|--------|
| Harmonized product database | 1,000 items (Met, Smithsonian, Fashionpedia) | Live |
| Fashionpedia taxonomy mapping | 27 categories, 294 attributes | Complete |
| Claude enrichment pipeline | Full + creative-only paths | Running |
| Text embeddings (384-dim) | 1,000 items in Qdrant | Live |
| Image embeddings (512-dim CLIP) | ~500 items | Partial |
| Cross-source bridge spec | Structural + semantic scoring | Designed, not built |

What this becomes at scale: 50K-500K items spanning 500 years of fashion history,
connected by a knowledge graph of style relationships.

---

## The Three Layers

```
┌─────────────────────────────────────────────────────┐
│            PRODUCTS (what people buy)                │
│                                                      │
│  Vintage Vestige    Style DNA API    Trend Oracle    │
│  (consumer app)     (B2B SaaS)      (analytics)     │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          INTELLIGENCE LAYER (the moat)              │
│                                                      │
│  Knowledge Graph  ·  Cross-Source Bridges            │
│  Enrichment Pipeline  ·  Taxonomy Harmonization      │
│  Embedding Spaces (visual + semantic)                │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            DATA LAYER (raw ingredients)              │
│                                                      │
│  Met Museum  ·  Smithsonian  ·  Fashionpedia         │
│  iDesigner (runway)  ·  V&A  ·  Europeana            │
│  Etsy/Depop (eventually)  ·  User uploads            │
└─────────────────────────────────────────────────────┘
```

The data layer is mostly public/open-source. The intelligence layer is the
defensible asset — the harmonization, enrichment, and graph connections are
what nobody else has built. The products sit on top and serve different
customer segments.

---

## Customer Segments & Their Problems

### 1. Resale Platforms (Depop, ThredUp, The RealReal, Vestiaire Collective, Poshmark)

**Their problem:** Sellers upload items with terrible metadata. "Blue dress" tells
you nothing. Categorization is inconsistent. Search is keyword-based and awful.
Recommendations are weak. They can't tell you that a $30 Zara blazer on Depop
is structurally identical to a $3,000 Balmain piece on Vestiaire.

**What we solve:**
- **Auto-enrichment API** — seller uploads photo → returns structured taxonomy
  (silhouette, neckline, era, textile, construction), style tags, rich description,
  and suggested category. Powers better search and discovery.
- **Cross-listing similarity** — "this item on your platform is similar to these
  items on competing platforms" (competitive intelligence for the platform)
- **Style-based recommendations** — not "other blue dresses" but "other items
  with this silhouette from this era with this vibe"

**Revenue model:** Per-API-call pricing or monthly SaaS ($500-5,000/mo per platform)

**Why they'd pay:** Better metadata = better search = higher conversion = more GMV.
ThredUp processes 4M+ items/year. Even $0.05/item enrichment = $200K/year from
one customer.

### 2. Fashion Brands & Designers

**Their problem:** Trend research is expensive and manual. Designers hire trend
forecasters (WGSN charges $30K+/year), tear through vintage archives, and build
mood boards by hand. They lack a systematic way to understand what historical
references are embedded in their own collections — or their competitors'.

**What we solve:**
- **Collection Analysis** — "Upload your Fall 2027 collection. Here's the
  historical DNA: 40% 1970s bohemian, 30% Victorian structure, 20% Art Deco
  geometry, 10% novel." With specific museum pieces that share each trait.
- **Inspiration Engine** — "I want 'dark academia meets cottagecore'. Here are
  12 museum pieces from 1820-1920 that blend those aesthetics, and here are
  modern garments that already bridge them."
- **Competitive Analysis** — "Here's what Valentino's last 5 collections reference
  historically vs. what Balenciaga references. Here's the gap — historical
  aesthetics nobody is mining right now."

**Revenue model:** Annual subscription ($5K-50K depending on team size)

**Why they'd pay:** Replaces or supplements WGSN/Heuritech at a fraction of cost
with a unique angle (historical DNA) they can't get anywhere else.

### 3. Fashion Media & Editorial

**Their problem:** Writing about fashion requires deep historical knowledge that
most writers don't have. "This Prada collection references..." requires someone
who recognizes the reference. Fact-checking style claims is time-consuming.

**What we solve:**
- **Reference Finder** — Upload a runway image, get specific museum pieces it
  echoes, with bridge narratives ("this shares the dramatic bustle silhouette
  of 1870s evening wear, updated with...")
- **Trend Archaeology** — "What's cycling back this season?" backed by data,
  not opinion. Show which historical silhouettes are appearing in modern
  collections with the highest bridge scores.
- **Story Generator** — "Give me 5 style connections between the Met's Costume
  Institute and the current Zara collection" for content marketing.

**Revenue model:** Freemium (limited queries free, premium $50-200/mo for
publications)

**Why they'd pay:** Content is their product. This generates unique content angles
that their competitors don't have access to.

### 4. Museums & Cultural Institutions

**Their problem:** Collections are vast but siloed. The Met has 33,000+ costume
items. Most are unseen, uncategorized by modern style vocabulary, and disconnected
from contemporary fashion. Museums want to make collections relevant to younger
audiences.

**What we solve:**
- **"Modern Echoes" exhibit feature** — for any museum piece, show modern items
  that inherited its design. Powers interactive exhibits and online collection
  pages.
- **Cross-museum connections** — "This Met piece connects to these Smithsonian
  pieces connects to these V&A pieces" — without the museums doing any
  cataloging work themselves.
- **Collection enrichment** — Add modern style vocabulary (vibe, aesthetic,
  style movement) to historical items so younger audiences can find them.

**Revenue model:** Institutional licensing ($10K-50K/year), grant-funded
partnerships, freemium API for researchers

**Why they'd pay:** Mission-aligned with making collections accessible. Digital
engagement metrics matter for funding.

### 5. Fashion Education

**Their problem:** Teaching fashion history is static — textbooks, slides,
memorization. Students at FIT, Parsons, Central Saint Martins learn eras in
isolation. The connections between eras (how one influenced the next) are taught
anecdotally.

**What we solve:**
- **Interactive style evolution explorer** — click a silhouette and watch it
  evolve through centuries, with real garments at each node
- **"Design DNA" assignments** — "analyze the historical references in this
  modern collection using the tool"
- **Research tool** — students query the knowledge graph for thesis research

**Revenue model:** Institutional license ($5K-20K/year per school), student
freemium

### 6. Vintage Sellers & Stylists (Long Tail)

**Their problem:** Listing vintage items is hard. What era is this? What's the
right terminology? How do I describe this to someone who isn't a vintage expert?

**What we solve:**
- **Listing assistant** — photo → complete listing with era, style tags,
  description, suggested price based on similar items, SEO keywords
- **Styling engine** — "What modern items pair with this vintage piece?"

**Revenue model:** SaaS $10-30/month or per-listing fee ($0.25-0.50)

---

## Product Roadmap

### Phase 1: Prove the Intelligence (NOW — Month 1-3)
What we're doing right now. Build the knowledge graph, run the enrichment
pipeline, compute cross-source bridges. Ship Vintage Vestige as the consumer
demo that proves the tech works.

**Deliverables:**
- 1,000+ enriched items across 3 sources
- Cross-source style bridges computed
- Working search with semantic + visual + structural matching
- Demo-able web interface

**Validates:** "Can we connect garments across time and sources in meaningful ways?"

### Phase 2: Style DNA API (Month 3-6)
Expose the intelligence layer as an API. Start with the simplest, most sellable
capability: image → structured taxonomy + style metadata.

**Endpoints:**
```
POST /api/v1/analyze
  Input: image (base64 or URL)
  Output: {
    taxonomy: { silhouette, neckline, waistline, length, textile_pattern, ... },
    style: { era, decade, vibe, style_tags, aesthetic_movements },
    description: "AI-generated rich description",
    historical_echoes: [ { museum_piece_id, bridge_score, shared_attributes } ]
  }

POST /api/v1/similar
  Input: image or product_id
  Output: [
    { item, score, relationship_type: "visual" | "semantic" | "structural" }
  ]

GET /api/v1/bridges/{product_id}
  Output: {
    modern_echoes: [...],
    historical_ancestors: [...],
    style_siblings: [...]
  }

GET /api/v1/timeline/{attribute}
  Input: attribute (e.g., "a-line", "empire waist")
  Output: [
    { decade, items: [...], prevalence_score }
  ]
```

**Pricing tiers:**
- Free: 100 API calls/month (developer adoption)
- Starter: $99/mo — 5,000 calls (indie sellers, small brands)
- Pro: $499/mo — 50,000 calls (mid-market resale platforms)
- Enterprise: Custom (Depop, ThredUp scale)

### Phase 3: Scale the Data Layer (Month 6-12)
Add more sources to make the intelligence more valuable:
- V&A Museum (Victoria & Albert — huge costume collection, public API)
- Europeana (pan-European cultural heritage, 50M+ items)
- iDesigner (50K runway images — maps designer → historical DNA)
- NYPL Digital Collections
- Chicago History Museum
- Eventually: scrape live inventory from resale platforms

Each new source makes every existing source more valuable (network effect).

### Phase 4: Trend Oracle (Month 9-15)
Analytics product built on the temporal dimension of the knowledge graph:
- "Which historical silhouettes are gaining bridge_score momentum with modern items?"
- "What era references are appearing in runway collections this season?"
- "Predict which vintage styles will surge in resale value based on bridge patterns"

This is the premium product — fashion forecasting backed by data instead of
opinion. Competes with WGSN ($30K+/yr subscriptions) from a completely different
angle.

### Phase 5: Platform & Marketplace (Month 12+)
- Open the knowledge graph to third-party contributors
- Let vintage sellers list directly with auto-enrichment
- Let museums self-onboard their collections
- Become the "fashion genome project" — open data + premium intelligence

---

## Competitive Landscape

| Competitor | What They Do | Our Edge |
|------------|-------------|----------|
| **WGSN** | Trend forecasting ($30K+/yr) | We use data, they use human analysts. We have historical depth they lack. |
| **Heuritech** | AI trend detection from social media | They look forward (social signals). We look backward AND forward (historical DNA + modern). |
| **Google Lens** | Visual search | Generic — no fashion intelligence, no temporal connections, no style vocabulary. |
| **Lyst / Tagwalk** | Fashion search/indexing | Index modern only. No historical dimension. No cross-temporal bridges. |
| **Museum APIs** | Raw collection data | Unstructured, siloed, no cross-museum connections, no modern relevance mapping. |

**The gap nobody fills:** Connecting fashion ACROSS TIME with structured intelligence.
Everyone else is either historical-only (museums), modern-only (fashion tech), or
generic (Google). We're the bridge.

---

## Defensibility & Moat

1. **Compounding knowledge graph** — Every item added creates N new potential
   connections. At 50K items, the graph has millions of edges. Hard to replicate.

2. **Taxonomy harmonization** — Mapping Met Museum's free-text descriptions to
   Fashionpedia's 294-attribute ontology is months of work. It's not the algorithm,
   it's the domain engineering.

3. **Enrichment quality** — Our Claude prompts are tuned for fashion. The difference
   between "blue dress" and "a midnight-blue bias-cut charmeuse gown channeling
   1930s Hollywood glamour" is the enrichment pipeline. That prompt engineering
   compounds with feedback.

4. **Cross-source bridges** — The pre-computed similarity connections between
   historical and modern items. Nobody else has this dataset because nobody else
   has combined these sources with this taxonomy.

5. **Embedding spaces trained on fashion context** — Our rich-text embeddings
   capture fashion semantics, not generic text similarity. "Dark academia" means
   something specific in our vector space.

---

## Revenue Projections (Conservative)

| Year | Primary Revenue | ARR |
|------|----------------|-----|
| Year 1 | Vintage Vestige consumer (freemium) + first API customers | $10K-50K |
| Year 2 | Style DNA API (10-20 paying platforms) + museum partnerships | $200K-500K |
| Year 3 | Trend Oracle + enterprise API + education licensing | $1M-3M |

The real value unlock is Year 2-3 when the B2B products kick in. The consumer
app is the proof-of-concept and top-of-funnel.

---

## The Pitch (30 Seconds)

"Fashion is a $1.7 trillion industry that still runs on tribal knowledge and mood
boards. We've built the first structured intelligence layer that maps garments
across 500 years of fashion history — connecting museum archives to modern
inventory through AI-powered design DNA analysis. Our knowledge graph understands
that a $30 Zara blazer and an 1890s Met Museum riding jacket share the same
structural DNA. We sell that intelligence to resale platforms, fashion brands,
and media companies as an API — and we use it ourselves to power the first
truly intelligent vintage fashion search engine."

---

## Open Questions

- [ ] Should the consumer app (Vintage Vestige) be the brand, or should the
      platform have a separate B2B brand?
- [ ] What's the right first B2B customer to pursue? (Resale platforms have
      clearest ROI, but museums might be easier first partnerships)
- [ ] How much of the knowledge graph should be open/free vs proprietary?
      (Open data attracts contributors, proprietary data is the moat)
- [ ] Should we pursue grant funding for the museum/cultural heritage angle?
      (NEH, NEA, Knight Foundation all fund digital humanities)
- [ ] Patent potential: structural similarity scoring across temporal fashion
      datasets? (Probably not patentable, but worth asking)
