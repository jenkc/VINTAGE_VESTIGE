"""
Targeted backfill: assign vibe_axes (6-axis pole system)
for products that are enriched but missing vibe_axes data.

Uses already-enriched fields (ai_description, vibe, era, culture,
silhouette, social_function, fp_category) — no image needed.

Usage:
  venv/bin/python enrichment/backfill_vibes.py [--limit=N] [--concurrency=N] [--dry-run]
  venv/bin/python enrichment/backfill_vibes.py --rebuild   # re-score ALL products

Safe to interrupt and resume — only processes products where vibe_scores IS NULL
(unless --rebuild is used).
"""

import sys
import os
import json
import time
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product
from enrichment.claude import ClaudeEnricher, VIBE_AXES
from sqlalchemy import text


def build_prompt(p: dict) -> str:
    sf = p.get('social_function') or ''
    if isinstance(sf, list):
        sf = ', '.join(sf)
    lines = [
        f"Garment: {p.get('title', 'unknown')}",
        f"Era: {p.get('era', 'unknown')} | Culture: {p.get('culture', 'unknown')}",
        f"Category: {p.get('fp_category', 'unknown')} | Silhouette: {p.get('silhouette', 'unknown')}",
        f"Function: {sf or 'unknown'}",
        f"Vibe (freeform): {p.get('vibe', 'unknown')}",
        "",
        f"Description: {p.get('ai_description', '')[:400]}",
        "",
        VIBE_AXES,
        "",
        'Return JSON only: {"vibe_axes": {"axis": ["Pole Name", confidence] or null}}',
        "",
        "Only score axes where the garment makes a clear argument for one pole.",
        "Skip (null) axes that don't apply. Confidence 0.5-1.0.",
        "Return valid JSON, nothing else.",
    ]
    return "\n".join(lines)


async def backfill_product(enricher, product_data: dict, semaphore):
    async with semaphore:
        prompt = build_prompt(product_data)
        try:
            response = await enricher.async_client.messages.create(
                model=enricher.model,
                max_tokens=300,
                temperature=0.3,
                system="You are a fashion historian scoring garments on aesthetic axes. Return valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            return product_data['id'], result, None
        except Exception as e:
            return product_data['id'], None, str(e)


async def run(limit=None, concurrency=5, dry_run=False, rebuild=False):
    db = SessionLocal()

    if rebuild:
        where_clause = "WHERE enriched_at IS NOT NULL"
    else:
        where_clause = "WHERE enriched_at IS NOT NULL AND vibe_scores IS NULL"

    rows = db.execute(text(f"""
        SELECT id, title, era, culture, fp_category, silhouette,
               vibe, ai_description, social_function
        FROM products
        {where_clause}
        ORDER BY id
    """)).fetchall()

    total = len(rows)
    if limit:
        rows = rows[:limit]

    label = "ALL products (rebuild)" if rebuild else "Products missing vibe_axes"
    print(f"{label}: {total}")
    print(f"Will process: {len(rows)}  (concurrency: {concurrency}{'  DRY RUN' if dry_run else ''})\n")

    if not rows:
        db.close()
        return

    products = []
    for r in rows:
        sf = r[8]
        if isinstance(sf, str):
            try:
                sf = json.loads(sf)
            except Exception:
                sf = [sf]
        products.append({
            'id': r[0], 'title': r[1], 'era': r[2], 'culture': r[3],
            'fp_category': r[4], 'silhouette': r[5], 'vibe': r[6],
            'ai_description': r[7], 'social_function': sf,
        })

    enricher = ClaudeEnricher()
    semaphore = asyncio.Semaphore(concurrency)
    batch_size = concurrency * 10

    updated = 0
    failed = 0
    start_time = time.time()

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        tasks = [backfill_product(enricher, p, semaphore) for p in batch]
        results = await asyncio.gather(*tasks)

        for product_id, result, error in results:
            if result:
                axes = result.get('vibe_axes') or {}

                if dry_run:
                    print(f"  id={product_id}  vibe_axes={axes}")
                else:
                    db.execute(text("""
                        UPDATE products
                        SET vibe_scores = :axes
                        WHERE id = :id
                    """), {
                        'axes': json.dumps(axes),
                        'id': product_id,
                    })
                updated += 1
            else:
                failed += 1
                if error:
                    print(f"  ERR id={product_id}: {error}")

        if not dry_run:
            db.commit()

        done = updated + failed
        elapsed = time.time() - start_time
        rate = updated / elapsed if elapsed > 0 else 0
        remaining = len(products) - done
        eta = remaining / rate if rate > 0 else 0
        print(f"  [{done}/{len(products)}]  +{len([r for r in results if r[1]])} ok  "
              f"+{len([r for r in results if not r[1]])} err  "
              f"{rate:.1f}/s  ETA {eta/60:.0f}m")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s — {updated} updated, {failed} failed")
    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 10
    dry_run = False
    rebuild = False

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=')[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=')[1])
        elif arg == '--dry-run':
            dry_run = True
        elif arg == '--rebuild':
            rebuild = True

    asyncio.run(run(limit=limit_val, concurrency=concurrency_val, dry_run=dry_run, rebuild=rebuild))
