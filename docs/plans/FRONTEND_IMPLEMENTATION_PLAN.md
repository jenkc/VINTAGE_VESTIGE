# Vintage Vestige — Frontend Implementation Plan

## Context

The Vintage Vestige web app has a complete FastAPI backend (search, products, bridges, filters) and a Next.js 16 skeleton with UI primitives and an API client that covers only basic endpoints. The Figma design system is finalized. This plan covers building out the full frontend — **mobile-first** — and connecting it to every API endpoint.

**Why mobile-first:** This is a consumer-facing fashion discovery tool. The primary audience (Gen Z / younger Millennials, 18-35) will mostly use it on their phones. Every component and page is designed starting from 390px mobile, then enhanced for tablet and desktop.

---

## Current State

### What's Built
- **Backend (FastAPI):** Complete and running on `localhost:8000`. 14 endpoints covering search, products, bridges, filters, health.
- **Frontend skeleton (Next.js 16 + React 19 + TypeScript + Tailwind 4):**
  - Root layout with Inter + Playfair Display fonts
  - Home page (hero, how-it-works, browse-by-era placeholder)
  - UI primitives: Button (4 variants), Card, Badge (4 variants), Input — all using `class-variance-authority`
  - API client: `searchByText`, `searchByImage`, `getProduct`, `getFilters`
  - Types: `Product`, `SearchResult`, `SearchResponse`, `SearchFilters`, `FilterOptions`
  - Utils: `cn()`, `formatPrice()`, `debounce()`
  - Tailwind config with 11-color vintage palette

### What's Empty (files exist, zero code)
- `components/layout/Header.tsx`, `Footer.tsx`, `Navigation.tsx`
- `components/search/SearchBar.tsx`, `ImageUpload.tsx`, `ProductCard.tsx`
- `styles/theme.ts`

### What Doesn't Exist Yet
- All bridge-related types, API functions, and components
- Search results page (`/search`), product detail page (`/product/[id]`), about page (`/about`)
- Loading, error, and empty state handling
- Mobile responsive breakpoints
- `next/image` configuration for external museum image domains

### Design System Mismatches to Fix
| Issue | Current | Target (Figma Handoff) |
|-------|---------|----------------------|
| Serif font | Playfair Display | **Cormorant Garamond** |
| Primary CTA | `#722F37` (burgundy) | `#C4553A` (terracotta) |
| Color token names | `vintage-burgundy`, `vintage-caerulean`, etc. | `terracotta`, `gold`, `sage`, etc. |
| Page background | `#F7F3EC` | `#F0ECE4` (cream-dark) |
| Primary text | `#2B2B2B` | `#2C2420` (charcoal) |
| Backend Product fields | Missing `fp_category`, `silhouette`, etc. | Frontend types lag behind Pydantic schemas |

---

## API Endpoint Reference

All endpoints the frontend needs to call:

| Method | Path | Purpose | Frontend Function |
|--------|------|---------|-------------------|
| `POST` | `/search/text` | Text search with filters | `searchByText()` ✅ exists |
| `POST` | `/search/image` | Image search (base64) | `searchByImage()` ✅ exists |
| `GET` | `/products/{id}` | Full product detail | `getProduct()` ✅ exists |
| `GET` | `/products/{id}/bridges` | Bridges for a product | `getProductBridges()` ❌ needs adding |
| `GET` | `/products/{id}/modern-echoes` | Newer related products | `getModernEchoes()` ❌ |
| `GET` | `/products/{id}/style-ancestry` | Older related products | `getStyleAncestry()` ❌ |
| `GET` | `/products/{id}/style-siblings` | Same-era related products | `getStyleSiblings()` ❌ |
| `GET` | `/bridges/top` | Top bridges (global, filterable) | `getTopBridges()` ❌ |
| `GET` | `/bridges/stats` | Aggregate bridge statistics | `getBridgeStats()` ❌ |
| `GET` | `/bridges/between/{a}/{b}` | Bridge between two products | `getBridgeBetween()` ❌ |
| `GET` | `/bridges/{id}` | Single bridge detail | `getBridgeDetail()` ❌ |
| `GET` | `/filters` | All filter options | `getFilters()` ✅ exists |
| `GET` | `/health` | Health check | — |

