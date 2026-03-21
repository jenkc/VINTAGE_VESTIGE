"""
Vibe Pipeline Audit — comprehensive analysis of vibe assignments.

Sections:
  1. Coverage       — how many products have vibes at all
  2. Term frequency — per-term counts and flags (BROAD / RARE / off-vocab)
  3. Platform       — vibe distribution by platform, skew detection
  4. Confidence     — vibe_scores stats per term
  5. Co-occurrence  — which terms always appear together (redundancy check)
  6. Samples        — random products per term for manual inspection
  7. Freeform map   — legacy `vibe` field vs controlled terms
  8. Bridge effect  — which vibes actually produce bridges

Usage:
  venv/bin/python tools/analysis/audit_vibes.py
  venv/bin/python tools/analysis/audit_vibes.py --section=2
  venv/bin/python tools/analysis/audit_vibes.py --sample=10
"""

import sys, os, json, statistics
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from storage.database import SessionLocal, Product, StyleBridge
from sqlalchemy import text, func

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTROLLED_TERMS = [
    # Axis 1 — Volume and Silhouette
    "Exaggerated Volume", "Column Minimalism", "Empire Suspension",
    "Constructed Armor", "Draped Fluidity", "Layered Accumulation",
    # Axis 2 — Ornament and Surface
    "Maximalist Ornament", "Austere Restraint", "Handcraft Visibility",
    "Material Luxury", "Pattern as Language", "Transparency and Revelation",
    # Axis 3 — Body Relationship
    "Body Liberation", "Body Transformation", "Body Concealment", "Body Display",
    # Axis 4 — Cultural Register
    "Pastoral Naturalism", "Ceremonial Formalism", "Dark Romanticism",
    "Transgressive Subversion", "Nostalgic Revival", "Elite Distinction",
]

AXES = {
    "Exaggerated Volume": "volume", "Column Minimalism": "volume",
    "Empire Suspension": "volume", "Constructed Armor": "volume",
    "Draped Fluidity": "volume", "Layered Accumulation": "volume",
    "Maximalist Ornament": "ornament", "Austere Restraint": "ornament",
    "Handcraft Visibility": "ornament", "Material Luxury": "ornament",
    "Pattern as Language": "ornament", "Transparency and Revelation": "ornament",
    "Body Liberation": "body", "Body Transformation": "body",
    "Body Concealment": "body", "Body Display": "body",
    "Pastoral Naturalism": "register", "Ceremonial Formalism": "register",
    "Dark Romanticism": "register", "Transgressive Subversion": "register",
    "Nostalgic Revival": "register", "Elite Distinction": "register",
}


# ===========================================================================
# SECTION 1: Coverage
# ===========================================================================

def report_coverage(db):
    print("=" * 60)
    print("SECTION 1: COVERAGE")
    print("=" * 60)

    total = db.query(func.count(Product.id)).scalar()
    enriched = db.query(func.count(Product.id)).filter(Product.enriched_at.isnot(None)).scalar()
    has_core = db.execute(text(
        "SELECT count(*) FROM products WHERE core_vibes IS NOT NULL AND array_length(core_vibes, 1) > 0"
    )).scalar()
    has_bridge = db.execute(text(
        "SELECT count(*) FROM products WHERE bridge_vibes IS NOT NULL AND array_length(bridge_vibes, 1) > 0"
    )).scalar()
    has_scores = db.query(func.count(Product.id)).filter(Product.vibe_scores.isnot(None)).scalar()
    has_freeform = db.query(func.count(Product.id)).filter(Product.vibe.isnot(None)).scalar()

    def pct(n):
        return f"{n:>5}  ({100*n/total:.1f}%)" if total else f"{n:>5}"

    print(f"  Total products:       {total}")
    print(f"  Enriched:             {pct(enriched)}")
    print(f"  Has core_vibes:       {pct(has_core)}")
    print(f"  Has bridge_vibes:     {pct(has_bridge)}")
    print(f"  Has vibe_scores:      {pct(has_scores)}")
    print(f"  Has freeform vibe:    {pct(has_freeform)}")

    gap = enriched - has_core
    if gap > 0:
        print(f"\n  ⚠ GAP: {gap} products enriched but missing core_vibes")
    print()


