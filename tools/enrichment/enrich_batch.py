"""
Batch enrichment using Claude Message Batches API.

50% cost reduction vs sequential API calls.
Submits all unenriched products as a single batch, polls for completion,
then writes results back to the database.

Usage:
  python enrichment/enrich_batch.py [--limit=N]        # Submit new batch
  python enrichment/enrich_batch.py --poll=BATCH_ID     # Check/process existing batch
  python enrichment/enrich_batch.py --yes [--limit=N]   # Skip confirmation

Run from project root.
"""
import sys
import os
import json
import time
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import anthropic
from dotenv import load_dotenv
load_dotenv()

from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator
from enrichment.claude import ClaudeEnricher, VIBE_VOCABULARY
from enrichment.era_taxonomy import (
    normalize_era, build_era_prompt_section,
    report_unrecognized_eras, export_unrecognized_eras,
)


SYSTEM_PROMPT = (
    "You are enriching a historical fashion record for Vintage Vestige, "
    "a knowledge graph that connects museum archival pieces to modern fashion. "
    "You are a fashion historian and vintage style expert. "
    "Return only valid JSON, no markdown."
)

MODEL = "claude-sonnet-4-20250514"


def build_batch_requests(products, enricher):
    """Build list of batch request dicts for the Batches API."""
    requests = []

    for product in products:
        has_expert = (
            product.platform == 'fashionpedia' and product.fp_category is not None
        )

        if has_expert:
            # Creative-only path
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

            prompt = f"""Analyze this fashion item and provide CREATIVE metadata for search discovery.

**Item:** {product.title}
**Category:** {product.category or product.fp_category or ''}

**Already-annotated structural attributes (expert-labeled, do NOT change these):**
{chr(10).join(struct_context) if struct_context else '(none)'}

Based on the image and attributes above, provide the creative/search-bridge fields AND any missing structural fields.
Think about: What modern aesthetic does this evoke? What would someone searching for this style type?

Return ONLY valid JSON with these fields:

=== MISSING STRUCTURAL FIELDS (infer from image, or null if not visible/applicable) ===

"silhouette": Pick ONE or null: a-line | pencil | straight | fit and flare | flare | trumpet | mermaid | balloon | bell | wide leg | peg | tent | tight fit | regular fit | loose fit | oversized
"neckline": Pick ONE or null: v-neck | crew neck | round neck | boat neck | scoop neck | square neckline | sweetheart | plunging | keyhole | halter neck | off-the-shoulder | one shoulder | turtle neck | cowl neck | high neck | collarless | surplice | u-neck | straight across
"waistline": Pick ONE or null: empire waistline | high waist | normal waist | low waist | dropped waistline | no waistline
"length": Pick ONE or null: above-the-hip | hip length | mini | above-the-knee | knee length | below the knee | midi | maxi | floor length
"sleeve_length": Pick ONE or null: sleeveless | short | elbow-length | three quarter | wrist-length
"opening_type": Pick ONE or null: single breasted | double breasted | zip-up | wrapping | lace up | no opening
"textile_pattern": Pick ONE: plain | floral | stripe | check | dot | geometric | paisley | abstract | houndstooth | herringbone | leopard | toile de jouy
"textile_finishing": Array of 0-3: distressed | quilted | pleated | ruched | cutout | slit | tiered | smocking | gathering | beaded | sequined | applique
"garment_parts": Array: hood | collar | lapel | epaulette | sleeve | pocket | buckle | zipper
"decorations": Array: applique | bead | bow | flower | fringe | ribbon | rivet | ruffle | sequin | tassel

=== CREATIVE / SEARCH-BRIDGE FIELDS ===

  "era": "EXACT name from taxonomy:\n""" + build_era_prompt_section() + """",
  "decade": "e.g. 2010s, 2020s, or null",
  "culture": "cultural/geographic influence (e.g. Western, Japanese, South Asian, African, Korean) or null",
  "style_tags": ["3-5 modern aesthetic tags"],
  "colors": ["2-4 specific colors"],
  "material": "primary fabric",
  "season": "spring/summer | fall/winter | all-season",
  "garment_type": "natural language (e.g. fitted blazer, flowy sundress)",
  """ + VIBE_VOCABULARY + """
  "core_vibes": ["1-3 terms from controlled vocabulary above"],
  "bridge_vibes": ["1-2 terms most likely to connect across eras"],
  "vibe_scores": {{"term": confidence_float}},
  "fit_style": "fit description (e.g. relaxed oversized, structured tailored)",
  "occasion": "e.g. everyday casual, date night, office",
  "ai_description": 100-150 words placing this piece in context, using assigned vibe terms. Specificity matters more than prose quality.
"""
        else:
            # Full enrichment path
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

        # Build content with image
        content = enricher._build_image_content(product.primary_image)
        content.append({"type": "text", "text": prompt})

        requests.append({
            "custom_id": str(product.id),
            "params": {
                "model": MODEL,
                "max_tokens": 1200,
                "temperature": 0.4,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": content}],
            }
        })

    return requests