---

## Phase 1: Foundation (Design System Alignment)

**Goal:** Align fonts, colors, and tokens with the Figma handoff so everything built on top is visually correct.

### Checklist

- [ ] **1.1 Switch font: Playfair Display → Cormorant Garamond**
  - Modify `vv-web/src/app/layout.tsx`
  - Import `Cormorant_Garamond` from `next/font/google` (weights: 400, 500, 600, 700; include italic for 400)
  - Keep CSS variable `--font-serif`

- [ ] **1.2 Overhaul Tailwind color palette**
  - Modify `vv-web/tailwind.config.ts`
  - Replace all `vintage.*` colors with Figma handoff tokens:
    ```
    Core:
      cream:         #F7F3ED    Card backgrounds, light surfaces
      cream-dark:    #F0ECE4    Page backgrounds
      warm-white:    #FFFCF7    Card fill, elevated surfaces
      charcoal:      #2C2420    Primary text
      charcoal-soft: #4A423A    Body text, narrative text
      muted:         #8A7E74    Secondary text, labels

    Borders:
      border:        #E8E0D4    Card borders, dividers
      border-light:  #D9D0C4    Subtle separators

    Accents:
      terracotta:    #C4553A    Primary accent, high scores (>80%), CTAs
      gold:          #B8924A    Secondary accent, bridge connector, labels
      sage:          #7A8B6F    Tertiary accent, shared DNA pills
      sage-dark:     #5C7A5E    Sage text on light backgrounds
      sage-text:     #4A5A40    Darkest sage for readability

    Platform badges:
      met:           #8B2332    The Met
      smithsonian:   #2E5A88    Smithsonian
      fashionpedia:  #5C7A5E    Fashionpedia
      etsy:          #D35400    Etsy
      depop:         #FF2300    Depop

    Score breakdown:
      semantic:      #2E5A88    Semantic similarity
      visual:        #8B5E3C    Visual similarity
      structural:    #7A8B6F    Structural similarity
    ```
  - Add custom shadows:
    ```
    card:       0 2px 8px rgba(44,36,32,0.04)
    card-hover: 0 20px 40px rgba(44,36,32,0.12), 0 4px 12px rgba(44,36,32,0.06)
    connector:  0 4px 16px rgba(44,36,32,0.15)
    ```
  - Add custom border radii: `sm` 10px, `md` 12px, `lg` 16px, `pill` 20px

- [ ] **1.3 Populate theme.ts**
  - Modify `vv-web/src/styles/theme.ts`
  - Export JS-accessible constants:
    - `PLATFORM_COLORS` — `{ met_museum: '#8B2332', smithsonian: '#2E5A88', ... }`
    - `PLATFORM_NAMES` — `{ met_museum: 'The Met', smithsonian: 'Smithsonian', ... }`
    - `SCORE_COLORS` — `{ semantic: '#2E5A88', visual: '#8B5E3C', structural: '#7A8B6F' }`
    - `scoreColorByValue(score: number)` — returns terracotta for >0.80, gold for >0.60, muted otherwise

- [ ] **1.4 Update globals.css**
  - Modify `vv-web/src/app/globals.css`
  - Change `bg-vintage-cream` → `bg-cream-dark`, `text-vintage-charcoal` → `text-charcoal`
  - Update border defaults: `border-vintage-taupe/20` → `border-border`
  - Add custom scrollbar styles for carousels (thin gold scrollbar thumb)

- [ ] **1.5 Update existing UI primitives** (4 files)
  - `Button.tsx` — Default: `bg-terracotta`; Outline: `border-border`; Ghost: `hover:bg-cream`; Link: `text-terracotta`
  - `Card.tsx` — `bg-warm-white border-border shadow-card`
  - `Badge.tsx` — Default: `bg-terracotta`; Secondary: `bg-sage`; Add `platform` variant
  - `Input.tsx` — Border: `border-border`; Focus: `ring-terracotta`

