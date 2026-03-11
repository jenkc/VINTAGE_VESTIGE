"""
Generate AI narratives for style bridges (async concurrent).

Finds bridges missing a narrative, calls Claude concurrently to generate
1-2 sentence explanations, and stores them on the bridge rows.

Usage:
  python analysis/generate_narratives.py [--limit=N] [--concurrency=N]

  --limit=N        Total bridges to process (default: all)
  --concurrency=N  Parallel API calls (default: 5)

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

from storage.database import SessionLocal, Product, StyleBridge
from enrichment.claude import ClaudeEnricher


async def process_bridge(enricher, bridge_data, product_map, semaphore):
    """Process a single bridge under the semaphore."""
    async with semaphore:
        src = product_map.get(bridge_data.source_id)
        tgt = product_map.get(bridge_data.target_id)
        if not src or not tgt:
            return bridge_data.id, None, "missing product"

        item_a = dict(src)  # shallow copy
        item_b = dict(tgt)

        shared = json.loads(bridge_data.shared_attributes) if bridge_data.shared_attributes else {}

        try:
            narrative = await enricher.generate_bridge_narrative_async(
                item_a, item_b, shared,
                connection_mode=bridge_data.connection_mode,
                contrast_pair=bridge_data.contrast_pair,
                temporal_type=bridge_data.temporal_type,
                crossing_type=bridge_data.crossing_type,
                primary_axis=bridge_data.primary_axis,
            )
            return bridge_data.id, narrative, None
        except Exception as e:
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

    target = min(limit, total_remaining) if limit else total_remaining
    print(f"Bridges without narratives: {total_remaining}")
    print(f"Will process: {target}  (concurrency: {concurrency})\n")

    # Pre-load all products as dicts (avoid SQLAlchemy objects in async)
    products = db.query(Product).all()
    product_map = {}
    for p in products:
        # Parse core_vibes from JSON/ARRAY to list
        cv = p.core_vibes
        if isinstance(cv, str):
            try:
                cv = json.loads(cv)
            except (json.JSONDecodeError, TypeError):
                cv = []
        product_map[p.id] = {
            'title': p.title, 'era': p.era, 'decade': p.decade,
            'material': p.material, 'silhouette': p.silhouette,
            'vibe': p.vibe, 'fp_category': p.fp_category,
            'culture': p.culture, 'social_function': p.social_function,
            'core_vibes': cv or [],
        }

    generated = 0
    failed = 0
    start_time = time.time()
    batch_size = concurrency * 10  # fetch in chunks

    while generated + failed < target:
        fetch_size = min(batch_size, target - generated - failed)
        bridges = (
            db.query(
                StyleBridge.id, StyleBridge.source_id, StyleBridge.target_id,
                StyleBridge.shared_attributes,
                StyleBridge.connection_mode, StyleBridge.contrast_pair,
                StyleBridge.temporal_type, StyleBridge.crossing_type,
                StyleBridge.primary_axis,
            )
            .filter(StyleBridge.bridge_narrative == None)
            .order_by(StyleBridge.text_similarity.desc())
            .limit(fetch_size)
            .all()
        )

        if not bridges:
            break

        # Fire all calls concurrently (semaphore limits parallelism)
        tasks = [
            process_bridge(enricher, b, product_map, semaphore)
            for b in bridges
        ]

        results = await asyncio.gather(*tasks)

        # Write results to DB
        batch_ok = 0
        batch_err = 0
        for bridge_id, narrative, error in results:
            if narrative:
                db.query(StyleBridge).filter(StyleBridge.id == bridge_id).update(
                    {StyleBridge.bridge_narrative: narrative}
                )
                batch_ok += 1
            else:
                batch_err += 1
                if error and error != "missing product":
                    print(f"  ERR bridge {bridge_id}: {error}")

        db.commit()
        generated += batch_ok
        failed += batch_err

        elapsed = time.time() - start_time
        done = generated + failed
        rate = generated / elapsed if elapsed > 0 else 0
        remaining_count = target - done
        eta = remaining_count / rate if rate > 0 else 0

        print(f"  [{done}/{target}]  +{batch_ok} ok  +{batch_err} err  "
              f"{rate:.1f}/s  ETA {eta/60:.0f}m")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s ({elapsed/60:.1f}m) — "
          f"{generated} generated, {failed} failed")
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
