"""
Remove low-quality items: portraits of people (not fashion documentation),
social scene lithographs, and unenriched textile fragments.

KEEPS: Fashion plates, design sketches, catalog illustrations, and enriched fragments.
REMOVES: "Unidentified Woman" portraits, social scenes, unenriched scraps.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scripts.storage.database import SessionLocal, Product

def cleanup_bad_titles(dry_run=True):
    db = SessionLocal()

    to_delete = []

    # 1. Portraits of people (not fashion documentation)
    # Match titles that are just names: "Mrs. Day", "Martha Washington", "Mme. Cartier"
    portrait_patterns = [
        'unidentified woman', 'unidentified man', 'unidentified person',
        'unidentified lady', 'unidentified gentleman', 'portrait of',
        'mrs. %', 'mr. %', 'miss %', 'mme. %', 'mlle. %',  # Honorifics suggest portraits
    ]

    for pattern in portrait_patterns:
        portraits = db.query(Product).filter(
            Product.title.ilike(pattern)
        ).all()
        to_delete.extend(portraits)

    # Also catch titles that are ONLY names (no garment words)
    # If title has no garment-related words AND is unenriched, likely a portrait
    unenriched_likely_portraits = db.query(Product).filter(
        Product.enriched_at == None,
        Product.platform == 'smithsonian'
    ).all()

    garment_words = ['dress', 'gown', 'coat', 'jacket', 'hat', 'shoe', 'glove',
                     'suit', 'skirt', 'blouse', 'pants', 'boot', 'bonnet']

    for item in unenriched_likely_portraits:
        title_lower = item.title.lower()
        has_garment_word = any(word in title_lower for word in garment_words)

        # If no garment word and very short title (likely just a name)
        if not has_garment_word and len(item.title.split()) <= 3:
            to_delete.append(item)

    # 2. Lithographs/Prints that weren't enriched (social scenes, not garment focus)
    unenriched_prints = db.query(Product).filter(
        (Product.category.ilike('%lithograph%')) |
        (Product.category.ilike('%print%')),
        Product.enriched_at == None
    ).all()
    to_delete.extend(unenriched_prints)

    # 3. Fragments that weren't enriched (scraps without context)
    unenriched_fragments = db.query(Product).filter(
        Product.title.ilike('%fragment%'),
        Product.enriched_at == None
    ).all()
    to_delete.extend(unenriched_fragments)

    # Deduplicate (same item might match multiple criteria)
    to_delete = list(set(to_delete))

    print(f'Found {len(to_delete)} items to delete')
    print()

    # Group by platform and deletion reason
    by_platform = {}
    by_reason = {'portraits': 0, 'unenriched_prints': 0, 'unenriched_fragments': 0}

    for item in to_delete:
        platform = item.platform
        by_platform[platform] = by_platform.get(platform, 0) + 1

        # Categorize reason
        title_lower = item.title.lower()
        if any(kw in title_lower for kw in ['unidentified woman', 'unidentified man', 'portrait of']):
            by_reason['portraits'] += 1
        elif item.category and ('lithograph' in item.category.lower() or 'print' in item.category.lower()):
            by_reason['unenriched_prints'] += 1
        elif 'fragment' in title_lower:
            by_reason['unenriched_fragments'] += 1

    print('By platform:')
    for platform, count in sorted(by_platform.items(), key=lambda x: x[1], reverse=True):
        print(f'  {platform:20s} {count:4d}')

    print()
    print('By reason:')
    for reason, count in by_reason.items():
        print(f'  {reason:25s} {count:4d}')

    print()
    print('Sample titles:')
    for item in to_delete[:20]:
        enriched = "✓" if item.enriched_at else "✗"
        print(f'  [{item.platform}] {enriched} {item.title[:70]}')

    print()
    print(f'Total in database before deletion: {db.query(Product).count()}')
    print(f'Items to delete: {len(to_delete)}')
    print(f'Remaining after deletion: {db.query(Product).count() - len(to_delete)}')
    print()

    # Show what we're KEEPING
    enriched_fragments = db.query(Product).filter(
        Product.title.ilike('%fragment%'),
        Product.enriched_at != None
    ).count()
    enriched_prints = db.query(Product).filter(
        (Product.category.ilike('%lithograph%')) | (Product.category.ilike('%print%')),
        Product.enriched_at != None
    ).count()

    print(f'KEEPING (enriched, useful):')
    print(f'  Enriched fragments:      {enriched_fragments}')
    print(f'  Enriched prints/plates:  {enriched_prints}')
    print()

    if dry_run:
        print('DRY RUN - no items deleted')
        print('Run with --execute to actually delete')
    else:
        print('DELETING items...')
        for item in to_delete:
            db.delete(item)
        db.commit()
        print(f'✓ Deleted {len(to_delete)} items')
        print(f'✓ {db.query(Product).count()} items remaining')

    db.close()


if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    cleanup_bad_titles(dry_run=dry_run)
