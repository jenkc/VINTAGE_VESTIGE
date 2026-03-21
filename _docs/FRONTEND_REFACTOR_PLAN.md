# Vintage Vestige — Frontend Refactor Implementation Plan

**Date:** March 20, 2026
**Target:** Deploy within 3 weeks (by April 10)
**Approach:** Guide Jen through changes step-by-step

---

## Master Checklist

### Phase 0: Backend API (Day 1-2)
- [ ] 0A. Update `api/schemas/bridge.py` — remove old fields, add new fields
- [ ] 0A. Update `api/schemas/product.py` — add KG fields
- [ ] 0B. Update `api/routers/bridges.py` — new filters, new connection_mode values
- [ ] 0B. Update `api/routers/search.py` — product response includes KG fields
- [ ] 0C. Update `analysis/bridge_queries.py` — new schema columns
- [ ] 0D. Verify: `curl http://localhost:8000/bridges/top?limit=3` returns new schema
- [ ] 0D. Verify: `curl http://localhost:8000/products/2152/bridges` returns new schema

### Phase 1: Types & Design Tokens (Day 2-3)
- [ ] 1A. Rewrite `BridgeResult` interface in `src/types/index.ts`
- [ ] 1A. Add KG fields to `ProductSummary` interface
- [ ] 1A. Remove old bridge fields from types
- [ ] 1B. Replace `CONNECTION_MODE_COLORS` in `src/styles/theme.ts`
- [ ] 1B. Replace `CONNECTION_MODE_LABELS` in `src/styles/theme.ts`
- [ ] 1B. Add `ENTITY_TYPE_LABELS` in `src/styles/theme.ts`
- [ ] 1B. Remove axis-related constants
- [ ] Verify: `npm run build` compiles with no type errors

### Phase 2: Bridge Components (Day 3-5)
- [ ] 2A. Simplify `ConnectionBadge.tsx` — remove primaryAxis prop
- [ ] 2B. Update `ScoreBreakdown.tsx` — rename labels (Text, Image, Entity)
- [ ] 2C. Update `AttributePill.tsx` usage — render from shared_entities
- [ ] 2D. Rewrite `BridgeCardFull.tsx` — entity headlines, lineage arrows, distance label
- [ ] 2E. Simplify `BridgeCardCompact.tsx` — entity tags, remove connector
- [ ] 2F. Delete `BridgeConnector.tsx`
- [ ] 2F. Update `bridge/index.ts` barrel exports
- [ ] Verify: bridge cards render correctly with test data

### Phase 3: Pages (Day 5-9)
- [ ] 3A. Homepage — kill "How It Works", add Bridge of the Day, add entry points
- [ ] 3B. Product Detail — rename sections (Connected To, Echoes Across Time, Pull the Thread CTA)
- [ ] 3B. Product Detail — add KG fields to metadata grid (designer, movements, influences)
- [ ] 3B. Product Detail — use display_title
- [ ] 3C. Bridges page — rename to "Connections", new filter bar, add presets
- [ ] 3D. Explore Functions — update filter logic for new connection modes
- [ ] 3E. About page — update tech description
- [ ] 3F. Search page — add browse mode tabs (Era, Culture, Movement, Function)
- [ ] 3G. Error/Loading pages — verify colors/fonts
- [ ] Verify: all routes render in dev, no console errors

### Phase 4: Interactions (Day 9-12)
- [ ] 4A. Build `ThreadPull.tsx` component
- [ ] 4A. Create `/thread/[id]` route
- [ ] 4A. Thread Pull: lazy-loads next bridge on scroll
- [ ] 4A. Thread Pull: branch buttons at each node
- [ ] 4B. Build `BridgeOfTheDay.tsx` component
- [ ] 4B. Wire Bridge of the Day to homepage
- [ ] 4B. Daily rotation logic (date-based seed)
- [ ] Verify: Thread Pull walks the graph end-to-end

### Phase 5: API Client & Polish (Day 12-14)
- [ ] 5A. Update `api.ts` — remove old params, add new params
- [ ] 5A. Add `getThreadNext()` function
- [ ] 5B. Update `BridgeCardCompact.test.tsx` fixture data
- [ ] 5B. Add `ThreadPull.test.tsx`
- [ ] 5B. Update any other tests with old bridge fields
- [ ] 5C. Verify responsive: mobile bridge layouts
- [ ] 5C. Verify loading states / skeletons
- [ ] 5C. Verify image fallbacks
- [ ] 5D. `npm run build` — clean, no errors
- [ ] 5D. `npx vitest run` — all tests pass