- [ ] **1.6 Configure next/image remote patterns**
  - Modify `vv-web/next.config.ts`
  - Add `images.remotePatterns` for Met Museum CDN, Smithsonian CDN, Fashionpedia hosts

### Deliverable
App compiles with correct Cormorant Garamond font and new color palette. Existing home page renders coherently.

---

## Phase 2: Types & API Client Expansion

**Goal:** TypeScript types match backend Pydantic schemas exactly. API client covers every endpoint.

### Checklist

- [ ] **2.1 Reconcile Product type with backend ProductDetail schema**
  - Modify `vv-web/src/types/index.ts`
  - **Remove** fields backend doesn't return: `color`, `season`, `year`, `period`, `pattern`
  - **Add** fields backend does return: `fp_category`, `silhouette`, `neckline`, `waistline`, `length`, `sleeve_length`, `opening_type`, `textile_pattern`, `textile_finishing: string[]`, `nickname`, `garment_parts: string[]`, `decorations: string[]`
  - **Note:** `formatPrice()` divides by 100 (assumes cents) but backend stores dollars. Fix or gate by platform.

- [ ] **2.2 Add bridge types**
  - Modify `vv-web/src/types/index.ts`
  - Add these interfaces matching backend schemas exactly:
    ```typescript
    interface ProductSummary {
      id: number; platform: string; title: string;
      primary_image: string | null; era: string | null;
      decade: string | null; fp_category: string | null;
      silhouette: string | null; vibe: string | null;
      material: string | null; style_tags: string[];
      colors: string[]; ai_description: string | null;
    }

    interface BridgeResult {
      id: number; source: ProductSummary; target: ProductSummary;
      bridge_score: number; text_similarity: number;
      image_similarity: number | null; structural_score: number;
      bridge_type: string | null; bridge_narrative: string | null;
      shared_attributes: Record<string, unknown>; created_at: string;
    }

    interface BridgeListResponse {
      bridges: BridgeResult[]; total: number;
      limit: number; offset: number;
    }

    interface BridgeTypeStats {
      bridge_type: string; count: number; avg_score: number;
      min_score: number; max_score: number;
    }

    interface ScoreHistogramBucket { bucket: string; count: number; }

    interface BridgeStats {
      total_bridges: number; total_products_with_bridges: number;
      by_type: BridgeTypeStats[]; score_histogram: ScoreHistogramBucket[];
    }
    ```

- [ ] **2.3 Expand API client** (8 new functions)
  - Modify `vv-web/src/lib/api.ts`
  - All use the existing `fetchAPI` helper. GET endpoints build query strings from optional params.
    ```typescript
    getProductBridges(productId, opts?: { bridge_type?, min_score?, limit?, offset? })
    getModernEchoes(productId, opts?: { min_score?, limit?, offset? })
    getStyleAncestry(productId, opts?: { min_score?, limit?, offset? })
    getStyleSiblings(productId, opts?: { min_score?, limit?, offset? })
    getTopBridges(opts?: { bridge_type?, min_score?, max_score?, source_platform?, target_platform?, limit?, offset? })
    getBridgeStats()
    getBridgeBetween(a: number, b: number)
    getBridgeDetail(bridgeId: number)
    ```

- [ ] **2.4 Add constants**
  - Modify `vv-web/src/lib/constants.ts`
  - `DEFAULT_BRIDGE_LIMIT = 12`, `FEATURED_BRIDGES_LIMIT = 8`

### Deliverable
`npx tsc --noEmit` passes. Every backend endpoint is callable from the frontend.

---

## Phase 3: Core Components (Mobile-First)

All components designed at **390px first**, then enhanced with responsive breakpoints.

### 3A: Layout Components

- [ ] **3A.1 Header** — `components/layout/Header.tsx`
  - **Mobile (default):** Logo left, hamburger right → tapping opens full-screen nav overlay
  - **Desktop (md+):** Logo left, optional inline search bar (on search page), nav links right (Search, About)
  - Sticky, 64px height, `backdrop-filter: blur(12px)`, `bg-cream-dark/95`, `border-b border-border`

