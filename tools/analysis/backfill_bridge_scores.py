"""
Backfill bridge scores and clean shared_entities on existing bridges.

1. Adds LINEAGE_BONUS (5.0) to lineage bridge entity_scores and recomputes bridge_score
2. Strips blocklisted entity values from shared_entities JSON

Run from project root:
  PYTHONPATH=. venv/bin/python tools/analysis/backfill_bridge_scores.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
from storage.database import SessionLocal, StyleBridge
from sqlalchemy import text

LINEAGE_BONUS = 5.0

ENTITY_BLOCKLIST = {
    'social_function': {'everyday-practical', 'status-signaling'},
    'construction_technique': {'hand-sewing', 'machine-sewing', 'tailoring'},
    'motif_family': {'none', 'geometric', 'floral'},
}


def normalize_score(raw):
    """Same sigmoid normalization as better_bridges.py"""
    return round(1 - (1 / (1 + raw / 10)), 4)


def main():
    db = SessionLocal()

    # --- Step 1: Apply lineage bonus ---
    lineage_count = db.execute(text(
        "SELECT count(*) FROM style_bridges WHERE connection_mode = 'lineage'"
    )).scalar()
    print(f"Lineage bridges to update: {lineage_count}")

    if lineage_count > 0:
        # Fetch all lineage bridges
        lineage_bridges = db.execute(text('''
            SELECT id, entity_score, bridge_score, text_similarity, image_similarity
            FROM style_bridges WHERE connection_mode = 'lineage'
        ''')).fetchall()

        updated = 0
        for bid, entity_score, bridge_score, text_sim, image_sim in lineage_bridges:
            new_entity = (entity_score or 0) + LINEAGE_BONUS

            # Recompute context_score from bridge_score is tricky — just recompute raw
            # raw = entity_score + context_score + embedding_bonus
            # We know embedding_bonus and can back-derive context_score
            emb_bonus = 0.0
            if text_sim is not None:
                emb_bonus += text_sim * 0.1
            if image_sim is not None:
                emb_bonus += image_sim * 0.1

            # Back-derive context_score from old bridge_score
            # old_normalized = 1 - 1/(1 + old_raw/10)
            # old_raw = 10 * old_normalized / (1 - old_normalized)
            if bridge_score and bridge_score < 1.0:
                old_raw = 10 * bridge_score / (1 - bridge_score)
            else:
                old_raw = 0
            old_context = old_raw - (entity_score or 0) - emb_bonus

            new_raw = new_entity + max(old_context, 0) + emb_bonus
            new_bridge_score = normalize_score(new_raw)

            db.execute(text('''
                UPDATE style_bridges
                SET entity_score = :entity, bridge_score = :bridge
                WHERE id = :bid
            '''), {'entity': round(new_entity, 4), 'bridge': new_bridge_score, 'bid': bid})
            updated += 1

        db.commit()
        print(f"  Updated {updated} lineage bridge scores")

    # --- Step 2: Strip blocklisted values from shared_entities ---
    all_bridges = db.execute(text(
        'SELECT id, shared_entities FROM style_bridges WHERE shared_entities IS NOT NULL'
    )).fetchall()

    print(f"\nCleaning shared_entities on {len(all_bridges)} bridges...")
    cleaned = 0

    for bid, se_json in all_bridges:
        shared = json.loads(se_json)
        new_shared = {}
        changed = False

        for key, val in shared.items():
            if isinstance(val, list) and key in ENTITY_BLOCKLIST:
                filtered = [v for v in val if v not in ENTITY_BLOCKLIST[key]]
                if len(filtered) != len(val):
                    changed = True
                if filtered:
                    new_shared[key] = filtered
                # else: drop the key entirely
            else:
                new_shared[key] = val

        if changed:
            db.execute(text(
                'UPDATE style_bridges SET shared_entities = :se WHERE id = :bid'
            ), {'se': json.dumps(new_shared), 'bid': bid})
            cleaned += 1

        if cleaned > 0 and cleaned % 5000 == 0:
            db.commit()
            print(f"  [{cleaned} cleaned]")

    db.commit()
    print(f"  Cleaned {cleaned} bridges")

    # --- Summary ---
    above_gate = db.execute(text(
        "SELECT count(*) FROM style_bridges WHERE connection_mode = 'lineage' AND bridge_score >= 0.55"
    )).scalar()
    print(f"\nLineage bridges above narrative gate (0.55): {above_gate}")

    db.close()
    print("Done.")


if __name__ == '__main__':
    main()
