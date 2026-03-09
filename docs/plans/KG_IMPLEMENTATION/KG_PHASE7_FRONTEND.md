# KG_PHASE7_FRONTEND.md
# Phase 7 — Frontend Graph Features

**Duration:** 1 week  
**Status:** 🔲 Not Started — begins after Phase 6 (graph API live)  
**Prerequisite:** Phase 6 (all 7 graph endpoints live and tested)  
**Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, D3.js  
**Last Updated:** March 2026 (v2.0)

**v2.0 note:** The Next.js frontend is already complete — all 4 routes build
clean, error boundaries live, SEO in place, mobile-ready. This phase adds new
routes and components on top of the working app. The design system, component
library, and API client are already in place. New graph components follow the
same patterns already established in the codebase.

---

## Overview

Three new UI surfaces, each one only possible because of the knowledge graph:

| Surface | What it shows | Why it matters |
|---|---|---|
| **Influence Chain Visualizer** | 3-hop garment lineage with bridge narratives | Makes the paper's argument visible |
| **Design Movement Explorer** | Force-directed graph of garments through a shared element | Design movements as emergent data |
| **Design Element Index** | Browsable vocabulary of fashion's argument structure | The taxonomy made navigable |

These integrate into the existing product detail page and add a new standalone
Explore section.

---

## Checklist

### New TypeScript Types (`vv-web/src/types/graph.ts`)
- [ ] `InfluenceChainStep` — one garment in a chain (id, title, era, image_url, platform)
- [ ] `InfluenceChainBridge` — bridge between steps (narrative, semantic_type, score, shared_elements)
- [ ] `InfluenceChain` — full chain: `steps: InfluenceChainStep[]`, `bridges: InfluenceChainBridge[]`
- [ ] `DesignMovementGarment` — garment + its bridge context within a movement
- [ ] `DesignMovement` — element metadata + all garments across eras
- [ ] `DesignElement` — name, category, bridge_count, aat_uri, era_span
- [ ] `CrossInstitutionalBridge` — source garment + bridge + target garment

### New API Client Functions (`vv-web/src/lib/api.ts`)
- [ ] `getInfluenceChain(garmentId, semanticType?)` → `InfluenceChain`
- [ ] `getDesignMovement(elementName)` → `DesignMovement`
- [ ] `getStyleAncestryGraph(garmentId)` → `DesignMovementGarment[]`
- [ ] `getDesignElements()` → `DesignElement[]`
- [ ] `getCrossInstitutionalBridges()` → `CrossInstitutionalBridge[]`

### Component 1: Influence Chain Visualizer
**File:** `vv-web/src/components/graph/InfluenceChain.tsx`

- [ ] Horizontal timeline layout (left = oldest, right = newest)
- [ ] Each step renders a `GarmentNode` — image thumbnail, title, era badge, platform chip
- [ ] Each bridge renders a `BridgeEdge` — connection mode label, score, truncated narrative on hover
- [ ] Connection mode color coding:
  - `contrast` → rose (aesthetic opposition)
  - `resonance` → amber (same aesthetic language across time)
  - `affinity` → gray (family resemblance — axis tells the story)
- [ ] Contrast bridges show `contrast_pair` as a tooltip (e.g. "Exaggerated Volume ↔ Column Minimalism")
- [ ] Optional secondary badge for `primary_axis` (volume / ornament / body / register)
- [ ] Empty state when no chain found ("No influence chain discovered yet")
- [ ] Loading skeleton (3 placeholder nodes + 2 placeholder bridges)
- [ ] Mobile: collapses to vertical stack

### Component 2: Design Movement Explorer
**File:** `vv-web/src/components/graph/DesignMovement.tsx`

- [ ] Element selector dropdown (populated from `/graph/design-elements`)
- [ ] Force-directed graph using D3.js:
  - Nodes = garments (size proportional to bridge_score)
  - Edges = bridges (opacity proportional to score)
  - Color = era (each era gets distinct hue)
  - Hover tooltip: garment title + era + bridge narrative
