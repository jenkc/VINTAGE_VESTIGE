"""
Re-classify eras for products where the era might be a decade default
rather than a specific movement/aesthetic.

Sends Claude the image + basic metadata, asks it to pick the most
accurate era from the full taxonomy. Only updates if Claude disagrees
with the current era.

Usage:
  PYTHONPATH=. python tools/enrichment/backfill_eras.py                # audit only
  PYTHONPATH=. python tools/enrichment/backfill_eras.py --apply        # apply changes
  PYTHONPATH=. python tools/enrichment/backfill_eras.py --apply --limit=100
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import json
import time
from storage.database import SessionLocal, Product
from enrichment.claude import ClaudeEnricher
from enrichment.era_taxonomy import build_era_prompt_section
from sqlalchemy import text


# Eras that are likely over-assigned (decade defaults)
SUSPECT_ERAS = {
    'Space Age', 'Glam Rock', 'Quiet Luxury', 'Supermodel Era',
    'Disco', 'New Romanticism', 'Normcore', 'Athleisure',
    'Power Dressing', 'Y2K', 'Atomic Age',
}

def build_era_list_from_db(db):
    """Build the era list from what actually exists in the database."""
    rows = db.execute(text('SELECT DISTINCT era FROM products WHERE era IS NOT NULL ORDER BY era')).fetchall()
    return [r[0] for r in rows]


def build_system_prompt(era_list: list[str]) -> str:
    era_block = "\n".join(f"  - {e}" for e in era_list)
    return f"""You are a fashion historian. Your task is to assign the most accurate era/movement to a garment based on its visual appearance, construction, and cultural context.

IMPORTANT: A garment's era is about its AESTHETIC IDENTITY, not just its manufacture date. A plain wool coat made in 1973 is NOT Glam Rock — it's more likely Hippie/Counterculture or just everyday 1970s fashion. A basic cotton blouse from 1965 is NOT Space Age unless it has futuristic/mod design elements.

Choose the era that best describes the garment's DESIGN LANGUAGE. If the garment is generic/unremarkable for its decade, choose the most neutral era for that period.

Existing eras in the database (prefer these):
{era_block}

If none of these fit, you may suggest a new era name — but only if the garment clearly belongs to a distinct aesthetic movement not listed above. Otherwise, pick the closest match.

Return ONLY the era name. Nothing else."""


async def reclassify_era(enricher: ClaudeEnricher, product: dict, system_prompt: str) -> str | None:
    """Ask Claude to reclassify a product's era based on its image."""
    content = []

    # Add image if available
    if product['primary_image']:
        content.extend(enricher._build_image_content(product['primary_image']))

    prompt = f"""What era/movement does this garment belong to?

Title: {product['display_title'] or product['title']}
Decade: {product['decade'] or 'unknown'}
Culture: {product['culture'] or 'unknown'}
Material: {product['material'] or 'unknown'}
Current era (may be wrong): {product['era']}

Return ONLY the era name."""

    content.append({"type": "text", "text": prompt})

    try:
        response = await enricher.async_client.messages.create(
            model=enricher.model,
            max_tokens=50,
            temperature=0.0,
            system=[{"type": "text", "cache_control": {"type": "ephemeral"}, "text": system_prompt}],
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ERR: {e}")
        return None


async def main():
    apply_mode = '--apply' in sys.argv
    limit = None
    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])

    db = SessionLocal()
    enricher = ClaudeEnricher()

    # Build era taxonomy from DB
    era_list = build_era_list_from_db(db)
    system_prompt = build_system_prompt(era_list)
    print(f"Era taxonomy: {len(era_list)} eras from database")

    # Find products with suspect eras
    query = db.query(Product).filter(
        Product.era.in_(SUSPECT_ERAS),
        Product.enriched_at != None,
    )
    if limit:
        query = query.limit(limit)
    products = query.all()

    print(f"Products with suspect eras: {len(products)}")
    if not products:
        db.close()
        return

    # Count by current era
    era_counts = {}
    for p in products:
        era_counts[p.era] = era_counts.get(p.era, 0) + 1
    print("By era:")
    for era, cnt in sorted(era_counts.items(), key=lambda x: -x[1]):
        print(f"  {era}: {cnt}")

    if not apply_mode:
        # Audit mode — sample a few
        print(f"\nSampling 20 for preview...")
        import random
        sample = random.sample(products, min(20, len(products)))

        changes = 0
        for p in sample:
            product_data = {
                'title': p.title,
                'display_title': p.display_title,
                'decade': p.decade,
                'culture': p.culture,
                'material': p.material,
                'era': p.era,
                'primary_image': p.primary_image,
            }
            new_era = await reclassify_era(enricher, product_data, system_prompt)
            if new_era and new_era != p.era:
                print(f"  CHANGE id={p.id:>5} \"{(p.display_title or p.title)[:40]}\" {p.era} → {new_era}")
                changes += 1
            else:
                print(f"  KEEP   id={p.id:>5} \"{(p.display_title or p.title)[:40]}\" {p.era}")
            await asyncio.sleep(0.5)

        print(f"\n{changes}/{len(sample)} would change. Run with --apply to update all.")
        db.close()
        return

    # Apply mode
    print(f"\nReclassifying {len(products)} products...")
    confirm = input("Proceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        db.close()
        return

    changed = 0
    kept = 0
    errors = 0
    start = time.time()

    sem = asyncio.Semaphore(5)

    async def process(p):
        nonlocal changed, kept, errors
        async with sem:
            product_data = {
                'title': p.title,
                'display_title': p.display_title,
                'decade': p.decade,
                'culture': p.culture,
                'material': p.material,
                'era': p.era,
                'primary_image': p.primary_image,
            }
            new_era = await reclassify_era(enricher, product_data, system_prompt)

            if new_era and new_era != p.era:
                db.execute(text('UPDATE products SET era = :era WHERE id = :id'),
                          {'era': new_era, 'id': p.id})
                changed += 1
                if changed % 50 == 0:
                    db.commit()
                    elapsed = time.time() - start
                    print(f"  [{changed + kept + errors}/{len(products)}] {changed} changed, {kept} kept, {errors} err  {elapsed:.0f}s")
            elif new_era:
                kept += 1
            else:
                errors += 1

    tasks = [process(p) for p in products]
    await asyncio.gather(*tasks)
    db.commit()

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Changed: {changed}")
    print(f"  Kept: {kept}")
    print(f"  Errors: {errors}")

    db.close()


if __name__ == '__main__':
    asyncio.run(main())
