"""
Normalize fragmented social_function values into canonical clusters.

No API calls — pure SQL/Python string mapping.

Usage:
  PYTHONPATH=. python tools/analysis/normalize_social_functions.py          # audit
  PYTHONPATH=. python tools/analysis/normalize_social_functions.py --apply  # apply
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from storage.database import SessionLocal, Product
from sqlalchemy import text

# Canonical clusters — map fragmented terms to ~15 clean values
NORMALIZE_MAP = {
    # Evening / formal evening
    'evening-formal': 'formal-evening',
    'formal evening': 'formal-evening',
    'evening-social': 'formal-evening',
    'evening-entertainment': 'formal-evening',
    'evening-party': 'formal-evening',
    'evening party': 'formal-evening',
    'evening casual': 'formal-evening',
    'evening-casual': 'formal-evening',
    'luxury-evening': 'formal-evening',
    'luxury-casual': 'formal-evening',

    # Court / formal
    'formal': 'court-formal',
    'formal-ceremonial': 'court-formal',
    'formal-dress': 'court-formal',
    'formal-court': 'court-formal',
    'formal-traditional': 'court-formal',
    'formal-cultural': 'court-formal',
    'formal-contemporary': 'court-formal',
    'formal-social': 'court-formal',
    'formal-wear': 'court-formal',
    'formal-portrait': 'court-formal',
    'traditional-formal': 'court-formal',
    'red-carpet-formal': 'court-formal',
    'formal-daywear': 'everyday-practical',
    'formal-business': 'everyday-practical',

    # Subculture
    'subculture': 'protest-subculture',
    'subculture-identity': 'protest-subculture',
    'subculture-expression': 'protest-subculture',
    'subculture-fashion': 'protest-subculture',
    'subculture-reference': 'protest-subculture',
    'subculture-statement': 'protest-subculture',
    'youth-subculture': 'protest-subculture',
    'alternative-subculture': 'protest-subculture',
    'artistic-subculture': 'protest-subculture',

    # Artistic / avant-garde
    'artistic-statement': 'avant-garde',
    'artistic statement': 'avant-garde',
    'artistic expression': 'avant-garde',
    'artistic-expression': 'avant-garde',
    'artistic-display': 'avant-garde',
    'artistic display': 'avant-garde',
    'artistic-contemporary': 'avant-garde',
    'artistic avant-garde': 'avant-garde',
    'artistic-avant-garde': 'avant-garde',
    'artistic wear': 'avant-garde',
    'artistic statement wear': 'avant-garde',
    'avant-garde fashion': 'avant-garde',
    'avant-garde-fashion': 'avant-garde',
    'avant-garde fashion statement': 'avant-garde',
    'avant-garde-art': 'avant-garde',
    'avant-garde statement': 'avant-garde',
    'avant-garde streetwear': 'avant-garde',

    # Ceremonial / religious
    'ceremonial': 'religious-ceremonial',
    'ceremonial-formal': 'religious-ceremonial',
    'ceremonial-parade': 'religious-ceremonial',
    'ceremonial-gift': 'religious-ceremonial',
    'cultural-ceremony': 'religious-ceremonial',
    'formal-ceremonial': 'religious-ceremonial',

    # Cultural heritage (includes cultural-ceremonial)
    'cultural-identity': 'cultural-heritage',
    'cultural-expression': 'cultural-heritage',
    'cultural-celebration': 'cultural-heritage',
    'cultural-pride': 'cultural-heritage',
    'cultural-preservation': 'cultural-heritage',
    'cultural-fusion': 'cultural-heritage',
    'cultural-ceremonial': 'cultural-heritage',
    'cultural ceremonial': 'cultural-heritage',

    # Wedding
    'wedding': 'wedding',

    # Military
    'military-uniform': 'military-uniform',

    # Performance
    'performance-costume': 'performance-costume',

    # Fashion / artistic / avant-garde → all fold into avant-garde
    'fashion-statement': 'avant-garde',
    'fashion-forward': 'avant-garde',
    'fashion-forward daywear': 'avant-garde',
    'fashion-editorial': 'avant-garde',
    'fashion-presentation': 'avant-garde',
    'fashion retail display': 'avant-garde',
    'fashion-forward-statement': 'avant-garde',
    'fashionable-daywear': 'avant-garde',
    'fashionable-statement': 'avant-garde',
    'fashionable-menswear': 'avant-garde',
    'fashionable-outerwear': 'avant-garde',
    'fashionable street wear': 'avant-garde',
    'high-fashion': 'avant-garde',
    'fashion-contemporary': 'avant-garde',
    'fashion-forward-contemporary': 'avant-garde',
    'art-exhibition': 'avant-garde',
    'artistic-formal': 'avant-garde',

    # Leisure
    'leisure-resort': 'leisure-resort',
    'leisure-social': 'leisure-resort',
    'leisure-play': 'leisure-resort',

    # Cocktail
    'cocktail-party': 'formal-evening',
    'cocktail-evening': 'formal-evening',
    'cocktail-formal': 'formal-evening',

    # Streetwear → everyday
    'streetwear': 'everyday-practical',

    # Mourning
    'mourning': 'mourning',

    # Festival
    'festival-celebration': 'festival-celebration',

    # Domestic / portrait — map to everyday
    'domestic-idealization': 'everyday-practical',
    'domestic-portraiture': 'everyday-practical',
    'domestic-scene': 'everyday-practical',
    'formal-portrait': 'everyday-practical',

    # Children's / evening-practical → formal-evening
    "children's formal": 'formal-evening',
    'evening-practical': 'formal-evening',

    # Misc one-offs → closest cluster
    'bohemian-lifestyle': 'leisure-resort',
    'smart-casual': 'everyday-practical',
    'casual-wear': 'everyday-practical',
    'date-night': 'formal-evening',
    'nightclub-entertainment': 'formal-evening',
    'nightlife-clubbing': 'formal-evening',
    'party-social': 'formal-evening',
    'romantic-encounter': 'formal-evening',
    'novelty-gift': 'everyday-practical',
    'novelty-experimental': 'avant-garde',
    'social-commentary': 'protest-subculture',
    'political-commentary': 'protest-subculture',
    'patriotic-ceremonial': 'religious-ceremonial',
    'patriotic-display': 'religious-ceremonial',
    'commemorative': 'religious-ceremonial',
    'diplomatic-gift': 'court-formal',
    'courtship': 'court-formal',
    'coming-of-age': 'religious-ceremonial',
    'storybook illustration': 'performance-costume',
    'entertainment-advertising': 'performance-costume',
    'fitness-training': 'sportswear',
    'health-reform': 'everyday-practical',
    'literary-romantic': 'performance-costume',
    'outdoor formal': 'court-formal',
    'fraternal organization': 'religious-ceremonial',
    'fundraising-community': 'everyday-practical',
    'academic-formal': 'court-formal',
}


def main():
    apply_mode = '--apply' in sys.argv
    db = SessionLocal()

    # Get all products with social_function
    products = db.query(Product).filter(Product.social_function != None).all()
    print(f"Products with social_function: {len(products)}")

    changes = 0
    unchanged = 0
    before_counts = {}
    after_counts = {}

    for p in products:
        # Parse JSON
        sf = p.social_function
        if isinstance(sf, str):
            try:
                sf = json.loads(sf)
            except (json.JSONDecodeError, TypeError):
                sf = [sf] if sf else []
        if not isinstance(sf, list):
            sf = [sf] if sf else []

        # Normalize
        new_sf = []
        changed = False
        for term in sf:
            before_counts[term] = before_counts.get(term, 0) + 1
            normalized = NORMALIZE_MAP.get(term, term)
            if normalized != term:
                changed = True
            new_sf.append(normalized)
            after_counts[normalized] = after_counts.get(normalized, 0) + 1

        # Deduplicate
        new_sf = sorted(set(new_sf))

        if changed:
            changes += 1
            if apply_mode:
                db.execute(text(
                    'UPDATE products SET social_function = :sf WHERE id = :id'
                ), {'sf': json.dumps(new_sf), 'id': p.id})

                if changes % 500 == 0:
                    db.commit()
                    print(f"  [{changes} updated]")
        else:
            unchanged += 1

    if apply_mode:
        db.commit()

    print(f"\nResults:")
    print(f"  Changed: {changes}")
    print(f"  Unchanged: {unchanged}")

    # Show before/after distinct counts
    print(f"\nBefore: {len(before_counts)} distinct values")
    print(f"After:  {len(after_counts)} distinct values")

    # Show the canonical set
    print(f"\nCanonical functions (after):")
    for fn, cnt in sorted(after_counts.items(), key=lambda x: -x[1]):
        print(f"  {cnt:>5}  {fn}")

    if not apply_mode and changes > 0:
        print(f"\nRun with --apply to update {changes} products.")

    db.close()


if __name__ == '__main__':
    main()