# ===========================================================================
# SECTION 2: Term Frequency
# ===========================================================================

def report_term_frequency(db):
    print("=" * 60)
    print("SECTION 2: TERM FREQUENCY")
    print("=" * 60)

    total = db.execute(text(
        "SELECT count(*) FROM products WHERE core_vibes IS NOT NULL AND array_length(core_vibes, 1) > 0"
    )).scalar() or 1

    # core_vibes
    rows = db.execute(text(
        "SELECT val, count(*) as cnt FROM products, unnest(core_vibes) AS val "
        "WHERE core_vibes IS NOT NULL GROUP BY val ORDER BY cnt DESC"
    )).fetchall()

    core_counts = {r[0]: r[1] for r in rows}

    # bridge_vibes
    bridge_rows = db.execute(text(
        "SELECT val, count(*) as cnt FROM products, unnest(bridge_vibes) AS val "
        "WHERE bridge_vibes IS NOT NULL GROUP BY val ORDER BY cnt DESC"
    )).fetchall()
    bridge_counts = {r[0]: r[1] for r in bridge_rows}

    print(f"\n  {'TERM':<35} {'CORE':>6} {'%':>6}  {'BRIDGE':>7} {'%':>6}  FLAGS")
    print(f"  {'-'*35} {'-'*6} {'-'*6}  {'-'*7} {'-'*6}  {'-'*15}")

    controlled_set = set(CONTROLLED_TERMS)
    all_terms = set(core_counts.keys()) | set(bridge_counts.keys()) | controlled_set
    off_vocab = []

    for term in CONTROLLED_TERMS:
        cc = core_counts.get(term, 0)
        bc = bridge_counts.get(term, 0)
        cpct = 100 * cc / total
        bpct = 100 * bc / total
        flags = []
        if cpct > 30:
            flags.append("BROAD")
        if cc > 0 and cpct < 1:
            flags.append("RARE")
        if cc == 0:
            flags.append("UNUSED")
        axis = AXES.get(term, "?")
        print(f"  {term:<35} {cc:>6} {cpct:>5.1f}%  {bc:>7} {bpct:>5.1f}%  {' '.join(flags)}  [{axis}]")

    # Off-vocabulary terms
    for term in sorted(all_terms - controlled_set):
        cc = core_counts.get(term, 0)
        bc = bridge_counts.get(term, 0)
        off_vocab.append((term, cc, bc))

    if off_vocab:
        print(f"\n  OFF-VOCABULARY TERMS (Claude hallucinated):")
        for term, cc, bc in off_vocab:
            print(f"    {term:<40} core={cc}  bridge={bc}")

    # Terms that never appear
    never = [t for t in CONTROLLED_TERMS if core_counts.get(t, 0) == 0]
    if never:
        print(f"\n  NEVER ASSIGNED: {', '.join(never)}")
    print()


# ===========================================================================
# SECTION 3: Platform Breakdown
# ===========================================================================

