"""
Load real vintage fashion from Met Museum's Costume Institute.

Two-phase approach:
  1. Scan metadata to find Costume Institute objects with images
  2. Download images only for the ones that have them
"""

import requests
from storage.database import SessionLocal, Product
import json
import random
import base64
from io import BytesIO
from PIL import Image
import sys
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


def download_image(url):
    """Download image and convert to data URL. Returns data_url or None."""
    try:
        resp = SESSION.get(url, timeout=15)
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        img.thumbnail((400, 400))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return None


def extract_era(date_str):
    """Extract era from Met date string"""
    for decade in ['1920', '1930', '1940', '1950', '1960', '1970', '1980']:
        if decade in date_str:
            return f'{decade}s'
    if '19th century' in date_str.lower():
        return '1800s'
    if '18th century' in date_str.lower():
        return '1700s'
    return None


def obj_to_product(obj, image_data):
    """Convert Met object + already-downloaded image to Product dict."""
    title = obj.get('title', 'Vintage Item')
    date = obj.get('objectDate', '')
    period = obj.get('period', '')
    medium = obj.get('medium', '')
    culture = obj.get('culture', '')
    name = obj.get('objectName', 'clothing')

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
        'era': extract_era(date) or period or None,
        'object_date': date if date else None,
        'culture': culture if culture else None,
        'period': period if period else None,
        'style_tags': json.dumps([p for p in [period, culture] if p]),
    }


def load_met_vintage(num_items=200):
    print("\n" + "=" * 60)
    print("LOADING VINTAGE FROM MET MUSEUM COSTUME INSTITUTE")
    print("=" * 60 + "\n")

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
    print(f"\nPhase 1: Scanning objects for image availability (sequential, ~2 req/sec)...")
    has_image = []
    scanned = 0

    for obj_id in candidate_ids:
        if len(has_image) >= num_items:
            print(f"\n  Found enough!")
            break

        obj = fetch_object(obj_id)
        scanned += 1
        time.sleep(0.5)

        if obj and obj.get('department') == 'Costume Institute' and obj.get('primaryImage'):
            has_image.append(obj)

        if scanned % 50 == 0:
            print(f"  scanned {scanned} — {len(has_image)} with images | errors: {dict(errors)}")

    print(f"\nPhase 1 done: {len(has_image)} objects have images (scanned {scanned})")

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

        image_data = download_image(obj['primaryImage'])
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
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    load_met_vintage(num_items=num)