- [ ] **3A.2 Footer** — `components/layout/Footer.tsx`
  - **Mobile:** Single column stack (brand → nav links → built with → copyright)
  - **Desktop (md+):** 3-column grid per Figma spec
  - `border-t border-border`, `py-12`

- [ ] **3A.3 MobileNav** — `components/layout/Navigation.tsx`
  - Full-screen slide-in overlay (from right)
  - Nav links, search bar, close button
  - Closes on link click or outside tap
  - CSS transform animation

- [ ] **3A.4 Update root layout** — `vv-web/src/app/layout.tsx`
  - Wrap children: `<Header />` above, `<Footer />` below `<main>`

### 3B: Search Components

- [ ] **3B.1 SearchBar** — `components/search/SearchBar.tsx`
  - Props: `onSearch(query: string)`, `defaultValue?`, `variant: 'large' | 'compact'`
  - **Mobile:** Full-width, min 44px height touch target
  - **Desktop:** `max-w-640` (large) or `max-w-480` (compact/header)
  - Submit on Enter, debounce on input change
  - Search icon (lucide-react) right-aligned inside input

- [ ] **3B.2 ImageUpload** — `components/search/ImageUpload.tsx`
  - **Mobile:** Full-width, large tap target, camera icon + "Take photo or upload"
  - **Desktop:** Dashed border drop zone, 2px dashed `border`, `rounded-lg`, max-w-400
  - Accept images only, convert to base64, show preview with X clear button
  - Hover: border transitions to gold

- [ ] **3B.3 ProductCard** — `components/search/ProductCard.tsx`
  - Props: accepts `SearchResult` or `ProductSummary`
  - Image 3:4 ratio, platform badge overlay (top-left), era badge + match % bottom row
  - Title: Cormorant Garamond 700/14px, 2-line clamp
  - **Mobile:** 2-column grid, smaller text
  - **Desktop:** 4-column grid, `hover:translateY(-4px) hover:shadow-card-hover`
  - Links to `/product/[id]`, handles missing image with gradient placeholder

### 3C: Bridge Components (New: `vv-web/src/components/bridge/`)

- [ ] **3C.1 PlatformBadge.tsx** — Frosted-glass pill overlay
  - `bg-warm-white/92`, `backdrop-blur-sm`, `rounded-pill`, height 22px, padding 4px 10px
  - Text: Cormorant Garamond 600/10px, color from `PLATFORM_COLORS`

- [ ] **3C.2 EraBadge.tsx** — Dark translucent pill
  - `bg-charcoal/72`, `backdrop-blur-sm`, `rounded-md`, height 20px, padding 3px 10px
  - Text: cream, format `"Victorian · ca. 1895"`

- [ ] **3C.3 ScoreCircle.tsx** — Circular match display
  - 52px desktop / 44px mobile, 2.5px border
  - Border+number color: `>0.80` → terracotta, `>0.60` → gold, `≤0.60` → muted
  - Content: number (Cormorant 700/16px) + "MATCH" (Cormorant 400/7px uppercase)

- [ ] **3C.4 BridgeConnector.tsx** — Gold circle with exchange icon
  - Full: 44px, 2px border gold, `shadow-connector`
  - Compact: 30px, 1.5px border
  - Double-arrow SVG icon, stroke gold

- [ ] **3C.5 AttributePill.tsx** — Shared DNA pill
  - `bg-sage/7`, `border border-sage/19`, `rounded-pill`
  - Format: `LABEL · value` (label 9px uppercase sage, value 11px sage-text)

- [ ] **3C.6 NarrativeBlock.tsx** — AI narrative quote block
  - `bg-cream`, `rounded-sm`, `border-l-3 border-gold`, padding 12px 16px
  - Text: Cormorant Garamond 400 italic/13px, `text-charcoal-soft`, line-height 1.6

- [ ] **3C.7 ScoreBreakdown.tsx** — Three horizontal bars
  - Each bar: label (8px uppercase), percentage (9px bold), 3px track with colored fill
  - Colors: semantic `#2E5A88`, visual `#8B5E3C`, structural `#7A8B6F` at 60% opacity

