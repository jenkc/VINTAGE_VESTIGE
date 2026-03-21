# Vintage Vestige — Design Handoff v2

**For:** Claude Code (Figma MCP + Next.js implementation)
**Date:** March 2026 (updated March 19 — bridge system reworked)
**Replaces:** February 2026 handoff (v1 — retired, too safe)

---

## The Problem with v1

The first design was hokey. Warm cream backgrounds, polite rounded corners, gold accents, everything safely inside cards. It looked like a nice SaaS product. Vintage Vestige is not a SaaS product. It's a fashion intelligence platform that makes arguments about 500 years of design history. The design should have an opinion.

---

## Design Vision

**One sentence:** An archive that feels like a magazine, a research tool that doesn't look like a research tool, serious about fashion history but not stuffy about it.

**The tagline that drives everything:** *Start from a question, not a timeline.*

### Tone

Fun, hip, playful, modern — but still sleek, stylish, professional. The intersection of three poles:

1. **Minimal/clinical** (YEEZY, BECANE) — extreme restraint, garments floating in space, the product *is* the design
2. **Brutalist/raw** (Brutalist Websites, RAW Magazine) — loud type, collage energy, personality bleeding through, things breaking the grid
3. **Editorial/navigable** (W Concept, W Magazine) — image-forward, confident typography, but still a product you can use

The design lives where all three overlap.

### What This Means in Practice

- **Typography gets loud** — big confident headlines, dramatic scale contrasts, mix weights aggressively. Type is a compositional element, not just labels.
- **White space is structural** — emptiness is a design choice. Garments float. Space around things means something.
- **Color is either absent or committed** — mostly monochrome with one sharp accent, or full editorial color when the moment calls for it. No more polite sage-and-gold-and-terracotta-all-at-once.
- **Images break out of containers** — full-bleed, overlapping, asymmetric, cropped unexpectedly. Garment photographs exist in space, not in cards.
- **The UI has personality** — hover states that surprise, transitions with character, type that does unexpected things.
- **No more "nice SaaS"** — no rounded pill badges on everything, no score circles, no card-based uniformity. Every page has a reason to look the way it does.

---

## 1. Design Tokens

### Color Palette

Stripped back. Monochrome base with intentional accent moments.

| Token | Hex | Role |
|---|---|---|
| `white` | `#FFFFFF` | Primary background, breathing space |
| `off-white` | `#F5F5F0` | Secondary backgrounds, subtle warmth |
| `black` | `#0A0A0A` | Primary text, bold elements |
| `dark` | `#1A1A1A` | Secondary text, UI elements |
| `grey-600` | `#6B6B6B` | Tertiary text, metadata |
| `grey-400` | `#9B9B9B` | Muted labels, inactive states |
| `grey-200` | `#E0E0E0` | Borders, dividers |
| `grey-100` | `#F0F0F0` | Subtle backgrounds, hover states |
| `accent` | `#C4553A` | Primary accent — terracotta. Used sparingly: one element per viewport max |
| `accent-hover` | `#A8432E` | Accent interactions |
| `signal-blue` | `#2E5A88` | Semantic similarity, data viz only |
| `signal-brown` | `#8B5E3C` | Visual similarity, data viz only |
| `signal-sage` | `#7A8B6F` | Structural similarity, data viz only |

**Platform colors** (used only in small type labels, never as fills):

| Platform | Color |
|---|---|
| The Met | `#8B2332` |
| Smithsonian | `#2E5A88` |
| Fashionpedia | `#6B6B6B` |
| V&A Museum | `#4A4A4A` |

### Typography

Two families, used with extreme contrast.

**Display:** Neue Haas Grotesk Display (or Helvetica Neue if licensing is an issue). Clean, authoritative, scales beautifully from 14px to 120px.

**Editorial / Accent:** Cormorant Garamond stays — but only for narratives, pull quotes, and editorial moments. Not for labels, not for badges, not for everything.

**Mono:** JetBrains Mono or IBM Plex Mono — for metadata, scores, technical labels. Gives the data layer a different texture from the editorial layer.

| Style | Font | Weight | Size | Usage |
|---|---|---|---|---|
| `display-hero` | Neue Haas Grotesk | 700 | 72–120px | Homepage hero, page titles |
| `display-lg` | Neue Haas Grotesk | 700 | 48–64px | Section headers |
| `display-md` | Neue Haas Grotesk | 600 | 32–40px | Sub-sections |
| `display-sm` | Neue Haas Grotesk | 600 | 24px | Card titles, product names |
| `body-lg` | Neue Haas Grotesk | 400 | 18px | Lead paragraphs |
| `body` | Neue Haas Grotesk | 400 | 16px | Body text |
| `body-sm` | Neue Haas Grotesk | 400 | 14px | Secondary text |
| `narrative` | Cormorant Garamond | 400 italic | 20–24px | Bridge narratives, pull quotes — this is the editorial voice |
| `mono-label` | JetBrains Mono | 400 | 11px | Metadata, scores, era dates, platform source |
| `mono-sm` | JetBrains Mono | 400 | 9px | Technical details, score breakdowns |

### Spacing

Use an 8px grid. Generous.

