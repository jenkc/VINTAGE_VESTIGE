"""
Load 1960-1989 fashion items from the Victoria and Albert Museum.

Targets gap eras: Space Age, Hippie, Glam Rock, Punk, Disco,
New Wave, Power Dressing. Shares helpers with load_va.py.

Usage:
  python storage/load_data/load_va_modern.py          # load 200 items (default)
  python storage/load_data/load_va_modern.py 100      # load 100 items
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import requests
import json
import time
from storage.database import SessionLocal, Product
from storage.load_data.load_va import (
    fetch_object, download_image, extract_date_fields,
    _parse_year, obj_to_product, errors,
)
from enrichment.era_taxonomy import year_to_era


BASE_URL = "https://api.vam.ac.uk/v2"
FASHION_CATEGORY = "THES48957"
SESSION = requests.Session()


def search_modern_random(page_size=100):
    """Search V&A fashion 1960-1989 for random items with images."""
    try:
        resp = SESSION.get(f"{BASE_URL}/objects/search", params={
            'id_category': FASHION_CATEGORY,
            'images_exist': 1,
            'year_made_from': 1960,
            'year_made_to': 1989,
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


def load_va_modern(num_new=400, max_per_era_pct=0.25):
    print("\n" + "=" * 60)
    print("LOADING 1960-1989 FASHION FROM V&A MUSEUM")
    print("=" * 60 + "\n")

    max_per_era = max(5, int(num_new * max_per_era_pct))
    print(f"Era diversity cap: max {max_per_era} items per era ({max_per_era_pct:.0%})")

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'va_museum'
        ).all()
    )
    print(f"Already in DB (all V&A): {len(existing)}")

    print("\nFetching random 1960-1989 fashion items from V&A API...")

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
    max_per_type = max(5, int(num_new * 0.15))

    while stored < num_new:
        if empty_batches >= 20:
            print("  Too many empty batches, stopping.")
            break

        records = search_modern_random(page_size=100)
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

            # Skip duplicate titles
            title_key = (record.get('_primaryTitle', '') or '').strip().lower()
            maker_key = (record.get('_primaryMaker', {}) or {}).get('name', '').strip().lower()
            dedup_key = f"{title_key}|{maker_key}" if title_key else None
            if dedup_key and dedup_key in seen_titles:
                skipped_title += 1
                continue

            # Cap any single objectType
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


if __name__ == '__main__':
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    load_va_modern(num_new=num)