- [ ] **3C.8 BridgeCardFull.tsx** — Hero component
  - **Mobile (default):** Full-width, images **stacked vertically** (source top, target below), connector between
  - **Desktop (md+):** Images **side-by-side**, max-w-680
  - `bg-warm-white border-border rounded-lg shadow-card`
  - Content section (padding 18px 20px):
    1. Title row: source label+title | ScoreCircle | target label+title
    2. NarrativeBlock
    3. "SHARED DESIGN DNA" label + AttributePill row (flex-wrap, gap 6px)
    4. ScoreBreakdown (separated by `border-t border-border`)
  - Source/target images and titles link to their product pages

- [ ] **3C.9 BridgeCardCompact.tsx** — Carousel card
  - **Mobile:** 240px width (shows 1.5 cards for peek/scroll affordance)
  - **Desktop:** 280px width
  - Image strip (140px height), compact connector overlay
  - Content: era arrow ("Victorian → Contemporary"), score %, 2-line narrative, pills (max 3)

- [ ] **3C.10 index.ts** — Barrel export for all bridge components

### 3D: Utility Components

- [ ] **3D.1 Skeleton.tsx** — `components/ui/Skeleton.tsx`
  - Reusable shimmer/pulse loader for loading states

- [ ] **3D.2 ImageWithFallback.tsx** — `components/ui/ImageWithFallback.tsx`
  - `next/Image` with `onError` fallback to gradient placeholder
  - Gradient: `linear-gradient(135deg, #E8E0D4 0%, #D9D0C4 100%)`

### Deliverable
All components render correctly at 390px and 1440px. Bridge card adapts between stacked (mobile) and side-by-side (desktop).

---

## Phase 4: Pages (Mobile-First)

### 4.1 Home Page

- **Modify** `vv-web/src/app/page.tsx`
- **Mobile layout:**
  - Hero: stacked, full-width, CTAs stack vertically (primary on top)
  - How It Works: single-column card stack
  - Featured Bridges: horizontal scroll carousel (cards peek at edge)
- **Desktop (md+):** Centered hero, 3-col how-it-works grid, wider carousel
- Server-fetch `getTopBridges({ limit: 8 })` for featured bridges
- Hero CTAs: "Start Searching" → `/search`, "Upload Image" → `/search?mode=image`
- Background: subtle cross-stitch SVG pattern (gold at 3% opacity)

### 4.2 Search Results Page

- **Create** `vv-web/src/app/search/page.tsx`
- URL: `/search?q=...`
- **Mobile layout:**
  - Full-width search bar at top (sticky below header)
  - 2-column product card grid
  - "Load More" button (avoid pagination on mobile)
- **Desktop (lg+):** 4-column grid, search bar in header
- **States:**
  - Empty: large search bar + image upload zone (search landing)
  - Loading: skeleton grid (shimmer cards)
  - No results: friendly message + suggestions
  - Error: error message + retry button
- Client component wrapper for interactive search (URL param updates)

### 4.3 Product Detail Page

- **Create** `vv-web/src/app/product/[id]/page.tsx`
- **Mobile layout:**
  - Product image: full-width, 3:4 ratio
  - Info below: platform badge, title, style tags, AI description, metadata grid (2-col)
  - Bridge sections stacked vertically:
    - Style Ancestry: full-width BridgeCardFull (stacked images)
    - Modern Echoes: same
    - Style Siblings: horizontal scroll carousel of compact cards
- **Desktop (lg+):** 2-column product hero (image left, info right), 2-col bridge grids
- Server-fetch: `getProduct`, `getStyleAncestry`, `getModernEchoes`, `getStyleSiblings`
- Also create: `loading.tsx`, `not-found.tsx`

### 4.4 About Page

- **Create** `vv-web/src/app/about/page.tsx`
- Simple prose, max-w-720, centered
- Sections: What is VV, How Bridges Work, Data Sources, Tech Stack

### Deliverable
All 4 pages navigable and rendering real API data. Mobile layout is the primary design.

---

## Phase 5: Integration & Polish

### Core Integration

