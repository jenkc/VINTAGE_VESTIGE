"""
Load fashion items from the Fashionpedia dataset.

Downloads the annotation JSON, filters to commercially-safe images,
maps Fashionpedia category/attribute IDs to our Product schema,
and downloads images from their original URLs.

Dataset: https://fashionpedia.github.io/home/Fashionpedia_download.html
License: CC BY 4.0 (annotations/ontology), mixed image licenses
"""

import sys
import os
from storage.image_storage import upload_product_image

# Ensure project root is first in path so local storage/ is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
import json
import time
import random
from io import BytesIO
from PIL import Image
from collections import defaultdict
from datetime import datetime

from storage.database import SessionLocal, Product
from enrichment.fashionpedia_taxonomy import (
    CATEGORY_BY_ID, ATTRIBUTE_BY_ID,
    GARMENT_PARTS, CLOSURES, DECORATIONS,
)

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'VintageVestige/1.0 (fashion research project)'
})

ANNOTATIONS_URL = "https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_train2020.json"
ANNOTATIONS_CACHE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'fashionpedia_train2020.json')

# License IDs that are commercially safe
SAFE_LICENSE_IDS = {0, 1, 6, 7, 8, 9, 10}

# Garment part category IDs (27-33)
GARMENT_PART_IDS = {p['id'] for p in GARMENT_PARTS}
# Closure category IDs (34-35)
CLOSURE_IDS = {p['id'] for p in CLOSURES}
# Decoration category IDs (36-45)
DECORATION_IDS = {p['id'] for p in DECORATIONS}
# Main apparel category IDs (0-26)
MAIN_APPAREL_IDS = set(range(27))


