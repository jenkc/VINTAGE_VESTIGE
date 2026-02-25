"""
Load modern items (1900-2025) from Met Museum Costume Institute.
Three tiers:
  - 2010-2025: ALL items with images
  - 1900-1980: 200 items with images
  - 1980-2010: 100 items with images
"""

import requests
from storage.database import SessionLocal, Product
import json
import base64
from io import BytesIO
from PIL import Image
import time
import random

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
SESSION = requests.Session()


def search_costume_by_date(date_begin, date_end):
    """Search Costume Institute for items in a date range"""
    resp = SESSION.get(f"{BASE_URL}/search", params={
        'departmentIds': 8,
        'dateBegin': date_begin,
        'dateEnd': date_end,
        'q': '*',
    })
    data = resp.json()
    ids = data.get('objectIDs') or []
    print(f"  {date_begin}-{date_end}: {len(ids)} objects found")
    return ids


def fetch_object(obj_id):
    """Fetch object metadata"""
    try:
        resp = SESSION.get(f"{BASE_URL}/objects/{obj_id}", timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def download_image(url):
    """Download and resize image to data URL"""
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
    for decade in range(1900, 2030, 10):
        if str(decade) in date_str:
            return f'{decade}s'
    if '19th century' in date_str.lower():
        return '1800s'
    if '18th century' in date_str.lower():
        return '1700s'
    return None


def obj_to_product(obj, image_data):
    """Convert Met object to Product dict"""
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


def load_tier(db, existing, obj_ids, max_items, tier_label):
    """Load items from a list of object IDs, up to max_items"""
    print(f"\n{'=' * 60}")
    print(f"  {tier_label}")
    print(f"  Scanning {len(obj_ids)} objects, target: {'ALL with images' if max_items is None else max_items}")
    print(f"{'=' * 60}")

    random.shuffle(obj_ids)
    stored = 0
    scanned = 0
    no_image = 0

    for obj_id in obj_ids:
        if max_items is not None and stored >= max_items:
            break

        if f'met_{obj_id}' in existing:
            continue

        obj = fetch_object(obj_id)
        scanned += 1
        time.sleep(0.5)

        if not obj:
            no_image += 1
            if scanned % 50 == 0:
                print(f"  scanned {scanned} — stored {stored} — {no_image} skipped")
            continue

        # Verify this is actually a Costume Institute item
        if obj.get('department') != 'Costume Institute':
            if scanned % 50 == 0:
                print(f"  scanned {scanned} — stored {stored} — {no_image} skipped")
            continue

        if not obj.get('primaryImage'):
            no_image += 1
            if scanned % 50 == 0:
                print(f"  scanned {scanned} — stored {stored} — {no_image} skipped")
            continue

        image_data = download_image(obj['primaryImage'])
        time.sleep(0.3)

        if not image_data:
            continue

        product_data = obj_to_product(obj, image_data)
        try:
            db.add(Product(**product_data))
            db.commit()
            existing.add(f'met_{obj_id}')
            stored += 1
            date = product_data.get('object_date', '?')
            print(f"  [{stored}] {product_data['title'][:50]} ({date})")
        except Exception as e:
            db.rollback()
            print(f"  DB error: {e}")

    print(f"\n  {tier_label} done: stored {stored} (scanned {scanned}, {no_image} without images)")
    return stored


def load_met_modern():
    print("\n" + "=" * 60)
    print("LOADING MODERN ITEMS FROM MET COSTUME INSTITUTE")
    print("=" * 60)

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'met_museum'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    # Get IDs for each tier
    print("\nSearching Met API by date range...")
    ids_2010 = search_costume_by_date(2010, 2025)
    ids_1900 = search_costume_by_date(1900, 1980)
    ids_1980 = search_costume_by_date(1980, 2010)

    total = 0

    # Tier 1: 2010-2025 — get ALL with images
    total += load_tier(db, existing, ids_2010, max_items=None, tier_label="2010-2025 (ALL with images)")

    # Tier 2: 1900-1980 — get 200
    total += load_tier(db, existing, ids_1900, max_items=200, tier_label="1900-1980 (200 items)")

    # Tier 3: 1980-2010 — get 100
    total += load_tier(db, existing, ids_1980, max_items=100, tier_label="1980-2010 (100 items)")

    # Summary
    all_count = db.query(Product).count()
    met_count = db.query(Product).filter(Product.platform == 'met_museum').count()

    print(f"\n{'=' * 60}")
    print(f"LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items loaded: {total}")
    print(f"  Total Met items: {met_count}")
    print(f"  Total in database: {all_count}")

    db.close()


if __name__ == '__main__':
    load_met_modern()