def report_platform_breakdown(db):
    print("=" * 60)
    print("SECTION 3: PLATFORM BREAKDOWN")
    print("=" * 60)

    rows = db.execute(text(
        "SELECT p.platform, val, count(*) as cnt "
        "FROM products p, unnest(p.core_vibes) AS val "
        "WHERE p.core_vibes IS NOT NULL "
        "GROUP BY p.platform, val "
        "ORDER BY p.platform, cnt DESC"
    )).fetchall()

    # Organize by platform
    platform_data = defaultdict(list)
    term_platform_counts = defaultdict(lambda: defaultdict(int))
    for platform, term, cnt in rows:
        platform_data[platform].append((term, cnt))
        term_platform_counts[term][platform] = cnt

    for platform in sorted(platform_data.keys()):
        items = platform_data[platform]
        total = sum(c for _, c in items)
        print(f"\n  {platform} ({total} vibe assignments, top 10):")
        for term, cnt in items[:10]:
            print(f"    {term:<35} {cnt:>5}  ({100*cnt/total:.1f}%)")

    # Skew analysis
    print(f"\n  SKEW ANALYSIS (terms where one platform > 70% of assignments):")
    skewed = False
    for term in CONTROLLED_TERMS:
        pc = term_platform_counts[term]
        total = sum(pc.values())
        if total == 0:
            continue
        for platform, cnt in pc.items():
            if cnt / total > 0.70:
                print(f"    {term:<35} {platform} has {cnt}/{total} ({100*cnt/total:.0f}%)")
                skewed = True
                break
    if not skewed:
        print("    (none)")
    print()


# ===========================================================================
# SECTION 4: Confidence Distribution
# ===========================================================================

