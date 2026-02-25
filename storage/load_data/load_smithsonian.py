"""
Load fashion items from the Smithsonian Open Access API.

Searches across all Smithsonian museums for clothing, accessories, and textiles
with available images. Key sources:
  - NMAAHC (African American History): dresses, gowns, coats
  - CHNDM (Cooper Hewitt Design Museum): textiles, fashion design
  - NMAH (American History): historical clothing
"""

import sys
import os

# Ensure project root is first in path so local storage/ is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
from scripts.storage.database import SessionLocal, Product
import json
import base64
from io import BytesIO
from PIL import Image
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('SMITHSONIAN_API_KEY')
BASE_URL = "https://api.si.edu/openaccess/api/v1.0"
SESSION = requests.Session()

# Fashion-specific search queries to cast a wide net
FASHION_QUERIES = [
    "dress gown",
    "evening dress",
    "wedding gown",
    "coat jacket",
    "blouse skirt",
    "hat bonnet",
    "shoes boots",
    "suit clothing",
    "corset bodice",
    "kimono robe",
    "silk satin velvet",
    "lace embroidery",
    "handbag purse gloves",
    "vintage fashion",
    "costume garment",
    "textile fabric",
    "uniform military coat",
    "fur cape shawl",
    "cocktail dress",
    "ball gown formal",
]

# Object types that are actual fashion (not books, prints, photos of people, etc.)
FASHION_OBJECT_TYPES = {
    'dresses', 'dress', 'gown', 'coat', 'jacket', 'blouse', 'skirt', 'hat',
    'bonnet', 'shoes', 'boots', 'suit', 'corset', 'bodice', 'kimono', 'robe',
    'gloves', 'handbag', 'purse', 'scarf', 'shawl', 'cape', 'cloak', 'vest',
    'waistcoat', 'stockings', 'socks', 'belt', 'tie', 'cravat', 'collar',
    'cuff', 'apron', 'petticoat', 'chemise', 'nightgown', 'parasol', 'fan',
    'muff', 'stole', 'wrap', 'sweater', 'cardigan', 'uniform', 'ensemble',
    'costume', 'textile', 'fabric', 'accessory', 'footwear', 'headwear',
    'outerwear', 'underwear', 'lingerie', 'negligee', 'peignoir', 'slipper',
    'sandal', 'pump', 'heel', 'mule', 'loafer', 'oxford',
}

# Skip these - they show up in results but aren't wearable fashion
SKIP_TYPES = {
    'books', 'book', 'print', 'photograph', 'painting', 'drawing',
    'poster', 'catalog', 'magazine', 'article', 'sculpture', 'medal',
    'coin', 'stamp', 'postcard', 'letter', 'manuscript', 'document',
    'furniture', 'tool', 'instrument', 'weapon', 'vehicle', 'model',
    'exhibition', 'encyclopedia', 'portfolio', 'negative', 'slide',
    'film', 'video', 'audio', 'map', 'chart', 'diagram',
    'portrait', 'tintype', 'daguerreotype', 'ambrotype', 
}


def is_fashion_item(row):
    """Check if a Smithsonian result is an actual fashion/clothing item."""
    content = row.get('content', {})
    idx = content.get('indexedStructured', {})
    ft = content.get('freetext', {})

    obj_types = idx.get('object_type', [])
    obj_types_lower = [t.lower() for t in obj_types]

    # Explicit skip
    for t in obj_types_lower:
        for skip in SKIP_TYPES:
            if skip in t:
                return False

    # Check if any object type matches fashion
    for t in obj_types_lower:
        for fashion in FASHION_OBJECT_TYPES:
            if fashion in t:
                return True

    # Also check freetext objectType
    ft_types = [x.get('content', '').lower() for x in ft.get('objectType', [])]
    for t in ft_types:
        for fashion in FASHION_OBJECT_TYPES:
            if fashion in t:
                return True
    # Skip if title suggests it's a portrait
    title = row.get('title', '').lower()
    if 'unidentified' in title and ('woman' in title or 'man' in title or 'person' in title):
        return False
    # Check topics
    topics = [t.lower() for t in idx.get('topic', [])]
    fashion_topics = {'clothing', 'fashion', 'costume', 'dress', 'textile', 'apparel'}
    for topic in topics:
        for ft_topic in fashion_topics:
            if ft_topic in topic:
                return True

    return False


def has_images(row):
    """Check if a result has downloadable images."""
    content = row.get('content', {})
    dnr = content.get('descriptiveNonRepeating', {})
    media = dnr.get('online_media', {})
    return media.get('mediaCount', 0) > 0


def get_image_url(row):
    """Extract the best image URL from a result."""
    content = row.get('content', {})
    dnr = content.get('descriptiveNonRepeating', {})
    media = dnr.get('online_media', {})
    media_list = media.get('media', [])

    for m in media_list:
        if m.get('type') == 'Images':
            return m.get('content', '')
    # Fallback to first media item
    if media_list:
        return media_list[0].get('content', '')
    return None


def download_image(url):
    """Download image and convert to data URL."""
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        img.thumbnail((400, 400))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return None


