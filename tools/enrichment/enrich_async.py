"""
Async concurrent enrichment using Claude API.

Sends multiple enrichment requests in parallel (default 5 concurrent)
for ~5x speedup over sequential processing.

Usage:
  python enrichment/enrich_async.py [--limit=N] [--concurrency=5] [--yes]

Run from project root.
"""
import sys
import os
import json
import time
import asyncio
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import anthropic
from dotenv import load_dotenv
load_dotenv()

from storage.database import SessionLocal, Product
from enrichment.claude import ClaudeEnricher, VIBE_AXES
from enrichment.era_taxonomy import (
    normalize_era, build_era_prompt_section,
    report_unrecognized_eras, export_unrecognized_eras,
)


MODEL = "claude-sonnet-4-20250514"


def build_request(product, enricher):
    """Build the messages content for a single product enrichment."""
    has_expert = (
        product.platform == 'fashionpedia' and product.fp_category is not None
    )

    if has_expert:
        # Fashionpedia: use enrich_creative_only path via the cached system prompt
        # The system prompt contains all field definitions; user message has item details
        existing_fields = {
            'fp_category': product.fp_category,
            'nickname': product.nickname,
            'silhouette': product.silhouette,
            'neckline': product.neckline,
            'waistline': product.waistline,
            'length': product.length,
            'sleeve_length': product.sleeve_length,
            'opening_type': product.opening_type,
            'textile_pattern': product.textile_pattern,
            'textile_finishing': json.loads(product.textile_finishing) if product.textile_finishing else [],
            'garment_parts': json.loads(product.garment_parts) if product.garment_parts else [],
            'decorations': json.loads(product.decorations) if product.decorations else [],
        }

        struct_context = []
        for key in ('fp_category', 'nickname', 'silhouette', 'neckline', 'waistline',
                    'length', 'sleeve_length', 'opening_type', 'textile_pattern'):
            val = existing_fields.get(key)
            if val:
                struct_context.append(f"- {key}: {val}")
        for key in ('textile_finishing', 'garment_parts', 'decorations'):
            val = existing_fields.get(key)
            if val and isinstance(val, list) and val:
                struct_context.append(f"- {key}: {', '.join(val)}")

        prompt = f"""Analyze this item and return the JSON object specified in your instructions.

**Item Details (from expert-annotated dataset — structural fields are pre-filled, do NOT change them):**
- Title: {product.title}
- Source category: {product.category or product.fp_category or ''}

**Expert-annotated structural attributes (already correct):**
{chr(10).join(struct_context) if struct_context else '(none)'}

Fill in creative, cross-cultural, and knowledge graph fields only. Keep all structural fields as provided."""

    else:
        prompt = enricher._build_enrichment_prompt(
            title=product.title,
            category=product.category,
            color=product.color,
            season=product.season,
            year=product.year,
            material=product.material,
            pattern=product.pattern,
            culture=product.culture,
            period=product.period,
            era=product.era,
            object_date=product.object_date,
        )

    system = enricher._build_enrichment_system_prompt()
    content = enricher._build_image_content(product.primary_image)
    content.append({"type": "text", "text": prompt})

    return system, content, has_expert


def parse_response(response_text):
    """Extract JSON from Claude response."""
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    return json.loads(json_str)