def download_annotations():
    """Download and cache the annotations JSON."""
    cache_path = os.path.abspath(ANNOTATIONS_CACHE)
    cache_dir = os.path.dirname(cache_path)

    if os.path.exists(cache_path):
        print(f"Using cached annotations: {cache_path}")
        with open(cache_path, 'r') as f:
            return json.load(f)

    print(f"Downloading annotations ({ANNOTATIONS_URL})...")
    print("  This is ~50MB, may take a minute...")
    resp = SESSION.get(ANNOTATIONS_URL, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(data, f)
    print(f"  Cached to {cache_path}")

    return data


def download_image(url, storage_key):
    """Download image, upload to Supabase Storage, return public URL."""
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        img.thumbnail((400, 400))

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return upload_product_image(storage_key, buf.getvalue())

    except Exception:
        return None



def map_annotations_to_fields(annotations):
    """
    Map a list of Fashionpedia annotations for one image to our Product fields.

    Each annotation has category_id and attribute_ids[].
    We pick the primary (largest) main apparel annotation and aggregate parts/decorations.
    """
    # Separate main apparel annotations from parts/decorations
    main_annotations = []
    part_names = []
    decoration_names = []

    for ann in annotations:
        cat_id = ann['category_id']
        if cat_id in MAIN_APPAREL_IDS:
            # Estimate area from segmentation if available
            area = ann.get('area', 0)
            main_annotations.append((area, ann))
        elif cat_id in GARMENT_PART_IDS:
            cat_info = CATEGORY_BY_ID.get(cat_id)
            if cat_info:
                part_names.append(cat_info['name'])
        elif cat_id in DECORATION_IDS:
            cat_info = CATEGORY_BY_ID.get(cat_id)
            if cat_info:
                decoration_names.append(cat_info['name'])

    if not main_annotations:
        return None

    # Pick the largest main apparel annotation as primary
    main_annotations.sort(key=lambda x: x[0], reverse=True)
    _, primary = main_annotations[0]

    cat_id = primary['category_id']
    cat_info = CATEGORY_BY_ID.get(cat_id, {})
    attr_ids = primary.get('attribute_ids', [])

    # Map attributes by supercategory
    fields = {
        'fp_category': None,
        'nickname': None,
        'silhouette': None,
        'neckline': None,
        'waistline': None,
        'length': None,
        'sleeve_length': None,
        'opening_type': None,
        'textile_pattern': None,
        'textile_finishing': [],
        'garment_parts': list(set(part_names)),
        'decorations': list(set(decoration_names)),
    }

    # fp_category from category_id
    fp_cat_name = cat_info.get('name', '')
    # Map to our fp_category format (pick first name for combo categories)
    fields['fp_category'] = fp_cat_name.split(',')[0].strip() if fp_cat_name else None

    # Garment length vs sleeve length distinction
    # Length IDs 146-155 are garment lengths, 156-160 are sleeve lengths
    GARMENT_LENGTH_IDS = set(range(146, 156))
    SLEEVE_LENGTH_IDS = set(range(156, 161))

    for attr_id in attr_ids:
        attr_info = ATTRIBUTE_BY_ID.get(attr_id)
        if not attr_info:
            continue

        supcat = attr_info['supercategory']
        name = attr_info['name']

        # Clean name: strip parenthetical qualifiers
        clean_name = name.split(' (')[0].strip()

        if supcat == 'nickname' and not fields['nickname']:
            fields['nickname'] = clean_name
        elif supcat == 'silhouette' and not fields['silhouette']:
            fields['silhouette'] = clean_name
        elif supcat == 'neckline type' and not fields['neckline']:
            fields['neckline'] = clean_name
        elif supcat == 'waistline' and not fields['waistline']:
            fields['waistline'] = clean_name
        elif supcat == 'length':
            if attr_id in SLEEVE_LENGTH_IDS and not fields['sleeve_length']:
                fields['sleeve_length'] = clean_name
            elif attr_id in GARMENT_LENGTH_IDS and not fields['length']:
                fields['length'] = clean_name
        elif supcat == 'opening type' and not fields['opening_type']:
            fields['opening_type'] = clean_name
        elif supcat == 'textile pattern' and not fields['textile_pattern']:
            fields['textile_pattern'] = clean_name
        elif supcat == 'textile finishing, manufacturing techniques':
            if clean_name not in ('no special manufacturing technique', 'lining'):
                fields['textile_finishing'].append(clean_name)

    # Also aggregate attributes from secondary main annotations
    for _, ann in main_annotations[1:]:
        for attr_id in ann.get('attribute_ids', []):
            attr_info = ATTRIBUTE_BY_ID.get(attr_id)
            if not attr_info:
                continue
            supcat = attr_info['supercategory']
            name = attr_info['name'].split(' (')[0].strip()
            if supcat == 'textile finishing, manufacturing techniques':
                if name not in fields['textile_finishing'] and name not in ('no special manufacturing technique', 'lining'):
                    fields['textile_finishing'].append(name)

    return fields


def build_title(fields):
    """Generate a descriptive title from taxonomy fields."""
    # Primary garment name: prefer nickname, fallback to category
    garment = fields.get('nickname') or fields.get('fp_category') or 'item'

    # Add interesting modifiers
    modifiers = []
    if fields.get('textile_pattern') and fields['textile_pattern'] not in ('plain', 'no special manufacturing technique'):
        modifiers.append(fields['textile_pattern'].title())
    if fields.get('silhouette') and fields['silhouette'] not in ('regular', 'symmetrical'):
        modifiers.append(fields['silhouette'].title())
    if fields.get('neckline'):
        modifiers.append(fields['neckline'].title())
    if fields.get('length') and fields.get('length') not in ('above-the-hip',):
        modifiers.append(fields['length'].title())

    # Build: "Floral A-Line Midi Wrap Dress"
    title_parts = modifiers[:3] + [garment.title()]
    return " ".join(title_parts)


def build_description(fields):
    """Generate a description from taxonomy fields."""
    desc_parts = []
    if fields.get('fp_category'):
        desc_parts.append(f"Category: {fields['fp_category']}")
    if fields.get('nickname'):
        desc_parts.append(f"Type: {fields['nickname']}")
    if fields.get('silhouette'):
        desc_parts.append(f"Silhouette: {fields['silhouette']}")
    if fields.get('neckline'):
        desc_parts.append(f"Neckline: {fields['neckline']}")
    if fields.get('length'):
        desc_parts.append(f"Length: {fields['length']}")
    if fields.get('textile_pattern') and fields['textile_pattern'] != 'plain':
        desc_parts.append(f"Pattern: {fields['textile_pattern']}")
    return " | ".join(desc_parts) if desc_parts else None


def load_fashionpedia(num_new=500):
    print("\n" + "=" * 60)
    print("LOADING FASHION FROM FASHIONPEDIA DATASET")
    print("=" * 60 + "\n")

    # Step 1: Download/load annotations
    data = download_annotations()

    images = {img['id']: img for img in data['images']}
    print(f"Total images in dataset: {len(images)}")

    # Group annotations by image_id
    anns_by_image = defaultdict(list)
    for ann in data['annotations']:
        anns_by_image[ann['image_id']].append(ann)

    # Filter to commercially-safe images
    safe_images = [
        img for img in data['images']
        if img.get('license') in SAFE_LICENSE_IDS
    ]
    print(f"Commercially safe images: {len(safe_images)}")

    # Filter to images that have at least one main apparel annotation
    fashion_images = []
    for img in safe_images:
        anns = anns_by_image.get(img['id'], [])
        has_main = any(a['category_id'] in MAIN_APPAREL_IDS for a in anns)
        if has_main:
            fashion_images.append(img)
    print(f"With main apparel annotations: {len(fashion_images)}")

    random.shuffle(fashion_images)

    # Check existing
    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'fashionpedia'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    stored = 0
    skipped_no_url = 0
    skipped_download_fail = 0
    skipped_no_fields = 0

    for i, img in enumerate(fashion_images):
        if stored >= num_new:
            break

        ext_id = f"fp_{img['id']}"
        if ext_id in existing:
            continue

        # Get original URL
        original_url = img.get('original_url', '')
        if not original_url:
            skipped_no_url += 1
            continue

        # Map annotations to fields
        anns = anns_by_image.get(img['id'], [])
        fields = map_annotations_to_fields(anns)
        if not fields:
            skipped_no_fields += 1
            continue

        # Download image
        image_data = download_image(original_url, ext_id)
        if not image_data:
            skipped_download_fail += 1
            continue

        time.sleep(0.3)

        # Build product
        title = build_title(fields)
        description = build_description(fields)

        product_data = {
            'external_id': ext_id,
            'platform': 'fashionpedia',
            'title': title[:255],
            'description': description[:500] if description else None,
            'price': 0.0,
            'currency': 'USD',
            'primary_image': image_data,
            'image_urls': json.dumps([original_url]),
            'seller_name': 'Fashionpedia Dataset',
            'url': original_url,
            'category': fields.get('fp_category'),
            # Fashionpedia taxonomy fields
            'fp_category': fields.get('fp_category'),
            'nickname': fields.get('nickname'),
            'silhouette': fields.get('silhouette'),
            'neckline': fields.get('neckline'),
            'waistline': fields.get('waistline'),
            'length': fields.get('length'),
            'sleeve_length': fields.get('sleeve_length'),
            'opening_type': fields.get('opening_type'),
            'textile_pattern': fields.get('textile_pattern'),
            'textile_finishing': json.dumps(fields.get('textile_finishing', [])),
            'garment_parts': json.dumps(fields.get('garment_parts', [])),
            'decorations': json.dumps(fields.get('decorations', [])),
        }

        try:
            db.add(Product(**product_data))
            db.commit()
            existing.add(ext_id)
            stored += 1
            nickname = fields.get('nickname', '')
            pattern = fields.get('textile_pattern', '')
            print(f"  [{stored}/{num_new}] {title[:50]} ({nickname or pattern or ''})")
        except Exception as e:
            db.rollback()
            print(f"  DB error: {e}")

        # Checkpoint every 50
        if stored % 50 == 0 and stored > 0:
            print(f"\n  --- Checkpoint: {stored}/{num_new} stored ---\n")

    # Summary
    all_count = db.query(Product).count()
    fp_count = db.query(Product).filter(Product.platform == 'fashionpedia').count()

    print(f"\n{'=' * 60}")
    print(f"LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items loaded: {stored}")
    print(f"  Skipped (no URL): {skipped_no_url}")
    print(f"  Skipped (download fail): {skipped_download_fail}")
    print(f"  Skipped (no fashion annotations): {skipped_no_fields}")
    print(f"  Total Fashionpedia items: {fp_count}")
    print(f"  Total in database: {all_count}")

    db.close()


if __name__ == '__main__':
    num_new = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    load_fashionpedia(num_new=num_new)