### Phase 6: Deploy (Day 14-15)
- [ ] 6A. Deploy FastAPI backend
- [ ] 6A. Verify production API returns correct data
- [ ] 6B. Deploy Next.js frontend
- [ ] 6B. Verify all routes work in production
- [ ] 6B. Verify images load from Supabase Storage
- [ ] 6C. Generate narratives for more bridges (lower score gate)
- [ ] 6C. Monitor for errors

---

## What Changed in the Backend

The bridge system was completely rewritten from embedding-similarity to entity-based discovery. The frontend must catch up.

| Old (v1) | New (v2) |
|----------|----------|
| `bridge_type` (transmission/echo/etc) | `connection_mode` (shared_entity/lineage/visual_echo) |
| `connection_mode` (contrast/lineage/echo/parallel/visual) | `connection_mode` (shared_entity/lineage/visual_echo) |
| `shared_garment_fields` (generic key-value) | `shared_entities` (typed: designer, movement, technique, etc.) |
| `structural_score` | `entity_score` (IDF-weighted) |
| `primary_axis`, `secondary_axis`, `contrast_pair` | REMOVED |
| `discovery_metadata` | REMOVED |
| `shared_designer`, `shared_movements`, `shared_influences` | Merged into `shared_entities` JSON |
| `bridge_type` | REMOVED |
| — | `directed` (boolean, lineage bridges flow older→newer) |

---

## Phase 0: Backend API Updates (Day 1-2)
*Must happen before any frontend work.*

### 0A. Update API Schemas (`api/schemas/bridge.py`, `api/schemas/product.py`)

**Bridge response schema:**
- Remove: `structural_score`, `bridge_type`, `primary_axis`, `secondary_axis`, `contrast_pair`, `shared_garment_fields`, `discovery_metadata`, `shared_designer`, `shared_movements`, `shared_influences`
- Add: `entity_score` (float), `directed` (bool), `shared_entities` (dict)
- Keep: `bridge_score`, `text_similarity`, `image_similarity`, `year_gap`, `crossing_type`, `connection_mode`, `bridge_narrative`

**Product response schema:**
- Add: `display_title`, `designer`, `influence_references`, `named_movements`, `production_mode`, `material_origin`, `garment_system`, `low_confidence_fields`

### 0B. Update API Routers (`api/routers/bridges.py`, `api/routers/search.py`)

**Bridge endpoints:**
- `/bridges/top` filters: update `connection_mode` accepted values to `shared_entity`, `lineage`, `visual_echo`
- Remove `primary_axis` filter parameter
- Add `directed` filter parameter (optional bool)
- Add `min_entity_score` filter parameter
- `/products/{id}/bridges` — return bridges sorted by `bridge_score` desc
- `/products/{id}/style-ancestry` — redefine as bridges with `year_gap > 30` (cross-time connections)
- `/products/{id}/style-siblings` — redefine as bridges with `year_gap <= 30` (same-era connections)

### 0C. Update Bridge Queries (`analysis/bridge_queries.py`)

- Update all query functions to use new schema columns
- Remove references to old columns

### 0D. Verify API works

```bash
curl http://localhost:8000/bridges/top?limit=3
curl http://localhost:8000/products/2152/bridges
```

**Deliverable:** API returns new bridge schema. Old columns gone from responses.

---

## Phase 1: Types & Design Tokens (Day 2-3)

### 1A. Update TypeScript Types (`src/types/index.ts`)

**BridgeResult — complete rewrite:**
```typescript
interface BridgeResult {
  id: number
  source: ProductSummary
  target: ProductSummary

  // Scores
  bridge_score: number
  entity_score: number
  text_similarity: number | null
  image_similarity: number | null

  // Classification
  connection_mode: 'shared_entity' | 'lineage' | 'visual_echo'
  crossing_type: string | null
  year_gap: number | null
  directed: boolean

  // Entity data — the "why" of the connection
  shared_entities: {
    designer?: string[]
    named_movements?: string[]
    construction_technique?: string[]
    social_function?: string[]
    motif_family?: string[]
    garment_system?: string[]
    influence_references?: string[]
    lineage_reference?: string    // only on lineage bridges
    lineage_match_score?: number  // only on lineage bridges
    image_similarity?: number     // only on visual_echo bridges
  }

  // Narrative
  bridge_narrative: string | null
  created_at: string
}
```