- [ ] **5.1 Error boundaries** — `error.tsx` for global, search, and product routes
- [ ] **5.2 Loading states** — `loading.tsx` for search and product routes using Skeleton
- [ ] **5.3 Image handling** — Wire ImageWithFallback everywhere; finalize `next.config` remote patterns
- [ ] **5.4 Client-side search flow** — SearchBar → `router.push('/search?q=...')` for text; `useState` for image results
- [ ] **5.5 Home data caching** — `revalidate: 3600` on featured bridges fetch
- [ ] **5.6 shared_attributes rendering** — Parse `Record<string, unknown>` → label/value pairs for AttributePills

### Mobile-Specific Polish

- [ ] **5.7 Touch targets** — All interactive elements ≥ 44×44px (WCAG 2.5.5)
- [ ] **5.8 Scroll performance** — `will-change: transform` on carousel items; native `scroll-snap-type: x mandatory`
- [ ] **5.9 Image optimization** — `sizes="(max-width: 768px) 50vw, 25vw"` on product images
- [ ] **5.10 Mobile search UX** — Large prominent search bar on home, auto-focus keyboard on tap

### General Polish

- [ ] **5.11 Hover effects** (desktop only) — Card lift + shadow, connector rotation. Wrap in `@media (hover: hover)`
- [ ] **5.12 SEO metadata** — `generateMetadata` on product pages (dynamic title, description, OG image)
- [ ] **5.13 Accessibility** — Alt text, aria-labels on scores, keyboard carousel nav, focus rings
- [ ] **5.14 CSS cleanup** — Remove all old `vintage-*` class references

### Deliverable
Production-ready app. Full flow: home → search → results → product → bridges → linked product. Performant on mobile.

---

## File Manifest

### Modify (13 files)
| File | Phase | What Changes |
|------|-------|-------------|
| `vv-web/src/app/layout.tsx` | 1.1, 3A.4 | Font swap + add Header/Footer |
| `vv-web/tailwind.config.ts` | 1.2 | Full color palette replacement |
| `vv-web/src/styles/theme.ts` | 1.3 | Platform colors, score helpers |
| `vv-web/src/app/globals.css` | 1.4 | Base styles to new tokens |
| `vv-web/src/components/ui/Button.tsx` | 1.5 | Color classes |
| `vv-web/src/components/ui/Card.tsx` | 1.5 | Color classes |
| `vv-web/src/components/ui/Badge.tsx` | 1.5 | Color classes + platform variant |
| `vv-web/src/components/ui/Input.tsx` | 1.5 | Color classes |
| `vv-web/next.config.ts` | 1.6 | Remote image patterns |
| `vv-web/src/types/index.ts` | 2.1, 2.2 | Fix Product + add bridge types |
| `vv-web/src/lib/api.ts` | 2.3 | 8 bridge API functions |
| `vv-web/src/lib/constants.ts` | 2.4 | Bridge constants |
| `vv-web/src/app/page.tsx` | 4.1 | Rebuild home page |

### Populate (6 empty stubs)
| File | Phase | Component |
|------|-------|-----------|
| `vv-web/src/components/layout/Header.tsx` | 3A.1 | Sticky header (mobile hamburger / desktop nav) |
| `vv-web/src/components/layout/Footer.tsx` | 3A.2 | 3-column footer |
| `vv-web/src/components/layout/Navigation.tsx` | 3A.3 | Mobile slide-in nav |
| `vv-web/src/components/search/SearchBar.tsx` | 3B.1 | Search input (large + compact) |
| `vv-web/src/components/search/ImageUpload.tsx` | 3B.2 | Drag-and-drop / tap-to-upload |
| `vv-web/src/components/search/ProductCard.tsx` | 3B.3 | Product result card |

