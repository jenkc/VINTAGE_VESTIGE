"""
Backfill display_title for all products.

Generates concise, descriptive titles from existing enrichment data.
Lightweight — no image needed, small prompt, fast.

Usage:
  venv/bin/python tools/enrichment/backfill_display_titles.py [--limit=N] [--concurrency=15] [--yes]
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

SYSTEM_PROMPT = [{
    "type": "text",
    "cache_control": {"type": "ephemeral"},
    "text": (
        "You are generating concise, descriptive titles for fashion items in a knowledge graph. "
        "Return ONLY the title text — no JSON, no quotes, no explanation.\n\n"
        "Rules:\n"
        "- 5-10 words\n"
        "- Include the most distinctive attributes: material, color, garment type, defining feature\n"
        "- Do NOT include dates, era names, or designer names\n"
        "- If the original title is already specific and descriptive (e.g. 'Abraham Lincoln's Office Suit'), keep it unchanged\n"
        "- For fragments/textiles, describe the material and pattern\n"
        "- For accessories, name the object type and key material\n"
        "Examples:\n"
        "  'Dress' + silk + burgundy + mermaid → Burgundy Silk Mermaid Evening Dress\n"
        "  'Fragment' + velvet + brocade + floral → Crimson Silk Velvet Fragment with Floral Brocade\n"
        "  'Classic' + cotton + sage green + t-shirt → Sage Green Cotton Crew Neck T-Shirt\n"
        "  'Abraham Lincoln's Office Suit' → Abraham Lincoln's Office Suit"
    )
}]


def build_prompt(product):
    """Build per-product prompt from stored fields."""
    parts = [f"Original title: {product.title}"]
    if product.garment_type:
        parts.append(f"Type: {product.garment_type}")
    if product.material:
        parts.append(f"Material: {product.material}")
    if product.fp_category:
        parts.append(f"Category: {product.fp_category}")
    if product.nickname:
        parts.append(f"Nickname: {product.nickname}")
    if product.silhouette:
        parts.append(f"Silhouette: {product.silhouette}")
    if product.colors:
        try:
            colors = json.loads(product.colors) if isinstance(product.colors, str) else product.colors
            if colors:
                parts.append(f"Colors: {', '.join(colors[:3])}")
        except (json.JSONDecodeError, TypeError):
            pass
    if product.ai_description:
        parts.append(f"Description: {product.ai_description[:150]}")

    return "\n".join(parts)


async def generate_one(semaphore, async_client, product_id, prompt, counter, total):
    async with semaphore:
        try:
            response = await async_client.messages.create(
                model=MODEL,
                max_tokens=50,
                temperature=0.3,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            title = response.content[0].text.strip().strip('"').strip("'")
            done = counter['done'] = counter['done'] + 1
            if done % 50 == 0 or done == total:
                elapsed = time.time() - counter['start']
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [{done:>5}/{total}] {rate:.1f} req/s  ETA {eta:.0f}s")
            return product_id, title, None
        except Exception as e:
            counter['done'] = counter['done'] + 1
            counter['errors'] = counter['errors'] + 1
            return product_id, None, str(e)


async def run_async(requests, concurrency):
    async_client = anthropic.AsyncAnthropic(max_retries=3)
    semaphore = asyncio.Semaphore(concurrency)
    counter = {'done': 0, 'errors': 0, 'start': time.time()}
    total = len(requests)

    tasks = [
        generate_one(semaphore, async_client, pid, prompt, counter, total)
        for pid, prompt in requests
    ]

    results = await asyncio.gather(*tasks)
    await async_client.close()
    return results


def main(limit=None, concurrency=15):
    db = SessionLocal()

    query = db.query(Product).filter(
        Product.enriched_at != None,
        Product.display_title == None,
    )
    if limit:
        query = query.limit(limit)
    products = query.all()

    if not products:
        print("All products already have display titles.")
        db.close()
        return

    # Cost: ~100 input tokens + ~20 output tokens per call, very cheap
    est_cost = len(products) * 0.0005
    est_time = len(products) / (concurrency * 1.5) / 60

    print(f"\n{'=' * 60}")
    print(f"DISPLAY TITLE BACKFILL — {concurrency} concurrent")
    print(f"{'=' * 60}")
    print(f"  Products: {len(products)}")
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print(f"  Estimated time: ~{est_time:.0f} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

    # Build requests
    requests = [(p.id, build_prompt(p)) for p in products]

    # Phase 1: async API calls
    print(f"\n  Phase 1: Generating {len(requests)} titles...")
    start = time.time()
    results = asyncio.run(run_async(requests, concurrency))
    api_elapsed = time.time() - start
    print(f"  API calls complete in {api_elapsed:.0f}s")

    # Phase 2: write results
    try:
        db.close()
    except Exception:
        pass
    db = SessionLocal()

    print(f"\n  Phase 2: Writing to DB...")
    success = 0
    failed = 0

    for product_id, title, error in results:
        if error or not title:
            failed += 1
            continue

        product = db.get(Product, product_id)
        if product:
            product.display_title = title
            success += 1

        if success % 200 == 0 and success > 0:
            db.commit()

    db.commit()
    total_elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print(f"BACKFILL COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Succeeded: {success}")
    print(f"  Failed:    {failed}")
    print(f"  Total:     {total_elapsed:.0f}s")

    # Show samples
    samples = db.execute(
        __import__('sqlalchemy').text(
            "SELECT title, display_title FROM products "
            "WHERE display_title IS NOT NULL ORDER BY random() LIMIT 5"
        )
    ).fetchall()
    if samples:
        print(f"\n  Samples:")
        for orig, display in samples:
            print(f"    \"{orig[:40]}\" → \"{display}\"")

    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 15

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=', 1)[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=', 1)[1])

    main(limit=limit_val, concurrency=concurrency_val)