| Token | Value |
|---|---|
| `space-1` | 8px |
| `space-2` | 16px |
| `space-3` | 24px |
| `space-4` | 32px |
| `space-6` | 48px |
| `space-8` | 64px |
| `space-12` | 96px |
| `space-16` | 128px |

### Borders & Radii

Minimal. Borders are thin or absent. Radius is 0 or barely there.

| Token | Value | Notes |
|---|---|---|
| `border-default` | 1px solid `grey-200` | Used sparingly — prefer whitespace over borders |
| `radius-none` | 0 | Default for images, cards, containers |
| `radius-sm` | 4px | Buttons, inputs only |
| `radius-pill` | 999px | Tags only |

No rounded-corner cards. No 16px radius on everything. Sharp edges.

---

## 2. Component Specifications

### 2.1 Garment Image

The most important component. Not a thumbnail. Not trapped in a card.

**Default display:**
- No border, no border-radius, no container shadow
- Background: transparent or `white`
- Images are object-fit: contain — the garment's silhouette is the shape
- Generous padding around the garment so it floats (like YEEZY grid)
- On hover: subtle scale (1.02) + cursor pointer. No shadow lift.

**Full-bleed variant:**
- Image fills entire width or height of its container
- Object-fit: cover
- Used for hero moments, editorial layouts
- Text overlays directly on image with sufficient contrast

**Silhouette variant (BECANE-style):**
- Garment on white/transparent background
- Lined up horizontally like a collection lineup
- Small, almost icon-scale, with mono label below
- Used in collection overviews, axis sliders

### 2.2 Platform Label

Not a badge. Not a pill. Just text.

- **Font:** `mono-label` (11px JetBrains Mono)
- **Color:** Platform-specific color (see tokens)
- **No background, no border, no pill shape**
- Positioned near the image, not overlaid on it
- Example: `THE MET` or `SMITHSONIAN` in small mono type

### 2.3 Era Label

Same philosophy — just information, not decoration.

- **Font:** `mono-label`
- **Color:** `grey-600`
- **Format:** `Victorian · ca. 1895` or just `1895`
- No background, no pill

### 2.4 Score Display

Scores are data, not decoration. They belong to the mono/technical layer.

- **Font:** `mono-label` or `mono-sm`
- **Format:** `87%` or `0.87` — pick one and commit
- **Color:** `grey-600` normally, `accent` if you want to highlight high scores
- No circles. No rings. No gauge visualizations. Just the number.
- Score breakdowns (semantic / visual / structural) shown as a simple row of three numbers, mono type, with thin progress bars below if needed

### 2.5 Bridge Narrative

This is the editorial centerpiece. The one moment where Cormorant Garamond owns the page.

- **Font:** `narrative` (Cormorant Garamond italic, 20–24px)
- **Color:** `black` or `dark`
- **No quote box. No left border. No background color.**
- Just the text, large, breathing in whitespace
- Can be overlaid on a blurred/dimmed image background for dramatic moments
- Opening quote mark can be oversized (72px+) as a typographic element

### 2.6 Attribute Tags

What was "Shared Design DNA pills" — simplified.

- Small horizontal list of terms
- **Font:** `mono-sm` (9px) or `body-sm` (14px)
- **Style:** Either plain text separated by middot (`Fitted bodice · Off-shoulder · Floor-length`) or minimal tag with 1px border and `radius-pill`
- **Color:** `grey-600` for text, `grey-200` for border if tagged
- No sage green, no pill-label/value pairs, no complexity

### 2.7 Bridge Display

The bridge between two garments. Replaces the "bridge card" concept entirely.

**The bridge is not a card. It's a layout. A bridge is a path — it shows how two garments connect through shared DNA, not how they disagree.**

**Full bridge layout (product detail page, bridge explorer):**
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   [GARMENT A]                         [GARMENT B]           │
│   large image                         large image           │
│   floating in space                   floating in space     │
│                                                             │
│   THE MET · 1895                      V&A · 1920            │
│   Evening Dress                       Beaded Evening Gown   │
│                                                             │
│              FRENCH → BRITISH · 25 YEARS                    │
│                                                             │
│         "Both gowns deploy the same structural              │
│          logic: a fitted boned bodice releasing              │
│          into floor-length volume, but where the             │
│          Victorian version conceals in taffeta,              │
│          the Jazz Age answer strips to beaded                │
│          silk that moves with the body."                     │
│                                                             │
│   SHARED: hand-sewing · boning · floor length               │
│   MOVEMENT: Neoclassicism                                   │
│   INFLUENCES: French court fashion                          │
│                                                             │
│   85%  TEXT 81%  VISUAL 79%  STRUCTURAL 72%                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Key principles:
- Two images, side by side or asymmetric (one larger than the other)
- No card border, no card background, no card shadow
- The narrative is the center of gravity — large italic serif
- The **path label** between garments shows crossing + year gap: `FRENCH → AMERICAN · 120 YEARS` or `CROSS-CULTURE · SAME ERA`
- Shared garment fields, movements, influences, designer shown as the "why" of the connection
- Metadata (scores, tags, platform) lives in the mono layer below
- No gold circle connector. No exchange-arrows icon. No axis labels. No contrast pair names.

**Compact bridge (horizontal scroll, grids):**
- Two garment images side by side, small (140–180px height)
- Single line below: `Victorian → Art Deco · 25yr · 85%` in `mono-label`
- Narrative truncated to one line on hover tooltip
- No border, no card shadow. Just images + one line of text.

