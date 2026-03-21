"""
Targeted re-enrichment: creative fields + KG fields only.

Skips structural fields (already correct) and vibes (already backfilled).
Updates: ai_description, culture, designer, influence_references, production_mode,
         material_origin, garment_system, named_movements, low_confidence_fields.

Usage:
  venv/bin/python tools/enrichment/reenrich_creative_kg.py [--limit=N] [--concurrency=10] [--yes]
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
from enrichment.era_taxonomy import build_era_prompt_section

MODEL = "claude-sonnet-4-20250514"

# --- Cached system prompt (static, shared across all calls) ---

def build_system_prompt():
    era_prompt = build_era_prompt_section()
    text = f"""You are enriching a historical fashion record for Vintage Vestige, a fashion knowledge graph. You are a fashion historian and vintage style expert. Return only valid JSON, no markdown.

If an image is provided, it is your primary source. Trust the image over metadata.

For accessories, fashion plates, textiles, or non-garment objects: focus on material, construction, and cultural context.

Return a JSON object with ONLY these fields:

"era": EXACT name from this list:
{era_prompt}
"decade": e.g. "1780s", "1920s", "2010s" or null
"culture": cultural/geographic origin (e.g. "French", "Japanese", "American") or null
"material": Primary fabric — refine if provided in input (e.g. "silk" → "silk taffeta")
"colors": 2-4 specific colors visible (e.g. ["navy blue", "cream"])
"garment_type": Natural language (e.g. "bustle evening gown", "tailored riding jacket")
"fit_style": Fit description (e.g. "corseted fitted", "flowing draped")
"occasion": e.g. "formal evening", "everyday wear", "garden party"

"ai_description": 80-120 words. Describe what you see: silhouette, construction, materials, surface treatment, and how the garment relates to its era and culture. Be specific about physical details — the width of a lapel, the weight of a fabric, the geometry of a cut. Do NOT use aesthetic axis terms (e.g. do not write "Exaggerated Volume" or "Bare Surface"). Do NOT use generic praise ("stunning", "elegant", "beautiful"). Write for someone who cannot see the garment.

=== CROSS-CULTURAL BRIDGE FIELDS ===

"construction_technique": Array of 1-3: hand-embroidery | machine-embroidery | hand-weaving | machine-weaving | knitting | crocheting | felting | draping | tailoring | resist-dyeing | block-printing | screen-printing | digital-printing | batik | tie-dye | quilting | smocking | pleating | lacework | beadwork | applique | tapestry | brocade-weaving | jacquard-weaving | hand-sewing | couture-construction | leather-working | metalwork | null
"social_function": Array of 1-2: wedding | mourning | religious-ceremonial | court-formal | military-uniform | status-signaling | everyday-practical | workwear | sportswear | performance-costume | coming-of-age | festival-celebration | diplomatic-gift | academic-formal | protest-subculture | leisure-resort (or your own concise label). Use ["none"] only if truly none applies.
"motif_family": Array of 1-3: geometric | floral | paisley | chevron-zigzag | spiral-scroll | animal-figurative | bird-figurative | mythological | calligraphic | lattice-trellis | medallion | stripe-band | dot-spot | tree-of-life | cloud-wave | star-celestial | heraldic | abstract-organic | none

=== KNOWLEDGE GRAPH FIELDS ===

"designer": Designer, maker, or design house name. String or null.
"influence_references": Array of 1-3 specific historical/cultural references (e.g. ["1890s leg-of-mutton sleeve", "Japanese obi wrapping"]). Null if none.
"production_mode": haute couture | ready-to-wear | handmade | mass-produced | one-of-a-kind | artisan-craft | null
"material_origin": Geographic origin of the primary textile (distinct from garment culture). String or null.
"garment_system": Array of garments this piece requires/implies (e.g. ["corset", "chemise", "petticoat"]). Null if self-contained.
"named_movements": Array of 1-2 design/cultural movements beyond the era label (e.g. ["Japonisme", "Aesthetic Movement"]). Null if none.

"low_confidence_fields": Array of field names where you are uncertain. Use [] if confident in all.

