"""
Backfill silhouette on products where it's NULL.

Sends a focused prompt to Claude with title + description + image,
asking only for silhouette classification from the controlled vocab.
Much cheaper than full re-enrichment.

Usage:
  python enrichment/backfill_silhouette.py                    # dry-run (count only)
  python enrichment/backfill_silhouette.py --apply            # run backfill
  python enrichment/backfill_silhouette.py --apply --limit=50 # test subset
  python enrichment/backfill_silhouette.py --apply --concurrency=10

Run from project root.
"""
import sys
import os
import json
import time
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import anthropic
from dotenv import load_dotenv
load_dotenv()

from storage.database import SessionLocal, Product


MODEL = "claude-sonnet-4-20250514"

SILHOUETTE_VALUES = [
    "a-line", "pencil", "straight", "fit and flare", "flare",
    "trumpet", "mermaid", "balloon", "bell", "wide leg", "peg",
    "tent", "tight fit", "regular fit", "loose fit", "oversized",
]

PROMPT_TEMPLATE = """Look at this fashion item and classify its silhouette.

Title: {title}
Description: {description}

Pick exactly ONE from this list, or "null" if not applicable (e.g. accessories):
{values}

Return ONLY a JSON object: {{"silhouette": "value"}} or {{"silhouette": null}}
No explanation, no markdown."""


async def backfill_one(client, semaphore, product, stats):
    """Send one silhouette classification request."""
    async with semaphore:
        desc = (product.description or '')[:500]
        prompt = PROMPT_TEMPLATE.format(
            title=product.title or 'Unknown',
            description=desc,
            values=' | '.join(SILHOUETTE_VALUES),
        )

        messages_content = [{"type": "text", "text": prompt}]

        # Add image if available
        first_image = None
        if product.image_urls:
            try:
                urls = json.loads(product.image_urls) if isinstance(product.image_urls, str) else product.image_urls
                if urls:
                    first_image = urls[0]
            except (json.JSONDecodeError, TypeError):
                pass
        if first_image:
            messages_content.insert(0, {
                "type": "image",
                "source": {"type": "url", "url": first_image},
            })

        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=50,
                messages=[{"role": "user", "content": messages_content}],
                system="You are a fashion taxonomy classifier. Return only valid JSON, no markdown.",
            )
        except anthropic.BadRequestError:
            # Likely bad image URL — retry text-only
            text_only = [c for c in messages_content if c["type"] == "text"]
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=50,
                    messages=[{"role": "user", "content": text_only}],
                    system="You are a fashion taxonomy classifier. Return only valid JSON, no markdown.",
                )
            except anthropic.APIError as e:
                stats['errors'] += 1
                if stats['errors'] <= 5:
                    print(f"    API error on product {product.id}: {e}")
                return
        except anthropic.APIError as e:
            stats['errors'] += 1
            if stats['errors'] <= 5:
                print(f"    API error on product {product.id}: {e}")
            return

        try:
            text = response.content[0].text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

            result = json.loads(text)
            silhouette = result.get('silhouette')

            if silhouette and silhouette.lower() in SILHOUETTE_VALUES:
                product.silhouette = silhouette.lower()
                stats['updated'] += 1
            elif silhouette is None or silhouette == 'null':
                stats['null_response'] += 1
            else:
                stats['invalid'] += 1
                stats['invalid_values'].append((product.id, silhouette))

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            stats['errors'] += 1
            if stats['errors'] <= 5:
                print(f"    Parse error on product {product.id}: {e}")


        stats['processed'] += 1
        if stats['processed'] % 50 == 0:
            elapsed = time.time() - stats['start_time']
            rate = stats['processed'] / elapsed
            remaining = (stats['total'] - stats['processed']) / rate if rate > 0 else 0
            print(f"  [{stats['processed']:>5}/{stats['total']}]  "
                  f"updated={stats['updated']}  null={stats['null_response']}  "
                  f"errors={stats['errors']}  {rate:.1f}/s  ETA {remaining:.0f}s")


async def run_async(limit=None, concurrency=5):
    """Run the backfill."""
    db = SessionLocal()

    query = db.query(Product).filter(Product.silhouette.is_(None))
    total_missing = query.count()

    if limit:
        products = query.limit(limit).all()
    else:
        products = query.all()

    print(f"\n{'=' * 60}")
    print(f"SILHOUETTE BACKFILL")
    print(f"{'=' * 60}")
    print(f"\n  Total missing silhouette: {total_missing}")
    print(f"  Processing: {len(products)}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Model: {MODEL}\n")

    # Platform breakdown
    by_platform = {}
    for p in products:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {platform:20s} {count:4d}")

    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(concurrency)

    stats = {
        'processed': 0, 'updated': 0, 'null_response': 0,
        'invalid': 0, 'errors': 0, 'total': len(products),
        'start_time': time.time(), 'invalid_values': [],
    }

    print(f"\nStarting...\n")

    # Process in batches to commit periodically
    batch_size = 100
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        tasks = [backfill_one(client, semaphore, p, stats) for p in batch]
        await asyncio.gather(*tasks)

        # Commit after each batch
        db.commit()


    db.commit()

    elapsed = time.time() - stats['start_time']
    print(f"\n{'=' * 60}")
    print(f"COMPLETE in {elapsed:.0f}s")
    print(f"{'=' * 60}")
    print(f"  Processed:      {stats['processed']}")
    print(f"  Updated:        {stats['updated']}")
    print(f"  Null (N/A):     {stats['null_response']}")
    print(f"  Invalid values: {stats['invalid']}")
    print(f"  Errors:         {stats['errors']}")

    if stats['invalid_values']:
        print(f"\n  Invalid values returned:")
        for pid, val in stats['invalid_values'][:20]:
            print(f"    product {pid}: '{val}'")

    db.close()


def run(limit=None, concurrency=5, apply=False):
    if not apply:
        db = SessionLocal()
        missing = db.query(Product).filter(Product.silhouette.is_(None)).count()
        by_platform = {}
        for row in db.query(Product.platform, Product).filter(Product.silhouette.is_(None)).all():
            by_platform[row[0]] = by_platform.get(row[0], 0) + 1

        print(f"\nDRY RUN — {missing} products missing silhouette:")
        for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
            print(f"  {platform:20s} {count:4d}")
        print(f"\nRun with --apply to backfill.")
        db.close()
        return

    asyncio.run(run_async(limit=limit, concurrency=concurrency))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backfill silhouette on products')
    parser.add_argument('--apply', action='store_true', help='Run backfill (default is dry-run)')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of products')
    parser.add_argument('--concurrency', type=int, default=5, help='Concurrent API calls')
    args = parser.parse_args()

    run(limit=args.limit, concurrency=args.concurrency, apply=args.apply)
