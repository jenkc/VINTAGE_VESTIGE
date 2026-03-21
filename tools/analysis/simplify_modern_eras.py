"""
Simplify post-1950 eras to decade names (1950s, 1960s, etc.)
Preserves the old era name in named_movements before overwriting.

Usage:
  PYTHONPATH=. python tools/analysis/simplify_modern_eras.py          # preview
  PYTHONPATH=. python tools/analysis/simplify_modern_eras.py --apply  # apply
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from storage.database import SessionLocal, Product
from sqlalchemy import text

# Eras that map to decades (post-1950)
ERA_TO_DECADE = {
    # 1950s
    'New Look / Post-War': '1950s',
    'Atomic Age': '1950s',
    # 1960s
    'Space Age': '1960s',
    # 1970s
    'Hippie / Counterculture': '1970s',
    'Glam Rock': '1970s',
    'Punk': '1970s',
    'Disco': '1970s',
    # 1980s
    'New Romanticism': '1980s',
    'Power Dressing': '1980s',
    # 1990s
    'Hip-Hop': '1990s',
    'Grunge': '1990s',
    'Rave / Club Kid': '1990s',
    'Supermodel Era': '1990s',
    'Minimalism': '1990s',
    # 2000s
    'Y2K': '2000s',
    'Indie Sleaze': '2000s',
    # 2010s
    'Normcore': '2010s',
    'Dark Academia': '2010s',
    'Athleisure': '2010s',
    'Gorpcore': '2010s',
    # 2020s
    'Cottagecore': '2020s',
    'Dopamine Dressing': '2020s',
    'Quiet Luxury': '2020s',
    'Preppy / Ivy League': '2020s',
}

# These are already decade names — skip movement preservation
ALREADY_DECADE = {'1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s'}


def main():
    apply_mode = '--apply' in sys.argv
    db = SessionLocal()

    products = db.query(Product).filter(
        Product.era.in_(list(ERA_TO_DECADE.keys())),
        Product.enriched_at != None,
    ).all()

    print(f"Products with post-1950 named eras: {len(products)}")

    # Count by current era
    era_counts = {}
    for p in products:
        era_counts[p.era] = era_counts.get(p.era, 0) + 1
    print("\nCurrent eras:")
    for era, cnt in sorted(era_counts.items(), key=lambda x: -x[1]):
        print(f"  {cnt:>4}  {era} → {ERA_TO_DECADE[era]}")

    changed = 0
    movements_added = 0

    for p in products:
        old_era = p.era
        new_era = ERA_TO_DECADE.get(old_era)
        if not new_era:
            continue

        # Parse current named_movements
        nm = p.named_movements
        if isinstance(nm, str):
            try:
                nm = json.loads(nm)
            except (json.JSONDecodeError, TypeError):
                nm = []
        if not isinstance(nm, list):
            nm = []

        # Preserve old era name as a movement (if not already there)
        movement_name = old_era
        if movement_name not in nm and movement_name not in ALREADY_DECADE:
            nm.append(movement_name)
            movements_added += 1

        if apply_mode:
            db.execute(text(
                'UPDATE products SET era = :era, named_movements = :nm WHERE id = :id'
            ), {'era': new_era, 'nm': json.dumps(nm), 'id': p.id})

            if changed % 500 == 0 and changed > 0:
                db.commit()
                print(f"  [{changed} updated]")

        changed += 1

    if apply_mode:
        db.commit()

    print(f"\nResults:")
    print(f"  Eras simplified: {changed}")
    print(f"  Movements preserved: {movements_added}")

    if not apply_mode and changed > 0:
        print(f"\nRun with --apply to update {changed} products.")

    # Show what the new era distribution looks like
    if apply_mode:
        print("\nNew era distribution (post-1950):")
        rows = db.execute(text('''
            SELECT era, count(*) FROM products
            WHERE era IN ('1950s','1960s','1970s','1980s','1990s','2000s','2010s','2020s')
            GROUP BY era ORDER BY era
        ''')).fetchall()
        for era, cnt in rows:
            print(f"  {era}: {cnt}")

    db.close()


if __name__ == '__main__':
    main()