**Bridge connection types** (used for sorting/filtering, not prominent display):
- `lineage` — one garment explicitly references the other's tradition
- `echo` — same form reappearing 40+ years apart
- `parallel` — independent expressions of the same idea across cultures
- `visual` — they look alike despite different contexts
- `contrast` — opposite aesthetic arguments with shared structural DNA

---

## 3. Page Specifications

### 3.1 Homepage

The homepage makes one argument: this is not a regular fashion site.

**Hero section:**
- Full viewport height
- `VINTAGE VESTIGE` in `display-hero` (80–120px), either centered on white or overlaid on a full-bleed collage of garment images
- Below: the tagline. Not "A fashion knowledge graph connecting 500 years of design history." Instead: **"Start from a question, not a timeline."** — set in `narrative` style, 28px italic.
- One CTA: `EXPLORE` — minimal button, black fill, white text, small, doesn't dominate
- No "How It Works" section. No three-icon cards. That's SaaS language. Kill it.

**Bridge of the Day:**
- Full-width section below hero
- One high-scoring bridge with a narrative, displayed as a full bridge layout
- Rotates daily, biased toward: cross-culture, large year gap, lineage or echo connections
- The narrative is the headline — huge italic serif text
- Two garment images flanking it, full-bleed or floating
- `mono-label` metadata below: crossing type, year gap, shared movements/influences

**Collection pulse:**
- Dense grid of garment silhouettes (BECANE-style) — maybe 20–30 garments across, small scale
- A living texture that shows the scope of the collection
- Hovering any garment reveals its name and era
- Clicking enters the product detail
- Alternative: mosaic wall — all 4,234 garments as tiny thumbnails, color-sorted or era-sorted

**Entry points:**
- Not navigation cards. Text links, set large:
  - `BROWSE BY ERA`
  - `BROWSE BY CULTURE`
  - `BROWSE BY FUNCTION`
  - `EXPLORE CONNECTIONS`
- Set in `display-md`, stacked vertically, left-aligned, with generous spacing
- Each one is a door into the collection

### 3.2 Product Search / Explore Page

**Route:** `/search` (text search) and `/explore` (browse entries)

This page serves multiple entry modes. The mode determines what you see.

**Search bar:**
- Top of page, full width, minimal
- Large input text (18px), no border — just a bottom rule
- Placeholder: `Search garments, eras, vibes, or paste a question...`
- Results appear below as a grid

**Browse modes (tabs or large text links at top):**

**By Era:**
- Timeline ribbon — horizontal band, eras proportionally spaced
- Each era segment shows its outbound bridge count as density/thickness
- Click an era → its garments + where its design ideas traveled (bridges to other eras)
- Not just "here are Victorian garments" but "Victorian connects to these 6 periods — here's how"

**By Culture:**
- Same concept as era — pick a culture, see where its design ideas traveled via bridges
- "Show me every culture's formal evening wear" as a visual survey

**By Social Function:**
- Functions listed: Ceremonial, Mourning, Labor, Courtship, Religious, Military, Performance, Daily Wear
- Click one → all garments with that function, across every culture and era
- Grouped by culture or era (user toggles)
- "Show me every culture's answer to wedding dress"

**Search results grid:**
- Clean grid, 3–4 columns desktop, 1–2 mobile
- Each result: garment image (no container), title in `display-sm`, platform + era in `mono-label`
- No score shown in grid — scores appear on product detail
- Hover: image scales subtly (1.02), metadata fades in below

### 3.3 Product Detail Page

**Route:** `/product/[id]`

**Hero:**
- Large garment image, left side (or full-width bleed)
- Title in `display-lg` (40–48px)
- Platform + era + date in `mono-label` below title
- Tags (category, material, construction) as minimal text or thin-border pills
- AI description in `body-lg`
- Structured metadata (era, culture, material) in a 2-column grid, `mono-label` keys, `body-sm` values

**"CONNECTED TO" — PRIMARY BRIDGE SECTION:**
- This is the main event on the product page
- Section headline: `CONNECTED TO` in `display-md`
- Shows bridges sorted by `bridge_score` descending — strongest connections first
- Each bridge shows: the connected garment, the narrative (if available), the year gap, and the shared DNA (techniques, movements, influences, designer)
- Lineage bridges (explicit influence references) get priority display
- Displayed as full bridge layouts (see component spec 2.7)

**"ECHOES ACROSS TIME":**
- Secondary section below
- Echo bridges (40+ year gap) — same form reappearing across decades/centuries
- Displayed as compact bridges in a horizontal scroll or 2-column grid
- Focus on the temporal span: `1895 → 1960s · 65 YEARS` prominently displayed

**"PULL THE THREAD":**
- Tertiary section — a CTA, not a list
- One button/link: `PULL THE THREAD →`
- Takes you into the Thread Pull interaction (see 4.6) starting from this product
- The graph picks the path — you follow where the connections lead

### 3.4 Bridge Explorer Page — NEW

**Route:** `/bridges` or `/explore/bridges`

A dedicated space for browsing bridges as first-class objects.

**Hero:**
- `CONNECTIONS` in `display-hero`
- Subhead: `18,798 paths between garments across 500 years` in `mono-label`

