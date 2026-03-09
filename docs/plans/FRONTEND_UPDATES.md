# Frontend Updates — New API Endpoints & Bridge Dimensions

## New Backend Capabilities

### Explore API (`/explore`)
- `GET /explore/functions` — all social functions with product counts
- `GET /explore/functions/{function}?culture=&era=` — products by social function, filterable

### Bridge Filters (existing `/bridges/top`, new params)
- `shared_function` — bridges where both products share a social function
- `temporal_type` — transmission | continuation | contemporary
- `crossing_type` — same_context | cross_category | cross_culture | cross_category_culture
- `connection_mode` — contrast | resonance | affinity
- `primary_axis` — volume | ornament | body | register

### Bridge Response (new fields on every bridge)
- `temporal_type`, `crossing_type`, `connection_mode`
- `primary_axis`, `secondary_axis`, `contrast_pair`

---

## Proposed Frontend Changes

### 1. Social Function Explorer Page (`/explore/functions`)

**Landing view:** Grid of social function cards, each showing function name + product count. Click through to detail.

**Detail view (`/explore/functions/[function]`):**
- **Timeline layout** — products ordered by era/decade, horizontal scroll or vertical timeline
- **Cultural grid** — group products by culture (rows) x era (columns)
- Filter chips for culture and era
- Link to related bridges: "See how different cultures approach {function}"

**API calls:**
- Landing: `GET /explore/functions`
- Detail: `GET /explore/functions/{function}`
- Related bridges: `GET /bridges/top?shared_function={function}&limit=10`

### 2. Bridge Card Enhancements

Current bridge cards show score + narrative. New fields enable richer display:

- **Connection mode badge** — contrast (rose), resonance (amber), affinity (gray)
- **Axis pill** — show primary_axis (e.g., "volume", "ornament") as a subtle label
- **Contrast pair callout** — when `connection_mode == 'contrast'`, display the `contrast_pair` string (e.g., "Exaggerated Volume <-> Column Minimalism")
- **Temporal badge** — transmission / continuation / contemporary icon or label

### 3. Bridge Filtering UI

Add filter controls to the bridges/top view:

- **Connection mode toggle** — contrast | resonance | affinity (or "all")
- **Temporal type toggle** — transmission | continuation | contemporary
- **Axis filter** — volume | ornament | body | register
- **Social function dropdown** — populated from `/explore/functions`

### 4. "Same Question, Different Answers" View

Dedicated view for contrasting approaches to the same social function:

- Pick a function (e.g., "wedding")
- Show bridges with `shared_function=wedding&connection_mode=contrast`
- Display as side-by-side product pairs with contrast_pair highlighted
- Fallback to `connection_mode=affinity` bridges if no contrasts found

---

## Jen's Notes

<!-- Add your frontend notes below -->


