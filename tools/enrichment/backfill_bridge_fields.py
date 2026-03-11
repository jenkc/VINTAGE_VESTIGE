"""
Backfill construction_technique, social_function, and motif_family
on already-enriched products using async Claude calls.

These fields enable cross-cultural and cross-temporal bridging:
  - construction_technique: how the garment was made (resist-dyeing, hand-embroidery, etc.)
  - social_function: what social role it serves (wedding, mourning, status signaling, etc.)
  - motif_family: decorative motif families (geometric, floral, paisley, etc.)

Usage:
  python enrichment/scripts/backfill_bridge_fields.py [--limit=N] [--concurrency=5] [--yes]

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

SYSTEM_PROMPT = (
    "You are a fashion historian and textile scholar enriching records for Vintage Vestige, "
    "a knowledge graph that connects museum archival pieces to modern fashion across cultures and centuries. "
    "Return only valid JSON, no markdown."
)

BACKFILL_PROMPT_TEMPLATE = """Analyze this fashion item and provide three cross-cultural bridging fields.

**Item:** {title}
**Category:** {category}
**Era:** {era}
**Decade:** {decade}
**Culture:** {culture}
**Material:** {material}
**Garment type:** {garment_type}
**Silhouette:** {silhouette}
**Textile pattern:** {textile_pattern}
**Decorations:** {decorations}
**AI Description:** {ai_description}

Return a JSON object with exactly these three fields:

"construction_technique": Array of 1-3 techniques from this controlled vocabulary:
  hand-embroidery | machine-embroidery | hand-weaving | machine-weaving |
  knitting | crocheting | felting | draping | tailoring | resist-dyeing |
  block-printing | screen-printing | digital-printing | batik | tie-dye |
  quilting | smocking | pleating | lacework | beadwork | applique |
  tapestry | brocade-weaving | jacquard-weaving | hand-sewing | couture-construction |
  leather-working | metalwork | null
  Pick techniques visible or strongly implied. Use null only if truly unknown.

"social_function": Array of 1-2 social roles this garment serves. Prefer terms from this list:
  wedding | mourning | religious-ceremonial | court-formal | military-uniform |
  status-signaling | everyday-practical | workwear | sportswear | performance-costume |
  coming-of-age | festival-celebration | diplomatic-gift | academic-formal |
  protest-subculture | leisure-resort
  But if the garment's function isn't captured by these terms, use your own concise
  label (e.g. "dance", "hunting", "nursing", "pilgrimage").
  Use ["none"] only if truly no social function applies.

"motif_family": Array of 1-3 motif families from this controlled vocabulary:
  geometric | floral | paisley | chevron-zigzag | spiral-scroll |
  animal-figurative | bird-figurative | mythological | calligraphic |
  lattice-trellis | medallion | stripe-band | dot-spot | tree-of-life |
  cloud-wave | star-celestial | heraldic | abstract-organic | none
  Pick motif families visible on the garment. Use ["none"] for plain garments.