**Filter bar:**
- Horizontal row of filter dropdowns/toggles:
  - Connection: `LINEAGE` · `ECHO` · `PARALLEL` · `VISUAL` · `ALL`
  - Time: `SAME ERA` · `20-80 YEARS` · `80+ YEARS` · `ALL`
  - Crossing: `CROSS CULTURE` · `CROSS CATEGORY` · `ALL`
- Filters in `mono-label` style, minimal toggles (underline active, grey inactive)

**Preset quick links:**
- `LONGEST ECHOES` — echo connections, 80+ year gap, sorted by year_gap desc
- `LINEAGE` — bridges where one garment's influence_references match the other
- `INDEPENDENT INVENTIONS` — same-era, cross-culture parallel connections
- `SAME DNA, DIFFERENT WORLDS` — high structural overlap, cross-culture
- `SURPRISE ME` — random high-score bridge with narrative

**Results:**
- Full bridge layouts, stacked vertically
- One bridge per viewport height for dramatic impact
- Infinite scroll or paginated

**Bridge of the Day** featured at the top with editorial treatment

### 3.5 About Page

- Minimal. Max-width 640px centered.
- Headline: the product copy line — "Start from a question, not a timeline."
- Body: what it is, who built it, what data sources, what the tech does (briefly)
- No hero image. Typography carries it.

---

## 4. Interaction Vocabulary

All specced for implementation. Organized by build priority.

### Tier 1: Launch Set

These ship first. They demonstrate the core argument.

**4.1 Thread Pull**

Pick any garment, follow the graph wherever it leads. This is the signature interaction.

- Click "Pull the thread" on any product
- System traces a continuous path: product → strongest bridge → connected product → strongest bridge → ...
- Path follows highest `bridge_score` bridges, preferring lineage and echo connections
- Displayed as a vertical scroll: garment, narrative, year gap + crossing label, garment, narrative...
- You don't choose the destination. The graph does.
- Stop at any point and branch to a different thread from the current garment
- The shared DNA (movements, influences, techniques) is shown at each step — you see *why* the graph went there
- **Data source:** iterative bridge lookups via `GET /products/{id}/bridges`, sorted by `bridge_score` desc

**4.2 Bridge of the Day**

One editorial-quality bridge, prominently displayed on the homepage.

- Full bridge layout with both garment images large
- The narrative in `narrative` style as the headline
- Year gap and crossing context in `mono-label`
- Shared movements, influences, techniques below
- Rotates daily, biased toward: lineage connections, large year gaps, cross-culture, bridges with narratives
- **Data source:** `GET /bridges/top` filtered by `connection_mode` and `min_score`

**4.3 "Connected To"**

On product detail pages. Already specced in section 3.3.

- Shows strongest bridges for the current product
- Full bridge layout with narrative, year gap, shared DNA
- Lineage bridges get priority (explicit influence references)
- Falls back to highest `bridge_score` bridges

### Tier 2: Second Wave

Built after launch set proves the concept.

**4.4 Movement Trails**

Pick a named movement, follow it through the collection.

- Entry: click a movement (Neoclassicism, Art Deco, Japonisme, Power Dressing, Mod, etc.)
- Shows all products tagged with that movement
- Products connected by bridges that share the movement are linked — follow the thread
- The trail is: Movement → Product → Bridge (shared movement) → Product → Bridge → ...
- Display as a vertical scroll with alternating: garment, narrative, garment, narrative
- Feels like reading a visual essay about one design idea traveling through time and culture
- **Data source:** products' `named_movements`, bridges with `shared_movements`

**4.5 Social Function Threads**

All garments with a shared social function, connected by their bridges.

- Entry: click a function (ceremonial, mourning, labor, etc.)
- Shows all garments with that function across every culture and era
- Can group by: culture (default) or era
- Within each group, bridges between garments are shown
- "Every culture's answer to wedding dress" as a visual survey
- **Data source:** products' `social_function` array, bridges with `shared_function` filter, explore endpoints

**4.6 Influence Map**

Trace where a garment's influences came from and where they went.

- Entry: click "See influences" on any product with `influence_references`
- Shows the product's stated influences as entry points
- For each influence, find products in the collection that match (via text similarity or exact field match)
- Display as a visual tree: influences flow in from the left, the product sits center, and products it influenced (via lineage bridges) flow out to the right
- **Data source:** products' `influence_references`, lineage bridges

**4.7 Split Screen Compare**

Workbench for building your own pairings.

- Two panels side by side, each independently browsable
- Drag/search a garment into either panel
- The space between fills with bridge data (if a bridge exists) or "No bridge computed" if not
- Great for students researching specific comparisons
- Can save/share pairings via URL
- **Data source:** bridges `between` endpoint

### Tier 3: Exhibition Pieces

High-impact, high-effort. Demo/grant-application gold.

**4.8 Constellation Map**

Spatial visualization of the entire collection.

- All 4,234 garments positioned in 2D space
- Positioning by: era × culture, or axis position, or vibe cluster (user selects)
- Garments as small dots or tiny thumbnails
- Bridges as lines between dots (filtered by mode/axis)
- Filters reveal/hide clusters — toggle an era, a culture, a vibe
- Click/hover any dot to reveal the garment
- Zoom: overview → cluster → individual garment
- Like a semantic Google Earth for fashion history
- **Data source:** product attributes for positioning, bridges for connections

