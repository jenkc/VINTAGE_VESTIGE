"""
Audit and fix era misclassifications.

Finds products where the era doesn't match the decade/object_date.
Reports mismatches and optionally fixes them using the era_taxonomy.

Usage:
  PYTHONPATH=. python tools/analysis/audit_eras.py              # audit only
  PYTHONPATH=. python tools/analysis/audit_eras.py --fix        # audit + fix
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import re
import json
from storage.database import SessionLocal, Product
from enrichment.era_taxonomy import year_to_era
from sqlalchemy import text

# ERA_MIDPOINTS for reverse lookup (era → approximate year range)
ERA_YEAR_RANGES = {
    'Ancient Roman': (0, 400),
    'Gothic / High Medieval': (1100, 1350),
    'Late Medieval': (1350, 1450),
    'Northern Renaissance': (1450, 1500),
    'Italian Renaissance': (1450, 1530),
    'Renaissance': (1450, 1600),
    'Elizabethan': (1558, 1603),
    'Jacobean': (1603, 1625),
    'Restoration': (1660, 1685),
    'Baroque': (1620, 1720),
    'Rococo': (1720, 1780),
    'Neoclassical Transition': (1760, 1790),
    'Revolutionary / Directoire': (1789, 1804),
    'Empire / Regency': (1804, 1830),
    'Romantic': (1825, 1850),
    'Victorian Early / Crinoline': (1840, 1870),
    'Victorian Late / Bustle': (1870, 1900),
    'Belle Epoque': (1880, 1914),
    'Fin de Siecle / Gibson Girl': (1890, 1910),
    'Edwardian': (1901, 1914),
    'World War I Transition': (1914, 1920),
    'Roaring Twenties / Art Deco': (1920, 1930),
    'Great Depression': (1930, 1940),
    'Wartime / Utility Fashion': (1940, 1947),
    'New Look / Post-War': (1947, 1955),
    'Atomic Age': (1950, 1960),
    'Space Age': (1960, 1970),
    'Hippie / Counterculture': (1965, 1975),
    'Glam Rock': (1970, 1978),
    'Punk': (1975, 1980),
    'Disco': (1975, 1980),
    'New Romanticism': (1980, 1985),
    'Power Dressing': (1983, 1990),
    'Hip-Hop': (1985, 1995),
    'Grunge': (1990, 1996),
    'Rave / Club Kid': (1990, 1997),
    'Supermodel Era': (1994, 2000),
    'Minimalism': (1995, 2005),
    'Y2K': (2000, 2006),
    'Indie Sleaze': (2005, 2012),
    'Normcore': (2008, 2015),
    'Dark Academia': (2012, 2020),
    'Athleisure': (2013, 2020),
    'Gorpcore': (2016, 2024),
    'Cottagecore': (2018, 2022),
    'Dopamine Dressing': (2020, 2024),
    'Quiet Luxury': (2020, 2026),
    'Preppy / Ivy League': (2020, 2026),
}


def parse_year(s):
    """Extract a 4-digit year from a string."""
    if not s:
        return None
    m = re.search(r'(\d{4})', str(s))
    return int(m.group(1)) if m else None


def era_matches_year(era, year, tolerance=15):
    """Check if an era is plausible for a given year, with tolerance."""
    if not era or not year:
        return True  # can't check, assume OK
    year_range = ERA_YEAR_RANGES.get(era)
    if not year_range:
        return True  # unknown era, assume OK
    return (year_range[0] - tolerance) <= year <= (year_range[1] + tolerance)


def main():
    fix_mode = '--fix' in sys.argv
    db = SessionLocal()

    products = db.query(Product).filter(Product.enriched_at.isnot(None)).all()
    print(f'Auditing {len(products)} enriched products...\n')

    mismatches = []
    no_date = 0
    ok = 0

    for p in products:
        # Get the best year from decade or object_date
        year = None
        if p.decade:
            year = parse_year(p.decade)
        if not year and p.object_date:
            year = parse_year(p.object_date)

        if not year:
            no_date += 1
            continue

        if not p.era:
            continue

        if era_matches_year(p.era, year):
            ok += 1
        else:
            correct_era = year_to_era(year)
            mismatches.append({
                'id': p.id,
                'title': p.title[:50],
                'platform': p.platform,
                'current_era': p.era,
                'decade': p.decade,
                'object_date': p.object_date,
                'year': year,
                'correct_era': correct_era,
            })

    print(f'Results:')
    print(f'  OK:          {ok}')
    print(f'  Mismatched:  {len(mismatches)}')
    print(f'  No date:     {no_date}')

    if mismatches:
        print(f'\nMismatches:')
        # Group by type of mismatch
        by_shift = {}
        for m in mismatches:
            key = f'{m["current_era"]} → {m["correct_era"]}'
            by_shift.setdefault(key, []).append(m)

        for shift, items in sorted(by_shift.items(), key=lambda x: -len(x[1])):
            print(f'\n  {shift} ({len(items)} items):')
            for item in items[:5]:
                print(f'    id={item["id"]:>5} [{item["platform"]:12s}] '
                      f'"{item["title"]}" decade={item["decade"]} date={item["object_date"]}')
            if len(items) > 5:
                print(f'    ... and {len(items) - 5} more')

    if fix_mode and mismatches:
        print(f'\n--- FIXING {len(mismatches)} mismatched eras ---')
        fixed = 0
        for m in mismatches:
            if m['correct_era']:
                db.execute(text(
                    'UPDATE products SET era = :era WHERE id = :id'
                ), {'era': m['correct_era'], 'id': m['id']})
                fixed += 1

        db.commit()
        print(f'Fixed: {fixed}')
    elif mismatches and not fix_mode:
        print(f'\nRun with --fix to correct these.')

    db.close()


if __name__ == '__main__':
    main()