If a field cannot be determined, use null. Do not guess. Return ONLY valid JSON."""

    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


SYSTEM_PROMPT = build_system_prompt()


def build_user_prompt(product):
    """Build per-product user message — just the item details."""
    prompt = f"""Analyze this item and return the JSON specified in your instructions.

**Item Details (from museum/source records — may be incomplete or inaccurate):**
- Title: {product.title}
- Source category: {product.category or ''}"""

    if product.object_date:
        prompt += f"\n- Date: {product.object_date}"
    if product.era:
        prompt += f"\n- Era: {product.era}"
    if product.culture:
        prompt += f"\n- Culture: {product.culture}"
    if product.material:
        prompt += f"\n- Material: {product.material}"
    if product.color:
        prompt += f"\n- Color: {product.color}"
    if product.pattern:
        prompt += f"\n- Pattern: {product.pattern}"

    return prompt


def apply_results(product, enrichment, enricher):
    """Write creative + KG enrichment to product. Returns True on success."""
    if not enrichment.get('ai_description'):
        return False

    # Creative fields
    product.ai_description = enrichment.get('ai_description')
    product.garment_type = enrichment.get('garment_type') or product.garment_type
    product.fit_style = enrichment.get('fit_style') or product.fit_style
    product.occasion = enrichment.get('occasion') or product.occasion
    product.material = enrichment.get('material') or product.material
    if enrichment.get('culture'):
        product.culture = enrichment['culture']
    if enrichment.get('colors'):
        product.colors = json.dumps(enrichment['colors'])

    # Cross-cultural fields
    for field in ('construction_technique', 'social_function', 'motif_family'):
        val = enrichment.get(field)
        if val and isinstance(val, list):
            setattr(product, field, json.dumps(val))
        elif val and val != 'null':
            setattr(product, field, json.dumps([val]))

    # KG fields
    product.designer = enrichment.get('designer')
    if enrichment.get('influence_references') and isinstance(enrichment['influence_references'], list):
        product.influence_references = json.dumps(enrichment['influence_references'])
    product.production_mode = enrichment.get('production_mode')
    product.material_origin = enrichment.get('material_origin')
    if enrichment.get('garment_system') and isinstance(enrichment['garment_system'], list):
        product.garment_system = json.dumps(enrichment['garment_system'])
    if enrichment.get('named_movements') and isinstance(enrichment['named_movements'], list):
        product.named_movements = json.dumps(enrichment['named_movements'])
    if enrichment.get('low_confidence_fields') is not None:
        product.low_confidence_fields = json.dumps(enrichment['low_confidence_fields'])

    # Rebuild enriched_text with new data
    full_enrichment = {
        'ai_description': product.ai_description,
        'garment_type': product.garment_type,
        'nickname': product.nickname,
        'era': product.era,
        'decade': product.decade,
        'material': product.material,
        'colors': json.loads(product.colors) if product.colors else [],
        'silhouette': product.silhouette,
        'neckline': product.neckline,
        'length': product.length,
        'waistline': product.waistline,
        'sleeve_length': product.sleeve_length,
        'style_tags': json.loads(product.style_tags) if product.style_tags else [],
        'vibe_scores': product.vibe_scores,
        'fit_style': product.fit_style,
        'textile_pattern': product.textile_pattern,
        'textile_finishing': product.textile_finishing,
        'occasion': product.occasion,
        'decorations': product.decorations,
        'construction_technique': product.construction_technique,
        'social_function': product.social_function,
        'motif_family': product.motif_family,
        'designer': product.designer,
        'influence_references': product.influence_references,
        'named_movements': product.named_movements,
    }
    product.enriched_text = enricher.build_rich_text(
        product_data={'title': product.title, 'category': product.category},
        enrichment=full_enrichment
    )

    product.enriched_at = datetime.now()
    return True


def parse_response(response_text):
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    return json.loads(json_str)


async def enrich_one(semaphore, async_client, product_id, content, counter, total):
    async with semaphore:
        try:
            response = await async_client.messages.create(
                model=MODEL,
                max_tokens=800,  # Smaller — no structural fields in output
                temperature=0.4,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            done = counter['done'] = counter['done'] + 1
            if done % 25 == 0 or done == total:
                elapsed = time.time() - counter['start']
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [{done:>5}/{total}] {rate:.1f} req/s  ETA {eta:.0f}s")
            return product_id, response.content[0].text, None
        except Exception as e:
            counter['errors'] = counter['errors'] + 1
            counter['done'] = counter['done'] + 1
            print(f"    [{product_id}] error: {str(e)[:80]}")
            return product_id, None, str(e)


async def run_async(requests, concurrency):
    async_client = anthropic.AsyncAnthropic(max_retries=3)
    semaphore = asyncio.Semaphore(concurrency)
    counter = {'done': 0, 'errors': 0, 'start': time.time()}
    total = len(requests)

    tasks = [
        enrich_one(semaphore, async_client, pid, content, counter, total)
        for pid, content in requests
    ]

    results = await asyncio.gather(*tasks)
    await async_client.close()
    return results


def main(limit=None, concurrency=10):
    db = SessionLocal()
    enricher = ClaudeEnricher()

    query = db.query(Product).filter(Product.enriched_at != None)
    if limit:
        query = query.limit(limit)
    products = query.all()

    if not products:
        print("No enriched products found.")
        db.close()
        return

    print(f"\n{'=' * 70}")
    print(f"CREATIVE + KG RE-ENRICHMENT — {concurrency} concurrent")
    print(f"{'=' * 70}")
    print(f"\n  Products: {len(products)}")
    print(f"  Fields: ai_description, culture, construction_technique, social_function,")
    print(f"          motif_family, designer, influence_references, production_mode,")
    print(f"          material_origin, garment_system, named_movements, low_confidence_fields")
    print(f"  Skipping: structural fields (already correct), vibes (already backfilled)")

    # Smaller output = cheaper
    estimated_cost = len(products) * 0.012  # ~$0.012 per call (no structural output, cached system)
    estimated_time = len(products) / (concurrency * 0.8) / 60
    print(f"\n  Estimated cost: ~${estimated_cost:.2f}")
    print(f"  Estimated time: ~{estimated_time:.0f} min")

    if '--yes' not in sys.argv:
        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

    # Build requests
    requests = []
    for product in products:
        prompt = build_user_prompt(product)
        content = enricher._build_image_content(product.primary_image)
        content.append({"type": "text", "text": prompt})
        requests.append((product.id, content))

    # Phase 1: async API calls
    print(f"\n  Phase 1: Sending {len(requests)} API requests...")
    start = time.time()
    results = asyncio.run(run_async(requests, concurrency))
    api_elapsed = time.time() - start
    print(f"  API calls complete in {api_elapsed:.0f}s")

    # Phase 2: write results — fresh session
    try:
        db.close()
    except Exception:
        pass
    db = SessionLocal()

    print(f"\n  Phase 2: Writing results to DB...")
    process_start = time.time()
    success = 0
    failed = 0

    for product_id, response_text, error in results:
        product = db.get(Product, product_id)

        if error:
            failed += 1
            continue

        try:
            enrichment = parse_response(response_text)
        except json.JSONDecodeError:
            failed += 1
            continue

        if apply_results(product, enrichment, enricher):
            success += 1
        else:
            failed += 1

        if success % 100 == 0 and success > 0:
            db.commit()
            print(f"    {success} written ({time.time() - process_start:.0f}s)")

    db.commit()
    total_elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print(f"RE-ENRICHMENT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Succeeded: {success}")
    print(f"  Failed:    {failed}")
    print(f"  API time:  {api_elapsed:.0f}s")
    print(f"  Total:     {total_elapsed:.0f}s")
    print(f"\n  Next: rebuild embeddings (enriched_text changed)")

    db.close()


if __name__ == '__main__':
    limit_val = None
    concurrency_val = 10

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=', 1)[1])
        elif arg.startswith('--concurrency='):
            concurrency_val = int(arg.split('=', 1)[1])

    main(limit=limit_val, concurrency=concurrency_val)
