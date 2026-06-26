# Thread Pull v2 — Implementation Plan & Diff Shape

**Author:** Iris (engineering) · **Date:** 2026-06-25
**Companion design work:** Soren (Deliverable #1, motion/branch/wayfinding visual directions)
**Status:** PROPOSAL — awaiting Jen's green-light before large edits. Built so Jen can walk through and hand-implement.

This document is the **engineering** counterpart to the brief at
`.claude/plans/before-we-start-working-flickering-plum.md`. It describes *which files change, what each
change is, and the shape of the diff* — not a finished implementation. Small scaffolding edits (CSS
keyframes, a pure util) are flagged as low-risk; everything touching `ThreadPull.tsx` state is described
as a structure, for review first.

---

## 0. Guardrails I'm honoring (restating so the diff stays inside them)

- **No backend.** Everything below consumes the existing `getProductBridges(id, { limit })`. The only
  change to API usage is raising `limit` (10 → ~12–15) so the branch runners-up come back for free.
- **No deploy-path files.** Nothing here touches `api/`, deploy config, `requirements.txt`, or env vars.
- **No new dependency.** No Framer Motion, no animation lib. Motion is CSS keyframes + an SVG path with
  animated `stroke-dashoffset`. The repo has zero animation deps today and an editorial aesthetic — a lib
  would be both overkill and off-brand. (If Soren's direction needs spring physics we can revisit, but I
  don't think it will — the "unspool" reads better as a steady draw than a bounce.)
- **Preserve correctness:** highest-score-first default traversal, visited-cycle prevention, lineage edges
  showing `lineage_reference`, distance line, narrative, and the **gradient fallback for missing
  `primary_image`** all survive. The `Node`/`Edge` render bodies are reused almost verbatim.
- **`prefers-reduced-motion`** is a first-class branch, not an afterthought — see §3.4.

---

## 1. A bug to fix while we're in here (cycle guard)

Current `ThreadPull.tsx` rebuilds `visitedIds` on every render from `steps` (lines 40–45), but `pullNext`
is a `useCallback` with `[steps]` deps that *mutates* that freshly-built set inside its async body. For
**linear pull** this happens to work, because `steps` is fresh on each render and the callback is recreated
each render. **It will not survive branching.** The moment we replace-the-tail (truncate `steps` and
continue), a garment that was on the old tail must be *removed* from `visitedIds` so it can be revisited on
a different branch — but the current derivation can't express "visited on the *current* path" cleanly, and
the mutate-the-derived-set pattern is a footgun.

**Fix (small, do this first):** derive `visitedIds` from the path with `useMemo`, and never mutate it
inside the callback. After a branch truncates the path, the memo recomputes the correct visited set
automatically.

```ts
const visitedIds = useMemo(
  () => new Set(steps.map(s => s.product.id)),
  [steps]
);
```

Then `pullNext` reads `visitedIds` but does not `.add()` to it — the `setSteps` append (or branch
truncate-then-append) is the single source of truth, and the memo follows. This is the linchpin that makes
branching correct, so it lands first.

---

## 2. State model (the heart of the change)

Today: `steps: ThreadStep[]` + `loading` + `exhausted`. That's enough for linear pull. Branching and
wayfinding need a little more, but **not much** — the whole point of "replace-the-tail" (Decision below) is
that there is still exactly one `steps` array; we just sometimes truncate it before appending.

Proposed component state:

```ts
interface ThreadStep {
  product: ProductSummary;
  bridge?: BridgeResult;          // the bridge that led TO this product (unchanged)
}

const [steps, setSteps]   = useState<ThreadStep[]>(initialPath ?? [{ product: startProduct }]);
const [loading, setLoading] = useState(false);
const [exhausted, setExhausted] = useState(false);

// NEW — for branching: the alternative bridges available from the current last node.
// Fetched lazily; cached so opening the branch tray doesn't re-hit the API.
const [optionsByNodeId, setOptionsByNodeId] = useState<Record<number, BridgeResult[]>>({});
const [openTrayNodeId, setOpenTrayNodeId]   = useState<number | null>(null);

const visitedIds = useMemo(() => new Set(steps.map(s => s.product.id)), [steps]);
```

Notes:
- `optionsByNodeId` caches the full `bridges` array per node so the same node's branch tray is instant on
  reopen and `pullNext` can reuse it instead of re-fetching.
- `openTrayNodeId` is pure UI (which node's "other paths" drawer is expanded).
- **No fork state.** Replace-the-tail means we never hold two threads at once. (See Decision 1.)

---

## 3. The three problem areas — diff shape

### 3.1 Motion & the "pulling" feel

**Where:** `ThreadPull.tsx` (`Edge` component + the step wrapper), `globals.css` (keyframes), one new tiny
helper for the reduced-motion check.

**The connector draws itself.** The current `Edge` uses a static left border (`border-l border-grey-200`).
Replace the *visual line* with an inline SVG positioned in the same 110px gutter, a single vertical
`<path>` (or `<line>`) with `stroke-dasharray` = its own length and an animated `stroke-dashoffset`
from full-length → 0. That's the literal "thread being drawn" effect, and it's GPU-cheap.

Shape:

```tsx
// inside Edge, replacing the border-l visual (metadata layout unchanged)
<svg className="thread-line" aria-hidden width="2" height="100%" preserveAspectRatio="none">
  <line x1="1" y1="0" x2="1" y2="100%"
        className="thread-line-path"   // stroke + dash animation in CSS
        stroke="var(--thread-stroke, #E0E0E0)" strokeWidth="2" />
</svg>
```

```css
/* globals.css — @layer utilities or a bare keyframes block */
@keyframes thread-draw   { from { stroke-dashoffset: var(--len); } to { stroke-dashoffset: 0; } }
@keyframes thread-rise   { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

.thread-line-path { stroke-dasharray: var(--len); animation: thread-draw 520ms ease-out both; }
.thread-rise      { animation: thread-rise 420ms ease-out both; }
.thread-rise-late { animation: thread-rise 420ms ease-out 180ms both; }   /* staggered metadata */

@media (prefers-reduced-motion: reduce) {
  .thread-line-path { animation: none; stroke-dashoffset: 0; }
  .thread-rise, .thread-rise-late { animation: thread-fade 200ms ease-out both; }
}
@keyframes thread-fade { from { opacity: 0; } to { opacity: 1; } }
```

Because `stroke-dasharray`/`offset` want a concrete length, set `--len` from the rendered height with a
tiny `useEffect`+`ref` (measure `path.getTotalLength()` or the SVG client height) OR — simpler and good
enough at this scale — use a fixed generous `--len` (e.g. 400) larger than any edge height; the visual is
identical because the dash just needs to cover the line. I lean **fixed `--len`** to avoid a measure pass.
We can decide together.

**New node + edge animate in.** Wrap each freshly-appended step's content in `.thread-rise` (node) and
`.thread-rise-late` (edge metadata), so the line draws, then the "why" reveals just behind it. Only the
*newest* step animates — apply the class conditionally on `i === steps.length - 1` so re-renders don't
re-animate the whole list. (Stable `key={step.product.id}` already prevents remount thrash.)

**Smooth scroll-into-view.** After append, `useEffect` on `steps.length` calls
`lastStepRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "center" })`.
A `ref` on the last step wrapper.

**Tactile affordance.** Keep the button as the deliberate control (Decision 2). Restyle copy from
"Pull next" to a thread metaphor — e.g. **"Pull the thread →"** with the arrow translating on hover (the
hover-translate already exists at line 119; keep it). Optional: a faint vertical "loose thread" stub under
the last node that the button sits beside, so the button reads as *grabbing* the thread end.

**Reduced motion:** all of the above collapse to instant line + 200ms fade, no translate, `scrollIntoView`
behavior `"auto"`. One helper:

```ts
// lib/useReducedMotion.ts  (tiny, client)
export function usePrefersReducedMotion() { /* matchMedia('(prefers-reduced-motion: reduce)'), subscribe */ }
```

### 3.2 Branching at nodes

**Model: replace-the-tail (one visible thread).** See Decision 1 for the why. UX:

- On the **current/last node**, a quiet affordance: `"3 other paths from here →"` (mono, grey-400),
  rendered only when that node has ≥1 unvisited alternative beyond the auto-pick.
- Clicking it opens a **branch tray** (`openTrayNodeId`) listing the runners-up. Each row reuses the
  *same* "why" vocabulary as the `Edge`: a `ConnectionBadge` (or lineage line), up to ~3 `AttributePill`s
  from `shared_entities`, and the `bridge_score` as a faint mono number. This is the brief's "the entities
  tell you why, applied to the menu."
- Picking a row: **truncate `steps` to that node, then append the chosen step.** Because `visitedIds` is
  derived (§1), the truncate automatically frees the garments that were below — they become revisitable on
  the new branch, and the cycle guard still blocks anything *currently* on the path.

```ts
function chooseBranch(fromNodeIndex: number, bridge: BridgeResult) {
  const fromId = steps[fromNodeIndex].product.id;
  const other  = bridge.source.id === fromId ? bridge.target : bridge.source;
  setSteps(prev => [
    ...prev.slice(0, fromNodeIndex + 1),         // keep path up to and incl. the branch node
    { product: other, bridge },                  // the chosen branch
  ]);
  setOpenTrayNodeId(null);
}
```

- The auto-`pullNext` and the branch tray share data: `pullNext` should `setOptionsByNodeId` with the full
  `bridges` array it already fetched, so opening the tray on the node it just left is free. The tray's
  "options" = `optionsByNodeId[nodeId]` filtered to unvisited `other` endpoints, minus the one already
  taken (so we show genuine *alternatives*).
- **Ideal (not required for v2):** expose the tray on *any* node, not just the last. The truncate logic
  above already supports it (`fromNodeIndex` is general). I'd ship last-node-only first, then widen if it
  feels right — flagged, not built.

### 3.3 Wayfinding & exit

**Position indicator.** A slim sticky rail, not a heavy minimap. Two options, both cheap:
- (a) A right-side vertical dot rail: one dot per step, current step filled, click a dot to scroll to it.
- (b) A sticky top-corner `"Step 4 / 4 · 3 connections"` mono marker.
I lean **(b) + a thin progress hairline** for v2 (less layout risk on mobile at 375px), with the dot rail
noted as a desktop enhancement. Soren's wayfinding direction decides the final look; the data (step index,
count) is trivially available from `steps`.

**Shareable thread via URL (no backend).** A thread *is* a list of product IDs. Encode the path as a query
param on the existing `/thread/[id]` route and replay client-side. The route's dynamic segment stays the
**origin** id (so the page title / "back to product" still work); the *rest* of the path rides in the query:

```
/thread/123?path=123.456.789.1011
```

- **Encoding:** dot-joined (or `-`-joined) product IDs, origin first. Pure, no lib:
  `encodePath(ids) => ids.join('.')` / `decodePath(str) => str.split('.').map(Number).filter(Boolean)`.
- **Replay:** the **server** page reads `searchParams.path`, and — *without any new endpoint* — we can
  replay one of two ways:
  1. **Client replay (recommended):** pass the decoded id list to `ThreadPull` as `initialPathIds`. On
     mount, the component walks the list, calling `getBridgeBetween(a, b)` (already in `api.ts:137,
     `/bridges/between/{a}/{b}`) for each consecutive pair to recover the `bridge` (the "why") that
     connected them, building `steps`. This faithfully reproduces the edges, not just the nodes. It costs
     N-1 small fetches on load; fine for a shared link (and we can show the thread drawing in as they
     resolve — the replay literally re-unspools, which is a lovely demo moment).
  2. **Nodes-only replay (fallback):** if `getBridgeBetween` is ever unavailable for a pair, render the
     node without an edge rather than failing. Graceful, no dead link.
- **"Copy this thread" affordance:** a button that builds the URL from current `steps` ids and writes it to
  clipboard. Lives near the exhaustion/footer area.
- **Confirmed:** no backend change. `getBridgeBetween` already exists; if for some reason we'd rather not
  do N-1 calls, the nodes-only path needs only `getProduct` per id — also already exists. Either way, zero
  new endpoints. (I recommend the `getBridgeBetween` replay; flagging the choice in DECISIONS.)

**Start over / new thread.** Two controls in the footer: "Start over" (reset `steps` to
`[{product: startProduct}]`, clear trays/options, drop the `?path` query) and "Pull a different thread"
(link back to `/product/[id]` or a random origin — link only, no logic).

**Graceful exhaustion.** Replace the current dead-end copy with an ending that offers the obvious next
move: "The thread runs out here — N garments, N−1 connections." + buttons: *Branch back* (open the last
node's tray if it has unvisited alternatives), *Start over*, *Back to product*. Same components, warmer
framing.

### 3.4 `prefers-reduced-motion` (cross-cutting)

One `usePrefersReducedMotion()` hook gates: animation classes (CSS already no-ops via media query, the
hook is for the JS-driven bits), `scrollIntoView` behavior, and the optional replay "re-unspool". The CSS
media query is the real guarantee; the hook keeps JS-scheduled motion honest.

---

## 4. File-by-file diff shape

| File | Change | Risk |
|---|---|---|
| `vv-web/src/components/explore/ThreadPull.tsx` | Main evolution: `useMemo` visited fix; add `optionsByNodeId`/`openTrayNodeId` state; raise `limit`; add `chooseBranch`, branch tray UI, scroll-into-view effect, animation classes on newest step, replay-from-`initialPathIds` effect, share/start-over/exhaustion footer. **`Node` and `Edge` render bodies reused ~verbatim** (gradient fallback, lineage line, pills, distance, narrative all preserved). | Medium — the file we're here to evolve. Review the state diff first. |
| `vv-web/src/app/thread/[id]/page.tsx` | Read `searchParams.path`, decode to id list, pass as `initialPathIds` to `<ThreadPull>`. ~6 lines. | Low |
| `vv-web/src/app/globals.css` | Add keyframes (`thread-draw`, `thread-rise`, `thread-fade`) + reduced-motion overrides. Additive, no existing rule touched. | Low — safe scaffolding |
| `vv-web/src/lib/threadPath.ts` *(new)* | Pure `encodePath` / `decodePath`. ~8 lines, unit-testable. | Low — safe scaffolding |
| `vv-web/src/lib/useReducedMotion.ts` *(new)* | `usePrefersReducedMotion` hook. ~15 lines. | Low — safe scaffolding |
| `vv-web/src/components/explore/BranchTray.tsx` *(new, optional split)* | The runners-up list. Could stay inline in `ThreadPull.tsx`; splitting it keeps the main file readable. | Low |

No changes to: `api.ts` (reuse `getProductBridges`, `getBridgeBetween`, `getProduct`), `types/index.ts`,
`theme.ts`, any bridge component, anything under `api/` or deploy.

**Suggested landing order (so Jen can hand-implement in safe chunks):**
1. CSS keyframes + `useReducedMotion` + `threadPath` utils (pure scaffolding, zero behavior change).
2. The `useMemo` cycle-guard fix (isolated, makes existing behavior correct-by-construction).
3. Motion on linear pull (line draw + rise + scroll) — visible win, no new model.
4. Share URL encode + replay.
5. Branch tray + `chooseBranch` (depends on #2 being in).
6. Wayfinding rail + exhaustion rewrite.

Each step is independently shippable and `tsc`/`build`-clean.

---

## 5. Verification (the repo's existing bar)

- `npx tsc --noEmit` and `npm run build` clean after each chunk.
- Manually pull a 5+ step thread: line draws, node rises, scrolls into view, no garment repeats.
- Open a branch tray, pick a non-#1 option: tail replaces, cycle guard still blocks current-path garments.
- Copy share URL, open fresh tab: same path replays (edges recovered via `getBridgeBetween`).
- Resize to 375px: thread + rail + tray stay legible.
- OS reduced-motion on: instant line, fade-only, `auto` scroll — re-pull confirms.

---

## 6. Open questions for Jen (need answers before chunk 3+)

1. **Line length:** fixed generous `--len` (simpler) vs measured `getTotalLength()` (exact)? I lean fixed.
2. **Wayfinding shape:** sticky "Step N / N" marker (my v2 pick) vs dot rail (richer, more mobile risk)?
   Soren's direction may settle this.
3. **Replay fidelity:** recover edges via `getBridgeBetween` (true re-unspool, N-1 fetches) vs nodes-only
   (cheaper, loses the "why" on shared links)? I lean edge-recovery — the "why" *is* the product.
4. **Branch reach:** last-node-only for v2 (my pick) vs any-node tray (the truncate logic already supports
   it)?
