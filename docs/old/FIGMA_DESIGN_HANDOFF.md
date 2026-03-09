# Vintage Vestige — Figma Design Handoff

**For:** Claude Code (with Figma Dev Mode MCP Server)
**Figma File:** Vintage Vestige (`3AXCKfChPdugtQOQ5629BP`)
**Date:** February 2026

---

## What This Is

This document specifies the complete design system and page layouts for the Vintage Vestige web app. Use it to populate the Figma file with frames, components, and styles. The file is currently empty.

The app is a **fashion knowledge graph** that connects garments across 500 years of design history via AI-computed "style bridges." The audience is Gen Z / younger Millennials (18–35) who value sustainability and unique style but lack vintage knowledge.

---

## 1. Design Tokens

### Color Palette

Set up these as Figma color variables:

| Token Name | Hex | Usage |
|---|---|---|
| `cream` | `#F7F3ED` | Card backgrounds, light surfaces |
| `cream-dark` | `#F0ECE4` | Page backgrounds |
| `warm-white` | `#FFFCF7` | Card fill, elevated surfaces |
| `charcoal` | `#2C2420` | Primary text |
| `charcoal-soft` | `#4A423A` | Body text, narrative text |
| `muted` | `#8A7E74` | Secondary text, labels |
| `border` | `#E8E0D4` | Card borders, dividers |
| `border-light` | `#D9D0C4` | Subtle separators |
| `terracotta` | `#C4553A` | Primary accent, high scores (>80%), CTAs |
| `gold` | `#B8924A` | Secondary accent, bridge connector, labels, headings |
| `sage` | `#7A8B6F` | Tertiary accent, shared DNA pills, nature/organic |
| `sage-dark` | `#5C7A5E` | Sage text on light backgrounds |
| `sage-text` | `#4A5A40` | Darkest sage for readability |
| `met-red` | `#8B2332` | Platform badge: The Met |
| `smithsonian-blue` | `#2E5A88` | Platform badge: Smithsonian |
| `fashionpedia-green` | `#5C7A5E` | Platform badge: Fashionpedia |
| `etsy-orange` | `#D35400` | Platform badge: Etsy |
| `depop-red` | `#FF2300` | Platform badge: Depop |
| `semantic-blue` | `#2E5A88` | Score breakdown: Semantic similarity |
| `visual-brown` | `#8B5E3C` | Score breakdown: Visual similarity |
| `structural-sage` | `#7A8B6F` | Score breakdown: Structural similarity |

### Typography

Two font families. Set up as Figma text styles:

**Display / Headings:** Cormorant Garamond (Google Fonts — serif, elegant, editorial)
**Body / UI:** Inter or system sans-serif (clean, readable)

| Style Name | Font | Weight | Size | Line Height | Letter Spacing | Usage |
|---|---|---|---|---|---|---|
| `heading-xl` | Cormorant Garamond | 700 | 36px | 1.2 | 0 | Page titles |
| `heading-lg` | Cormorant Garamond | 700 | 28px | 1.25 | 0 | Section headers |
| `heading-md` | Cormorant Garamond | 700 | 20px | 1.3 | 0 | Card section headers |
| `heading-sm` | Cormorant Garamond | 700 | 14px | 1.3 | 0 | Card titles |
| `label-uppercase` | Cormorant Garamond | 600 | 10px | 1 | 2.5px | Category labels (HISTORICAL, MODERN, etc.) |
| `label-uppercase-sm` | Cormorant Garamond | 600 | 9px | 1 | 2.5px | Smallest labels (SHARED DESIGN DNA) |
| `label-uppercase-xs` | Cormorant Garamond | 600 | 8px | 1 | 2.5px | Score breakdown labels |
| `score-lg` | Cormorant Garamond | 700 | 16px | 1 | 0 | Score circle number |
| `score-unit` | Cormorant Garamond | 400 | 7px | 1 | 0.5px | "MATCH" label under score |
| `narrative` | Cormorant Garamond | 400 italic | 13px | 1.6 | 0 | Bridge narratives |
| `body` | Inter | 400 | 16px | 1.6 | 0 | Body text, descriptions |
| `body-sm` | Inter | 400 | 14px | 1.5 | 0 | Smaller body text |
| `pill` | Cormorant Garamond | 500 | 11px | 1 | 0 | Attribute pills |
| `pill-label` | Cormorant Garamond | 400 | 9px | 1 | 1px | Pill sub-labels (uppercase) |
| `badge` | Cormorant Garamond | 600 | 10px | 1 | 0.3px | Platform/era badges |
| `button` | Inter | 600 | 14px | 1 | 0 | Button text |

