"""
Load fashion items from the Victoria and Albert Museum collection.

Uses V&A's public API (no auth required) with IIIF image serving.
Fashion category (~45k objects with images) covers ancient through present.

Usage:
  python storage/load_data/load_va.py                  # load 400 random items
  python storage/load_data/load_va.py 200              # load 200 random items
  python storage/load_data/load_va.py --keywords 100   # load 100 via keyword search
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import requests
import re
import json
import random
from storage.image_storage import upload_product_image
import time
from io import BytesIO
from PIL import Image
from storage.database import SessionLocal, Product
from enrichment.era_taxonomy import year_to_era


BASE_URL = "https://api.vam.ac.uk/v2"
FASHION_CATEGORY = "THES48957"
SESSION = requests.Session()

errors = {'timeout': 0, 'http': 0, 'other': 0}


def search_fashion_random(page_size=100):
    """Search V&A fashion collection for random items with images."""
    try:
        resp = SESSION.get(f"{BASE_URL}/objects/search", params={
            'id_category': FASHION_CATEGORY,
            'images_exist': 1,
            'page_size': page_size,
            'random': 1,
        }, timeout=15)
        if resp.status_code != 200:
            errors['http'] += 1
            return []
        data = resp.json()
        return data.get('records', [])
    except requests.exceptions.Timeout:
        errors['timeout'] += 1
        return []
    except Exception:
        errors['other'] += 1
        return []


def fetch_object(system_number):
    """Fetch full object detail from V&A API."""
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
    """Download image via IIIF URL, resize, and upload to our storage."""
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


def extract_date_fields(detail):
    """Extract era, decade, and object_date from V&A object detail.

    Uses productionDates[].date.earliest/.latest (date strings like '1902-01-01')
    for reliable era mapping. Falls back to _primaryDate string parsing.
    """
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

    if not era and not object_date:
        # Try _primaryDate from search result (stored on detail too sometimes)
        pass

    return era, decade, object_date


def _parse_year(date_str):
    """Extract a 4-digit year from a date string like '1902-01-01' or '1902'."""
    if not date_str:
        return None
    m = re.search(r'(\d{4})', str(date_str))
    return int(m.group(1)) if m else None


def obj_to_product(search_record, detail, image_data):
    """Convert V&A search record + detail into a Product dict."""
    sys_num = search_record['systemNumber']
    obj_type = search_record.get('objectType', 'clothing')
    primary_date = search_record.get('_primaryDate', '')
    primary_place = search_record.get('_primaryPlace', '')

    # Title: prefer _primaryTitle, fall back to briefDescription or objectType
    title = search_record.get('_primaryTitle', '').strip()
    if not title and detail:
        title = (detail.get('briefDescription') or '').strip()
    if not title:
        title = f"{obj_type} ({primary_date})" if primary_date else obj_type

    # Materials
    materials = ''
    if detail:
        materials = detail.get('materialsAndTechniques', '') or ''

    # Culture / place of origin
    culture = primary_place
    if not culture and detail:
        places = detail.get('placesOfOrigin') or []
        if places:
            culture = places[0].get('place', {}).get('text', '')

    # Physical description (rich text for our description field)
    phys_desc = ''
    if detail:
        phys_desc = detail.get('physicalDescription', '') or ''

    # Maker
    maker = ''
    maker_info = search_record.get('_primaryMaker', {})
    if maker_info:
        maker = maker_info.get('name', '')

    # Era from detail production dates
    era, decade, object_date = (None, None, None)
    if detail:
        era, decade, object_date = extract_date_fields(detail)

    # Fallback: parse _primaryDate
    if not era and primary_date:
        year = _parse_year(primary_date)
        if year:
            era = year_to_era(year)
            decade = f'{(year // 10) * 10}s'
        object_date = object_date or primary_date

    # Build description
    desc_parts = [p for p in [
        obj_type,
        f"Date: {primary_date}" if primary_date else None,
        f"Place: {culture}" if culture else None,
        f"Materials: {materials}" if materials else None,
        f"Maker: {maker}" if maker else None,
        phys_desc[:200] if phys_desc else None,
    ] if p]

    # Style tags
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


def load_va(num_new=400, max_per_era_pct=0.25):
    print("\n" + "=" * 60)
    print("LOADING FASHION FROM V&A MUSEUM")
    print("=" * 60 + "\n")

    max_per_era = max(5, int(num_new * max_per_era_pct))
    print(f"Era diversity cap: max {max_per_era} items per era ({max_per_era_pct:.0%})")

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'va_museum'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    print("\nFetching random fashion items from V&A API...")

    stored = 0
    scanned = 0
    skipped_era = 0
    skipped_dup = 0
    skipped_title = 0
    no_image = 0
    empty_batches = 0
    era_counts = {}
    seen_titles = set()
    type_counts = {}
    max_per_type = max(5, int(num_new * 0.15))  # cap any single objectType at 15%

    while stored < num_new:
        # Stop if we get too many empty batches (all dupes/filtered)
        if empty_batches >= 20:
            print("  Too many empty batches, stopping.")
            break

        records = search_fashion_random(page_size=100)
        time.sleep(1.0)

        if not records:
            empty_batches += 1
            continue

        batch_stored = 0

        for record in records:
            if stored >= num_new:
                break

            sys_num = record['systemNumber']
            if f'va_{sys_num}' in existing:
                skipped_dup += 1
                continue

            # Skip duplicate titles (V&A has thousands of near-identical items)
            title_key = (record.get('_primaryTitle', '') or '').strip().lower()
            maker_key = (record.get('_primaryMaker', {}) or {}).get('name', '').strip().lower()
            dedup_key = f"{title_key}|{maker_key}" if title_key else None
            if dedup_key and dedup_key in seen_titles:
                skipped_title += 1
                continue

            # Cap any single objectType (e.g., "Fashion design" sketches)
            obj_type = record.get('objectType', 'unknown')
            if type_counts.get(obj_type, 0) >= max_per_type:
                skipped_title += 1
                continue

            image_id = record.get('_primaryImageId')
            if not image_id:
                no_image += 1
                continue

            # Fetch full object detail
            detail = fetch_object(sys_num)
            scanned += 1
            time.sleep(1.0)

            # Check era diversity
            era = None
            if detail:
                era, _, _ = extract_date_fields(detail)
            if not era:
                primary_date = record.get('_primaryDate', '')
                year = _parse_year(primary_date)
                if year:
                    era = year_to_era(year)

            era_key = era or 'Unknown'
            if era_counts.get(era_key, 0) >= max_per_era:
                skipped_era += 1
                if scanned % 25 == 0:
                    print(f"  scanned {scanned} — stored {stored} — {skipped_era} era-capped | errors: {dict(errors)}")
                continue

            # Download image
            image_data = download_image(image_id, f'va_{sys_num}')
            time.sleep(1.0)

            if not image_data:
                no_image += 1
                if scanned % 25 == 0:
                    print(f"  scanned {scanned} — stored {stored} — {no_image} no image | errors: {dict(errors)}")
                continue

            product_data = obj_to_product(record, detail, image_data)
            try:
                db.add(Product(**product_data))
                db.commit()
                existing.add(f'va_{sys_num}')
                era_counts[era_key] = era_counts.get(era_key, 0) + 1
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
                if dedup_key:
                    seen_titles.add(dedup_key)
                stored += 1
                batch_stored += 1
                print(f"  [{stored}/{num_new}] {product_data['title'][:50]} ({era_key}, {product_data.get('object_date', '?')})")
            except Exception as e:
                db.rollback()
                print(f"  DB error: {e}")

            if scanned % 25 == 0:
                print(f"  --- scanned {scanned} — stored {stored} — {skipped_era} era-capped, {skipped_dup} dups | errors: {dict(errors)}")

        if batch_stored == 0:
            empty_batches += 1
        else:
            empty_batches = 0

    # Summary
    print(f"\n{'=' * 60}")
    print(f"LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items stored: {stored}")
    print(f"  Objects scanned: {scanned}")
    print(f"  Skipped (era cap): {skipped_era}")
    print(f"  Skipped (duplicate ID): {skipped_dup}")
    print(f"  Skipped (title/type): {skipped_title}")
    print(f"  Skipped (no image): {no_image}")
    print(f"  Errors: {dict(errors)}")
    print(f"\nObject type distribution:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")
    print(f"\nEra distribution:")
    for era_name, count in sorted(era_counts.items(), key=lambda x: -x[1]):
        print(f"  {era_name}: {count}")

    va_count = db.query(Product).filter(Product.platform == 'va_museum').count()
    total_count = db.query(Product).count()
    print(f"\n  Total V&A items in DB: {va_count}")
    print(f"  Total items in DB: {total_count}")

    db.close()


# =============================================================================
# KEYWORD SEARCH MODE — targeted loading by search term
# =============================================================================

# Keyword groups for targeted gap-filling.
# Each entry: (search_term, optional year_from, optional year_to)
VA_KEYWORD_QUERIES = [
    # --- Hip-hop / Streetwear ---
    ("tracksuit", None, None),
    ("trainer", None, None),
    ("sneakers", None, None),
    ("hoodie", None, None),
    ("sportswear", 1980, None),
    ("streetwear", None, None),
    ("Nike", None, None),
    ("Adidas", None, None),
    ("hip hop", None, None),

    # --- South Asian ---
    ("sari", None, None),
    ("shalwar", None, None),
    ("kurta", None, None),
    ("lehenga", None, None),
    ("choli", None, None),
    ("dupatta", None, None),
    ("dhoti", None, None),

    # --- East Asian ---
    ("kimono", None, None),
    ("hanfu", None, None),
    ("cheongsam", None, None),
    ("qipao", None, None),
    ("hanbok", None, None),
    ("obi", None, None),

    # --- Middle Eastern / North African ---
    ("kaftan", None, None),
    ("caftan", None, None),
    ("djellaba", None, None),
    ("abaya", None, None),
    ("thobe", None, None),

    # --- African ---
    ("kente", None, None),
    ("dashiki", None, None),
    ("agbada", None, None),
    ("boubou", None, None),
    ("ankara", None, None),

    # --- Latin American ---
    ("huipil", None, None),
    ("poncho", None, None),
    ("rebozo", None, None),
]


def search_fashion_keyword(query, year_from=None, year_to=None, page=1, page_size=45):
    """Search V&A fashion category by keyword, optionally filtered by date range."""
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


def load_va_keywords(num_new=200, max_per_query=25):
    """Load V&A items via targeted keyword searches for gap-filling."""
    print("\n" + "=" * 60)
    print("LOADING V&A ITEMS BY KEYWORD SEARCH")
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
    skipped_title = 0
    no_image = 0
    seen_titles = set()
    query_stats = {}

    queries = list(VA_KEYWORD_QUERIES)
    random.shuffle(queries)

    for query_term, year_from, year_to in queries:
        if stored >= num_new:
            break

        query_stored = 0
        date_label = ""
        if year_from or year_to:
            date_label = f" ({year_from or '?'}-{year_to or '?'})"

        # Check how many results exist
        _, total = search_fashion_keyword(query_term, year_from, year_to, page=1, page_size=1)
        time.sleep(1.0)
        print(f"\n--- \"{query_term}\"{date_label}: {total} results ---")

        if total == 0:
            continue

        # Paginate through results (randomize page order for variety)
        max_pages = min(10, (total // 45) + 1)
        pages = list(range(1, max_pages + 1))
        random.shuffle(pages)

        for page in pages:
            if stored >= num_new or query_stored >= max_per_query:
                break

            records, _ = search_fashion_keyword(query_term, year_from, year_to, page=page)
            time.sleep(1.0)

            if not records:
                break

            for record in records:
                if stored >= num_new or query_stored >= max_per_query:
                    break

                sys_num = record['systemNumber']
                if f'va_{sys_num}' in existing:
                    skipped_dup += 1
                    continue

                # Dedup by title+maker
                title_key = (record.get('_primaryTitle', '') or '').strip().lower()
                maker_key = (record.get('_primaryMaker', {}) or {}).get('name', '').strip().lower()
                dedup_key = f"{title_key}|{maker_key}" if title_key else None
                if dedup_key and dedup_key in seen_titles:
                    skipped_title += 1
                    continue

                image_id = record.get('_primaryImageId')
                if not image_id:
                    no_image += 1
                    continue

                # Fetch full object detail
                detail = fetch_object(sys_num)
                scanned += 1
                time.sleep(1.0)

                # Download image
                image_data = download_image(image_id, f'va_{sys_num}')
                time.sleep(1.0)

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
                    era_label = product_data.get('era') or '?'
                    print(f"  [{stored}/{num_new}] {product_data['title'][:50]} ({era_label})")
                except Exception as e:
                    db.rollback()
                    print(f"  DB error: {e}")

        query_stats[query_term] = query_stored

    # Summary
    print(f"\n{'=' * 60}")
    print(f"KEYWORD LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items stored: {stored}")
    print(f"  Objects scanned: {scanned}")
    print(f"  Skipped (duplicate ID): {skipped_dup}")
    print(f"  Skipped (duplicate title): {skipped_title}")
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
    if '--keywords' in sys.argv:
        idx = sys.argv.index('--keywords')
        num = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 200
        load_va_keywords(num_new=num)
    else:
        num = int(sys.argv[1]) if len(sys.argv) > 1 else 400
        load_va(num_new=num)
