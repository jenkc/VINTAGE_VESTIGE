"""
Generate an HTML report visualizing style bridges.

Usage:
  python tests/data_integrity/bridge_report.py [--limit=N] [--type=transmission]

Run from project root.
"""

import sys
import os
import json
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from storage.database import SessionLocal, Product, StyleBridge


def generate_report(limit=100, bridge_type=None, output='bridge_report.html'):
    db = SessionLocal()

    # Query bridges
    query = db.query(StyleBridge).order_by(StyleBridge.text_similarity.desc())
    if bridge_type:
        query = query.filter(StyleBridge.bridge_type == bridge_type)
    bridges = query.limit(limit).all()

    if not bridges:
        print("No bridges found.")
        db.close()
        return

    # Collect all product IDs we need
    product_ids = set()
    for b in bridges:
        product_ids.add(b.source_id)
        product_ids.add(b.target_id)

    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    # Bridge type stats
    type_counts = {}
    for b in bridges:
        type_counts[b.bridge_type] = type_counts.get(b.bridge_type, 0) + 1

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Style Bridge Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Georgia', serif;
    background: #1a1a1a;
    color: #e8e0d4;
    padding: 2rem;
  }}
  h1 {{
    text-align: center;
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #f5efe6;
    letter-spacing: 2px;
  }}
  .subtitle {{
    text-align: center;
    font-size: 0.9rem;
    color: #998f80;
    margin-bottom: 2rem;
  }}
  .filters {{
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    padding: 0.4rem 1rem;
    border: 1px solid #444;
    border-radius: 20px;
    background: transparent;
    color: #c8bfb0;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85rem;
    transition: all 0.2s;
  }}
  .filter-btn:hover, .filter-btn.active {{
    background: #3a3530;
    border-color: #8a7f70;
    color: #f5efe6;
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-bottom: 2rem;
    font-size: 0.85rem;
    color: #998f80;
  }}
  .stat-num {{ color: #d4c9b8; font-weight: bold; }}

  .bridge-card {{
    background: #252220;
    border: 1px solid #3a3530;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    overflow: hidden;
    transition: border-color 0.2s;
  }}
  .bridge-card:hover {{
    border-color: #5a5040;
  }}
  .bridge-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.8rem 1.2rem;
    background: #2a2725;
    border-bottom: 1px solid #3a3530;
  }}
  .bridge-score {{
    font-size: 1.4rem;
    font-weight: bold;
    color: #d4a574;
  }}
  .bridge-type {{
    font-size: 0.75rem;
    padding: 0.25rem 0.7rem;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: bold;
  }}
  .type-transmission {{ background: #3d2b2b; color: #e8a0a0; }}
  .type-continuation {{ background: #3d332b; color: #e8c8a0; }}
  .type-revival {{ background: #3d3a2b; color: #e8d8a0; }}
  .type-cross_category {{ background: #2b2b3d; color: #a0a0e8; }}
  .type-cross_vibe {{ background: #3d2b3d; color: #d8a0e8; }}
  .type-cross_culture {{ background: #2b3d2f; color: #a0e8c0; }}

  .bridge-body {{
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 0;
  }}
  .item {{
    padding: 1rem 1.2rem;
  }}
  .item-img {{
    width: 100%;
    height: 200px;
    object-fit: contain;
    background: #1e1c1a;
    border-radius: 8px;
    margin-bottom: 0.8rem;
  }}
  .no-image {{
    width: 100%;
    height: 200px;
    background: #2a2725;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #665f55;
    margin-bottom: 0.8rem;
  }}
  .item-title {{
    font-size: 0.95rem;
    font-weight: bold;
    color: #e8e0d4;
    margin-bottom: 0.4rem;
    line-height: 1.3;
  }}
  .item-meta {{
    font-size: 0.8rem;
    color: #998f80;
    line-height: 1.6;
  }}
  .item-meta span {{
    display: inline-block;
    background: #2a2725;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin: 0.1rem 0;
  }}
  .item-platform {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #776f65;
    margin-bottom: 0.3rem;
  }}

  .bridge-connector {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1rem 0.5rem;
    min-width: 60px;
  }}
  .connector-arrow {{
    font-size: 1.5rem;
    color: #5a5040;
    margin: 0.3rem 0;
  }}
  .connector-scores {{
    font-size: 0.7rem;
    color: #776f65;
    text-align: center;
    line-height: 1.6;
  }}

  .shared-attrs {{
    padding: 0.6rem 1.2rem;
    background: #2a2725;
    border-top: 1px solid #3a3530;
    font-size: 0.8rem;
  }}
  .shared-label {{
    color: #776f65;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.3rem;
  }}
  .shared-tag {{
    display: inline-block;
    background: #3a3530;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    margin: 0.15rem;
    color: #c8bfb0;
  }}
</style>
</head>
<body>

<h1>VINTAGE VESTIGE</h1>
<p class="subtitle">Style Bridge Report &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="stats">
  <span><span class="stat-num">{len(bridges)}</span> bridges shown</span>
  <span><span class="stat-num">{len(product_map)}</span> unique items</span>
  <span><span class="stat-num">{len(type_counts)}</span> bridge types</span>
</div>

<div class="filters">
  <button class="filter-btn active" onclick="filterBridges('all')">All</button>
"""

    for bt in sorted(type_counts.keys()):
        html += f'  <button class="filter-btn" onclick="filterBridges(\'{bt}\')">{bt} ({type_counts[bt]})</button>\n'

    html += '</div>\n\n'

    # Bridge cards
    for b in bridges:
        src = product_map.get(b.source_id)
        tgt = product_map.get(b.target_id)
        if not src or not tgt:
            continue

        shared = json.loads(b.shared_attributes) if b.shared_attributes else {}

        # Source image
        if src.primary_image and src.primary_image.startswith('data:image'):
            src_img = f'<img class="item-img" src="{src.primary_image}" alt="{src.title}">'
        else:
            src_img = '<div class="no-image">No image</div>'

        # Target image
        if tgt.primary_image and tgt.primary_image.startswith('data:image'):
            tgt_img = f'<img class="item-img" src="{tgt.primary_image}" alt="{tgt.title}">'
        else:
            tgt_img = '<div class="no-image">No image</div>'

        # Shared attributes HTML
        shared_html = ''
        if shared:
            tags = ''
            for k, v in shared.items():
                if isinstance(v, list):
                    v = ', '.join(v)
                tags += f'<span class="shared-tag">{k}: {v}</span>'
            shared_html = f"""
    <div class="shared-attrs">
      <div class="shared-label">Shared design DNA</div>
      {tags}
    </div>"""

        html += f"""
  <div class="bridge-card" data-type="{b.bridge_type}">
    <div class="bridge-header">
      <span class="bridge-score">T:{b.text_similarity:.2f} I:{(b.image_similarity or 0):.2f} S:{b.structural_score:.2f}</span>
      <span class="bridge-type type-{b.bridge_type}">{b.bridge_type}</span>
    </div>
    <div class="bridge-body">
      <div class="item">
        {src_img}
        <div class="item-platform">{src.platform}</div>
        <div class="item-title">{src.title[:80]}</div>
        <div class="item-meta">
          {f'<span>{src.era}</span>' if src.era else ''}
          {f'<span>{src.decade}</span>' if src.decade else ''}
          {f'<span>{src.fp_category}</span>' if src.fp_category else ''}
          {f'<span>{src.silhouette}</span>' if src.silhouette else ''}
          {f'<span>{src.vibe}</span>' if src.vibe else ''}
        </div>
      </div>
      <div class="bridge-connector">
        <div class="connector-arrow">&harr;</div>
        <div class="connector-scores">
          txt {b.text_similarity:.2f}<br>
          img {f'{b.image_similarity:.2f}' if b.image_similarity else '—'}<br>
          str {b.structural_score:.2f}
        </div>
      </div>
      <div class="item">
        {tgt_img}
        <div class="item-platform">{tgt.platform}</div>
        <div class="item-title">{tgt.title[:80]}</div>
        <div class="item-meta">
          {f'<span>{tgt.era}</span>' if tgt.era else ''}
          {f'<span>{tgt.decade}</span>' if tgt.decade else ''}
          {f'<span>{tgt.fp_category}</span>' if tgt.fp_category else ''}
          {f'<span>{tgt.silhouette}</span>' if tgt.silhouette else ''}
          {f'<span>{tgt.vibe}</span>' if tgt.vibe else ''}
        </div>
      </div>
    </div>
    {shared_html}
  </div>
"""

    html += """
<script>
function filterBridges(type) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.bridge-card').forEach(card => {
    card.style.display = (type === 'all' || card.dataset.type === type) ? 'block' : 'none';
  });
}
</script>

</body>
</html>
"""

    output_path = os.path.join(project_root, output)
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Report generated: {output_path}")
    print(f"  {len(bridges)} bridges, {len(product_map)} products")

    db.close()


if __name__ == '__main__':
    limit_val = 100
    type_val = None
    output_val = 'bridge_report.html'

    for arg in sys.argv[1:]:
        if arg.startswith('--limit='):
            limit_val = int(arg.split('=')[1])
        elif arg.startswith('--type='):
            type_val = arg.split('=')[1]
        elif arg.startswith('--output='):
            output_val = arg.split('=')[1]

    generate_report(limit=limit_val, bridge_type=type_val, output=output_val)