**ProductSummary — add KG fields:**
```typescript
interface ProductSummary {
  // ... existing fields ...
  display_title: string | null
  designer: string | null
  named_movements: string[] | null
  influence_references: string[] | null
  production_mode: string | null
}
```

**Remove old fields from BridgeResult:**
- `structural_score`, `bridge_type`, `primary_axis`, `secondary_axis`, `contrast_pair`
- `shared_garment_fields`, `discovery_metadata`
- `shared_designer`, `shared_movements`, `shared_influences`

### 1B. Update Design Tokens (`src/styles/theme.ts`)

**Replace CONNECTION_MODE_COLORS:**
```typescript
export const CONNECTION_MODE_COLORS: Record<string, string> = {
  shared_entity: '#6B6B6B',   // grey — most common, neutral
  lineage: '#C4553A',          // accent — most interesting, highlighted
  visual_echo: '#8B5E3C',     // brown — visual connection
}
```

**Replace CONNECTION_MODE_LABELS:**
```typescript
export const CONNECTION_MODE_LABELS: Record<string, string> = {
  shared_entity: 'SHARED',
  lineage: 'LINEAGE',
  visual_echo: 'VISUAL ECHO',
}
```

**Add ENTITY_TYPE_LABELS:**
```typescript
export const ENTITY_TYPE_LABELS: Record<string, string> = {
  designer: 'Designer',
  named_movements: 'Movement',
  construction_technique: 'Technique',
  social_function: 'Function',
  motif_family: 'Motif',
  garment_system: 'Worn with',
  influence_references: 'Influences',
}
```

**Remove:**
- `scoreColorByValue` (if still present)
- Any axis-related constants

**Deliverable:** Types compile. No runtime errors on bridge data.

---

## Phase 2: Bridge Components (Day 3-5)

### 2A. ConnectionBadge — Simplify

**Current:** Shows mode label + axis label with colored badge
**New:** Shows mode label only, simpler styling

```tsx
// Just mono text with accent color for lineage
<span className="font-mono text-[11px] uppercase tracking-wider"
      style={{ color: CONNECTION_MODE_COLORS[mode] }}>
  {CONNECTION_MODE_LABELS[mode]}
</span>
```

Remove `primaryAxis` prop entirely.

### 2B. ScoreBreakdown — Update Labels

**Current:** 3 bars (Semantic, Visual, Structural)
**New:** 3 bars (Text, Image, Entity)

- Rename "Semantic" → "Text"
- Rename "Structural" → "Entity"
- Change `structural` prop to `entity` (maps to `entity_score`)
- Keep "Visual" / "Image"

### 2C. AttributePill → EntityTag

**Current:** Generic `label · value` pills from `shared_garment_fields`
**New:** Entity-typed tags from `shared_entities`

The component itself is fine — just rename and update how it's called. In BridgeCardFull:

```tsx
// Old:
{Object.entries(shared_garment_fields).map(([key, val]) => (
  <AttributePill label={key} value={String(val)} />
))}

// New:
{Object.entries(shared_entities).map(([entityType, values]) => {
  if (!Array.isArray(values)) return null
  const label = ENTITY_TYPE_LABELS[entityType] || entityType
  return values.map(v => (
    <AttributePill label={label} value={v} key={`${entityType}-${v}`} />
  ))
})}
```

### 2D. BridgeCardFull — Major Rewrite

**Remove:**
- Contrast pair display (`connection_mode === 'contrast'` block)
- ScoreCircle (or move to small mono text)
- "SHARED DESIGN DNA" heading

**Add:**
- Shared entities as headline tags between images
- Year gap + crossing type as distance label: `40 YEARS · CROSS-CULTURE`
- Lineage indicator for directed bridges: arrow + reference text
- `display_title` instead of `title` for product names

**Layout:**
```
[Image A]                    [Image B]
PLATFORM · ERA               PLATFORM · ERA
Display Title                Display Title

         SHARED ENTITIES AS TAGS
         ART DECO · DRAPING · HAND-EMBROIDERY
         40 years apart · cross-culture

         "Narrative text in italic serif..."

         LINEAGE (small)    85%
```

For lineage bridges, add directional context:
```
[SOURCE: The Original] ──→ [TARGET: References It]
LINEAGE: "Japanese kimono draping"
```

