"""
Generate AI narratives for style bridges (async concurrent).

Finds bridges missing a narrative, calls Claude concurrently to generate
2-3 sentence editorial explanations, and stores them on the bridge rows.

Usage:
  python tools/analysis/generate_narratives.py [--limit=N] [--concurrency=N]

  --limit=N        Total bridges to process (default: all)
  --concurrency=N  Parallel API calls (default: 5)
  --yes            Skip confirmation prompt

Safe to interrupt and resume — only processes bridges where
bridge_narrative IS NULL.

Run from project root.
"""

import sys
import os
import json
import time
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import sqlalchemy
from storage.database import SessionLocal, Product, StyleBridge
from enrichment.claude import ClaudeEnricher

# Minimum bridge_score to generate a narrative (saves API cost on weak bridges)
MIN_NARRATIVE_SCORE = 0.55
# Lineage bridges are the most interesting — lower gate to capture more
LINEAGE_MIN_SCORE = 0.45
# Visual echo bridges have lower entity scores by nature — use a lower gate
VISUAL_ECHO_MIN_SCORE = 0.45
# Max narratives per product to prevent one well-connected item dominating
MAX_NARRATIVES_PER_PRODUCT = 20


async def process_bridge(enricher, bridge_data, product_map, semaphore):
    """Process a single bridge under the semaphore."""
    async with semaphore:
        # Quality gate
        mode = bridge_data.connection_mode
        if not mode:
            return bridge_data.id, None, "no connection mode"

        score = bridge_data.bridge_score
        if mode == 'visual_echo':
            min_score = VISUAL_ECHO_MIN_SCORE
        elif mode == 'lineage':
            min_score = LINEAGE_MIN_SCORE
        else:
            min_score = MIN_NARRATIVE_SCORE
        if score is not None and score < min_score:
            return bridge_data.id, None, "below quality gate"

        src = product_map.get(bridge_data.source_id)
        tgt = product_map.get(bridge_data.target_id)
        if not src or not tgt:
            return bridge_data.id, None, "missing product"

        item_a = dict(src)
        item_b = dict(tgt)

        shared = json.loads(bridge_data.shared_entities) if bridge_data.shared_entities else {}

        for attempt in range(2):  # 1 retry on failure
            try:
                narrative = await enricher.generate_bridge_narrative_async(
                    item_a, item_b, shared,
                    connection_mode=mode,
                    crossing_type=bridge_data.crossing_type,
                    year_gap=bridge_data.year_gap,
                    directed=bridge_data.directed or False,
                )
                # Length validation
                if narrative and len(narrative) < 50:
                    return bridge_data.id, None, "too short"
                if narrative and len(narrative) > 500:
                    narrative = narrative[:500].rsplit('. ', 1)[0] + '.'
                return bridge_data.id, narrative, None
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                return bridge_data.id, None, str(e)