**4.9 Gravity Well**

One garment in the center, its bridges orbiting.

- Selected garment centered, large
- Connected garments orbit at distances proportional to tension score
- Lineage/echo bridges orbit close and hot (accent color)
- Visual/parallel bridges drift further out (grey)
- Click any orbiting garment → it swaps to center, constellation rearranges
- Walking the graph spatially
- **Data source:** product's bridges, sorted by tension score

**4.10 Timeline Ribbon**

Horizontal timeline where eras are proportionally spaced.

- Eras as segments, width proportional to temporal span
- Garments float above/below the line based on a dimension (bridge count, institutional vs. vernacular)
- Dense clusters = rich data, gaps = something interesting too
- Click era segment → expands to show cross-era bridge connections radiating outward
- Bridges rendered as arcs connecting eras above the timeline
- **Data source:** products by era/decade, bridges with year_gap

**4.11 Mosaic Wall**

All 4,234 garments as a dense image grid.

- Tiny thumbnails (30–50px), packed tight
- Can sort by: era (chronological), color (dominant color), culture, platform
- Hover: garment pops to full size with metadata tooltip
- Click: navigate to product detail
- Filter by vibe/function and watch tiles fade in/out
- The density itself is the statement — this is what 500 years of fashion looks like
- **Data source:** all products, sorted by chosen dimension

**4.12 Stack / Deck**

Garments as a swipeable card deck.

- One garment visible at a time, full-screen
- Swipe/arrow to reveal next
- Each card shows the bridge relationship to the previous card
- Not random browsing — the system picks the path based on entry mode
- Movement trail entry → cards follow the movement thread
- Function entry → cards follow the function across cultures
- Thread pull entry → cards follow highest-score bridges
- Mobile-first interaction
- **Data source:** ordered sequence from vibe trail / axis walk / function thread logic

---

## 5. Navigation Structure

### Global Navigation

Minimal. Top of page, not sticky (the content should own the viewport).

- **Left:** `VINTAGE VESTIGE` in bold sans (not decorative — the brand IS the typography)
- **Right:** `SEARCH` · `EXPLORE` · `BRIDGES` · `ABOUT`
- **Style:** `mono-label` or small `body-sm`, uppercase, spaced
- On mobile: hamburger, full-screen overlay menu with large type

### Site Map

```
/                   Homepage (hero + bridge of the day + collection pulse + entry points)
/search             Product search (text search + browse modes)
/search?function=X  Filtered by social function
/search?era=X       Filtered by era
/search?culture=X   Filtered by culture
/search?movement=X  Filtered by named movement
/product/[id]       Product detail (hero + connected to + echoes + pull the thread)
/bridges            Bridge explorer (filter + presets + full bridge layouts)
/about              About page
```

### Routes (5 total, up from 4)

| Route | Rendering | Notes |
|---|---|---|
| `/` | Static + ISR (1hr) | Bridge of the Day changes daily |
| `/search` | Client-side data fetching | Multiple browse modes via query params |
| `/product/[id]` | Server-rendered | Dynamic per product |
| `/bridges` | Client-side data fetching | Heavy filtering |
| `/about` | Static | |

---

## 6. Responsive Behavior

### Desktop (1440px+)
- Full-width layouts, generous whitespace
- Bridge displays: two garments side by side
- Search grid: 3–4 columns
- Axis slider: full-width horizontal

### Tablet (768–1439px)
- Narrower margins
- Bridge displays: still side by side but tighter
- Search grid: 2–3 columns
- Axis slider: full-width, slightly smaller garment previews

### Mobile (< 768px)
- Single column
- Bridge displays: garments stacked vertically, narrative between
- Search grid: 1–2 columns
- Axis slider: horizontal scroll, swipe-based
- Stack/deck interaction becomes primary bridge browsing mode
- Navigation: full-screen overlay menu

---

## 7. Animation & Interaction Principles

- **Transitions:** 300ms ease-out default. No spring physics, no bounce. Clean.
- **Image hover:** scale 1.02–1.05, no shadow lift, no border change
- **Page transitions:** fade or slide, minimal. Content should appear quickly.
- **Scroll:** smooth scroll for anchor links. No parallax. No scroll-jacking.
- **Axis slider:** drag should feel immediate, no lag. Garments appear/fade with 200ms opacity transition.
- **Loading states:** skeleton screens are fine, but use simple pulsing rectangles (not the card-shaped skeletons from v1). Or: just show a progress bar.
- **No animation for its own sake.** Every motion should communicate state change or spatial relationship.

---

## 8. Sample Content

Use these for all mockups and prototypes.

### Bridge 1 — Lineage: Victorian Gymnasium Suits

- Source: "Forest Green Wool Gymnasium Suit with Red Trim" · Smithsonian · Victorian · ca. 1890
- Target: "Tan Wool Twill Three-Piece Gymnasium Suit" · Smithsonian · Victorian · ca. 1890
- Score: 77% (Text 74%, Visual 82%, Structural 76%)
- Mode: Lineage
- Shared movements: Dress Reform Movement
- Shared influences: Turkish trouser influence
- Narrative: "Both gymnasium suits adopted the Turkish trouser — scandalous in its day — as a practical concession to women's movement, revealing how dress reform borrowed from Eastern garment traditions to argue for Western women's physical freedom."
- Shared: wool · tailoring · trouser construction