### 2E. BridgeCardCompact — Simplify

**Remove:** BridgeConnector SVG, axis display
**Update:** Show entity tags instead of attribute pills, year gap in mono

```
[Img A] [Img B]
ENTITY · ENTITY · ENTITY
1870s → 1920s · cross-culture · 85%
```

### 2F. Delete BridgeConnector

Not needed. Remove from barrel export (`bridge/index.ts`).

**Deliverable:** Bridge cards render with new entity data. No axis/contrast references.

---

## Phase 3: Pages (Day 5-9)

### 3A. Homepage (`app/page.tsx`)

**Kill:** "How It Works" pipeline section
**Rework:** Featured Bridges → "Bridge of the Day"
- Full-width single bridge layout (not a carousel)
- Shared entities as mono headline
- Narrative in large italic serif
- Picks highest-score lineage bridge with narrative

**Add:** Entry points section
```
BROWSE BY ERA
BROWSE BY CULTURE
BROWSE BY FUNCTION
EXPLORE CONNECTIONS
```
Large text links, `display-md`, stacked vertically.

**Add:** Collection Pulse (optional — dense grid of tiny garment thumbnails, 80-100px)

### 3B. Product Detail (`app/product/[id]/page.tsx`)

**Rework bridge sections:**
- "Style Ancestry" → **"CONNECTED TO"** — top bridges by bridge_score, lineage priority
- "Style Siblings" → **"ECHOES ACROSS TIME"** — bridges with year_gap > 40
- **Add:** "PULL THE THREAD →" CTA at bottom (links to Thread Pull view — Phase 4)

**Update product hero:**
- Use `display_title` as primary title
- Add KG fields to metadata grid: designer, movements, influences, production_mode

### 3C. Bridges Page (`app/bridges/page.tsx`)

**Rename:** "Bridge Explorer" → "CONNECTIONS"

**Replace filter bar:**
- Old: Connection Mode (5 values) + Axis (6 values) + Social Function
- New: Type (shared_entity / lineage / visual_echo / all) + Entity Type (designer / movement / technique / all) + Time (30+ years / 80+ years / all) + Crossing (cross-culture / cross-category / all)

**Add presets:**
- `SAME MAKER` — `connection_mode=shared_entity` + filter for shared designer
- `LONGEST ECHOES` — sort by year_gap desc
- `LINEAGE` — `connection_mode=lineage`
- `VISUAL SURPRISES` — `connection_mode=visual_echo`
- `SURPRISE ME` — random high-score bridge

**Update results:** Full BridgeCardFull stacked vertically, not 2-col grid.

### 3D. Explore Functions Page (`app/explore/functions/[function]/page.tsx`)

**Update:** "Same Question, Different Answers" section
- Old: filters `connection_mode: 'contrast'`
- New: filters bridges that share this function as an entity, sorted by year_gap

### 3E. About Page (`app/about/page.tsx`)

**Update:** Tech description to mention entity-based bridge system, IDF scoring, 3-pass architecture.

### 3F. Search Page (`app/search/page.tsx`)

**Add browse modes** (tabs or large text links):
- By Era, By Culture, By Movement, By Function
- These link to filtered search results or dedicated browse pages

### 3G. Error/Loading Pages

**Update:** Colors/fonts if still using old v1 tokens.

**Deliverable:** All pages render with new bridge data. No old axis/contrast UI.

---

## Phase 4: Interactions (Day 9-12)

### 4A. Thread Pull — NEW Component

`src/components/explore/ThreadPull.tsx`

The signature interaction. Vertical scroll through connected garments.

**Implementation:**
1. Start with a product ID
2. Fetch its bridges: `GET /products/{id}/bridges`
3. Pick the highest bridge_score bridge (prefer lineage)
4. Render: garment → shared entities → narrative → next garment
5. Fetch next garment's bridges
6. Repeat until user stops or no more bridges

**Route:** `/thread/[id]` — dedicated page, or inline on product detail

**UI:**
```
[Garment Image + Title + Era]
     │
     │  LINEAGE: "traditional Korean hanbok construction"
     │  SHARED: hand-sewing · chima + jeogori
     ↓
[Next Garment Image + Title + Era]
     │
     │  SHARED: Dress Reform Movement · tailoring
     │  30 years · cross-culture
     ↓
[Next Garment...]
```