async def generate_narratives(limit=None, concurrency=5):
    db = SessionLocal()
    enricher = ClaudeEnricher()
    semaphore = asyncio.Semaphore(concurrency)

    total_remaining = (
        db.query(StyleBridge)
        .filter(StyleBridge.bridge_narrative == None)
        .count()
    )

    if total_remaining == 0:
        print("All bridges already have narratives.")
        db.close()
        return

    # Count bridges that will pass the quality gate
    passable = db.execute(sqlalchemy.text('''
        SELECT count(*) FROM style_bridges
        WHERE bridge_narrative IS NULL
        AND connection_mode IS NOT NULL
        AND (bridge_score >= :min_score
             OR (connection_mode = 'visual_echo' AND bridge_score >= :visual_min)
             OR (connection_mode = 'lineage' AND bridge_score >= :lineage_min))
    '''), {'min_score': MIN_NARRATIVE_SCORE, 'visual_min': VISUAL_ECHO_MIN_SCORE,
           'lineage_min': LINEAGE_MIN_SCORE}).scalar()

    target = min(limit, passable) if limit else passable

    # Cost estimate
    avg_cost_per_bridge = 0.007
    est_cost = target * avg_cost_per_bridge
    est_time = target / (concurrency * 0.8) / 60

    print(f"\n{'=' * 60}")
    print(f"NARRATIVE GENERATION")
    print(f"{'=' * 60}")
    print(f"  Bridges without narratives: {total_remaining}")
    print(f"  Passing quality gate:       {passable}")
    print(f"  Will process: {target}  (concurrency: {concurrency})")
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print(f"  Estimated time: ~{est_time:.0f} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

    # Pre-load all products as dicts
    products = db.query(Product).all()
    product_map = {}
    for p in products:
        product_map[p.id] = {
            'title': p.title,
            'display_title': p.display_title or p.title,
            'era': p.era,
            'decade': p.decade,
            'material': p.material,
            'culture': p.culture,
            'primary_image': p.primary_image,
        }

    generated = 0
    skipped = 0
    failed = 0
    start_time = time.time()
    batch_size = concurrency * 10
    product_narrative_count = {}

    while generated + skipped + failed < target:
        fetch_size = min(batch_size, target - generated - skipped - failed)
        bridges = (
            db.query(
                StyleBridge.id, StyleBridge.source_id, StyleBridge.target_id,
                StyleBridge.shared_entities,
                StyleBridge.connection_mode, StyleBridge.crossing_type,
                StyleBridge.year_gap, StyleBridge.directed,
                StyleBridge.bridge_score,
            )
            .filter(
                StyleBridge.bridge_narrative == None,
                StyleBridge.connection_mode != None,
                sqlalchemy.or_(
                    StyleBridge.bridge_score >= MIN_NARRATIVE_SCORE,
                    sqlalchemy.and_(StyleBridge.connection_mode == 'visual_echo', StyleBridge.bridge_score >= VISUAL_ECHO_MIN_SCORE),
                    sqlalchemy.and_(StyleBridge.connection_mode == 'lineage', StyleBridge.bridge_score >= LINEAGE_MIN_SCORE),
                )
            )
            .order_by(
                # Lineage first (most specific story), then visual echo, then shared entity
                sqlalchemy.case(
                    (StyleBridge.connection_mode == 'lineage', 1),
                    (StyleBridge.connection_mode == 'visual_echo', 2),
                    (StyleBridge.connection_mode == 'shared_entity', 3),
                    else_=4,
                ),
                StyleBridge.bridge_score.desc(),
            )
            .limit(fetch_size)
            .all()
        )

        if not bridges:
            break

        # Filter out bridges where either product already has enough narratives
        filtered = []
        batch_skipped = 0
        for b in bridges:
            src_count = product_narrative_count.get(b.source_id, 0)
            tgt_count = product_narrative_count.get(b.target_id, 0)
            if src_count >= MAX_NARRATIVES_PER_PRODUCT or tgt_count >= MAX_NARRATIVES_PER_PRODUCT:
                batch_skipped += 1
                continue
            filtered.append(b)

        tasks = [
            process_bridge(enricher, b, product_map, semaphore)
            for b in filtered
        ]

        results = await asyncio.gather(*tasks)

        # Write results to DB
        batch_ok = 0
        batch_err = 0
        batch_gate_skip = 0
        bridge_lookup = {b.id: b for b in filtered}
        for bridge_id, narrative, error in results:
            if narrative:
                db.query(StyleBridge).filter(StyleBridge.id == bridge_id).update(
                    {StyleBridge.bridge_narrative: narrative}
                )
                batch_ok += 1
                b = bridge_lookup.get(bridge_id)
                if b:
                    product_narrative_count[b.source_id] = product_narrative_count.get(b.source_id, 0) + 1
                    product_narrative_count[b.target_id] = product_narrative_count.get(b.target_id, 0) + 1
            elif error in ("below quality gate", "no connection mode", "missing product", "too short"):
                batch_gate_skip += 1
            else:
                batch_err += 1
                if error:
                    print(f"  ERR bridge {bridge_id}: {error}")

        db.commit()
        generated += batch_ok
        skipped += batch_skipped + batch_gate_skip
        failed += batch_err

        elapsed = time.time() - start_time
        done = generated + skipped + failed
        rate = generated / elapsed if elapsed > 0 else 0
        remaining_count = target - done
        eta = remaining_count / rate if rate > 0 else 0

        print(f"  [{done}/{target}]  +{batch_ok} ok  +{batch_skipped + batch_gate_skip} skip  "
              f"+{batch_err} err  {rate:.1f}/s  ETA {eta/60:.0f}m")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s ({elapsed/60:.1f}m) — "
          f"{generated} generated, {skipped} skipped, {failed} failed")
    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 5

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=')[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=')[1])

    asyncio.run(generate_narratives(limit=limit_val, concurrency=concurrency_val))
