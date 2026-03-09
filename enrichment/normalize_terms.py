"""
Normalize JSON array fields on products for vocabulary consistency.

Targets: construction_technique, social_function, motif_family
These are Jaccard-compared in bridge structural scoring — inconsistent
terms (e.g. "hand-embroidery" vs "embroidery") cause silent misses.

Usage:
  python enrichment/normalize_terms.py                # dry-run (report only)
  python enrichment/normalize_terms.py --apply        # apply changes
  python enrichment/normalize_terms.py --field=motif_family  # single field

Run from project root.
"""
import sys
import os
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product


# ---------------------------------------------------------------------------
# Canonical term maps — add entries as you find inconsistencies.
# Key = raw term (lowercased), Value = canonical form.
# Terms not in the map are kept as-is (lowercased + stripped).
# ---------------------------------------------------------------------------

CONSTRUCTION_TECHNIQUE_MAP = {
    'embroidery': 'hand-embroidery',
    'hand embroidery': 'hand-embroidery',
    'handembroidery': 'hand-embroidery',
    'machine embroidery': 'machine-embroidery',
    'resist dye': 'resist-dyeing',
    'resist-dye': 'resist-dyeing',
    'resist dyeing': 'resist-dyeing',
    'block-print': 'block-printing',
    'block print': 'block-printing',
    'blockprint': 'block-printing',
    'block printed': 'block-printing',
    'screen-print': 'screen-printing',
    'screen print': 'screen-printing',
    'screenprint': 'screen-printing',
    'screen printed': 'screen-printing',
    'hand-weaving': 'hand-weaving',
    'hand weaving': 'hand-weaving',
    'handwoven': 'hand-weaving',
    'hand-woven': 'hand-weaving',
    'hand woven': 'hand-weaving',
    'hand-knitting': 'hand-knitting',
    'hand knitting': 'hand-knitting',
    'handknit': 'hand-knitting',
    'hand-knit': 'hand-knitting',
    'hand knit': 'hand-knitting',
    'hand-stitching': 'hand-stitching',
    'hand stitching': 'hand-stitching',
    'hand stitched': 'hand-stitching',
    'hand-stitched': 'hand-stitching',
    'tailoring': 'tailoring',
    'tailored': 'tailoring',
    'drape': 'draping',
    'draped': 'draping',
    'pleat': 'pleating',
    'pleated': 'pleating',
    'pleats': 'pleating',
    'quilt': 'quilting',
    'quilted': 'quilting',
    'smock': 'smocking',
    'smocked': 'smocking',
    'crochet': 'crochet',
    'crocheted': 'crochet',
    'crocheting': 'crochet',
    'felt': 'felting',
    'felted': 'felting',
    'lace-making': 'lace-making',
    'lacemaking': 'lace-making',
    'lace making': 'lace-making',
    'bead': 'beading',
    'beaded': 'beading',
    'beadwork': 'beading',
    'bead-work': 'beading',
    'applique': 'applique',
    'appliqued': 'applique',
    'appliqué': 'applique',
    'batik': 'batik',
    'wax-resist': 'batik',
    'tie-dye': 'tie-dyeing',
    'tie dye': 'tie-dyeing',
    'tie-dyeing': 'tie-dyeing',
    'tie dyed': 'tie-dyeing',
    'ikat': 'ikat',
    'shibori': 'shibori',
}

SOCIAL_FUNCTION_MAP = {
    'wedding ceremony': 'wedding',
    'bridal': 'wedding',
    'marriage': 'wedding',
    'mourning dress': 'mourning',
    'funeral': 'mourning',
    'status signaling': 'status-signaling',
    'status-signalling': 'status-signaling',
    'status signalling': 'status-signaling',
    'social status': 'status-signaling',
    'court dress': 'court-dress',
    'court-wear': 'court-dress',
    'court wear': 'court-dress',
    'religious': 'religious-ceremony',
    'religious ceremony': 'religious-ceremony',
    'ritual': 'ritual',
    'ceremonial': 'ceremony',
    'ceremony': 'ceremony',
    'everyday': 'everyday-wear',
    'everyday wear': 'everyday-wear',
    'daily wear': 'everyday-wear',
    'casual': 'casual-wear',
    'casual wear': 'casual-wear',
    'formal': 'formal-wear',
    'formal wear': 'formal-wear',
    'formalwear': 'formal-wear',
    'evening': 'evening-wear',
    'evening wear': 'evening-wear',
    'evening-dress': 'evening-wear',
    'work': 'workwear',
    'work wear': 'workwear',
    'work-wear': 'workwear',
    'occupational': 'workwear',
    'military': 'military',
    'military uniform': 'military',
    'performance': 'performance',
    'stage': 'performance',
    'theatrical': 'performance',
    'protest': 'protest',
    'political': 'political-expression',
    'political expression': 'political-expression',
}