def apply_enrichment(product, enrichment, enricher, is_creative_only):
    """Write enrichment results to a product (no embedding). Returns True on success."""
    has_content = (
        enrichment.get('era') or
        enrichment.get('fp_category') or
        enrichment.get('garment_type')
    )
    if not has_content:
        return False

    # If creative-only, merge with existing structural fields
    if is_creative_only:
        existing = {
            'fp_category': product.fp_category,
            'nickname': product.nickname,
            'silhouette': product.silhouette,
            'neckline': product.neckline,
            'waistline': product.waistline,
            'length': product.length,
            'sleeve_length': product.sleeve_length,
            'opening_type': product.opening_type,
            'textile_pattern': product.textile_pattern,
        }
        for key, val in existing.items():
            if val and not enrichment.get(key):
                enrichment[key] = val

    rich_text = enricher.build_rich_text(
        product_data={'title': product.title, 'category': product.category},
        enrichment=enrichment
    )
    product.enriched_text = rich_text

    product.era = normalize_era(enrichment.get('era'), product_id=product.id)
    product.decade = enrichment.get('decade')
    if enrichment.get('culture'):
        product.culture = enrichment['culture']
    product.style_tags = json.dumps(enrichment.get('style_tags', []))
    product.colors = json.dumps(enrichment.get('colors', []))
    product.material = enrichment.get('material')
    product.pattern = enrichment.get('pattern')
    product.garment_type = enrichment.get('garment_type')
    # Vibe scores — new 6-axis format (old vibe/core_vibes/bridge_vibes cleared)
    product.vibe = None
    product.core_vibes = None
    product.bridge_vibes = None
    product.vibe_scores = enrichment.get('vibe_scores')
    product.fit_style = enrichment.get('fit_style')
    product.occasion = enrichment.get('occasion')
    product.ai_description = enrichment.get('ai_description')
    product.fp_category = enrichment.get('fp_category', product.fp_category)
    product.nickname = enrichment.get('nickname', product.nickname)
    product.silhouette = enrichment.get('silhouette', product.silhouette)
    product.neckline = enrichment.get('neckline', product.neckline)
    product.waistline = enrichment.get('waistline', product.waistline)
    product.length = enrichment.get('length', product.length)
    product.sleeve_length = enrichment.get('sleeve_length', product.sleeve_length)
    product.opening_type = enrichment.get('opening_type', product.opening_type)
    product.textile_pattern = enrichment.get('textile_pattern', product.textile_pattern)
    product.textile_finishing = json.dumps(enrichment.get('textile_finishing', []))
    product.garment_parts = json.dumps(enrichment.get('garment_parts', []))
    product.decorations = json.dumps(enrichment.get('decorations', []))

    # Cross-cultural bridge fields
    ct = enrichment.get('construction_technique')
    if ct and isinstance(ct, list):
        product.construction_technique = json.dumps(ct)
    elif ct and ct != 'null':
        product.construction_technique = json.dumps([ct])

    sf = enrichment.get('social_function')
    if sf and isinstance(sf, list):
        product.social_function = json.dumps(sf)
    elif sf and sf != 'null' and sf != 'none':
        product.social_function = json.dumps([sf])

    mf = enrichment.get('motif_family')
    if mf and isinstance(mf, list):
        product.motif_family = json.dumps(mf)
    elif mf and mf != 'null':
        product.motif_family = json.dumps([mf])

    # Knowledge graph fields
    product.designer = enrichment.get('designer')
    ir = enrichment.get('influence_references')
    if ir and isinstance(ir, list):
        product.influence_references = json.dumps(ir)
    product.production_mode = enrichment.get('production_mode')
    product.material_origin = enrichment.get('material_origin')
    gs = enrichment.get('garment_system')
    if gs and isinstance(gs, list):
        product.garment_system = json.dumps(gs)
    nm = enrichment.get('named_movements')
    if nm and isinstance(nm, list):
        product.named_movements = json.dumps(nm)
    lcf = enrichment.get('low_confidence_fields')
    if lcf is not None:
        product.low_confidence_fields = json.dumps(lcf)
    if enrichment.get('display_title'):
        product.display_title = enrichment['display_title']

    product.enriched_at = datetime.now()

    return True


