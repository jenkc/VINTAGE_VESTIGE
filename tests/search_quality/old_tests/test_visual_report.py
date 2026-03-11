"""
Generate an HTML visual report of search results.
Shows images alongside scores so you can judge quality by eye.
"""

from embeddings.generator import EmbeddingGenerator
from tools.migration.vector_db import VectorDB
from storage.database import SessionLocal, Product
from datetime import datetime
import html


def generate_visual_report():
    print("Generating visual search report...")

    generator = EmbeddingGenerator()
    vector_db = VectorDB()
    db = SessionLocal()

    # Build a lookup for primary_image by product ID
    products = db.query(Product.id, Product.primary_image).all()
    image_lookup = {p.id: p.primary_image for p in products}

    test_queries = [
        ("silk evening dress", "Basic: evening dresses"),
        ("wool coat or cape", "Basic: outerwear"),
        ("lace bonnet", "Basic: bonnets/headwear"),
        ("embroidered waistcoat", "Basic: waistcoats"),
        ("18th century robe", "Era: 1700s robes/gowns"),
        ("1800s Victorian dress", "Era: 19th century items"),
        ("Georgian era fashion", "Era: 1700s-1800s items"),
        ("French silk gown", "Culture: French items"),
        ("British corset or stays", "Culture: British items"),
        ("American formal wear", "Culture: American items"),
        ("dark academia aesthetic", "Vibe: dark academia"),
        ("cottagecore pastoral dress", "Vibe: cottagecore"),
        ("romantic gothic fashion", "Vibe: romantic gothic"),
        ("old money elegance", "Vibe: old money"),
    ]

    report_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Vintage Vestige — Search Quality Report</title>
<style>
  body {{ font-family: 'Inter', system-ui, sans-serif; background: #F7F3EC; color: #2B2B2B; max-width: 1200px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-family: 'Georgia', serif; color: #722F37; }}
  h2 {{ font-family: 'Georgia', serif; margin-top: 48px; border-bottom: 2px solid #E0D0B0; padding-bottom: 8px; }}
  .query-section {{ margin-bottom: 40px; }}
  .query-label {{ color: #8B7E74; font-size: 14px; margin-bottom: 4px; }}
  .query-text {{ font-size: 20px; font-weight: 600; margin-bottom: 16px; }}
  .results-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
  .result-card {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .result-card img {{ width: 100%; height: 250px; object-fit: contain; background: #f0ebe3; }}
  .result-info {{ padding: 12px; }}
  .result-title {{ font-weight: 600; font-size: 14px; }}
  .result-fields {{ font-size: 12px; color: #8B7E74; margin-top: 6px; line-height: 1.6; }}
  .result-fields strong {{ color: #2B2B2B; }}
  .no-image {{ width: 100%; height: 250px; background: #E0D0B0; display: flex; align-items: center; justify-content: center; color: #8B7E74; }}
  .summary {{ background: white; padding: 24px; border-radius: 8px; margin-top: 48px; }}
  .timestamp {{ color: #8B7E74; font-size: 12px; }}
</style>
</head>
<body>
<h1>Vintage Vestige — Search Quality Report</h1>
<p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
"""

    categories = {
        "Basic Queries (garment + material)": [],
        "Era Queries (historical periods)": [],
        "Culture Queries (origin)": [],
        "Modern Vibe Queries (enrichment target)": [],
    }
    cat_keys = list(categories.keys())

    all_scores = []

    for idx, (query, label) in enumerate(test_queries):
        query_embedding = generator.generate_text_embedding(query)
        results = vector_db.search_similar(
            collection='vintage_text',
            query_vector=query_embedding,
            limit=5
        )

        # Determine category
        if idx < 4:
            cat = cat_keys[0]
        elif idx < 7:
            cat = cat_keys[1]
        elif idx < 10:
            cat = cat_keys[2]
        else:
            cat = cat_keys[3]

        section_html = f"""<div class="query-section">
  <div class="query-label">{html.escape(label)}</div>
  <div class="query-text">"{html.escape(query)}"</div>
  <div class="results-grid">
"""
        top_score = results[0]['score'] if results else 0
        all_scores.append(top_score)

        for result in results:
            pid = result.get('product_id', result.get('id'))
            title = html.escape(result.get('title', 'Unknown'))
            score = result.get('score', 0)

            # Collect all enrichment fields
            fields = [
                ('Score', f"{score:.3f}"),
                ('Era', result.get('era')),
                ('Decade', result.get('decade')),
                ('Garment', result.get('garment_type')),
                ('Material', result.get('material')),
                ('Pattern', result.get('pattern')),
                ('Colors', ', '.join(result.get('colors', [])) if isinstance(result.get('colors'), list) else result.get('colors')),
                ('Vibe', result.get('vibe')),
                ('Fit', result.get('fit_style')),
                ('Style', ', '.join(result.get('style_tags', [])) if isinstance(result.get('style_tags'), list) else result.get('style_tags')),
                ('Season', result.get('season')),
                ('Occasion', result.get('occasion')),
                ('Culture', result.get('culture')),
            ]

            fields_html = ""
            for label, value in fields:
                if value:
                    fields_html += f'<div><strong>{label}:</strong> {html.escape(str(value))}</div>\n'

            img = image_lookup.get(pid, '')
            if img and img.startswith('data:image'):
                img_html = f'<img src="{img}" alt="{title}">'
            else:
                img_html = f'<div class="no-image">No image</div>'

            section_html += f"""    <div class="result-card">
      {img_html}
      <div class="result-info">
        <div class="result-title">{title}</div>
        <div class="result-fields">
{fields_html}        </div>
      </div>
    </div>
"""
        section_html += "  </div>\n</div>\n"
        categories[cat].append(section_html)

        print(f"  [{idx+1}/{len(test_queries)}] '{query}' — top score: {top_score:.3f}")

    # Build full HTML by category
    for cat_name, sections in categories.items():
        report_html += f"<h2>{cat_name}</h2>\n"
        for s in sections:
            report_html += s

    # Summary
    avg = sum(all_scores) / len(all_scores) if all_scores else 0
    report_html += f"""
<div class="summary">
  <h2 style="margin-top: 0; border: none;">Summary</h2>
  <p>Queries tested: {len(test_queries)}</p>
  <p>Average top score: <strong>{avg:.3f}</strong></p>
  <p>Baseline to beat: <strong>0.656</strong></p>
</div>
</body>
</html>"""

    output_path = "search_report.html"
    with open(output_path, 'w') as f:
        f.write(report_html)

    print(f"\nReport saved to {output_path}")
    print(f"Average top score: {avg:.3f}")
    print("Open in a browser to review results visually.")

    db.close()


if __name__ == '__main__':
    generate_visual_report()
