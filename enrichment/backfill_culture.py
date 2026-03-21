"""
Backfill missing culture field for enriched products.

Sends Claude the existing enriched fields and asks for cultural/geographic origin.

Usage:
  venv/bin/python enrichment/backfill_culture.py [--limit=N] [--concurrency=N] [--dry-run]
"""

import sys
import os
import json
import time
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product
from enrichment.claude import ClaudeEnricher
from sqlalchemy import text


def build_prompt(p: dict) -> str:
    return f"""What is the cultural or geographic origin of this garment?

Title: {p.get('title', 'unknown')}
Era: {p.get('era', 'unknown')}
Material: {p.get('material', 'unknown')}
Category: {p.get('fp_category', 'unknown')}
Platform: {p.get('platform', 'unknown')}
Description: {(p.get('ai_description') or '')[:300]}

Return a single term like: Western, British, French, American, Japanese, South Asian, Chinese, Korean, African, Middle Eastern, etc.
If the garment blends traditions, pick the dominant one.
Return ONLY the culture term, nothing else."""


async def backfill_product(enricher, product_data: dict, semaphore):
    async with semaphore:
        prompt = build_prompt(product_data)
        try:
            response = await enricher.async_client.messages.create(
                model=enricher.model,
                max_tokens=20,
                temperature=0.2,
                system="You are a fashion historian. Return only the cultural/geographic origin term.",
                messages=[{"role": "user", "content": prompt}],
            )
            culture = response.content[0].text.strip().strip('"').strip("'")
            return product_data['id'], culture, None
        except Exception as e:
            return product_data['id'], None, str(e)


async def run(limit=None, concurrency=10, dry_run=False):
    db = SessionLocal()

    rows = db.execute(text("""
        SELECT id, title, era, material, fp_category, platform, ai_description
        FROM products
        WHERE enriched_at IS NOT NULL
          AND (culture IS NULL OR culture = '')
        ORDER BY id
    """)).fetchall()

    total = len(rows)
    if limit:
        rows = rows[:limit]

    print(f"Products missing culture: {total}")
    print(f"Will process: {len(rows)}  (concurrency: {concurrency}{'  DRY RUN' if dry_run else ''})\n")

    if not rows:
        db.close()
        return

    products = [
        {'id': r[0], 'title': r[1], 'era': r[2], 'material': r[3],
         'fp_category': r[4], 'platform': r[5], 'ai_description': r[6]}
        for r in rows
    ]

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

        for product_id, culture, error in results:
            if culture:
                if dry_run:
                    print(f"  id={product_id}  culture={culture}")
                else:
                    db.execute(text(
                        "UPDATE products SET culture = :culture WHERE id = :id"
                    ), {'culture': culture, 'id': product_id})
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
        print(f"  [{done}/{len(products)}]  {updated} ok  {failed} err  {rate:.1f}/s")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s — {updated} updated, {failed} failed")
    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 10
    dry_run = False

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=')[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=')[1])
        elif arg == '--dry-run':
            dry_run = True

    asyncio.run(run(limit=limit_val, concurrency=concurrency_val, dry_run=dry_run))