def report_confidence_distribution(db):
    print("=" * 60)
    print("SECTION 4: CONFIDENCE DISTRIBUTION")
    print("=" * 60)

    scores_rows = db.query(Product.vibe_scores).filter(Product.vibe_scores.isnot(None)).all()

    term_scores = defaultdict(list)
    all_scores = []

    for (scores_json,) in scores_rows:
        if not scores_json:
            continue
        scores = scores_json if isinstance(scores_json, dict) else json.loads(scores_json)
        for term, val in scores.items():
            if isinstance(val, (int, float)):
                term_scores[term].append(val)
                all_scores.append(val)

    if not all_scores:
        print("  No vibe_scores data found.\n")
        return

    # Overall histogram
    buckets = [0] * 5
    for s in all_scores:
        idx = min(int(s * 5), 4)
        buckets[idx] += 1
    total = len(all_scores)

    print(f"\n  Overall confidence histogram ({total} scores):")
    labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    for label, count in zip(labels, buckets):
        bar = "#" * int(40 * count / max(buckets))
        print(f"    {label}  {count:>5} ({100*count/total:>5.1f}%)  {bar}")

    # Per-term stats
    print(f"\n  {'TERM':<35} {'N':>5} {'MEAN':>6} {'MED':>5} {'STD':>5} {'MIN':>5} {'MAX':>5}  FLAG")
    print(f"  {'-'*35} {'-'*5} {'-'*6} {'-'*5} {'-'*5} {'-'*5} {'-'*5}  {'-'*10}")

    high_confidence_count = 0
    for term in CONTROLLED_TERMS:
        vals = term_scores.get(term, [])
        if not vals:
            print(f"  {term:<35}     0")
            continue
        m = statistics.mean(vals)
        med = statistics.median(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0
        mn, mx = min(vals), max(vals)
        flag = ""
        if m > 0.85:
            flag = "RUBBER-STAMP"
            high_confidence_count += 1
        elif sd < 0.05 and len(vals) > 5:
            flag = "LOW-VARIANCE"
        print(f"  {term:<35} {len(vals):>5} {m:>6.3f} {med:>5.2f} {sd:>5.3f} {mn:>5.2f} {mx:>5.2f}  {flag}")

    if high_confidence_count > len(CONTROLLED_TERMS) * 0.6:
        print(f"\n  ⚠ {high_confidence_count}/{len(CONTROLLED_TERMS)} terms have mean confidence > 0.85 — Claude may be rubber-stamping")
    print()


# ===========================================================================
# SECTION 5: Co-occurrence
# ===========================================================================

def report_cooccurrence(db):
    print("=" * 60)
    print("SECTION 5: CO-OCCURRENCE")
    print("=" * 60)

    rows = db.execute(text(
        "SELECT core_vibes FROM products "
        "WHERE core_vibes IS NOT NULL AND array_length(core_vibes, 1) >= 2"
    )).fetchall()

    pair_counts = Counter()
    term_products = defaultdict(set)

    for i, (vibes,) in enumerate(rows):
        for v in vibes:
            term_products[v].add(i)
        for pair in combinations(sorted(vibes), 2):
            pair_counts[pair] += 1

    if not pair_counts:
        print("  No products with 2+ core_vibes found.\n")
        return

    # Top 20 pairs
    print(f"\n  Top 20 co-occurring pairs:")
    print(f"  {'PAIR':<65} {'COUNT':>6} {'JACCARD':>8}  FLAG")
    print(f"  {'-'*65} {'-'*6} {'-'*8}  {'-'*15}")

    for (a, b), cnt in pair_counts.most_common(20):
        union = len(term_products[a] | term_products[b])
        jaccard = cnt / union if union else 0
        axis_a = AXES.get(a, "?")
        axis_b = AXES.get(b, "?")
        flags = []
        if jaccard > 0.3:
            flags.append("REDUNDANT?")
        if axis_a == axis_b:
            flags.append(f"SAME-AXIS({axis_a})")
        print(f"  {a + ' + ' + b:<65} {cnt:>6} {jaccard:>8.3f}  {' '.join(flags)}")

    # Same-axis co-occurrence (suspicious)
    print(f"\n  Same-axis co-occurrence (potentially problematic):")
    same_axis = [(pair, cnt) for pair, cnt in pair_counts.items()
                 if AXES.get(pair[0]) == AXES.get(pair[1]) and AXES.get(pair[0]) is not None]
    same_axis.sort(key=lambda x: -x[1])
    if same_axis:
        for (a, b), cnt in same_axis[:10]:
            print(f"    {a + ' + ' + b:<60} {cnt:>6}  [{AXES.get(a)}]")
    else:
        print("    (none)")
    print()


# ===========================================================================
# SECTION 6: Samples
# ===========================================================================

def report_samples(db, n=5):
    print("=" * 60)
    print(f"SECTION 6: SAMPLES ({n} per term)")
    print("=" * 60)

    for term in CONTROLLED_TERMS:
        rows = db.execute(text(
            "SELECT id, title, platform, era, core_vibes, bridge_vibes, vibe, "
            "LEFT(ai_description, 150) as desc_preview "
            "FROM products WHERE :term = ANY(core_vibes) "
            "ORDER BY random() LIMIT :n"
        ), {"term": term, "n": n}).fetchall()

        axis = AXES.get(term, "?")
        print(f"\n  {term} [{axis}] — {len(rows)} sample(s):")
        if not rows:
            print(f"    (no products assigned this term)")
            continue
        for r in rows:
            pid, title, platform, era, cv, bv, vibe, desc = r
            title_short = (title or "untitled")[:60]
            print(f"    id={pid}  {platform:<14} {era or '?':<20} \"{title_short}\"")
            print(f"      core={cv}  bridge={bv}  freeform=\"{vibe}\"")
            if desc:
                print(f"      desc: {desc}...")
    print()


# ===========================================================================
# SECTION 7: Freeform Mapping
# ===========================================================================

def report_freeform_mapping(db):
    print("=" * 60)
    print("SECTION 7: FREEFORM VIBE vs CONTROLLED TERMS")
    print("=" * 60)

    # Top freeform vibes
    freeform_rows = db.execute(text(
        "SELECT vibe, count(*) as cnt FROM products "
        "WHERE vibe IS NOT NULL GROUP BY vibe ORDER BY cnt DESC LIMIT 30"
    )).fetchall()

    total_with_vibe = sum(r[1] for r in freeform_rows)
    print(f"\n  Top 30 freeform vibes ({total_with_vibe} products):")
    for vibe_val, cnt in freeform_rows:
        print(f"    {vibe_val:<30} {cnt:>5} ({100*cnt/total_with_vibe:.1f}%)")

    # Cross-tab: for top 15 freeform vibes, what core_vibes co-occur
    print(f"\n  Cross-tab: freeform vibe → most common core_vibes:")
    for vibe_val, _ in freeform_rows[:15]:
        cross = db.execute(text(
            "SELECT val, count(*) as cnt FROM products, unnest(core_vibes) AS val "
            "WHERE vibe = :v AND core_vibes IS NOT NULL GROUP BY val ORDER BY cnt DESC LIMIT 3"
        ), {"v": vibe_val}).fetchall()
        if cross:
            terms = ", ".join(f"{r[0]}({r[1]})" for r in cross)
            print(f"    {vibe_val:<25} → {terms}")
    print()


# ===========================================================================
# SECTION 8: Bridge Effectiveness
# ===========================================================================

def report_bridge_effectiveness(db):
    print("=" * 60)
    print("SECTION 8: BRIDGE EFFECTIVENESS")
    print("=" * 60)

    total_bridges = db.query(func.count(StyleBridge.id)).scalar()
    if not total_bridges:
        print("  No bridges in database yet.\n")
        return

    print(f"\n  Total bridges: {total_bridges}")

    # Per vibe: how many bridges involve products with that vibe
    # Use source_id and target_id joins
    rows = db.execute(text("""
        SELECT val, count(DISTINCT b.id) as bridge_count
        FROM style_bridges b
        JOIN products p ON p.id = b.source_id OR p.id = b.target_id
        , unnest(p.core_vibes) AS val
        WHERE p.core_vibes IS NOT NULL
        GROUP BY val
        ORDER BY bridge_count DESC
    """)).fetchall()

    vibe_bridge_counts = {r[0]: r[1] for r in rows}

    # Contrast bridges per pair
    contrast_rows = db.execute(text(
        "SELECT contrast_pair, count(*) FROM style_bridges "
        "WHERE contrast_pair IS NOT NULL "
        "GROUP BY contrast_pair ORDER BY count(*) DESC"
    )).fetchall()

    contrast_by_pair = {r[0]: r[1] for r in contrast_rows}
    total_contrast = sum(r[1] for r in contrast_rows)

    # Build per-term contrast count (term appears in any contrast_pair string)
    term_contrast = defaultdict(int)
    for pair_str, cnt in contrast_by_pair.items():
        for term in CONTROLLED_TERMS:
            if term in pair_str:
                term_contrast[term] += cnt

    print(f"  Contrast bridges: {total_contrast}")

    print(f"\n  {'TERM':<35} {'BRIDGES':>8} {'CONTRAST':>9}  FLAG")
    print(f"  {'-'*35} {'-'*8} {'-'*9}  {'-'*15}")

    for term in CONTROLLED_TERMS:
        bc = vibe_bridge_counts.get(term, 0)
        cc = term_contrast.get(term, 0)
        flag = ""
        if bc == 0:
            flag = "DEAD WEIGHT"
        elif cc == 0 and bc > 0:
            flag = "no contrast"
        print(f"  {term:<35} {bc:>8} {cc:>9}  {flag}")

    if contrast_rows:
        print(f"\n  Contrast pair distribution:")
        for pair_str, cnt in contrast_rows:
            print(f"    {pair_str:<55} {cnt:>5}")
    print()


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Audit vibe pipeline')
    parser.add_argument('--section', type=int, default=None, help='Run only this section (1-8)')
    parser.add_argument('--sample', type=int, default=5, help='Samples per term in section 6')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        sections = {
            1: lambda: report_coverage(db),
            2: lambda: report_term_frequency(db),
            3: lambda: report_platform_breakdown(db),
            4: lambda: report_confidence_distribution(db),
            5: lambda: report_cooccurrence(db),
            6: lambda: report_samples(db, n=args.sample),
            7: lambda: report_freeform_mapping(db),
            8: lambda: report_bridge_effectiveness(db),
        }

        if args.section:
            if args.section in sections:
                sections[args.section]()
            else:
                print(f"Invalid section {args.section}. Valid: 1-8")
        else:
            for s in sorted(sections.keys()):
                sections[s]()
    finally:
        db.close()


if __name__ == '__main__':
    main()