def extract_metadata(row):
    """Extract fashion-relevant metadata from a Smithsonian result."""
    content = row.get('content', {})
    idx = content.get('indexedStructured', {})
    ft = content.get('freetext', {})
    dnr = content.get('descriptiveNonRepeating', {})

    title = row.get('title', 'Unknown Item')

    # Date
    dates = idx.get('date', [])
    date_str = dates[0] if dates else ''
    ft_dates = [x.get('content', '') for x in ft.get('date', [])]
    if not date_str and ft_dates:
        date_str = ft_dates[0]

    # Era from date
    era = None
    if date_str:
        for decade in range(1900, 2030, 10):
            if str(decade) in date_str:
                era = f'{decade}s'
                break
        if not era:
            if '19th century' in date_str.lower() or '1800' in date_str:
                era = '1800s'
            elif '18th century' in date_str.lower() or '1700' in date_str:
                era = '1700s'
            elif '20th century' in date_str.lower():
                era = '1900s'
            elif '21st century' in date_str.lower():
                era = '2000s'

    # Materials
    materials = [x.get('content', '') for x in ft.get('physicalDescription', [])]
    material_str = materials[0][:255] if materials else None

    # Culture/place
    cultures = idx.get('culture', [])
    places = idx.get('place', [])
    culture = cultures[0] if cultures else (places[0] if places else None)

    # Object type
    obj_types = idx.get('object_type', [])
    category = obj_types[0] if obj_types else None

    # Topics as style tags
    topics = idx.get('topic', [])

    # Description
    notes = [x.get('content', '') for x in ft.get('notes', [])]
    desc_parts = [p for p in [
        category,
        f"Date: {date_str}" if date_str else None,
        f"Culture: {culture}" if culture else None,
        f"Materials: {material_str}" if material_str else None,
        notes[0][:200] if notes else None,
    ] if p]

    # Record link
    record_link = dnr.get('record_link', '')
    guid = dnr.get('guid', '')
    url = record_link or guid

    # Unit/source
    unit = row.get('unitCode', '')
    record_id = dnr.get('record_ID', row.get('id', ''))

    return {
        'external_id': f'si_{record_id}',
        'platform': 'smithsonian',
        'title': title[:255],
        'description': " | ".join(desc_parts)[:500],
        'price': 0.0,
        'currency': 'USD',
        'seller_name': f'Smithsonian ({unit})',
        'seller_url': url,
        'url': url,
        'category': category[:100] if category else None,
        'garment_type': category[:100] if category else None,
        'material': material_str[:255] if material_str else None,
        'era': era,
        'object_date': date_str[:100] if date_str else None,
        'culture': culture[:100] if culture else None,
        'style_tags': json.dumps(topics[:10]) if topics else None,
    }


def load_smithsonian(target=300):
    print("\n" + "=" * 60)
    print("LOADING FASHION FROM SMITHSONIAN OPEN ACCESS")
    print("=" * 60 + "\n")

    if not API_KEY:
        print("ERROR: SMITHSONIAN_API_KEY not set in .env")
        return

    db = SessionLocal()
    existing = set(
        r[0] for r in db.query(Product.external_id).filter(
            Product.platform == 'smithsonian'
        ).all()
    )
    print(f"Already in DB: {len(existing)}")

    stored = 0
    seen_ids = set()
    skipped_no_fashion = 0
    skipped_no_image = 0
    skipped_download_fail = 0

    for query in FASHION_QUERIES:
        if stored >= target:
            break

        print(f"\n--- Searching: \"{query}\" ---")
        start = 0

        while stored < target:
            resp = SESSION.get(f"{BASE_URL}/search", params={
                'api_key': API_KEY,
                'q': query,
                'rows': 50,
                'start': start,
            })

            if resp.status_code != 200:
                print(f"  API error: {resp.status_code}")
                break

            data = resp.json()
            rows = data.get('response', {}).get('rows', [])

            if not rows:
                break

            for row in rows:
                if stored >= target:
                    break

                row_id = row.get('id', '')
                if row_id in seen_ids:
                    continue
                seen_ids.add(row_id)

                # Must be a fashion item
                if not is_fashion_item(row):
                    skipped_no_fashion += 1
                    continue

                # Must have images
                if not has_images(row):
                    skipped_no_image += 1
                    continue

                metadata = extract_metadata(row)

                # Skip if already in DB
                if metadata['external_id'] in existing:
                    continue

                # Get image URL and download
                img_url = get_image_url(row)
                if not img_url:
                    skipped_no_image += 1
                    continue

                image_data = download_image(img_url)
                time.sleep(0.3)

                if not image_data:
                    skipped_download_fail += 1
                    continue

                metadata['primary_image'] = image_data
                metadata['image_urls'] = json.dumps([image_data])

                try:
                    db.add(Product(**metadata))
                    db.commit()
                    existing.add(metadata['external_id'])
                    stored += 1
                    era = metadata.get('era', '?')
                    print(f"  [{stored}/{target}] {metadata['title'][:50]} ({era})")
                except Exception as e:
                    db.rollback()
                    print(f"  DB error: {e}")

            start += 50
            time.sleep(0.5)  # Rate limiting

    # Summary
    all_count = db.query(Product).count()
    si_count = db.query(Product).filter(Product.platform == 'smithsonian').count()

    print(f"\n{'=' * 60}")
    print(f"LOADING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  New items loaded: {stored}")
    print(f"  Skipped (not fashion): {skipped_no_fashion}")
    print(f"  Skipped (no image): {skipped_no_image}")
    print(f"  Skipped (download fail): {skipped_download_fail}")
    print(f"  Total Smithsonian items: {si_count}")
    print(f"  Total in database: {all_count}")

    db.close()


if __name__ == '__main__':
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    load_smithsonian(target=target)