Return ONLY valid JSON."""


def build_backfill_content(product):
    """Build prompt content for a single product."""
    # Parse JSON array fields safely
    decorations = ''
    if product.decorations:
        try:
            deco_list = json.loads(product.decorations) if isinstance(product.decorations, str) else product.decorations
            decorations = ', '.join(deco_list) if deco_list else ''
        except (json.JSONDecodeError, TypeError):
            pass

    prompt = BACKFILL_PROMPT_TEMPLATE.format(
        title=product.title or '',
        category=product.category or product.fp_category or '',
        era=product.era or 'unknown',
        decade=product.decade or 'unknown',
        culture=product.culture or 'unknown',
        material=product.material or 'unknown',
        garment_type=product.garment_type or 'unknown',
        silhouette=product.silhouette or 'unknown',
        textile_pattern=product.textile_pattern or 'unknown',
        decorations=decorations or 'none',
        ai_description=(product.ai_description or '')[:300],
    )

    content = []

    # Include image if available
    if product.primary_image:
        if product.primary_image.startswith('http'):
            content.append({
                "type": "image",
                "source": {"type": "url", "url": product.primary_image}
            })
        elif product.primary_image.startswith('data:image'):
            header, encoded = product.primary_image.split(',', 1)
            media_type = header.split(':')[1].split(';')[0]
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": encoded}
            })

    content.append({"type": "text", "text": prompt})
    return content


def parse_response(response_text):
    """Extract JSON from Claude response."""
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    return json.loads(json_str)


async def backfill_one(semaphore, async_client, product_id, content, counter, total):
    """Send one backfill request with concurrency limit."""
    async with semaphore:
        try:
            response = await async_client.messages.create(
                model=MODEL,
                max_tokens=300,
                temperature=0.3,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            done = counter['done'] = counter['done'] + 1
            if done % 10 == 0 or done == total:
                elapsed = time.time() - counter['start']
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [{done}/{total}] {rate:.1f} req/s  ETA {eta:.0f}s")
            return product_id, response.content[0].text, None
        except Exception as e:
            counter['errors'] = counter['errors'] + 1
            counter['done'] = counter['done'] + 1
            print(f"    [{product_id}] error: {str(e)[:80]}")
            return product_id, None, str(e)


async def run_async(products, concurrency):
    """Fire off all backfill requests."""
    async_client = anthropic.AsyncAnthropic(max_retries=3)
    semaphore = asyncio.Semaphore(concurrency)
    counter = {'done': 0, 'errors': 0, 'start': time.time()}
    total = len(products)

    tasks = []
    for product in products:
        content = build_backfill_content(product)
        task = backfill_one(semaphore, async_client, product.id, content, counter, total)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    await async_client.close()
    return results


def main(limit=None, concurrency=5):
    db = SessionLocal()

    # Find enriched products that don't have the new fields yet
    query = db.query(Product).filter(
        Product.enriched_at != None,
        Product.construction_technique == None,
    )
    if limit:
        query = query.limit(limit)
    products = query.all()

    if not products:
        print("No products need backfilling.")
        db.close()
        return

    by_platform = {}
    for p in products:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print(f"\n{'=' * 70}")
    print(f"BACKFILL BRIDGE FIELDS — {concurrency} concurrent requests")
    print(f"{'=' * 70}")
    print(f"\n  Products to backfill: {len(products)}")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {platform:20s} {count:4d}")

    estimated_cost = len(products) * 0.01  # smaller prompt than full enrichment
    estimated_time = len(products) * 4 / concurrency / 60
    print(f"\n  Estimated cost: ~${estimated_cost:.2f}")
    print(f"  Estimated time: ~{estimated_time:.0f} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

    product_map = {p.id: p for p in products}

    # Phase 1: async API calls
    print(f"\n  Phase 1: Sending {len(products)} API requests...")
    start = time.time()
    results = asyncio.run(run_async(products, concurrency))
    api_elapsed = time.time() - start
    print(f"  API calls complete in {api_elapsed:.0f}s")

    # Phase 2: write results (fresh session — old one timed out during API calls)
    try:
        db.close()
    except Exception:
        pass
    db = SessionLocal()
    print(f"\n  Phase 2: Writing results to DB...")
    success = 0
    failed = 0

    for product_id, response_text, error in results:
        product = db.get(Product, product_id)

        if error:
            print(f"  [{product_id}] API error: {error[:80]}")
            failed += 1
            continue

        try:
            data = parse_response(response_text)
        except json.JSONDecodeError as e:
            print(f"  [{product_id}] JSON parse error: {e}")
            failed += 1
            continue

        # Write the three new fields
        ct = data.get('construction_technique')
        if ct and isinstance(ct, list):
            product.construction_technique = json.dumps(ct)
        elif ct and ct != 'null':
            product.construction_technique = json.dumps([ct])

        sf = data.get('social_function')
        if sf and isinstance(sf, list):
            product.social_function = json.dumps(sf)
        elif sf and sf != 'null' and sf != 'none':
            product.social_function = json.dumps([sf])

        mf = data.get('motif_family')
        if mf and isinstance(mf, list):
            product.motif_family = json.dumps(mf)
        elif mf and mf != 'null':
            product.motif_family = json.dumps([mf])

        success += 1

        if success % 50 == 0:
            db.commit()
            print(f"    {success} written")

    db.commit()
    total_elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print("BACKFILL COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Succeeded: {success}")
    print(f"  Failed:    {failed}")
    print(f"  Time:      {total_elapsed:.0f}s")
    print(f"\n  Next: re-embed products to include new fields in text_embedding")
    print(f"        then recompute bridges with --rebuild")

    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 5

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=', 1)[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=', 1)[1])

    main(limit=limit_val, concurrency=concurrency_val)
