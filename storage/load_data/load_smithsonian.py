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

from storage.image_storage import upload_product_image

# Ensure project root is first in path so local storage/ is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
from storage.database import SessionLocal, Product
from enrichment.era_taxonomy import year_to_era
import json
import re
import random
from io import BytesIO
from PIL import Image
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('SMITHSONIAN_API_KEY')
BASE_URL = "https://api.si.edu/openaccess/api/v1.0"
SESSION = requests.Session()

# Fashion search queries — one term per query for precision, covering garment
# types across all eras. The is_fashion_item() filter handles false positives.
FASHION_QUERIES = [
    # Dresses & gowns
    # "gown",
    # "evening gown",
    # "cocktail dress",
    # # Tops
    # "blouse",
    # "bodice",
    # "corset",
    # # Outerwear
    # "coat",
    # "jacket",
    # "shawl",
    # # Bottoms
    # "skirt",
    # "trousers",
    # # Full outfits
    # "uniform",
    # "ensemble",
    # "kimono",
    # "robe",
   
    # Era-specific queries (skip pre-1900, already well-covered)
    # "1950s dress",
    # "1950s garment",
    # "1960s clothing",
    # "1960s fashion",
    # "1960s dress",
    # "1970s clothing",
    # "1970s dress",
    # "1970s fashion",
    # "1980s clothing",
    # "1980s fashion",
    # "1980s dress",
    # "1990s clothing",
    # "1990s fashion",
    # "1990s dress",
    # "contemporary dress",
    # "contemporary fashion",
    # Gap-filling queries for underrepresented eras
    "punk fashion",
    "punk clothing",
    "hip hop fashion",
    "streetwear",
    "rave clothing",
    "club fashion",
    "power suit",
    "grunge fashion",
    "beatnik",

    # Hip-hop / streetwear — garment-specific terms (catch items not tagged "hip hop")
    "tracksuit",
    "sneakers",
    "leather jacket hip hop",
    "gold chain",
    "Kangol",
    "Adidas Run DMC",

    # Cultural diversity — African American fashion
    "African American dress",
    "African American clothing",
    "African textile",
    "kente cloth",
    "dashiki",

    # Cultural diversity — other traditions
    "Native American clothing",
    "Indigenous dress",
    "Latin American textile",
    "Chinese silk robe",
    "Japanese kimono",
    "Indian textile",
    "sari",
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
    # Streetwear / contemporary
    'tracksuit', 'sneakers', 'hoodie', 'sweatshirt', 'cap', 'jersey',
    # Non-Western garments
    'sari', 'saree', 'kurta', 'dashiki', 'kente', 'kaftan', 'caftan',
    'cheongsam', 'qipao', 'hanbok', 'huipil', 'moccasin', 'turban',
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

    # Skip fragments
    title = row.get('title', '').lower()
    if 'fragment' in title:
        return False

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


def download_image(url, storage_key):
    """Download image and upload to Supabase Storage."""
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

    # Era from date — use canonical taxonomy
    era = None
    if date_str:
        m = re.search(r'(\d{4})', date_str)
        if m:
            era = year_to_era(int(m.group(1)))
        elif '19th century' in date_str.lower():
            era = year_to_era(1850)
        elif '18th century' in date_str.lower():
            era = year_to_era(1750)
        elif '20th century' in date_str.lower():
            era = year_to_era(1950)
        elif '21st century' in date_str.lower():
            era = year_to_era(2010)

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
    skipped_era = 0
    era_counts = {}
    max_per_era = max(5, int(target * 0.15))

    # Shuffle query order for variety across runs
    queries = list(FASHION_QUERIES)
    random.shuffle(queries)
    max_per_query = max(5, target // len(queries))
    print(f"Max per query: {max_per_query}, max per era: {max_per_era}")

    for query in queries:
        if stored >= target:
            break

        query_stored = 0
        start = 0
        print(f"\n--- Searching: \"{query}\" ---")

        while stored < target and query_stored < max_per_query:
            resp = SESSION.get(f"{BASE_URL}/search", params={
                'api_key': API_KEY,
                'q': query,
                'rows': 50,
                'start': start,
                'sort': 'random',
            })

            if resp.status_code != 200:
                print(f"  API error: {resp.status_code}")
                break

            data = resp.json()
            rows = data.get('response', {}).get('rows', [])

            if not rows:
                break

            # Shuffle within batch for extra variety
            random.shuffle(rows)

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

                # Era diversity cap
                era_key = metadata.get('era') or 'Unknown'
                if era_counts.get(era_key, 0) >= max_per_era:
                    skipped_era += 1
                    continue

                # Get image URL and download
                img_url = get_image_url(row)
                if not img_url:
                    skipped_no_image += 1
                    continue

                image_data = download_image(img_url, metadata['external_id'])
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
                    era_counts[era_key] = era_counts.get(era_key, 0) + 1
                    stored += 1
                    query_stored += 1
                    print(f"  [{stored}/{target}] {metadata['title'][:50]} ({era_key})")
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
    print(f"  Skipped (era cap): {skipped_era}")
    print(f"\nEra distribution (this run):")
    for era_name, count in sorted(era_counts.items(), key=lambda x: -x[1]):
        print(f"  {era_name}: {count}")
    print(f"  Total Smithsonian items: {si_count}")
    print(f"  Total in database: {all_count}")

    db.close()


if __name__ == '__main__':
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    load_smithsonian(target=target)