### Spacing Scale

| Token | Value | Usage |
|---|---|---|
| `space-xs` | 4px | Tight gaps (inline elements) |
| `space-sm` | 6px | Pill gaps, badge padding |
| `space-md` | 8–10px | Badge insets, small padding |
| `space-lg` | 12–14px | Card content padding |
| `space-xl` | 16–20px | Card main padding, section gaps |
| `space-2xl` | 32px | Between card groups |
| `space-3xl` | 48px | Page section spacing |

### Border Radii

| Token | Value | Usage |
|---|---|---|
| `radius-sm` | 10px | Narrative block |
| `radius-md` | 12px | Compact cards, era badges |
| `radius-lg` | 16px | Full bridge cards |
| `radius-pill` | 20px | Attribute pills, platform badges |
| `radius-circle` | 50% | Score circle, bridge connector |

### Shadows

| Token | Value | Usage |
|---|---|---|
| `shadow-card` | `0 2px 8px rgba(44,36,32,0.04)` | Card resting state |
| `shadow-card-hover` | `0 20px 40px rgba(44,36,32,0.12), 0 4px 12px rgba(44,36,32,0.06)` | Card hover state |
| `shadow-connector` | `0 4px 16px rgba(44,36,32,0.15)` | Bridge connector circle |
| `shadow-badge` | none (use `backdrop-filter: blur(8px)` with semi-transparent bg) | Platform badges |

---

## 2. Component Specifications

### 2.1 Platform Badge

Small pill showing the data source.

- **Size:** Auto-width, height ~22px
- **Padding:** 4px 10px
- **Background:** `rgba(255,252,247,0.92)` with `backdrop-filter: blur(8px)`
- **Border radius:** `radius-pill` (20px)
- **Text:** `badge` style (10px Cormorant Garamond, weight 600)
- **Text color:** Platform-specific (see color tokens)
- **Position:** Overlaid on image, top-left (source) or top-right (target)

### 2.2 Era Badge

Small dark pill showing era + date.

