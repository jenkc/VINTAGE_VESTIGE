"""
Normalize existing era values in the database to canonical era names.

Reads all distinct Product.era values, maps them through normalize_era(),
reports what changed, and updates the database.

Usage:
  python enrichment/scripts/normalize_eras.py          # dry-run (report only)
  python enrichment/scripts/normalize_eras.py --apply   # apply changes

Run from project root.
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product
from enrichment.era_taxonomy import normalize_era, ERA_NAMES


def normalize_eras(apply=False):
    print("\n" + "=" * 60)
    print("ERA NORMALIZATION REPORT")
    print("=" * 60)

    db = SessionLocal()

    # Get all distinct era values
    distinct_eras = [
        r[0] for r in db.query(Product.era).distinct().all() if r[0]
    ]
    distinct_eras.sort()

    print(f"\nDistinct era values in database: {len(distinct_eras)}")
    print()

    mapped = []
    already_canonical = []
    unrecognized = []

    for raw in distinct_eras:
        normalized = normalize_era(raw)
        count = db.query(Product).filter(Product.era == raw).count()

        if normalized == raw and raw in ERA_NAMES:
            already_canonical.append((raw, count))
        elif normalized != raw and normalized in ERA_NAMES:
            mapped.append((raw, normalized, count))
        else:
            unrecognized.append((raw, normalized, count))

    # Report
    if already_canonical:
        print(f"Already canonical ({len(already_canonical)}):")
        for era, count in already_canonical:
            print(f"  {era} ({count} items)")

    if mapped:
        print(f"\nWill be mapped ({len(mapped)}):")
        for raw, normalized, count in mapped:
            print(f"  '{raw}' -> '{normalized}' ({count} items)")

    if unrecognized:
        print(f"\nUnrecognized - no mapping found ({len(unrecognized)}):")
        for raw, normalized, count in unrecognized:
            print(f"  '{raw}' ({count} items)")

    # Null count
    null_count = db.query(Product).filter(Product.era.is_(None)).count()
    print(f"\nNull era: {null_count} items")

    total_to_update = sum(count for _, _, count in mapped)
    print(f"\nTotal items to update: {total_to_update}")

    if not apply:
        print("\nDry run. Use --apply to update the database.")
        db.close()
        return

    # Apply updates
    if not mapped:
        print("\nNothing to update.")
        db.close()
        return

    print("\nApplying updates...")
    for raw, normalized, count in mapped:
        db.query(Product).filter(Product.era == raw).update(
            {Product.era: normalized}, synchronize_session='fetch'
        )
        print(f"  Updated {count}: '{raw}' -> '{normalized}'")
    db.commit()

    print("\nDone!")
    db.close()


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    normalize_eras(apply=apply)