### Bridge 2 — Echo: Japanese Kimono Across 75 Years

- Source: "Ivory Silk Kimono with Wisteria Embroidery" · V&A · Edwardian · ca. 1910
- Target: "Pale Blue Silk Satin Kimono with Embroidered Scenes" · V&A · Romantic · ca. 1835
- Score: 74% (Text 72%, Visual 78%, Structural 73%)
- Mode: Echo · 75 year gap
- Shared influences: traditional Japanese kimono construction
- Narrative: "Both kimono deploy the same T-shaped construction and obi-anchored silhouette, but where the earlier piece tells narrative scenes in thread, the later strips to botanical motifs — a 75-year evolution from storytelling to pure ornament within the same unchanging form."
- Shared: silk · hand-embroidery · T-shaped construction

### Bridge 3 — Parallel: French × American Empire Gowns

- Source: "Golden Yellow Silk Empire Waist Evening Gown" · V&A · Regency · ca. 1800 · French
- Target: "White Pink Blue Silk Empire Evening Gowns" · V&A · Regency · ca. 1810 · British
- Score: 85% (Text 88%, Visual 85%, Structural 83%)
- Mode: Parallel · cross-culture
- Shared movements: Neoclassicism
- Shared influences: Ancient Greek chiton, neoclassical drapery
- Narrative: "Both gowns employ the Neoclassical strategy of raising the waistline to just below the bust and letting fabric fall in columnar lines to the floor — a shared rejection of 18th-century artifice that spread simultaneously across French and British court fashion."
- Shared: a-line · empire waistline · draping · silk · floor length

---

## 9. Figma File Structure

```
Page 1: 🎨 Tokens
  ├── Color palette (swatches)
  ├── Typography scale (all styles)
  ├── Spacing & grid reference
  └── Border & radius reference

Page 2: 🧩 Components
  ├── Garment image (default + full-bleed + silhouette)
  ├── Platform label
  ├── Era label
  ├── Score display
  ├── Attribute tags
  ├── Bridge narrative
  ├── Bridge layout — full (with narrative + shared DNA)
  ├── Bridge layout — compact
  ├── Search bar
  ├── Filter bar
  ├── Axis slider
  ├── Nav header
  └── Nav mobile overlay

Page 3: 📱 Pages — Desktop (1440px)
  ├── Homepage
  ├── Search / Explore (era mode)
  ├── Search / Explore (culture mode)
  ├── Search / Explore (function mode)
  ├── Product Detail
  ├── Bridge Explorer
  └── About

Page 4: 📱 Pages — Mobile (390px)
  ├── Homepage
  ├── Search / Explore
  ├── Product Detail
  ├── Bridge Explorer
  └── About

Page 5: ✨ Interactions
  ├── Thread Pull (annotated flow)
  ├── Movement Trail (annotated flow)
  ├── Influence Map (annotated flow)
  └── Stack / Deck (annotated flow)

Page 6: 🔮 Exhibition Concepts
  ├── Constellation Map (concept sketch)
  ├── Gravity Well (concept sketch)
  ├── Timeline Ribbon (concept sketch)
  └── Mosaic Wall (concept sketch)
```

---

## 10. Tech Context

**Stack:** Next.js 16 + React 19 + TypeScript 5 + Tailwind 4

**Fonts:**
- Neue Haas Grotesk Display via `next/font/local` (or Helvetica Neue as fallback via `next/font/google`)
- Cormorant Garamond via `next/font/google`
- JetBrains Mono via `next/font/google`

**Components:** `vv-web/src/components/`
**Pages:** App Router at `vv-web/src/app/`
**API:** `vv-web/src/lib/api.ts` (12 functions covering all 16 backend endpoints)

**Backend endpoints available for interactions:**
- `POST /search/text` — text search with filters
- `GET /products/{id}` — product detail (includes KG fields: designer, influences, movements, garment_system, material_origin, production_mode)
- `GET /products/{id}/bridges` — all bridges for a product (sorted by bridge_score)
- `GET /bridges/top` — top bridges with filters: connection_mode, crossing_type, min_score, min_year_gap
- `GET /bridges/stats` — bridge statistics
- `GET /bridges/between/{a}/{b}` — bridge between two specific products
- `GET /explore/functions` — list social functions
- `GET /explore/functions/{name}` — function detail with culture/era filters
- `GET /filters` — all available filter values

**Bridge data model (what the API returns per bridge):**
- `bridge_score` — composite score (0-1), structural-heavy weighting
- `text_similarity`, `image_similarity`, `structural_score` — component scores
- `year_gap` — integer years between the two products
- `crossing_type` — cross_culture, cross_category, cross_category_culture, same_context
- `connection_mode` — lineage, echo, parallel, visual, contrast, or null
- `shared_garment_fields` — what structural DNA they share (silhouette, technique, etc.)
- `shared_designer`, `shared_movements`, `shared_influences` — KG edge data
- `bridge_narrative` — AI-generated story of the connection (editorial voice, 2-3 sentences)

---

*Build the tokens first. Then the components. Then compose the pages. The interactions layer on top.*