### Create (~22 new files)
| File | Phase | Purpose |
|------|-------|---------|
| `vv-web/src/components/bridge/PlatformBadge.tsx` | 3C.1 | Platform indicator |
| `vv-web/src/components/bridge/EraBadge.tsx` | 3C.2 | Era indicator |
| `vv-web/src/components/bridge/ScoreCircle.tsx` | 3C.3 | Score circle |
| `vv-web/src/components/bridge/BridgeConnector.tsx` | 3C.4 | Center connector icon |
| `vv-web/src/components/bridge/AttributePill.tsx` | 3C.5 | Shared DNA pill |
| `vv-web/src/components/bridge/NarrativeBlock.tsx` | 3C.6 | AI narrative quote |
| `vv-web/src/components/bridge/ScoreBreakdown.tsx` | 3C.7 | Three-bar breakdown |
| `vv-web/src/components/bridge/BridgeCardFull.tsx` | 3C.8 | Full bridge card |
| `vv-web/src/components/bridge/BridgeCardCompact.tsx` | 3C.9 | Compact bridge card |
| `vv-web/src/components/bridge/index.ts` | 3C.10 | Barrel export |
| `vv-web/src/components/ui/Skeleton.tsx` | 3D.1 | Shimmer loader |
| `vv-web/src/components/ui/ImageWithFallback.tsx` | 3D.2 | Image with fallback |
| `vv-web/src/app/search/page.tsx` | 4.2 | Search results page |
| `vv-web/src/app/search/loading.tsx` | 5.2 | Search skeleton |
| `vv-web/src/app/search/error.tsx` | 5.1 | Search error boundary |
| `vv-web/src/app/product/[id]/page.tsx` | 4.3 | Product detail page |
| `vv-web/src/app/product/[id]/loading.tsx` | 5.2 | Product skeleton |
| `vv-web/src/app/product/[id]/not-found.tsx` | 4.3 | Product 404 |
| `vv-web/src/app/product/[id]/error.tsx` | 5.1 | Product error boundary |
| `vv-web/src/app/about/page.tsx` | 4.4 | About page |
| `vv-web/src/app/error.tsx` | 5.1 | Global error boundary |

**Total: ~41 files** (13 modified + 6 populated + 22 created)

---

## Verification Plan

| Phase | How to Verify |
|-------|--------------|
| **1** | `npm run build` passes. Open `localhost:3000` — Cormorant Garamond renders, colors match Figma. |
| **2** | `npx tsc --noEmit` — zero type errors. |
| **3** | Create temp `/dev` page rendering each component with mock data. Check 390px + 1440px in DevTools. |
| **4** | Start backend (`uvicorn api.main:app`), then `npm run dev`. Full flow: Home → Search "dark academia" → click product → see bridges → click bridge target → new product. |
| **5** | Chrome DevTools mobile emulation at 390px. Verify: touch targets ≥ 44px, no horizontal overflow, carousels snap, images fallback, skeletons appear. |

---

## Key Mobile Design Decisions

| Component | Mobile (390px) | Desktop (1440px) |
|-----------|---------------|-----------------|
| **Header** | Logo + hamburger | Logo + search bar + nav links |
| **Product grid** | 2 columns | 4 columns |
| **BridgeCardFull images** | Stacked vertically | Side-by-side |
| **BridgeCardCompact** | 240px wide (peek scroll) | 280px wide |
| **Product detail hero** | Image full-width, info below | 2-column side-by-side |
| **Bridge grids** | Single column | 2 columns |
| **Footer** | Single column stack | 3-column grid |
| **CTAs** | Full-width stacked buttons | Inline side-by-side |
| **Search bar** | Full-width, prominent | Centered max-w-640 |
| **Carousels** | Scroll snap, peek edges | Scroll snap, wider cards |

---

## Risks & Notes

1. **External image URLs + next/Image:** Museum CDNs may not all be in `remotePatterns`. Use `ImageWithFallback` everywhere; iteratively add domains as broken images surface during development.
2. **shared_attributes is untyped:** Backend stores as generic JSON dict. Type as `Record<string, string | string[]>` on frontend, handle both cases in AttributePill.
3. **Tailwind v4 config:** Uses PostCSS plugin + `@config` directive in globals.css. Verify custom tokens are picked up. If issues, may need `@theme` blocks in CSS.
4. **Search page client/server split:** Initial load is server-side (from URL `searchParams`), subsequent searches are client-side. Use server component that passes initial data to client component wrapper.
5. **formatPrice() semantics:** Currently divides by 100 (assumes cents) but backend stores dollar floats. Most museum items have no price. Fix or only show price for marketplace platforms.
