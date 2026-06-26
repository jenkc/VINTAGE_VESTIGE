# Thread Pull v2 — Design Direction

**Author:** Soren (product design)
**Date:** 2026-06-25
**Status:** Design exploration (Deliverable #1). Iris owns the React/CSS build (Deliverable #2).
**Feel it:** `_docs/mockups/thread_pull_motion.html` — interactive. Pull the thread, open "Other paths," watch the left rail and bottom bar. Toggle "simulate reduced-motion" in the prototype's control strip to see the fallback.
**Grounded in:** the real v1 (`vv-web/src/components/explore/ThreadPull.tsx`), the tokens (`vv-web/src/styles/theme.ts`), the static references (`_docs/mockups/thread_pull_*.html`), and the v2 handoff (`_docs/FIGMA_DESIGN_HANDOFF_V2.md`).

---

## The problem, in one line

v1 is *correct but flat*. It reads as a list that grows. The signature claim — "pull a thread and watch the collection unspool, the entities telling you why the graph went where it went" — needs three things the list doesn't have: **motion that feels like pulling**, **a choice at each knot**, and **a sense of where you are and how to leave with the thread in hand**. Nothing below touches the traversal correctness (highest-score-first, visited-cycle guard, lineage refs, narrative) — it dresses the same skeleton.

Whose call is what: I specify *what the experience does and why*. Where the brief asks for an engineering model decision (replace-tail vs fork; scroll-trigger vs button), I give a recommendation and a reason, and mark it **Iris's call to finalize**.

---

## Direction 1 — Motion & the "pulling" feel  *(highest priority)*

**Intent:** when you pull, a thread is *drawn* down from the garment you're standing on, and the next garment arrives at the end of it. The line moves first; the reason for the move (entities, narrative) reveals just after the line gets there. It should feel like fabric being pulled taut — deliberate, weighted, quiet. Museum, not app-store.

### What animates, in order
1. **The connector draws itself.** The vertical line between the previous node and the new edge animates via `stroke-dashoffset` on an SVG `<path>` (dash-array = full length, offset animates to 0). This is the literal "thread" — it's the one motion that has to read as *drawing*, not *appearing*. (Alt for Iris if SVG is awkward inside the existing left-border layout: an animated `height` on a 1.5px element. The prototype uses SVG because it gives a clean `pathLength` to animate and survives reflow; pick whichever is cheaper in React — the *feel* is what matters, not the technique.)
2. **A bead rides the line down** as it draws, then settles into the existing grey dot at the bottom of the edge. Accent terracotta (`--accent #C4553A`) while moving, settling to `--grey-200`. This is the "fingertip on the thread" — small, one element, easy to cut. It's the single most "pulling" cue; keep it if you keep nothing else from the flourishes.
3. **The new node + edge fade and rise in** (`opacity 0→1`, `translateY(18px→0)`). Standard arrival.
4. **The edge metadata reveals just after the line lands** — staggered by ~55% of the draw duration so the line reaches the node *before* its "why" appears. This ordering is the whole point: the graph moves, *then* tells you why. (Matches the handoff §7: "shared entity tags fade in first, then the garment image, then the narrative" — I've kept that intent; the stagger is line → node → meta.)

### Timing (named, so Iris can drop them into Tailwind/transition config)
| Token | Value | Why |
|---|---|---|
| `--draw-ms` | **680ms** | the line drawing. Long enough to read as *drawn*, short enough not to make the user wait on every pull. |
| `--reveal-ms` | **460ms** | node + edge fade/rise. |
| meta stagger | **draw × 0.55** (~375ms) | metadata lands just after the line. |
| easing | `cubic-bezier(0.22, 0.61, 0.36, 1)` | ease-out, **no overshoot**. The handoff bans bounce/spring; this honors it. |

### The pull affordance itself
Not "Load more." A tactile, thread-metaphor control: a short stroke of "slack thread" hanging from the last node, then **`↦ pull →`** in mono. On hover the little thread-stroke *lengthens* and turns accent, and the arrow slides right — the affordance physically suggests the pull before you make it. On click, a brief "Following the thread…" beat (480ms, the existing copy) precedes the draw, so the pull feels like a deliberate act with a moment of tension, not an instant append.

### Scroll behavior — **recommendation: button-primary, smooth-scroll-into-view, NO scroll-trigger autoload**  *(Iris's call to finalize)*
The brief floats lazy-load-on-scroll as an accelerator. **I recommend against auto-pulling on scroll.** Thread Pull's entire premise is agency — "*you* decide whether to keep pulling." Auto-loading on scroll quietly removes that decision and drifts toward the cinematic auto-advance the brief explicitly rules out. Keep the button as the deliberate control; when a step is pulled, **smoothly bring it into view** (`scrollIntoView`, `block:'center'`) so the new garment isn't below the fold but the user never loses their place. That's the right use of scroll here: as *follow-through on a pull*, not as a trigger. If you later want an accelerator, a keyboard affordance (space / ↓ = pull) is more honest than scroll-load — it's still a deliberate act.

### Accessibility — built in, not retrofitted
- `prefers-reduced-motion: reduce` → **instant / fade-only**: no line-draw, no bead ride, no rise; the step just appears (a ~1ms fade so it's not jarring). The prototype implements this and exposes a toggle so you can see both. Iris: mirror this with a `useReducedMotion()` check (or the CSS media query) — the fallback must be a real path, not an afterthought.
- The pull control is a real `<button>` with a text label; the thread-stroke is decorative.
- Don't animate anything load-bearing into existence *only* via motion — the content is present in the DOM the instant it's pulled; motion is decoration over already-correct state.

---

## Direction 2 — Branching at nodes

**Intent:** the graph's pick is the strong default, not the only road. At the knot you're standing on, you can see the runners-up — and crucially, *why each one is offered* — and take one. Same principle as the whole product: the entities tell you why. This just applies it to the menu of options instead of the single pick.

### The pattern
Under the last node, beneath the pull control:
> **`› N other paths from here`** — a quiet mono toggle (grey, accent on hover). Collapsed by default so the default experience stays clean and the thread reads as one line.

Expanded, each alternative is **one row**, scannable:

```
[thumb]  Garment title                                    0.74
         ● connecting entities (the "why"), one line
```

- **Thumbnail** (56×72, object-contain on off-white) — you choose with your eyes first, it's a fashion tool.
- **Title** — turns accent on hover.
- **The "why"** in mono: a colored swatch keyed to `connection_mode` (`shared_entity` grey `#6B6B6B`, `lineage` terracotta `#C4553A`, `visual_echo` brown `#8B5E3C` — straight from `CONNECTION_MODE_COLORS`) + the connecting entities / reference. So at a glance you see *this one connects through Chinoiserie*, *that one is a lineage citation*. **This is the informed-choice requirement** — never a bare list of names.
- **The score** right-aligned in mono — the same `bridge_score` that ranked them. The user sees they're trading down from the auto-pick, and by how much.

These come **for free** from the data you already fetch: `getProductBridges` returns up to `limit` sorted by score; #0 (first unvisited) is the auto-pick, the rest are the alternatives. **No backend work** — the brief confirms it, and the prototype proves the shape. Iris: bump `limit` if you want a deeper menu (it's 10 today; the menu only needs the top handful of *unvisited* ones).

### Model: **replace-the-tail**, not fork  *(recommended; Iris's call to finalize)*
Picking an alternative continues the thread down *that* branch from the current node, replacing whatever tail was below. **One visible thread at a time.** Reasons:
- It keeps the mental model singular — "I'm pulling *a* thread" — which is the whole metaphor. Two live threads on screen is a different, busier product.
- It's drastically simpler to build and to share (a thread is still one linear path of ids).
- The cycle guard (`visitedIds`) stays trivially correct: taking a branch just adds the new target; nothing already on the path is re-offered (the prototype filters `unvisited` for exactly this).

**Fork is a real future idea, not v2.** If you ever want it: a fork would spawn a second column / saved alternate thread — high effort, and it muddies the "one thread" story. Park it. Note it. Don't let it sneak into this pass.

One consequence to honor: if branching replaces the tail, the steps you walked away from are *gone from view*. That's fine for v2 — the share URL of the path you keep is the artifact. (If a user wants the road not taken, they re-pull; the graph is deterministic on score.)

### Branch from *any* node vs only the last
The brief says "at minimum the current/last node; ideally any node." **For v2, last-node only** is the clean version and what the prototype does — it keeps "replace the tail" unambiguous (there's no tail below the last node to lose). Branching from an *earlier* node implies the same replace-tail rule applied mid-thread (everything below that node is discarded), which is a reasonable stretch but adds a "are you sure you want to drop 4 steps?" affordance question. I'd ship last-node branching, then add earlier-node branching only if it earns its keep. The exhaustion state (below) gives a gentle path back to earlier branch points without needing full any-node branching on day one.

---

## Direction 3 — Wayfinding & exit

**Intent:** a long thread shouldn't feel endless or trap you. You should always know roughly where you are, be able to leave *with the thread in hand* (it's the demo — a thread you can send someone IS the portfolio piece), start fresh, or hit the end and be offered the next move instead of a wall.

### Where am I — a slim sticky step-rail
A vertical rail of dots pinned to the left edge (`position: fixed`), one dot per step. Filled grey for visited, **accent + halo for the current step**, a small count at the bottom. Hovering a dot reveals a mono tooltip (`03 · Navy Blue Silk Sari`); clicking it scrolls you there. It's the spine of the thread rendered as a tiny map — present but never loud, and it scales: a 12-step thread is twelve small dots, not twelve screens of uncertainty. (On mobile this collapses — see below.)

This is deliberately *lighter* than a mini-map/graph viz. A side-rail of dots answers "how far am I / how far back is the start" without pulling focus from the garments, and it costs almost nothing to build. The handoff's anti-chrome principle applies: less UI, more garment.

### Share / save — a thread is its path of ids
The lowest-friction share: **encode the path in the URL** — `#thread=3578-4553-4556-104-2439` (or a query param) — and replay it client-side on load. **No backend.** The brief confirms the route can take a path param and replay it. A sticky bottom toolbar carries `↗ Share thread` (copies the link, flips to `✓ Link copied`), the live `N garments · N connections` stat, and `↺ Start over`.
- Iris: the encode/replay is a small client thing — on mount, if `#thread=` is present, hydrate `steps` by walking the ids and re-fetching each bridge (or just render the products and fetch the connecting bridge between consecutive ids via the existing `between` endpoint if you want the full edge metadata on replay). **Replay fidelity is your call** — minimum viable is "same garments in same order"; nicer is "same garments *and* the same edge narratives." Either satisfies the acceptance criterion. I recommend at least re-fetching the edges so a shared thread arrives with its "why" intact, since the why is the point.
- This is the single highest-portfolio-value piece: a sharable thread URL is a self-contained demo Jen can drop into an application. Treat it as a feature, not a nicety.

### Start over / new thread
`↺ Start over` in the toolbar (back to the origin garment, thread reset) and, at the end, `↺ Start a new thread`. Always one click from a fresh pull.

### Graceful exhaustion — an ending, not a dead-end
When there's no unvisited bridge from the current garment, don't just print a count. Close the loop and hand the user the next move:
> *"The thread ends here — for now. 5 garments, 4 connections, Elizabethan → New Look."*
> then: **Branch from an earlier garment** (if any earlier node still has an unvisited path) · **↗ Share this thread** · **↺ Start a new thread** · **Return to garment**

The editorial italic line (Cormorant) gives the ending a small sense of resolution — it *finishes* the story — and the actions make sure "finished" never means "stuck." The "branch from an earlier garment" action is how a user reaches back to a knot they passed without needing full any-node branching wired everywhere; it scrolls them to the earliest node that still has somewhere to go.

---

## Responsive / mobile  *(real audience — a portfolio link gets opened on phones)*

- **Step-rail** collapses on narrow screens: either a single sticky "Step N / M" marker top-corner, or the rail moves to a thin horizontal progress strip under the header. Don't keep the left-edge dots on a 375px screen — they'll crowd the garment. (Iris's layout call; the prototype is desktop-first by design — it's a feel demo.)
- **Node grid** (`180px 1fr`) stacks to single-column under ~520px — image over text, as the handoff's mobile spec already dictates for bridges.
- **Branch rows** stay one-per-line and remain tappable (the 56px thumb + title is a comfortable touch target).
- **Toolbar** stays bottom-pinned (thumb-reachable) but can shed the stat label and keep just the two icon-buttons on the smallest widths.

---

## What I'm explicitly leaving to Iris

1. **The draw technique** — SVG `stroke-dashoffset` vs animated-height border. I've specified the *feel* and the timings; pick the cheaper one in the real left-border layout.
2. **Branch model finalization** — I recommend **replace-tail, last-node-only** for v2 and have reasoned it. If the React shape makes fork or any-node branching nearly free, that's your latitude — but the default story is one thread.
3. **Scroll-trigger** — I recommend **button-only + smooth-scroll-into-view, no autoload**. If you want an accelerator, keyboard over scroll.
4. **Share replay fidelity** — minimum is "same path"; I recommend re-fetching edges so the "why" survives the share. Your call on cost.
5. **All final CSS, the component decomposition, performance, and the data layer** — yours, as always. This note is intent + named tokens + timings, not a build.

## What must NOT regress (from the brief's acceptance criteria)
Highest-score-first default traversal · visited-cycle prevention · lineage edges showing `lineage_reference` · distance line · narrative · the missing-image gradient fallback (`primary_image` can be null on ~51 V&A products) · reuse of `AttributePill` / `ConnectionBadge` / `NarrativeBlock` and the existing theme tokens · editorial/restrained aesthetic.

## Out of scope (parking lot — do not build here)
Auto-play / self-advancing mode · any new backend endpoint or bridge-schema change · Bridge-of-the-Day / Movement Trails / other browse modes · anything on the deploy path (`api/`, deploy config, `requirements.txt`, env vars) · reworking bridge cards / product detail beyond the existing entry CTA.