Each step is lazy-loaded as user scrolls. Branch buttons at each node.

### 4B. Bridge of the Day — NEW Component

`src/components/bridge/BridgeOfTheDay.tsx`

Full-width editorial treatment of one bridge. Used on homepage.

**Implementation:**
- Fetch: `GET /bridges/top?limit=1&connection_mode=lineage&min_score=0.7`
- Fallback: highest score bridge with narrative
- Daily rotation: use date-based seed for pseudo-random selection from top 50

**Deliverable:** Thread Pull works end-to-end. Bridge of the Day renders on homepage.

---

## Phase 5: API Client & Polish (Day 12-14)

### 5A. Update API Client (`src/lib/api.ts`)

- Update `getTopBridges` filter params: remove `primary_axis`, add `directed`, `min_entity_score`
- Update `getStyleAncestry` / `getStyleSiblings` to use new endpoint logic
- Add `getThreadNext(productId)` — fetches best bridge for Thread Pull
- Remove unused functions if any

### 5B. Update Tests

- `BridgeCardCompact.test.tsx` — update fixture data (new BridgeResult shape)
- `BridgeCardFull` — add test if missing
- Add `ThreadPull.test.tsx` — basic render test
- Update any test that references old bridge fields

### 5C. Visual Polish

- Verify responsive behavior (mobile bridge layouts stack vertically)
- Check loading states / skeletons match new layouts
- Verify image fallbacks work
- Check all links/routes work

### 5D. Build & Deploy Prep

```bash
npm run build    # catch type errors
npx vitest run   # catch test failures
```

Fix any issues. Verify all routes render in dev.

**Deliverable:** Clean build. All tests pass. Ready to deploy.

---

## Phase 6: Deploy (Day 14-15)

### 6A. Backend Deploy
- Deploy FastAPI with updated schemas/routers
- Verify bridge data is accessible via production API

### 6B. Frontend Deploy
- Deploy Next.js to Vercel (or chosen platform)
- Verify all routes work in production
- Check image loading from Supabase Storage

### 6C. Post-Deploy
- Generate narratives for more bridges (lower the score gate)
- Monitor for errors
- Collect feedback

---

## Timeline Summary

| Week | Days | Phase | Deliverable |
|------|------|-------|-------------|
| 1 | 1-2 | Phase 0: Backend API | API returns new schema |
| 1 | 2-3 | Phase 1: Types & Tokens | Types compile, tokens updated |
| 1 | 3-5 | Phase 2: Bridge Components | Cards render entity data |
| 2 | 5-9 | Phase 3: Pages | All pages updated |
| 2 | 9-12 | Phase 4: Interactions | Thread Pull + Bridge of Day |
| 3 | 12-14 | Phase 5: Polish & Tests | Clean build, tests pass |
| 3 | 14-15 | Phase 6: Deploy | Live |

---

## Files Changed (Complete List)

### Backend (Phase 0)
- `api/schemas/bridge.py`
- `api/schemas/product.py`
- `api/routers/bridges.py`
- `api/routers/search.py`
- `analysis/bridge_queries.py`

### Frontend — Types & Tokens (Phase 1)
- `src/types/index.ts`
- `src/styles/theme.ts`

### Frontend — Components (Phase 2)
- `src/components/bridge/ConnectionBadge.tsx`
- `src/components/bridge/ScoreBreakdown.tsx`
- `src/components/bridge/AttributePill.tsx` (rename to EntityTag)
- `src/components/bridge/BridgeCardFull.tsx`
- `src/components/bridge/BridgeCardCompact.tsx`
- `src/components/bridge/BridgeConnector.tsx` (DELETE)
- `src/components/bridge/index.ts` (update exports)

### Frontend — Pages (Phase 3)
- `src/app/page.tsx` (homepage)
- `src/app/product/[id]/page.tsx`
- `src/app/bridges/page.tsx`
- `src/app/explore/functions/[function]/page.tsx`
- `src/app/about/page.tsx`
- `src/app/search/page.tsx`

### Frontend — New Components (Phase 4)
- `src/components/explore/ThreadPull.tsx` (NEW)
- `src/components/bridge/BridgeOfTheDay.tsx` (NEW)
- `src/app/thread/[id]/page.tsx` (NEW route)

### Frontend — Client & Tests (Phase 5)
- `src/lib/api.ts`
- `src/test/` (update fixtures + add new tests)
