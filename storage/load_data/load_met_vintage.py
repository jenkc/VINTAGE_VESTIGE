"""
Load real vintage fashion from Met Museum's Costume Institute.

Two-phase approach:
  1. Scan metadata to find Costume Institute objects with images
  2. Download images only for the ones that have them
"""

import sys
import os

from storage.image_storage import upload_product_image

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import requests
from storage.database import SessionLocal, Product
from enrichment.era_taxonomy import year_to_era
import json
import random
from io import BytesIO
from PIL import Image
import time


BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
SESSION = requests.Session()


def get_all_costume_ids():
    """Get all Costume Institute object IDs"""
    print("Fetching Costume Institute catalog...")
    data = SESSION.get(f"{BASE_URL}/objects", params={'departmentIds': 8}).json()
    ids = data.get('objectIDs') or []
    print(f"{len(ids)} objects in Costume Institute")
    return ids


errors = {'timeout': 0, 'http': 0, 'other': 0}


def fetch_object(obj_id):
    """Fetch object metadata. Returns dict or None."""
    try:
        resp = SESSION.get(f"{BASE_URL}/objects/{obj_id}", timeout=10)
        if resp.status_code != 200:
            errors['http'] += 1
            return None
        return resp.json()
    except requests.exceptions.Timeout:
        errors['timeout'] += 1
        return None
    except Exception:
        errors['other'] += 1
        return None


def download_image(url, storage_key):
    """Download image , upload to Supabase Storage, return public URL."""
    try:
        resp = SESSION.get(url, timeout=15)
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        img.thumbnail((400, 400))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return upload_product_image(storage_key, buf.getvalue())
    except Exception:
        return None
    

# year_to_era imported from enrichment.era_taxonomy

def extract_date_fields(obj):
    """Extract decade, era, and object_date from Met API numeric + string date fields.

    Uses objectBeginDate/objectEndDate (integers) for reliable decade/era,
    falls back to objectDate (string) parsing if numeric fields are missing.
    """
    begin = obj.get('objectBeginDate')
    end = obj.get('objectEndDate')
    date_str = obj.get('objectDate', '')

    decade = None
    era = None
    object_date = date_str if date_str else None

    if isinstance(begin, (int, float)) and isinstance(end, (int, float)):
        mid_year = int((begin + end) / 2)
        decade = f'{(mid_year // 10) * 10}s'
        era = year_to_era(mid_year)
    elif date_str:
        # Fallback: try parsing the string
        import re
        m = re.search(r'(\d{4})', date_str)
        if m:
            year = int(m.group(1))
            decade = f'{(year // 10) * 10}s'
            era = year_to_era(year)
        else:
            # Handle century references like "Late 18th Century"
            m = re.search(r'(\d{1,2})(?:st|nd|rd|th)\s+century', date_str, re.IGNORECASE)
            if m:
                century = int(m.group(1))
                mid_year = (century - 1) * 100 + 50
                if 'late' in date_str.lower():
                    mid_year += 25
                elif 'early' in date_str.lower():
                    mid_year -= 25
                decade = f'{(mid_year // 10) * 10}s'
                era = year_to_era(mid_year)

    return era, decade, object_date


def obj_to_product(obj, image_data):
    """Convert Met object + already-downloaded image to Product dict."""
    title = obj.get('title', 'Vintage Item')
    date = obj.get('objectDate', '')
    period = obj.get('period', '')
    medium = obj.get('medium', '')
    culture = obj.get('culture', '')
    name = obj.get('objectName', 'clothing')

    era, decade, object_date = extract_date_fields(obj)

    desc_parts = [p for p in [
        name,
        f"Period: {period}" if period else None,
        f"Date: {date}" if date else None,
        f"Culture: {culture}" if culture else None,
        f"Materials: {medium}" if medium else None,
    ] if p]

    return {
        'external_id': f'met_{obj["objectID"]}',
        'platform': 'met_museum',
        'title': title[:255],
        'description': " | ".join(desc_parts)[:500],
        'price': 0.0,
        'currency': 'USD',
        'primary_image': image_data,
        'image_urls': json.dumps([image_data]),
        'seller_name': 'Metropolitan Museum',
        'seller_url': obj.get('objectURL', ''),
        'url': obj.get('objectURL', ''),
        'category': name,
        'garment_type': name if name else None,
        'material': medium if medium else None,
        'era': era or period or None,
        'decade': decade,
        'object_date': object_date,
        'culture': culture if culture else None,
        'period': period if period else None,
        'style_tags': json.dumps([p for p in [period, culture] if p]),
    }


def load_met_vintage(num_items=400, max_per_era_pct=0.25):
    print("\n" + "=" * 60)
    print("LOADING VINTAGE FROM MET MUSEUM COSTUME INSTITUTE")
    print("=" * 60 + "\n")

    max_per_era = max(5, int(num_items * max_per_era_pct))
    print(f"Era diversity cap: max {max_per_era} items per era ({max_per_era_pct:.0%})")

    all_ids = get_all_costume_ids()
    random.shuffle(all_ids)

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'met_museum'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    candidate_ids = [i for i in all_ids if f'met_{i}' not in existing]

    # Phase 1: Scan metadata sequentially to find objects with images
    # Apply era quotas to ensure diverse date coverage
    print(f"\nPhase 1: Scanning objects for image availability (sequential, ~2 req/sec)...")
    has_image = []
    era_counts = {}
    skipped_era = 0
    scanned = 0

    for obj_id in candidate_ids:
        if len(has_image) >= num_items:
            print(f"\n  Found enough!")
            break

        obj = fetch_object(obj_id)
        scanned += 1
        time.sleep(0.5)

        if obj and obj.get('department') == 'Costume Institute' and obj.get('primaryImage'):
            era, _, _ = extract_date_fields(obj)
            era_key = era or 'Unknown'

            if era_counts.get(era_key, 0) >= max_per_era:
                skipped_era += 1
                continue

            has_image.append(obj)
            era_counts[era_key] = era_counts.get(era_key, 0) + 1

        if scanned % 50 == 0:
            print(f"  scanned {scanned} — {len(has_image)} accepted, {skipped_era} skipped (era cap) | errors: {dict(errors)}")

    print(f"\nPhase 1 done: {len(has_image)} objects accepted (scanned {scanned}, {skipped_era} skipped for era diversity)")
    print(f"Era distribution: {dict(sorted(era_counts.items(), key=lambda x: -x[1]))}")

    if not has_image:
        print("No objects with images found!")
        db.close()
        return

    # Phase 2: Download images and store
    print(f"\nPhase 2: Downloading {len(has_image)} images and storing...")
    stored = 0

    for obj in has_image:
        if stored >= num_items:
            break

        image_data = download_image(obj['primaryImage'], f'met_{obj["objectID"]}')
        time.sleep(0.5)

        if image_data is None:
            continue

        product_data = obj_to_product(obj, image_data)
        try:
            db.add(Product(**product_data))
            db.commit()
            stored += 1
            print(f"  [{stored}/{num_items}] {product_data['title'][:50]} ({product_data.get('era', '?')})")
        except Exception as e:
            db.rollback()
            print(f"  DB error: {e}")

    db.close()
    print(f"\nDone! Loaded {stored} items")


if __name__ == '__main__':
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    
    load_met_vintage(num_items=num)
