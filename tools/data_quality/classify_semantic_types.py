import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
from sqlalchemy import func
from storage.database import SessionLocal, StyleBridge

def classify_semantic_type(bridge) -> str:
    btype  = bridge.bridge_type or ''
    score  = bridge.text_similarity or 0  # was bridge_score (removed)
    tsim   = bridge.text_similarity or 0
    struct = bridge.structural_score or 0
    attrs  = json.loads(bridge.shared_attributes or '{}')

    if 'silhouette' in attrs and btype == 'transmission':
        return 'SILHOUETTE_TRANSMISSION'
    if btype == 'transmission' and score > 0.6 and tsim > 0.85:
        return 'CROSS_ERA_CITATION'
    if btype == 'cross_vibe' and score > 0.6:
        return 'COUNTER_ARGUMENT'
    if btype == 'transmission' and 'material' in attrs:
        return 'MATERIAL_ECHO'
    if btype in ('cross_category', 'near_era') and struct > 0.5:
        return 'PARALLEL_EMERGENCE'
    if btype == 'continuation' and struct > 0.7:
        return 'STRUCTURAL_SIBLING'
    if btype == 'transmission':
        return 'CONSTRUCTION_INHERITANCE'
    return 'STRUCTURAL_SIBLING'

def run():
    db = SessionLocal()
    bridges = db.query(StyleBridge).all()
    for bridge in bridges:
        bridge.semantic_type = classify_semantic_type(bridge)
    db.commit()
    print(f"Classified {len(bridges)} bridges")

    dist = db.query(
        StyleBridge.semantic_type,
        func.count(StyleBridge.id)
    ).group_by(StyleBridge.semantic_type).all()

    for stype, count in sorted(dist, key=lambda x: -x[1]):
        print(f"  {stype}: {count}")
    db.close()

if __name__ == '__main__':
    run()