def submit_batch(limit=None):
    """Submit a batch of unenriched products to the Batches API."""
    db = SessionLocal()
    enricher = ClaudeEnricher()
    client = anthropic.Anthropic()

    # Get unenriched products
    query = db.query(Product).filter(Product.enriched_at == None)
    if limit:
        query = query.limit(limit)
    products = query.all()

    if not products:
        print("No unenriched products found.")
        db.close()
        return None

    # Show breakdown
    by_platform = {}
    for p in products:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1

    print(f"\nProducts to enrich: {len(products)}")
    for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"  {platform:20s} {count:4d}")

    # Batch API = 50% discount
    estimated_cost = len(products) * 0.025 * 0.50
    print(f"\nEstimated cost (50% batch discount): ~${estimated_cost:.2f}")

    if '--yes' not in sys.argv:
        confirm = input("\nSubmit batch? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return None

    print("\nBuilding batch requests...")
    requests = build_batch_requests(products, enricher)
    print(f"  Built {len(requests)} requests")

    print("Submitting to Batches API...")
    batch = client.messages.batches.create(requests=requests)

    print(f"\n  Batch ID: {batch.id}")
    print(f"  Status:   {batch.processing_status}")
    print(f"\nSave this batch ID! To check status / process results:")
    print(f"  python enrichment/enrich_batch.py --poll={batch.id}")

    db.close()
    return batch.id


def poll_and_process(batch_id):
    """Poll a batch for completion and process results into the database."""
    client = anthropic.Anthropic()
    enricher = ClaudeEnricher()

    print(f"\nPolling batch: {batch_id}")

    # Poll until done
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        total = counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired

        print(f"  Status: {batch.processing_status}  "
              f"({counts.succeeded} succeeded, {counts.errored} errored, "
              f"{counts.processing} processing / {total} total)")

        if batch.processing_status == "ended":
            break

        print("  Waiting 30s...")
        time.sleep(30)

    # Process results
    print(f"\nProcessing {counts.succeeded} results...")

    db = SessionLocal()
    generator = EmbeddingGenerator()

    success_count = 0
    failed_count = 0
    non_garment_count = 0

    for result in client.messages.batches.results(batch_id):
        product_id = int(result.custom_id)

        if result.result.type != "succeeded":
            print(f"  [{product_id}] {result.result.type}")
            failed_count += 1
            continue

        response_text = result.result.message.content[0].text

        # Parse JSON
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        try:
            enrichment = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  [{product_id}] JSON parse error: {e}")
            failed_count += 1
            continue

        # Check for meaningful content
        has_content = (
            enrichment.get('era') or
            enrichment.get('fp_category') or
            enrichment.get('garment_type')
        )
        if not has_content:
            non_garment_count += 1
            continue

        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            print(f"  [{product_id}] Product not found in DB")
            failed_count += 1
            continue

        # Build rich text and embedding
        rich_text = enricher.build_rich_text(
            product_data={'title': product.title, 'category': product.category},
            enrichment=enrichment
        )
        new_text_embedding = generator.generate_text_embedding(rich_text)
        product.text_embedding = new_text_embedding.tolist()

        # Write all fields
        product.era = normalize_era(enrichment.get('era'), product_id=product.id)
        product.decade = enrichment.get('decade')
        if enrichment.get('culture'):
            product.culture = enrichment['culture']
        product.style_tags = json.dumps(enrichment.get('style_tags', []))
        product.colors = json.dumps(enrichment.get('colors', []))
        product.material = enrichment.get('material')
        product.pattern = enrichment.get('pattern')
        product.garment_type = enrichment.get('garment_type')
        product.vibe = enrichment.get('vibe')
        product.core_vibes = enrichment.get('core_vibes')
        product.bridge_vibes = enrichment.get('bridge_vibes')
        product.vibe_scores = enrichment.get('vibe_scores')
        product.fit_style = enrichment.get('fit_style')
        product.occasion = enrichment.get('occasion')
        product.ai_description = enrichment.get('ai_description')
        product.enriched_text = rich_text
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
        product.enriched_at = datetime.now()

        success_count += 1

        if success_count % 100 == 0:
            db.commit()
            print(f"  Processed {success_count}...")

    db.commit()

    print(f"\n{'=' * 70}")
    print("BATCH ENRICHMENT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Succeeded:    {success_count}")
    print(f"  Failed:       {failed_count}")
    print(f"  Non-garments: {non_garment_count}")
    print(f"  API errors:   {counts.errored}")

    report_unrecognized_eras()
    export_unrecognized_eras()

    db.close()


if __name__ == '__main__':
    # Parse args
    poll_id = None
    limit_val = None

    for arg in sys.argv[1:]:
        if arg.startswith('--poll='):
            poll_id = arg.split('=', 1)[1]
        elif arg.startswith('--limit='):
            limit_val = int(arg.split('=', 1)[1])

    if poll_id:
        poll_and_process(poll_id)
    else:
        submit_batch(limit=limit_val)