async def enrich_one(semaphore, async_client, product_id, system, content, is_creative_only, counter, total):
    """Send one enrichment request, respecting concurrency limit."""
    async with semaphore:
        try:
            response = await async_client.messages.create(
                model=MODEL,
                max_tokens=1200,
                temperature=0.4 if not is_creative_only else 0.5,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
            done = counter['done'] = counter['done'] + 1
            if done % 10 == 0 or done == total:
                elapsed = time.time() - counter['start']
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [{done}/{total}] {rate:.1f} req/s  ETA {eta:.0f}s")
            return product_id, response.content[0].text, is_creative_only, None
        except Exception as e:
            counter['errors'] = counter['errors'] + 1
            counter['done'] = counter['done'] + 1
            print(f"    [{product_id}] error: {str(e)[:60]}")
            return product_id, None, is_creative_only, str(e)


async def run_async(products, enricher, concurrency):
    """Fire off all enrichment requests with bounded concurrency."""
    async_client = anthropic.AsyncAnthropic(max_retries=3)
    semaphore = asyncio.Semaphore(concurrency)
    counter = {'done': 0, 'errors': 0, 'start': time.time()}
    total = len(products)

    tasks = []
    for product in products:
        system, content, is_creative_only = build_request(product, enricher)
        task = enrich_one(semaphore, async_client, product.id, system, content, is_creative_only, counter, total)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    await async_client.close()
    return results


def main(limit=None, concurrency=5, rebuild=False):
    db = SessionLocal()
    enricher = ClaudeEnricher()

    if rebuild:
        query = db.query(Product)
    else:
        query = db.query(Product).filter(Product.enriched_at == None)
    if limit:
        query = query.limit(limit)
    products = query.all()

    if not products:
        print("No unenriched products found.")
        db.close()
        return

    by_platform = {}
    for p in products:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print(f"\n{'=' * 70}")
    print(f"ASYNC ENRICHMENT — {concurrency} concurrent requests")
    print(f"{'=' * 70}")
    print(f"\n  Products to enrich: {len(products)}")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"    {platform:20s} {count:4d}")

    estimated_cost = len(products) * 0.025
    estimated_time = len(products) * 6 / concurrency / 60
    print(f"\n  Estimated cost: ~${estimated_cost:.2f}")
    print(f"  Estimated time: ~{estimated_time:.0f} min (with {concurrency}x concurrency)")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

    product_map = {p.id: p for p in products}

    # Phase 1: async API calls
    print(f"\n  Phase 1: Sending {len(products)} API requests ({concurrency} concurrent)...")
    start = time.time()
    results = asyncio.run(run_async(products, enricher, concurrency))
    api_elapsed = time.time() - start
    print(f"  API calls complete in {api_elapsed:.0f}s")

    # Phase 2: process results (DB writes only — run embeddings separately)
    # Fresh session — old one may have timed out during API phase
    try:
        db.close()
    except Exception:
        pass
    db = SessionLocal()
    product_map = {pid: db.get(Product, pid) for pid in product_map}

    print(f"\n  Phase 2: Writing results to DB...")
    process_start = time.time()

    success_count = 0
    failed_count = 0
    non_garment_count = 0

    for product_id, response_text, is_creative_only, error in results:
        product = product_map[product_id]

        if error:
            print(f"  [{product_id}] API error: {error[:80]}")
            failed_count += 1
            continue

        try:
            enrichment = parse_response(response_text)
        except json.JSONDecodeError as e:
            print(f"  [{product_id}] JSON parse error: {e}")
            failed_count += 1
            continue

        if apply_enrichment(product, enrichment, enricher, is_creative_only):
            success_count += 1
        else:
            non_garment_count += 1

        if success_count % 100 == 0 and success_count > 0:
            db.commit()
            elapsed = time.time() - process_start
            print(f"    {success_count} processed ({elapsed:.0f}s)")

    db.commit()
    total_elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print("ASYNC ENRICHMENT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Succeeded:    {success_count}")
    print(f"  Failed:       {failed_count}")
    print(f"  Non-garments: {non_garment_count}")
    print(f"  API time:     {api_elapsed:.0f}s")
    print(f"  Total time:   {total_elapsed:.0f}s")
    print(f"\n  Next step: generate embeddings for newly enriched products")

    report_unrecognized_eras()
    export_unrecognized_eras()

    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 5
    rebuild_val = '--rebuild' in sys.argv

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=', 1)[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=', 1)[1])

    main(limit=limit_val, concurrency=concurrency_val, rebuild=rebuild_val)