- [ ] Era timeline sidebar: lists all eras that garments span
- [ ] Click node → opens product detail (or side panel)
- [ ] "Era span" counter: "This element appears across N eras, from X to Y"
- [ ] Mobile: falls back to ordered list view (D3 force layout doesn't work well on small screens)
- [ ] Loading state while graph calculates layout

**D3 setup:**
```typescript
// Install: npm install d3 @types/d3
import * as d3 from 'd3'

// Node type for D3
interface GraphNode extends d3.SimulationNodeDatum {
  id: string
  title: string
  era: string
  image_url: string
  bridge_score: number
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  narrative: string
  score: number
}
```

### Component 3: Design Element Index
**File:** `vv-web/src/components/graph/DesignElementIndex.tsx`

- [ ] Grid of element cards, sorted by bridge_count descending
- [ ] Each card: element name, category badge, bridge count, era span
- [ ] Category filter tabs: All | Silhouette | Construction | Material | Cultural
- [ ] Search/filter input (client-side, no additional API call)
- [ ] Click card → opens Design Movement Explorer filtered to that element
- [ ] Getty AAT link shown where `aat_uri` is populated (opens in new tab)
- [ ] Count badge: "142 bridges across 6 eras" per element

### Page: Explore (`/explore`)
**File:** `vv-web/src/app/explore/page.tsx`

- [ ] Hero: "Explore fashion's argument structure"
- [ ] Two sections: Design Element Index (primary) + Cross-Institutional Bridges (secondary)
- [ ] Cross-Institutional Bridges section:
  - [ ] Grid of bridge cards: Met garment | bridge narrative | Smithsonian garment
  - [ ] Score displayed prominently
  - [ ] Caption: "These connections don't exist in any single museum's database"
- [ ] Navigation item added to Header

### Product Detail Page Updates
**File:** `vv-web/src/app/products/[id]/page.tsx`

- [ ] Influence Chain panel added below existing Style Ancestry section
- [ ] "Influence Chain" tab in bridge navigation
- [ ] Semantic type pill on each bridge card (replaces raw type string)
- [ ] DesignElement chips shown on bridge detail ("Argues through: empire waistline, floor length")

### Navigation Update
**File:** `vv-web/src/components/layout/Navigation.tsx`
- [ ] "Explore" link added to main nav
- [ ] "Design Elements" sub-link under Explore
- [ ] Active state styling correct

---

## Design Principles

**Show the argument, not just the connection.** Every bridge in the UI should
surface its semantic type and at least one DesignElement. The user should
understand *why* two garments are connected, not just *that* they are.

**Era should be visually primary.** Color-code by era consistently across all
graph views. Use the same palette everywhere: Victorian = deep burgundy, 1920s =
gold, 1950s = teal, etc. Pick once and document in `styles/theme.ts`.

**Loading states are part of the product.** Neptune graph queries can take 500–800ms.
Every graph component needs a skeleton loader that matches the shape of the real content.
No spinners — skeleton shapes only.

**Mobile is a real constraint.** The D3 force graph doesn't work on mobile.
Design the fallback list view as a first-class experience, not an afterthought.

---

## Era Color Palette (define in `styles/theme.ts`)

```typescript
export const ERA_COLORS: Record<string, string> = {
  'early_1800s':  '#8B4513',  // saddle brown — Empire/Regency
  'victorian':    '#722F37',  // wine — Victorian
  'edwardian':    '#C4A35A',  // antique gold — Edwardian
  '1910s':        '#4A6741',  // sage green
  '1920s':        '#D4AF37',  // gold — Art Deco
  '1930s':        '#2C4A6E',  // deep blue — Depression era
  '1940s':        '#6B6B6B',  // utility gray — Wartime
  '1950s':        '#2E8B57',  // sea green — New Look
  '1960s':        '#E84C3D',  // mod red — Space Age
  '1970s':        '#8B6914',  // earthy brown — Boho
  '1980s':        '#9B59B6',  // power purple
  '1990s':        '#2C3E50',  // dark slate — Grunge/minimalism
  '2000s':        '#E67E22',  // orange — Y2K
  '2010s':        '#1ABC9C',  // teal — Normcore/maximalism
  '2020s':        '#34495E',  // charcoal — current
}
```

---

## Estimated Effort

| Task | Time |
|---|---|
| TypeScript types + API client functions | 3 hours |
| Influence Chain Visualizer | 6 hours |
| Design Movement Explorer (D3) | 8 hours |
| Design Element Index | 4 hours |
| Explore page | 3 hours |
| Product detail page updates | 3 hours |
| Navigation updates | 1 hour |
| Mobile responsive fixes | 3 hours |
| **Total** | **~31 hours** |
