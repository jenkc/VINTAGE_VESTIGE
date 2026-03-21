"""
Remove non-garment items from the database.

Deletes fashion plates, illustrations, photographs, fabric samples,
lithographs, bouquet holders, and other non-wearable items.

Usage:
  PYTHONPATH=. python tools/analysis/remove_non_garments.py          # preview
  PYTHONPATH=. python tools/analysis/remove_non_garments.py --apply  # apply
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from storage.database import SessionLocal, Product, StyleBridge
from sqlalchemy import or_

# Non-garment categories to remove (case-sensitive, matches `category` field)
NON_GARMENT_CATEGORIES = {
    # V&A
    'Fashion design',
    'Photograph',
    'Print',
    'Fashion plate',
    'Dress fabric',
    'Drawing',
    'Painting',
    'Poster',
    'Negative',
    'Slide',
    'Postcard',
    'Catalogue',
    'Pattern',

    # Smithsonian
    'Lithographs',
    'Silhouettes',
    'Bouquet holders',
    'Insignias',
    'Graphic arts',
    'Buttons (fasteners)',
    'Embroidery (visual works)',
    'Collages (visual works)',
    'Quilts',
    'Chromolithographs',
    'Christmas cards',
    'Idiophones',
    'Measuring devices',
    'Coat hangers',
    'Trunks (containers)',
    'straight pins',
    'Needle cases',
    'Labels (identifying artifacts)',
    'Personal equipment: grooming, hygiene and health care',
    'Decorative arts',
    'Bed coverings',
    'Napkins',
    'Border fragments',
    'Remnants',
    'canvas work',
    'Textile and Fiber Arts',
    'Busks',
    'case, vanity',
    'pocket watches',
    'wrist watches',
    'shoe trees',
    'Buckles (strap accessories)',

    # Met
    'Fashion Plate',
    'Button',
    'Cane',
    'Equipment',
    'Lace',
    'Ribbon',
    'Shoe Buckles',
    'Hairpin',
    'Busk',
    'Garters',
    'Suspenders',
}


def main():
    apply_mode = '--apply' in sys.argv
    db = SessionLocal()

    # Find products to remove
    to_remove = db.query(Product).filter(
        Product.category.in_(NON_GARMENT_CATEGORIES)
    ).all()

    remove_ids = {p.id for p in to_remove}

    print(f"Non-garment products to remove: {len(remove_ids)}")

    # Count by platform
    by_platform = {}
    by_category = {}
    for p in to_remove:
        by_platform[p.platform] = by_platform.get(p.platform, 0) + 1
        by_category[p.category] = by_category.get(p.category, 0) + 1

    print("\nBy platform:")
    for plat, cnt in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"  {plat}: {cnt}")

    print("\nBy category:")
    for cat, cnt in sorted(by_category.items(), key=lambda x: -x[1])[:20]:
        print(f"  {cnt:>4}  {cat}")

    if not remove_ids:
        print("\nNothing to remove.")
        db.close()
        return

    # Count affected bridges
    bridge_count = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id.in_(remove_ids),
            StyleBridge.target_id.in_(remove_ids),
        )
    ).count()
    print(f"\nBridges to remove: {bridge_count}")

    total_products = db.query(Product).count()
    total_bridges = db.query(StyleBridge).count()
    print(f"\nBefore: {total_products} products, {total_bridges} bridges")
    print(f"After:  {total_products - len(remove_ids)} products, {total_bridges - bridge_count} bridges")

    if not apply_mode:
        print(f"\nRun with --apply to remove {len(remove_ids)} products and {bridge_count} bridges.")
        db.close()
        return

    # Delete bridges first
    print("\nDeleting bridges...")
    deleted_bridges = db.query(StyleBridge).filter(
        or_(
            StyleBridge.source_id.in_(remove_ids),
            StyleBridge.target_id.in_(remove_ids),
        )
    ).delete(synchronize_session=False)
    db.commit()
    print(f"  Deleted {deleted_bridges} bridges")

    # Delete products
    print("Deleting products...")
    deleted_products = db.query(Product).filter(
        Product.id.in_(remove_ids)
    ).delete(synchronize_session=False)
    db.commit()
    print(f"  Deleted {deleted_products} products")

    # Verify
    remaining = db.query(Product).count()
    remaining_bridges = db.query(StyleBridge).count()
    print(f"\nDone: {remaining} products, {remaining_bridges} bridges remaining")

    db.close()


if __name__ == '__main__':
    main()