MOTIF_FAMILY_MAP = {
    'floral': 'floral',
    'flower': 'floral',
    'flowers': 'floral',
    'botanical': 'floral',
    'geometric': 'geometric',
    'geometrics': 'geometric',
    'stripe': 'stripes',
    'striped': 'stripes',
    'check': 'checks',
    'checked': 'checks',
    'checkered': 'checks',
    'plaid': 'plaid',
    'tartan': 'plaid',
    'polka dot': 'polka-dots',
    'polka dots': 'polka-dots',
    'polka-dot': 'polka-dots',
    'dot': 'polka-dots',
    'dots': 'polka-dots',
    'dotted': 'polka-dots',
    'paisley': 'paisley',
    'animal': 'animal-print',
    'animal print': 'animal-print',
    'leopard': 'animal-print',
    'zebra': 'animal-print',
    'abstract': 'abstract',
    'chevron': 'chevron',
    'zigzag': 'chevron',
    'zig-zag': 'chevron',
    'zig zag': 'chevron',
    'herringbone': 'herringbone',
    'houndstooth': 'houndstooth',
    "hound's tooth": 'houndstooth',
    'toile': 'toile',
    'damask': 'damask',
    'brocade': 'brocade',
    'jacquard': 'jacquard',
    'ikat': 'ikat',
    'medallion': 'medallion',
    'scroll': 'scrollwork',
    'scrollwork': 'scrollwork',
    'scroll-work': 'scrollwork',
    'figurative': 'figurative',
    'figural': 'figurative',
    'calligraphic': 'calligraphic',
    'calligraphy': 'calligraphic',
}

FIELD_MAPS = {
    'construction_technique': CONSTRUCTION_TECHNIQUE_MAP,
    'social_function': SOCIAL_FUNCTION_MAP,
    'motif_family': MOTIF_FAMILY_MAP,
}


# ---------------------------------------------------------------------------
# Normalization logic
# ---------------------------------------------------------------------------

def normalize_term(raw, term_map):
    """Normalize a single term: lowercase, strip, then map."""
    cleaned = raw.strip().lower()
    return term_map.get(cleaned, cleaned)


def normalize_field(product, field, term_map):
    """Normalize a JSON array field. Returns (new_value, changes) or (None, None) if no field."""
    raw = getattr(product, field, None)
    if not raw:
        return None, None

    try:
        terms = json.loads(raw) if isinstance(raw, str) else list(raw)
    except (json.JSONDecodeError, TypeError):
        return None, None

    if not terms:
        return None, None

    normalized = []
    changes = []
    seen = set()

    for term in terms:
        original = term.strip().lower()
        mapped = normalize_term(term, term_map)
        if mapped not in seen:
            normalized.append(mapped)
            seen.add(mapped)
        if original != mapped:
            changes.append((term.strip(), mapped))

    # Also check if dedup removed anything
    if len(normalized) == len(terms) and not changes:
        return None, None

    return json.dumps(sorted(normalized)), changes


def run(fields=None, apply=False):
    """Normalize terms across specified fields."""
    if fields is None:
        fields = list(FIELD_MAPS.keys())

    db = SessionLocal()
    products = db.query(Product).all()

    print(f"\n{'=' * 60}")
    print(f"TERM NORMALIZATION {'(DRY RUN)' if not apply else '(APPLYING)'}")
    print(f"{'=' * 60}")
    print(f"\nProducts: {len(products)}")
    print(f"Fields:   {', '.join(fields)}\n")

    total_changes = 0

    for field in fields:
        term_map = FIELD_MAPS[field]
        print(f"\n--- {field} ---")

        # First pass: collect all distinct terms for reporting
        all_terms = {}
        for p in products:
            raw = getattr(p, field, None)
            if not raw:
                continue
            try:
                terms = json.loads(raw) if isinstance(raw, str) else list(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            for t in terms:
                key = t.strip().lower()
                all_terms[key] = all_terms.get(key, 0) + 1

        print(f"  Distinct terms: {len(all_terms)}")

        # Show what will be mapped
        mapped_count = 0
        unmapped = []
        for term, count in sorted(all_terms.items(), key=lambda x: -x[1]):
            canonical = term_map.get(term)
            if canonical and canonical != term:
                print(f"    {term:30s} -> {canonical:30s} ({count} products)")
                mapped_count += 1
            else:
                unmapped.append((term, count))

        if mapped_count == 0:
            print("  No mappings to apply.")

        # Show top unmapped terms (might need adding to map)
        if unmapped:
            print(f"\n  Top unmapped terms (review for near-duplicates):")
            for term, count in unmapped[:30]:
                print(f"    {term:30s} ({count})")

        # Second pass: apply normalization
        field_changes = 0
        for p in products:
            new_val, changes = normalize_field(p, field, term_map)
            if new_val is not None:
                field_changes += 1
                if apply:
                    setattr(p, field, new_val)

        print(f"\n  Products to update: {field_changes}")
        total_changes += field_changes

    if apply and total_changes > 0:
        db.commit()
        print(f"\n{'=' * 60}")
        print(f"COMMITTED {total_changes} product updates")
        print(f"{'=' * 60}")
    elif total_changes > 0:
        print(f"\n{'=' * 60}")
        print(f"DRY RUN — {total_changes} products would be updated")
        print(f"Run with --apply to commit changes")
        print(f"{'=' * 60}")
    else:
        print(f"\nNo changes needed.")

    db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Normalize JSON array terms on products')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    parser.add_argument('--field', type=str, default=None,
                        help='Single field to normalize (construction_technique, social_function, motif_family)')
    args = parser.parse_args()

    fields = [args.field] if args.field else None
    run(fields=fields, apply=args.apply)