*When in doubt: less chrome, more garment. The clothing is the interface.*


# Implementation Plan
# Vintage Vestige v2 Redesign — Implementation Plan

## Context

The current frontend has a "nice SaaS" aesthetic (warm cream, gold accents, rounded cards, Inter font). The v2 design handoff calls for an editorial/brutalist/minimal redesign — "an archive that feels like a magazine." This plan covers the full transformation across 5 phases, with Jen typing the code guided step-by-step.

**Key decisions:**

- **Display font:** Space Grotesk (free, Google Fonts, geometric sans with personality)
- **Approach:** Guide Jen through each change (she types the code)
- **Scope:** Full redesign, Phase 1 (tokens/foundation) first

---

## Phase 1: Design Tokens & Foundation

**Goal:** Replace all design tokens so everything shifts to the new palette immediately.

### 1A. `vv-web/tailwind.config.ts`

- **Remove colors:** cream, cream-dark, warm-white, charcoal, charcoal-soft, muted, border, border-light, gold, sage, sage-dark, sage-text, etsy, depop
- **Add colors:** off-white (#F5F5F0), black (#0A0A0A), dark (#1A1A1A), grey-600/400/200/100, accent (#C4553A), accent-hover (#A8432E), signal-blue/brown/sage, va_museum (#4A4A4A)
- **Update:** fashionpedia color #5C7A5E → #6B6B6B, keep met/smithsonian/terracotta(→accent)
- **fontFamily:** display (Space Grotesk), editorial (Cormorant), mono (JetBrains Mono)
- **Remove boxShadow:** card, card-hover, connector (no shadows in v2)
- **Replace borderRadius:** none (0px default), sm (4px), tag (999px)

### 1B. `vv-web/src/app/layout.tsx`

- **Remove:** Inter import
- **Add:** Space_Grotesk and JetBrains_Mono from next/font/google
- **Rename:** Cormorant variable to `--font-editorial`
- **Add:** Space_Grotesk as `--font-display`, JetBrains_Mono as `--font-mono`
- **Body class:** `font-display antialiased min-h-screen flex flex-col`

### 1C. `vv-web/src/app/globals.css`

- **Body:** `bg-white text-black` (was bg-cream-dark text-charcoal)
- **Headings:** `font-display` (was font-serif)
- **Remove:** gold scrollbar → grey scrollbar
- **Remove:** `--radius: 0.5rem` → `--radius: 0px`

### 1D. `vv-web/src/styles/theme.ts`

- Update PLATFORM_COLORS (add va_museum, change fashionpedia)
- Update PLATFORM_NAMES (add V&A)
- Remove `scoreColorByValue()` function
- Update CONNECTION_MODE_COLORS to use accent/grey

### 1E. Global find-and-replace across all .tsx files

Mechanical swap of old Tailwind classes → new:

- `bg-cream-dark` → `bg-white`, `bg-cream` → `bg-off-white`, `bg-warm-white` → `bg-white`
- `text-charcoal` → `text-black`, `text-charcoal-soft` → `text-dark`, `text-muted` → `text-grey-400`
- `border-border` → `border-grey-200`, `text-gold` → `text-grey-400`
- `text-terracotta` → `text-accent`, `bg-terracotta` → `bg-accent`
- `shadow-card*` → remove, `rounded-2xl`/`rounded-xl` → `rounded-none`
- `font-serif` → context-dependent (`font-editorial` for narratives, `font-display` for headings)

**Verify:** dev server renders with new palette, no missing class errors.

---

## Phase 2: Atomic Components

**Goal:** Rebuild smallest components to match new design system.

| Component                       | File                       | Key Changes                                                                                                                                                                      |
| ------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Button**                      | ui/Button.tsx              | Remove rounded-md, add `rounded-sm tracking-wide uppercase font-mono text-[11px]`. Variants: default=black bg, outline=grey-200 border, ghost=grey-100 hover, add accent variant |
| **Card**                        | ui/Card.tsx                | Strip all chrome (rounded, border, shadow). Becomes a plain div or border-b only                                                                                                 |
| **Badge**                       | ui/Badge.tsx               | Kill pill shape. Mono-label style: `font-mono text-[11px] uppercase tracking-wider`                                                                                              |
| **Input**                       | ui/Input.tsx               | Bottom border only, no rounded, `text-lg bg-transparent border-b border-grey-200 focus:border-black`                                                                             |
| **Skeleton**                    | ui/Skeleton.tsx            | `bg-grey-100` (was bg-border)                                                                                                                                                    |
| **ImageWithFallback**           | ui/ImageWithFallback.tsx   | Fallback `bg-grey-100`                                                                                                                                                           |
| **PlatformBadge→PlatformLabel** | bridge/PlatformBadge.tsx   | Mono text only, platform color, no bg/border/pill                                                                                                                                |
| **EraBadge→EraLabel**           | bridge/EraBadge.tsx        | `font-mono text-[11px] text-grey-600`, no pill                                                                                                                                   |
| **ScoreCircle→ScoreDisplay**    | bridge/ScoreCircle.tsx     | Kill circle. Just `font-mono text-sm text-grey-600` number                                                                                                                       |
| **NarrativeBlock**              | bridge/NarrativeBlock.tsx  | Kill blockquote/border. `font-editorial text-xl italic` breathing in whitespace                                                                                                  |
| **AttributePill→AttributeTag**  | bridge/AttributePill.tsx   | Plain text with middots or minimal 1px border                                                                                                                                    |
| **ScoreBreakdown**              | bridge/ScoreBreakdown.tsx  | Mono typography, thinner bars (2px), signal colors                                                                                                                               |
| **ConnectionBadge**             | bridge/ConnectionBadge.tsx | Kill colored pills → mono-label text with middots                                                                                                                                |
| **BridgeConnector**             | bridge/BridgeConnector.tsx | Mark for deletion in Phase 3                                                                                                                                                     |

Update barrel exports in `bridge/index.ts` and `ui/index.ts`.

---

## Phase 3: Composite Components & Layout

|Component|File|Key Changes|
|---|---|---|
|**Header**|layout/Header.tsx|NOT sticky. Left: `VINTAGE VESTIGE` bold display. Right: `SEARCH · EXPLORE · BRIDGES · ABOUT` in mono. Mobile: full-screen overlay|
|**Footer**|layout/Footer.tsx|Minimal single-line mono. Kill 3-column grid|
|**BridgeCardFull→BridgeDisplay**|bridge/BridgeCardFull.tsx|NOT a card → a layout. Two floating images, narrative center, mono metadata below. No card chrome|
|**BridgeCardCompact→BridgeCompact**|bridge/BridgeCardCompact.tsx|Two images (140-180px), one line mono text. No card chrome|
|**ProductCard**|search/ProductCard.tsx|No rounded/border/shadow. Image `object-contain`, mono metadata, hover `scale-[1.02]`|
|**SearchBar**|search/SearchBar.tsx|Full-width, bottom border only, `text-lg font-display`|
|**ImageUpload**|search/ImageUpload.tsx|Dashed grey border, mono labels|

Delete `BridgeConnector.tsx` and remove from barrel.

---

## Phase 4: Pages

### 4A. Homepage (`app/page.tsx`) — Complete rewrite

1. **Hero:** Full viewport. `VINTAGE VESTIGE` in display-hero (72-120px). Tagline: "Start from a question, not a timeline" in editorial italic. Single `EXPLORE` CTA.
2. **Bridge of the Day:** One contrast bridge as opposition layout (two garments facing each other, narrative between).
3. **Collection Pulse:** Dense grid of tiny garment silhouettes (80-100px, 6-10 columns).
4. **Entry Points:** Large text links: `BROWSE BY VIBE` / `BROWSE BY ERA` / `BROWSE BY FUNCTION` / `EXPLORE BRIDGES` in display-md.
5. **Kill:** "How It Works" section.

### 4B. Search (`app/search/page.tsx`)

- Full-width search bar, bottom border only
- Browse mode tabs (By Era, By Culture, By Function, By Movement) in mono-label
- Clean grid results (4 cols desktop, 2 mobile)

### 4C. Product Detail (`app/product/[id]/page.tsx`)

- Large image left, display-lg title, mono metadata
- Sections: "CONNECTED TO" (strongest bridges), "ECHOES ACROSS TIME" (40+ yr gap), "PULL THE THREAD" (CTA into graph walk)

### 4D. Bridge Explorer (`app/bridges/page.tsx`)

- Display-hero title, mono filter bar, preset quick links
- Full BridgeDisplay layouts stacked vertically (not 2-col card grid)

### 4E. About (`app/about/page.tsx`)

- 640px centered, display title, mono "Built With" list, update tech references

### 4F-4G. Explore functions pages — restyle to match

### 4H. Error/loading/not-found pages — update colors/fonts

---

## Phase 5: Tier 1 Interactions
### 5A. Thread Pull — NEW `components/explore/ThreadPull.tsx`

- Vertical scroll experience: garment → narrative → garment → narrative
- Auto-follows highest bridge_score path from starting product
- Branch points at each garment (click to fork the thread)
- Used on `/product/[id]` (Pull the Thread CTA) and as standalone `/thread/[id]` route

### 5B. Bridge of the Day — NEW `components/bridge/BridgeOfTheDay.tsx`
- Editorial treatment of one high-quality bridge
- Full-width layout with large images, narrative as headline
- Year gap and crossing context prominently displayed
- Used on homepage
### 5C. Animation utilities in globals.css
- `transition-editorial`: 300ms ease-out
- `hover-lift`: scale-[1.02] transition

---
## Files NOT changing
- `lib/api.ts` — API layer stays as-is
- `lib/constants.ts` — constants stay
- `types/index.ts` — type definitions stay
- `lib/utils.ts` — cn() utility stays
## Verification
After each phase
1. Run `npm run dev` and visually inspect all routes
2. Check responsive behavior (mobile/tablet/desktop)
3. Run `npm run build` to catch type/compile errors
4. Run existing tests: `npx vitest run`

## Session Plan

- **Session 1:** Phase 1 (tokens + global find-replace)
- **Session 2:** Phase 2 (atomic components)
- **Session 3:** Phase 3 (composites + layout)
- **Session 4:** Phase 4A-4B (homepage + search)
- **Session 5:** Phase 4C-4D (product detail + bridges)
- **Session 6:** Phase 4E-4H (remaining pages)
- **Session 7:** Phase 5 (interactions)