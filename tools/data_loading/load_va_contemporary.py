"""
Load contemporary (post-2000) fashion items from V&A Museum.

Targeted pull to fill the gap left by Fashionpedia curation.
Uses keyword searches filtered to year_made_from=2000.

Usage:
  PYTHONPATH=. python tools/data_loading/load_va_contemporary.py          # load 300 items
  PYTHONPATH=. python tools/data_loading/load_va_contemporary.py 500      # load 500 items
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import requests
import re
import json
import random
import time
from io import BytesIO
from PIL import Image
from storage.database import SessionLocal, Product
from storage.image_storage import upload_product_image
from enrichment.era_taxonomy import year_to_era

BASE_URL = "https://api.vam.ac.uk/v2"
FASHION_CATEGORY = "THES48957"
SESSION = requests.Session()
errors = {'timeout': 0, 'http': 0, 'other': 0}

# Contemporary fashion keywords — designed to capture post-2000 fashion
CONTEMPORARY_QUERIES = [
    # Designers active post-2000
    ("Alexander McQueen", 2000, None),
    ("Comme des Garcons", 2000, None),
    ("Prada", 2000, None),
    ("Vivienne Westwood", 2000, None),
    ("Hussein Chalayan", 2000, None),
    ("Rick Owens", 2000, None),
    ("Maison Margiela", 2000, None),
    ("Balenciaga", 2000, None),
    ("Dries Van Noten", 2000, None),
    ("Yohji Yamamoto", 2000, None),
    ("Issey Miyake", 2000, None),
    ("Gareth Pugh", 2000, None),

    # Garment types
    ("dress", 2000, None),
    ("coat", 2000, None),
    ("jacket", 2000, None),
    ("suit", 2000, None),
    ("evening gown", 2000, None),
    ("trousers", 2000, None),
    ("skirt", 2000, None),
    ("blouse", 2000, None),
    ("knitwear", 2000, None),
    ("denim", 2000, None),

    # Movements / styles
    ("streetwear", 2000, None),
    ("sustainable fashion", 2000, None),
    ("athleisure", 2010, None),
    ("minimalist", 2000, None),
    ("avant-garde", 2000, None),
    ("punk", 2000, None),
    ("couture", 2000, None),

    # Cultural / global
    ("African fashion", 2000, None),
    ("Indian fashion", 2000, None),
    ("Chinese fashion", 2000, None),
    ("Japanese fashion", 2000, None),
    ("Korean fashion", 2000, None),
    ("hijab", 2000, None),
    ("modest fashion", 2000, None),

    # Materials / techniques
    ("3D printed", 2000, None),
    ("laser cut", 2000, None),
    ("recycled", 2000, None),
    ("upcycled", 2000, None),

    # General contemporary catch-all
    ("fashion", 2010, None),
    ("fashion", 2015, None),
    ("fashion", 2020, None),
    ("clothing", 2010, None),
    ("clothing", 2015, None),
]

# Object types to skip (non-garments)
SKIP_OBJECT_TYPES = {
    'fashion design', 'fashion plate', 'drawing', 'print', 'photograph',
    'painting', 'poster', 'illustration', 'pattern', 'sketch',
    'negative', 'slide', 'postcard', 'catalogue', 'book',
    'sample', 'swatch',
}


def search_fashion_keyword(query, year_from=None, year_to=None, page=1, page_size=45):
    params = {
        'id_category': FASHION_CATEGORY,
        'images_exist': 1,
        'q': query,
        'page': page,
        'page_size': page_size,
    }
    if year_from:
        params['year_made_from'] = year_from
    if year_to:
        params['year_made_to'] = year_to

    try:
        resp = SESSION.get(f"{BASE_URL}/objects/search", params=params, timeout=15)
        if resp.status_code != 200:
            errors['http'] += 1
            return [], 0
        data = resp.json()
        total = data.get('info', {}).get('record_count', 0)
        return data.get('records', []), total
    except requests.exceptions.Timeout:
        errors['timeout'] += 1
        return [], 0
    except Exception:
        errors['other'] += 1
        return [], 0


def fetch_object(system_number):
    try:
        resp = SESSION.get(f"{BASE_URL}/object/{system_number}", timeout=15)
        if resp.status_code != 200:
            errors['http'] += 1
            return None
        return resp.json().get('record')
    except requests.exceptions.Timeout:
        errors['timeout'] += 1
        return None
    except Exception:
        errors['other'] += 1
        return None


def download_image(image_id, storage_key):
    url = f"https://framemark.vam.ac.uk/collections/{image_id}/full/600,/0/default.jpg"
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


def _parse_year(date_str):
    if not date_str:
        return None
    m = re.search(r'(\d{4})', str(date_str))
    return int(m.group(1)) if m else None


def extract_date_fields(detail):
    era = None
    decade = None
    object_date = None

    prod_dates = detail.get('productionDates') or []
    if prod_dates:
        date_info = prod_dates[0].get('date', {})
        earliest_str = date_info.get('earliest', '')
        latest_str = date_info.get('latest', '')
        object_date = date_info.get('text')

        earliest_year = _parse_year(earliest_str)
        latest_year = _parse_year(latest_str)

        if earliest_year and latest_year:
            mid_year = (earliest_year + latest_year) // 2
            decade = f'{(mid_year // 10) * 10}s'
            era = year_to_era(mid_year)
        elif earliest_year:
            decade = f'{(earliest_year // 10) * 10}s'
            era = year_to_era(earliest_year)

    return era, decade, object_date


def obj_to_product(search_record, detail, image_data):
    sys_num = search_record['systemNumber']
    obj_type = search_record.get('objectType', 'clothing')
    primary_date = search_record.get('_primaryDate', '')
    primary_place = search_record.get('_primaryPlace', '')

    title = search_record.get('_primaryTitle', '').strip()
    if not title and detail:
        title = (detail.get('briefDescription') or '').strip()
    if not title:
        title = f"{obj_type} ({primary_date})" if primary_date else obj_type

    materials = ''
    if detail:
        materials = detail.get('materialsAndTechniques', '') or ''

    culture = primary_place
    if not culture and detail:
        places = detail.get('placesOfOrigin') or []
        if places:
            culture = places[0].get('place', {}).get('text', '')

    phys_desc = ''
    if detail:
        phys_desc = detail.get('physicalDescription', '') or ''

    maker = ''
    maker_info = search_record.get('_primaryMaker', {})
    if maker_info:
        maker = maker_info.get('name', '')

    era, decade, object_date = (None, None, None)
    if detail:
        era, decade, object_date = extract_date_fields(detail)

    if not era and primary_date:
        year = _parse_year(primary_date)
        if year:
            era = year_to_era(year)
            decade = f'{(year // 10) * 10}s'
        object_date = object_date or primary_date

    desc_parts = [p for p in [
        obj_type,
        f"Date: {primary_date}" if primary_date else None,
        f"Place: {culture}" if culture else None,
        f"Materials: {materials}" if materials else None,
        f"Maker: {maker}" if maker else None,
        phys_desc[:200] if phys_desc else None,
    ] if p]

    tags = [p for p in [culture, maker] if p]

    return {
        'external_id': f'va_{sys_num}',
        'platform': 'va_museum',
        'title': title[:255],
        'description': " | ".join(desc_parts)[:500],
        'price': 0.0,
        'currency': 'USD',
        'primary_image': image_data,
        'image_urls': json.dumps([image_data]),
        'seller_name': 'Victoria and Albert Museum',
        'seller_url': f'https://collections.vam.ac.uk/item/{sys_num}',
        'url': f'https://collections.vam.ac.uk/item/{sys_num}',
        'category': obj_type,
        'garment_type': obj_type if obj_type else None,
        'material': materials if materials else None,
        'era': era,
        'decade': decade,
        'object_date': object_date if object_date else None,
        'culture': culture if culture else None,
        'period': primary_date if primary_date else None,
        'style_tags': json.dumps(tags) if tags else None,
    }


def load_va_contemporary(num_new=300, max_per_query=20):
    print("\n" + "=" * 60)
    print("LOADING CONTEMPORARY V&A FASHION (post-2000)")
    print("=" * 60 + "\n")

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'va_museum'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    stored = 0
    scanned = 0
    skipped_dup = 0
    skipped_type = 0
    skipped_pre2000 = 0
    no_image = 0
    seen_titles = set()
    query_stats = {}

    queries = list(CONTEMPORARY_QUERIES)
    random.shuffle(queries)

    for query_term, year_from, year_to in queries:
        if stored >= num_new:
            break

        query_stored = 0
        _, total = search_fashion_keyword(query_term, year_from, year_to, page=1, page_size=1)
        time.sleep(0.5)
        print(f"\n--- \"{query_term}\" ({year_from}+): {total} results ---")

        if total == 0:
            continue

        max_pages = min(5, (total // 45) + 1)
        pages = list(range(1, max_pages + 1))
        random.shuffle(pages)

        for page in pages:
            if stored >= num_new or query_stored >= max_per_query:
                break

            records, _ = search_fashion_keyword(query_term, year_from, year_to, page=page)
            time.sleep(0.5)

            if not records:
                break

            for record in records:
                if stored >= num_new or query_stored >= max_per_query:
                    break

                sys_num = record['systemNumber']
                if f'va_{sys_num}' in existing:
                    skipped_dup += 1
                    continue

                # Skip non-garment object types
                obj_type = (record.get('objectType', '') or '').lower()
                if obj_type in SKIP_OBJECT_TYPES:
                    skipped_type += 1
                    continue

                # Dedup by title+maker
                title_key = (record.get('_primaryTitle', '') or '').strip().lower()
                maker_key = (record.get('_primaryMaker', {}) or {}).get('name', '').strip().lower()
                dedup_key = f"{title_key}|{maker_key}" if title_key else None
                if dedup_key and dedup_key in seen_titles:
                    continue

                image_id = record.get('_primaryImageId')
                if not image_id:
                    no_image += 1
                    continue

                # Fetch full detail
                detail = fetch_object(sys_num)
                scanned += 1
                time.sleep(0.5)

                # Verify it's actually post-2000
                era, decade, obj_date = (None, None, None)
                if detail:
                    era, decade, obj_date = extract_date_fields(detail)
                if not era:
                    primary_date = record.get('_primaryDate', '')
                    year = _parse_year(primary_date)
                    if year:
                        era = year_to_era(year)
                        decade = f'{(year // 10) * 10}s'

                # Check year is actually post-2000
                year_check = _parse_year(decade) if decade else None
                if year_check and year_check < 2000:
                    skipped_pre2000 += 1
                    continue

                # Download image
                image_data = download_image(image_id, f'va_{sys_num}')
                time.sleep(0.5)

                if not image_data:
                    no_image += 1
                    continue

                product_data = obj_to_product(record, detail, image_data)
                try:
                    db.add(Product(**product_data))
                    db.commit()
                    existing.add(f'va_{sys_num}')
                    if dedup_key:
                        seen_titles.add(dedup_key)
                    stored += 1
                    query_stored += 1
                    maker_label = maker_key[:20] if maker_key else ''
                    print(f"  [{stored}/{num_new}] {product_data['title'][:45]} ({era or '?'}) {maker_label}")
                except Exception as e:
                    db.rollback()
                    print(f"  DB error: {e}")

        query_stats[query_term] = query_stored

    # Summary
    print(f"\n{'=' * 60}")
    print(f"CONTEMPORARY LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items stored: {stored}")
    print(f"  Objects scanned: {scanned}")
    print(f"  Skipped (duplicate): {skipped_dup}")
    print(f"  Skipped (non-garment type): {skipped_type}")
    print(f"  Skipped (pre-2000): {skipped_pre2000}")
    print(f"  Skipped (no image): {no_image}")
    print(f"  Errors: {dict(errors)}")
    print(f"\nItems per query:")
    for q, count in sorted(query_stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {q}: {count}")

    va_count = db.query(Product).filter(Product.platform == 'va_museum').count()
    total_count = db.query(Product).count()
    print(f"\n  Total V&A items in DB: {va_count}")
    print(f"  Total items in DB: {total_count}")

    db.close()


if __name__ == '__main__':
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    load_va_contemporary(num_new=num)