- **Size:** Auto-width, height ~20px
- **Padding:** 3px 10px
- **Background:** `rgba(44,36,32,0.72)` with `backdrop-filter: blur(6px)`
- **Border radius:** `radius-md` (12px)
- **Text:** `badge` style, color `cream` (#F7F3ED)
- **Content:** `{era} · {date}` (e.g., "Victorian · ca. 1895")
- **Position:** Overlaid on image, bottom-left (source) or bottom-right (target)

### 2.3 Bridge Connector

Circle centered between the two images.

- **Size:** 44×44px (full variant), 30×30px (compact variant)
- **Background:** `warm-white`
- **Border:** 2px solid `gold` (1.5px for compact)
- **Shadow:** `shadow-connector`
- **Icon:** Two-arrow exchange icon, stroke `gold`, 18×18px (12×12px compact)
- **Z-index:** Above both images
- **Hover state (full):** Rotate 180° + scale 1.1

### 2.4 Score Circle

Circular match percentage display.

- **Size:** 52×52px
- **Border:** 2.5px solid, color varies:
  - `>80%` → `terracotta`
  - `>60%` → `gold`
  - `≤60%` → `muted`
- **Background:** Transparent (hover: tinted 8% opacity of border color)
- **Content:** Number (16px bold) + "MATCH" label (7px uppercase) stacked vertically

### 2.5 Attribute Pill (Shared Design DNA)

Shows a shared attribute between source and target.

- **Padding:** 5px 12px
- **Border radius:** `radius-pill` (20px)
- **Background:** `#7A8B6F12` (sage at 7% opacity)
- **Border:** 1px solid `#7A8B6F30` (sage at 19% opacity)
- **Content:** Label (9px uppercase, color sage) · separator (sage 25% opacity) · value (11px, color sage-text)
- **Example:** `SILHOUETTE · Fitted bodice`

### 2.6 Score Breakdown Bar

Thin horizontal progress bar with label.

- **Track:** 3px height, color `border`, `radius-sm`
- **Fill:** 3px height, colored per metric type (semantic-blue / visual-brown / structural-sage), 60% opacity
- **Label row above:** Metric name (left, 9px uppercase) + percentage (right, 9px bold)
- **Three bars side by side** in a row: Semantic, Visual, Structural

### 2.7 Narrative Block

Italicized quote block for the bridge narrative.

- **Padding:** 12px 16px
- **Background:** `cream`
- **Border radius:** `radius-sm` (10px)
- **Border left:** 3px solid `gold`
- **Text:** `narrative` style (13px Cormorant Garamond italic, color `charcoal-soft`)
- **Content wrapped in quotes:** `"Both share the dramatic off-shoulder decolletage..."`

---

## 3. Bridge Card — Full Variant

The hero component. Shows two garments side by side with their design connection.

**Overall card:**
- **Width:** Flexible (max ~680px in demo, full-width in grids)
- **Background:** `warm-white`
- **Border:** 1px solid `border`
- **Border radius:** `radius-lg` (16px)
- **Shadow:** `shadow-card` → `shadow-card-hover` on hover
- **Hover lift:** translateY(-4px)

**Layout (top to bottom):**

```
┌─────────────────────────────────────────────────┐
│  ┌──────────────┐    ◉    ┌──────────────┐     │
│  │              │  bridge  │              │     │
│  │   SOURCE     │ connect  │   TARGET     │     │
│  │   IMAGE      │  (gold)  │   IMAGE      │     │
│  │              │          │              │     │
│  │  [The Met]   │          │ [Fashionpedia]│    │
│  │       [Victorian·1895]  │    [Contemporary]  │
│  └──────────────┘          └──────────────┘     │
│                                                  │
│  HISTORICAL        ⟨87⟩        MODERN            │
│  Evening Dress    match    Off-Shoulder Gown     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │ "Both share the dramatic off-shoulder  │     │
│  │  decolletage and structured boned..."  │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  SHARED DESIGN DNA                               │
│  [Fitted bodice] [Off-shoulder] [Floor-length]  │
│                                                  │
│  ─────────────────────────────────────────      │
│  Semantic 81%   Visual 79%   Structural 72%     │
│  ████████░░     ███████░░░   ███████░░░░        │
└─────────────────────────────────────────────────┘
```

**Image pair section:**
- Two images side by side, each `flex: 1`
- Aspect ratio: 3:4
- `object-fit: cover`, centered
- Platform badge overlaid top-left (source) / top-right (target)
- Era badge overlaid bottom-left (source) / bottom-right (target)
- Bridge connector centered between images (absolute positioned)

**Content section (padding 18px 20px 20px):**
1. **Title row:** Three columns — source label+title (left), score circle (center), target label+title (right)
   - Labels: `label-uppercase` style, color `gold`, text "HISTORICAL" / "MODERN"
   - Titles: `heading-sm` style (14px bold Cormorant Garamond)
   - Score circle centered between them
2. **Narrative block:** Full width, see component spec 2.7
3. **Shared DNA section:**
   - Label: `label-uppercase-sm` (8px), color `muted`, text "SHARED DESIGN DNA"
   - Row of attribute pills (see component spec 2.5), flex-wrap, gap 6px
4. **Score breakdown:** Three bars in a row (see component spec 2.6), separated from above by 1px `border` line with 14px margin-top and 12px padding-top

---

## 4. Bridge Card — Compact Variant

For grids and horizontal scroll carousels.

**Overall card:**
- **Width:** Fixed 280px
- **Border radius:** `radius-md` (12px)
- **Other properties:** Same as full but with `shadow-card` / lighter hover shadow

**Layout:**

```
┌─────────────────────────┐
│  ┌──────┐ ◉ ┌──────┐  │  ← 140px height
│  │SOURCE│   │TARGET│  │
│  └──────┘   └──────┘  │
│                         │
│  Victorian → Contemporary  87%  │
│  "Both share the dramatic..."   │
│  [Fitted bodice] [Off-shoulder] │
└─────────────────────────┘
```

**Image pair:** 140px fixed height, same structure as full but smaller connector (30px)
**Content (padding 12px 14px 14px):**
1. Era labels row: `{source.era} → {target.era}` (left) + score percentage (right, terracotta bold)
2. Narrative: 2-line clamp, 11.5px italic
3. Attribute pills: Max 3 shown, smaller (padding 3px 8px, 9.5px text)

---

## 5. Page Layouts

### 5.1 Home Page

```
┌─────────────────────────────────────────────────┐
│  [Header]                                        │
├─────────────────────────────────────────────────┤
│                                                  │
│          V I N T A G E   V E S T I G E          │
│                                                  │
│     A fashion knowledge graph connecting         │
│     500 years of design history                  │
│                                                  │
│     [Start Searching]  [Upload Image]            │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  HOW IT WORKS                                    │
│                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐                  │
│  │ AI    │  │Search│  │Bridge│                  │
│  │Enrich │  │      │  │      │                  │
│  └──────┘  └──────┘  └──────┘                  │
│                                                  │
├─────────────────────────────────────────────────┤
│  FEATURED BRIDGES                                │
│                                                  │
│  [BridgeCard] [BridgeCard] [BridgeCard]         │
│  (compact, horizontal scroll)                    │
│                                                  │
├─────────────────────────────────────────────────┤
│  [Footer]                                        │
└─────────────────────────────────────────────────┘
```

- Hero section: Centered text, warm background with subtle cross-stitch SVG pattern overlay (gold at 3% opacity)
- Two CTA buttons: Primary (terracotta fill) + Secondary (outlined)
- How-it-works: Three icon cards explaining the pipeline
- Featured bridges: Horizontal scroll of compact bridge cards

### 5.2 Search Results Page

```
┌─────────────────────────────────────────────────┐
│  [Header with SearchBar integrated]              │
├─────────────────────────────────────────────────┤
│                                                  │
│  Search Results for "dark academia aesthetic"    │
│  24 results                                      │
│                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │Product │ │Product │ │Product │ │Product │  │
│  │Card    │ │Card    │ │Card    │ │Card    │  │
│  │        │ │        │ │        │ │        │  │
│  │ Title  │ │ Title  │ │ Title  │ │ Title  │  │
│  │ [Era]  │ │ [Era]  │ │ [Era]  │ │ [Era]  │  │
│  │ 85%    │ │ 78%    │ │ 72%    │ │ 68%    │  │
│  └────────┘ └────────┘ └────────┘ └────────┘  │
│                                                  │
│  (4-column grid, responsive to 1-col on mobile) │
│                                                  │
├─────────────────────────────────────────────────┤
│  [Footer]                                        │
└─────────────────────────────────────────────────┘
```

**Product Card (search result):**
- Aspect 3:4 image
- Title (2-line clamp)
- Era badge
- Match percentage
- Hover: lift + shadow

### 5.3 Product Detail Page

```
┌─────────────────────────────────────────────────┐
│  [Header]                                        │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐   Title                        │
│  │              │   [Victorian] [Dress] [Formal] │
│  │   PRODUCT    │                                │
│  │   IMAGE      │   "A magnificent evening gown  │
│  │              │    featuring intricate lace..." │
│  │              │                                │
│  └──────────────┘                                │
│                                                  │
│  (2-col grid: image left, details right)         │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  STYLE ANCESTRY                                  │
│  Historical garments that influenced this design │
│                                                  │
│  ┌─────────────────┐  ┌─────────────────┐      │
│  │  BridgeCard      │  │  BridgeCard      │      │
│  │  (full variant)  │  │  (full variant)  │      │
│  └─────────────────┘  └─────────────────┘      │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  MODERN ECHOES                                   │
│  Contemporary designs that echo this piece       │
│                                                  │
│  ┌─────────────────┐  ┌─────────────────┐      │
│  │  BridgeCard      │  │  BridgeCard      │      │
│  │  (full variant)  │  │  (full variant)  │      │
│  └─────────────────┘  └─────────────────┘      │
│                                                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  STYLE SIBLINGS                                  │
│  Related garments with similar design DNA        │
│                                                  │
│  [BridgeCard compact] [BridgeCard compact] ...  │
│  (horizontal scroll)                             │
│                                                  │
├─────────────────────────────────────────────────┤
│  [Footer]                                        │
└─────────────────────────────────────────────────┘
```

This is the showcase page. Bridge cards are the hero — they demonstrate the core innovation.

### 5.4 About Page

Simple prose page, max-width 720px centered. Sections: What is VV, How It Works, Data Sources, Tech Stack. Minimal design — the content speaks.

---

## 6. Shared Layout Components

### Header

- **Height:** 64px
- **Background:** `cream-dark` with 95% opacity + `backdrop-filter: blur(12px)`
- **Position:** Sticky top
- **Content:** Logo left ("Vintage Vestige" in Cormorant Garamond 24px bold, charcoal) + Nav right (Search, About — 14px Inter)
- **Border bottom:** 1px solid `border`

### Footer

- **Background:** transparent
- **Border top:** 1px solid `border`
- **Padding:** 48px vertical
- **Layout:** 3-column grid
  - Col 1: Brand name + one-sentence description
  - Col 2: Navigation links
  - Col 3: "Built with" tech list (Claude API, CLIP, Qdrant, Next.js & FastAPI)
- **Copyright:** Centered below, separated by border-top, 14px muted text

### Search Bar

- **Max width:** 640px
- **Input:** Full-width, rounded (radius-pill), subtle border, placeholder "Search for styles, eras, or garments..."
- **Icon:** Search icon right-aligned inside input, color `muted`
- **On home page:** Large, centered, prominent
- **In header:** Compact, integrated into nav area

### Image Upload Zone

- **Border:** 2px dashed `border`, radius-lg
- **Padding:** 32px
- **Icon:** Upload arrow, 48px, color `muted`
- **Text:** "Click to upload or drag image here" (14px, `muted`)
- **Hover:** Border color transitions to `gold`
- **With preview:** Shows image with X button to clear

---

## 7. Figma File Structure

Organize the file with these pages:

```
Page 1: 🎨 Design System
  ├── Color Palette (swatches with labels)
  ├── Typography Scale (all text styles)
  ├── Spacing & Radii reference
  └── Shadow reference

Page 2: 🧩 Components
  ├── Platform Badge (variants per source)
  ├── Era Badge
  ├── Bridge Connector (full + compact sizes)
  ├── Score Circle (3 color states)
  ├── Attribute Pill
  ├── Score Breakdown Bar
  ├── Narrative Block
  ├── Bridge Card — Full (with hover state)
  ├── Bridge Card — Compact (with hover state)
  ├── Product Card (search result)
  ├── Search Bar
  ├── Image Upload Zone
  ├── Header
  └── Footer

Page 3: 📱 Pages
  ├── Home (Desktop 1440px)
  ├── Home (Mobile 390px)
  ├── Search Results (Desktop)
  ├── Search Results (Mobile)
  ├── Product Detail (Desktop)
  ├── Product Detail (Mobile)
  └── About (Desktop)
```

---

## 8. Interaction Notes

- **Card hover:** Lift 4px + enhanced shadow, 0.4s ease with `cubic-bezier(0.23, 1, 0.32, 1)`
- **Bridge connector hover:** Rotate 180° + scale 1.1
- **Score circle hover:** Background fills with 8% opacity tint of border color
- **All transitions:** 0.3–0.4s, use spring-like cubic-bezier
- **No animation on the image pair for now** — merge/superimpose effect is planned for post-MVP (after CNN/IIT 4.0 implementation)

---

## 9. Sample Content for Mockups

Use these realistic bridge pairs:

**Bridge 1 — Victorian × Modern Evening Wear**
- Source: "Evening Dress" · The Met · Victorian · ca. 1895
- Target: "Off-Shoulder Lace Gown" · Fashionpedia · Contemporary · 2024
- Score: 87% (Semantic 81%, Visual 79%, Structural 72%)
- Narrative: "Both share the dramatic off-shoulder decolletage and structured boned bodice of formal evening wear, spanning a century of romantic design."
- Shared DNA: Fitted bodice, Off-shoulder, Floor-length, Lace overlay

**Bridge 2 — Regency × Modern Empire Waist**
- Source: "Promenade Dress" · Smithsonian · Regency · ca. 1815
- Target: "Empire Waist Maxi Dress" · Fashionpedia · Contemporary · 2024
- Score: 79% (Semantic 85%, Visual 68%, Structural 71%)
- Narrative: "The raised empire waistline and flowing full-length skirt connect Regency-era elegance to modern bohemian sensibility across two centuries."
- Shared DNA: Empire waist, Floor-length, Flowing skirt

**Bridge 3 — Art Deco × Modern Cocktail**
- Source: "Beaded Evening Dress" · The Met · Art Deco · ca. 1925
- Target: "Beaded Cocktail Dress" · Fashionpedia · Contemporary · 2025
- Score: 82% (Semantic 78%, Visual 84%, Structural 68%)
- Narrative: "Geometric beadwork and the straight dropped-waist silhouette bridge the Jazz Age flapper aesthetic to modern cocktail glamour."
- Shared DNA: Dropped waist, Beaded embellishment, Knee-length

---

## 10. Background Pattern

Used on page backgrounds (especially home hero):

A subtle cross-stitch / plus pattern in gold at 3% opacity. The SVG is:

```svg
<svg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'>
  <g fill='none' fill-rule='evenodd'>
    <g fill='#B8924A' fill-opacity='0.03'>
      <path d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/>
    </g>
  </g>
</svg>
```

Tile this as a fixed overlay on page backgrounds.

---

## 11. Tech Context (for code generation)

The frontend is **Next.js 16 + React 19 + TypeScript + Tailwind 4**. When generating code from these Figma designs:

- Use Tailwind utility classes, not inline styles
- Cormorant Garamond loaded via `next/font/google`
- Components live in `vv-web/src/components/`
- Pages use App Router: `vv-web/src/app/`
- API layer already exists: `vv-web/src/lib/api.ts`
- UI primitives exist: `vv-web/src/components/ui/` (Button, Input, Card, Badge)

---

*End of handoff. Build the design system first (tokens + components), then compose the pages.*
