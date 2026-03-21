"""
One-time migration: consolidate social_function values into canonical cluster vocab.

Canonical values (pass-throughs + clusters):
  Pass-throughs (already clean):
    status-signaling, everyday-practical, court-formal, performance-costume,
    sportswear, workwear, military-uniform, wedding, mourning, academic-formal,
    diplomatic-gift, dance, maternity, leisure-resort, festival-celebration,
    cultural-heritage, formal-evening, ceremonial, artistic-expression,
    subculture-identity

  New cluster names:
    ceremonial          — all ceremony/religious/civic variants
    formal-evening      — all dress-up/evening variants
    artistic-expression — art, avant-garde, experimental, decorative, none
    subculture-identity — subculture, protest, youth, counter, streetwear
    cultural-heritage   — cultural preservation/identity/revival
    festival-celebration— celebration, coming-of-age, commemorative
    leisure-resort      — leisure, resort, luxury-casual

Multi-value mappings (value spans two clusters):
    artistic-formal     -> [artistic-expression, formal-evening]
    artistic-ceremonial -> [artistic-expression, ceremonial]
    ceremonial-artistic -> [ceremonial, artistic-expression]
    luxury-fashion      -> [artistic-expression, status-signaling]
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import SessionLocal
from sqlalchemy import text

# Maps old value -> list of canonical values
# Single-item lists = single cluster; multi-item = spans clusters
VALUE_MAP = {
    # --- CEREMONIAL cluster ---
    'ceremony':               ['ceremonial'],
    'ceremonial-formal':      ['ceremonial'],
    'ceremonial-accessory':   ['ceremonial'],
    'ceremonial-fraternal':   ['ceremonial'],
    'ceremonial-gift':        ['ceremonial'],
    'formal-ceremonial':      ['ceremonial'],
    'civic-ceremonial':       ['ceremonial'],
    'cultural-ceremonial':    ['ceremonial'],
    'patriotic-ceremonial':   ['ceremonial'],
    'religious-ceremonial':   ['ceremonial'],

    # --- FORMAL-EVENING cluster ---
    'evening-formal':         ['formal-evening'],
    'evening-social':         ['formal-evening'],
    'evening-entertainment':  ['formal-evening'],
    'eveningwear':            ['formal-evening'],
    'formal-dress':           ['formal-evening'],
    'formal-indoor':          ['formal-evening'],
    'formal-visiting':        ['formal-evening'],
    'formal-contemporary':    ['formal-evening'],
    'formal-social':          ['formal-evening'],
    'formal-wear':            ['formal-evening'],

    # --- ARTISTIC-EXPRESSION cluster ---
    'artistic-statement':     ['artistic-expression'],
    'artistic statement':     ['artistic-expression'],
    'artistic-portrait':      ['artistic-expression'],
    'artistic-documentation': ['artistic-expression'],
    'artistic-avant-garde':   ['artistic-expression'],
    'avant-garde fashion':    ['artistic-expression'],
    'experimental-art':       ['artistic-expression'],
    'experimental-fashion':   ['artistic-expression'],
    'fashion-industry':       ['artistic-expression'],
    'design-reference':       ['artistic-expression'],
    'textile-reference':      ['artistic-expression'],
    'decorative-display':     ['artistic-expression'],
    'decorative-textile':     ['artistic-expression'],
    'representation':         ['artistic-expression'],
    'none':                   ['artistic-expression'],

    # --- SUBCULTURE-IDENTITY cluster ---
    'protest-subculture':     ['subculture-identity'],
    'subculture':             ['subculture-identity'],
    'subculture-signaling':   ['subculture-identity'],
    'subcultural-identity':   ['subculture-identity'],
    'subculture-expression':  ['subculture-identity'],
    'youth-subculture':       ['subculture-identity'],
    'youth culture':          ['subculture-identity'],
    'youth-culture':          ['subculture-identity'],
    'youth-fashion':          ['subculture-identity'],
    'youth-identity':         ['subculture-identity'],
    'counterculture':         ['subculture-identity'],
    'dress-reform':           ['subculture-identity'],
    'streetwear':             ['subculture-identity'],

    # --- CULTURAL-HERITAGE cluster ---
    'cultural-celebration':   ['cultural-heritage'],
    'cultural-preservation':  ['cultural-heritage'],
    'cultural-identity':      ['cultural-heritage'],
    'cultural celebration':   ['cultural-heritage'],
    'cultural commentary':    ['cultural-heritage'],
    'cultural revival':       ['cultural-heritage'],
    'cultural-revival':       ['cultural-heritage'],
    'cultural-bridge':        ['cultural-heritage'],
    'cultural-expression':    ['cultural-heritage'],

    # --- FESTIVAL-CELEBRATION cluster ---
    'celebration':            ['festival-celebration'],
    'coming-of-age':          ['festival-celebration'],
    'commemorative':          ['festival-celebration'],
    'commemorative-patriotic':['festival-celebration'],
    'cultural-celebration':   ['cultural-heritage'],  # already above, redundant

    # --- LEISURE-RESORT cluster ---
    'luxury-resort':          ['leisure-resort'],
    'luxury-casual':          ['leisure-resort'],
    'leisure-toy':            ['leisure-resort'],
    'play':                   ['leisure-resort'],
    'play-toy':               ['leisure-resort'],

    # --- MULTI-CLUSTER spans ---
    'artistic-formal':        ['artistic-expression', 'formal-evening'],
    'artistic-ceremonial':    ['artistic-expression', 'ceremonial'],
    'ceremonial-artistic':    ['ceremonial', 'artistic-expression'],
    'luxury-fashion':         ['artistic-expression', 'status-signaling'],

    # --- FOLD INTO EXISTING PASS-THROUGHS ---
    'maternity-support':      ['maternity'],
    'fitness-training':       ['sportswear'],
    'institutional-uniform':  ['military-uniform'],
    'medical-uniform':        ['military-uniform'],
    'entertainment-industry': ['performance-costume'],

    # Pass-throughs (identity mapping — listed here for completeness)
    'status-signaling':       ['status-signaling'],
    'everyday-practical':     ['everyday-practical'],
    'court-formal':           ['court-formal'],
    'performance-costume':    ['performance-costume'],
    'sportswear':             ['sportswear'],
    'workwear':               ['workwear'],
    'military-uniform':       ['military-uniform'],
    'wedding':                ['wedding'],
    'mourning':               ['mourning'],
    'academic-formal':        ['academic-formal'],
    'diplomatic-gift':        ['diplomatic-gift'],
    'dance':                  ['dance'],
    'maternity':              ['maternity'],
    'leisure-resort':         ['leisure-resort'],
    'festival-celebration':   ['festival-celebration'],
    'cultural-heritage':      ['cultural-heritage'],
    'formal-evening':         ['formal-evening'],
    'ceremonial':             ['ceremonial'],
    'artistic-expression':    ['artistic-expression'],
    'subculture-identity':    ['subculture-identity'],

    # Uncommon pass-throughs (distinct enough to keep)
    'hunting':                ['hunting'],
    'courtship':              ['courtship'],
    'body-shaping':           ['body-shaping'],
    'body-modification':      ['body-modification'],
    'novelty-gift':           ['novelty-gift'],
    'infant-care':            ['infant-care'],
    'medical-adaptive':       ['medical-adaptive'],
}


def consolidate(dry_run=True):
    db = SessionLocal()
    rows = db.execute(text(
        "SELECT id, social_function FROM products WHERE social_function IS NOT NULL"
    )).fetchall()

    updated = 0
    unmapped = set()

    for product_id, sf_raw in rows:
        try:
            old_values = json.loads(sf_raw) if isinstance(sf_raw, str) else sf_raw
        except Exception:
            continue
        if not old_values:
            continue

        new_values = []
        for v in old_values:
            mapped = VALUE_MAP.get(v.strip())
            if mapped:
                new_values.extend(mapped)
            else:
                unmapped.add(v.strip())
                new_values.append(v.strip())  # keep as-is if not in map

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for v in new_values:
            if v not in seen:
                seen.add(v)
                deduped.append(v)

        if deduped != old_values:
            updated += 1
            if dry_run:
                print(f"id={product_id}: {old_values} -> {deduped}")
            else:
                db.execute(
                    text("UPDATE products SET social_function = :v WHERE id = :id"),
                    {"v": json.dumps(deduped), "id": product_id}
                )

    if unmapped:
        print(f"\nWARNING: {len(unmapped)} unmapped values (kept as-is):")
        for v in sorted(unmapped):
            print(f"  {v}")

    print(f"\n{'[DRY RUN] Would update' if dry_run else 'Updated'} {updated} products.")

    if not dry_run:
        db.commit()
    db.close()


if __name__ == '__main__':
    import sys
    dry_run = '--apply' not in sys.argv
    if dry_run:
        print("DRY RUN — pass --apply to write changes\n")
    consolidate(dry_run=dry_run)
