# MMFashion Integration Plan: Vintage Vestige

## How MMFashion Data Affects Bridge Calculations

### What "Style Bridge Calculation" Currently Is

Right now your bridges are essentially **text-to-text semantic similarity** — Claude reads museum metadata and generates bridge descriptions, which get embedded alongside the record. When a user searches, Qdrant finds similar vectors. The bridge is implicit in the embedding space, not explicitly calculated.

MMFashion changes this because now you have **structured visual features** as a separate signal layer. That opens up a more sophisticated bridge architecture.

---

## How MMFashion Data Enters Bridge Calculations

### 1. Richer Embedding Input (Immediate Impact)

The most direct effect: your embedding text is now denser with visual vocabulary. Instead of embedding "1920s evening dress with geometric ornamentation," you're embedding "1920s evening dress with geometric ornamentation — visual attributes: dropped-waist, beaded, sheer-overlay, sleeveless, floral-pattern."

That seems small but it matters a lot. Embedding models respond to specific, concrete vocabulary. "Dropped-waist" as a term will cluster your record near other dropped-waist pieces in vector space — both historical and modern. The bridge is now partially encoded in the geometry of the embedding itself, not just in Claude's narrative prose.

### 2. Attribute-Based Bridge Matching (New Capability)

This is the bigger architectural shift. With MMFashion tags stored as structured fields in Qdrant's payload, you can move beyond pure semantic similarity to **multi-signal bridge scoring**.

Instead of one similarity score, each potential bridge now has multiple dimensions you can compare:

```
Historical piece tags:    [dropped-waist, sleeveless, sheer, floral, beaded]
Modern piece tags:        [dropped-waist, slip-silhouette, sheer, minimal]

Attribute overlap score:  3/5 shared concepts → 0.60
Semantic vector score:    0.78
Combined bridge score:    weighted average → 0.71
```

The bridge is no longer just "these two things feel similar" — it's "these two things share specific structural and aesthetic features, which is why they feel similar." That's a qualitatively better foundation for explaining bridges to users.

### 3. Silhouette Geometry as a Bridge Axis

MMFashion's landmark detection gives you structural keypoints — neckline position, waist placement, hem length, sleeve geometry. These are **era-defining features** in fashion history.

The New Look silhouette (Dior 1947) is defined by specific geometric relationships: nipped waist, full skirt, below-the-knee hem. If MMFashion captures even partial landmark data from your museum pieces, you can calculate geometric similarity between historical silhouettes and modern ones — finding bridges that are structurally grounded, not just visually approximate.

This is powerful for Vintage Vestige's core thesis because it lets you say: "This 1947 Dior piece and this 2023 Simone Rocha dress share the same silhouette geometry, which is why the bridge exists."

### 4. Confidence-Weighted Bridge Scoring

MMFashion confidence scores should modulate how much weight visual attributes get in bridge calculations. Low-confidence output on a difficult museum image shouldn't drag bridge quality down — it should reduce that signal's influence and let semantic similarity carry more weight.

```python
def calculate_bridge_score(
    historical_record,
    modern_candidate,
    semantic_similarity: float
) -> float:

    mmfashion_weight = historical_record['mmfashion_confidence']
    semantic_weight = 1.0  # always present

    # Attribute overlap between historical and modern piece
    attr_overlap = jaccard_similarity(
        set(historical_record['mmfashion_tags']),
        set(modern_candidate['mmfashion_tags'])
    )

    # Weighted combination
    score = (
        (semantic_similarity * semantic_weight) +
        (attr_overlap * mmfashion_weight)
    ) / (semantic_weight + mmfashion_weight)

    return score
```

Low MMFashion confidence → attribute overlap contributes very little → bridge is basically pure semantic similarity, same as before. High confidence → attributes contribute significantly → bridge is more structurally grounded. It degrades gracefully.

### 5. Claude's Bridge Reasoning Improves Qualitatively

When Claude generates the bridge narrative, it now has visual evidence to anchor its reasoning:

**Before MMFashion:**
> "This 1920s evening gown connects to contemporary minimalist fashion through its streamlined silhouette and rejection of Victorian ornamentation."

**After MMFashion (with confirmed tags: dropped-waist, sleeveless, sheer-overlay):**
> "The dropped waist and sheer overlay of this 1923 Vionnet piece directly anticipate the slip-dress revival of the 1990s and its current iteration in The Row's spring collections — both use fabric transparency and de-emphasis of the natural waist as a rejection of the corseted silhouette that preceded them."

The second bridge is falsifiable, traceable, and specific. MMFashion gave Claude the visual vocabulary to make an argument rather than an impression.

---

## The Deeper Architectural Shift

**Current bridge system (one layer):**

```
Museum metadata → embedding → vector similarity → bridge
```

**After MMFashion (three layers):**

```
Museum metadata     → semantic embedding  ↘
MMFashion tags      → attribute overlap   → combined bridge score
Landmark geometry   → structural sim      ↗
```

Each layer catches different kinds of bridges. Semantic similarity catches conceptual and cultural connections. Attribute overlap catches specific visual feature connections. Structural similarity catches silhouette and construction connections.

A great bridge ideally scores high on all three. A bridge that scores high on only one is still valid but should be surfaced with less confidence. This gives you a natural quality signal for ranking bridges in the UI.

---

## Implementation Plan

### Phase 1: Environment Setup
*Estimated time: 2–4 hours*

#### 1.1 Create a dedicated Python environment

```bash
cd ~/PROJECTS/VINTAGE_VESTIGE
python -m venv venv_mmfashion
source venv_mmfashion/bin/activate

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install mmcv-full
pip install mmfashion
pip install pillow requests psycopg2-binary python-dotenv tqdm
```

#### 1.2 Clone MMFashion and download pre-trained models

```bash
git clone https://github.com/open-mmlab/mmfashion.git
cd mmfashion
```

Download the ResNet50 attribute prediction checkpoint from `MODEL_ZOO.md` and place at:

```
mmfashion/
  checkpoints/
    resnet50_attr_pred.pth
```

#### 1.3 Validate installation with a test image

```python
# test_mmfashion.py
from mmfashion.apis import init_detector, inference_attribute_predictor

model = init_detector(
    'configs/attribute_predict/global_predictor_vgg.py',
    'checkpoints/resnet50_attr_pred.pth'
)

result = inference_attribute_predictor(model, 'test_image.jpg')
print(result)
```

---

### Phase 2: Database Schema Updates
*Estimated time: 1–2 hours*

```sql
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_raw_vector JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_tags TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_confidence FLOAT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_category VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_processed_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_status VARCHAR(20) DEFAULT 'pending';
-- statuses: pending | processed | low_confidence | failed

CREATE INDEX idx_mmfashion_status ON products(mmfashion_status);
```

---

### Phase 3: The MMFashion Batch Processor
*Estimated time: 3–5 hours*

> **Supabase migration note:** This script uses SQLAlchemy `SessionLocal()` for
> consistency with the rest of the codebase. Images are now URLs (Supabase Storage
> or external museum URLs) — `fetch_image()` downloads them over HTTP.

```python
# scripts/mmfashion_batch.py

import os
import sys
import json
import requests
from io import BytesIO
from PIL import Image
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from storage.database import SessionLocal, Product
from mmfashion.apis import init_detector, inference_attribute_predictor

CONFIDENCE_THRESHOLD = 0.45
BATCH_SIZE = 50
MODEL_CONFIG = 'configs/attribute_predict/global_predictor_vgg.py'
CHECKPOINT = 'checkpoints/resnet50_attr_pred.pth'

db = SessionLocal()

print("Loading MMFashion model...")
model = init_detector(MODEL_CONFIG, CHECKPOINT)
print("Model loaded.")

def fetch_image(url: str):
    """Download image from URL (Supabase Storage or external museum URL)."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGB')
    except Exception as e:
        print(f"  Image fetch failed: {url} — {e}")
        return None

def save_temp_image(image, path: str = '/tmp/vv_temp.jpg'):
    image.save(path)
    return path

def run_inference(image_path: str) -> dict:
    raw = inference_attribute_predictor(model, image_path)
    tags = [attr for attr, conf in raw if conf >= CONFIDENCE_THRESHOLD]
    avg_confidence = sum(conf for _, conf in raw) / len(raw) if raw else 0
    top_confidence = max(conf for _, conf in raw) if raw else 0
    return {
        'raw_vector': {attr: float(conf) for attr, conf in raw},
        'tags': tags,
        'avg_confidence': round(avg_confidence, 4),
        'top_confidence': round(top_confidence, 4),
    }

def process_batch():
    products = db.query(Product).filter(
        Product.mmfashion_status == 'pending',
        Product.primary_image.isnot(None),
    ).order_by(Product.id).limit(BATCH_SIZE).all()

    print(f"\nProcessing {len(products)} records...")

    for product in tqdm(products):
        print(f"\n→ [{product.id}] {product.title[:50]}")
        image = fetch_image(product.primary_image)
        if image is None:
            product.mmfashion_status = 'failed'
            product.mmfashion_processed_at = datetime.utcnow()
            db.commit()
            continue

        temp_path = save_temp_image(image)

        try:
            result = run_inference(temp_path)
        except Exception as e:
            print(f"  Inference failed: {e}")
            product.mmfashion_status = 'failed'
            product.mmfashion_processed_at = datetime.utcnow()
            db.commit()
            continue

        status = 'processed' if result['top_confidence'] >= 0.6 else 'low_confidence'

        product.mmfashion_raw_vector = json.dumps(result['raw_vector'])
        product.mmfashion_tags = result['tags']
        product.mmfashion_confidence = result['avg_confidence']
        product.mmfashion_status = status
        product.mmfashion_processed_at = datetime.utcnow()
        db.commit()

        print(f"  ✓ Tags: {result['tags'][:5]} (conf: {result['top_confidence']:.2f})")

if __name__ == '__main__':
    process_batch()
    db.close()
    print("\nBatch complete.")
```

**Run test batch first (10 records):**

```bash
# Set BATCH_SIZE = 10 temporarily
python scripts/mmfashion_batch.py
```

Review output in PostgreSQL before scaling to full 1,000 records.

---

### Phase 4: Update the Claude Enrichment Prompt
*Estimated time: 2–3 hours*

```python
# scripts/claude_enrichment.py (updated)

def build_enrichment_prompt(record: dict) -> str:

    mmfashion_section = ""
    if record.get('mmfashion_tags'):
        confidence_label = (
            "high" if record['mmfashion_confidence'] > 0.65 else
            "medium" if record['mmfashion_confidence'] > 0.45 else
            "low"
        )
        mmfashion_section = f"""
VISUAL ATTRIBUTES (detected by MMFashion, confidence: {confidence_label}):
{', '.join(record['mmfashion_tags'])}

Note: Confidence is {confidence_label}. {"Treat these as reliable visual facts." if confidence_label == "high" else "Cross-reference with metadata before using." if confidence_label == "medium" else "Use metadata as primary source; MMFashion results may be unreliable for this image type."}
"""

    return f"""You are enriching a historical fashion record for Vintage Vestige, a knowledge graph
that connects museum archival pieces to modern fashion through AI-powered style bridges.

MUSEUM METADATA:
Title: {record['title']}
Date: {record['date']}
Maker/Designer: {record.get('maker', 'Unknown')}
Culture/Origin: {record.get('culture', 'Unknown')}
Materials: {record.get('materials', 'Unknown')}
Source Collection: {record['source_collection']}
Original Description: {record.get('description', 'None provided')}
{mmfashion_section}
YOUR TASKS:

1. VALIDATE: If MMFashion attributes are present, note any that conflict with the historical
   metadata (e.g., MMFashion says "denim" but the piece is 1890s silk). Flag conflicts explicitly.

2. HISTORICAL CONTEXT: Write 2-3 sentences placing this piece in its fashion history moment.

3. STYLE BRIDGES: Generate exactly 3 style bridge connections to contemporary fashion.
   Each bridge should include:
   - The specific visual/structural element being bridged
   - A contemporary designer, brand, or movement that echoes it
   - Why this connection is meaningful (not superficial)

4. SEMANTIC DESCRIPTION: Write a 150-200 word description optimized for embedding search.
   Include era, silhouette, materials, cultural context, and modern resonance.

5. TAXONOMY TAGS: Assign tags from these controlled vocabularies:
   - Era: [1800s, 1900s, 1910s, 1920s, 1930s, 1940s, 1950s, 1960s, 1970s, 1980s, 1990s, 2000s]
   - Silhouette: [A-line, empire, hourglass, rectangular, bustle, dropped-waist, shift, wrap]
   - Occasion: [formal, everyday, ceremonial, workwear, sportswear, eveningwear]

Respond in JSON format with keys: validation_notes, historical_context, style_bridges,
semantic_description, taxonomy_tags
"""
```

---

### Phase 5: Re-Enrichment Batch for Existing Records
*Estimated time: 1 hour setup, runs overnight*

> **Supabase migration note:** Uses SQLAlchemy ORM queries instead of raw psycopg2.

```python
# scripts/re_enrich_batch.py

from storage.database import SessionLocal, Product

db = SessionLocal()

products = db.query(Product).filter(
    Product.mmfashion_status.in_(['processed', 'low_confidence']),
    (Product.enriched_at == None) | (Product.enriched_at < Product.mmfashion_processed_at)
).order_by(Product.mmfashion_confidence.desc()).limit(50).all()
```

---

### Phase 6: Regenerate pgvector Embeddings
*Estimated time: 2–3 hours*

> **Supabase migration note:** Qdrant has been replaced by pgvector. Embeddings
> are stored as `text_embedding vector(384)` and `image_embedding vector(512)`
> columns directly on the `products` table. No separate vector DB to sync.
> `mmfashion_tags` and `mmfashion_confidence` are regular columns — filterable
> via SQL `WHERE` clauses, no payload management needed.

```python
def build_embedding_text(product: Product) -> str:
    """Build rich text for embedding, now including MMFashion visual attributes."""
    parts = [
        product.ai_description or '',
        product.enriched_text or '',
        ' '.join(json.loads(product.style_tags)) if product.style_tags else '',
        ' '.join(product.mmfashion_tags) if product.mmfashion_tags else '',
        product.title or '',
        product.material or '',
    ]
    return ' '.join(filter(None, parts))


# Regenerate embeddings for MMFashion-processed products
db = SessionLocal()
generator = EmbeddingGenerator()

products = db.query(Product).filter(
    Product.mmfashion_status.in_(['processed', 'low_confidence'])
).all()

for product in products:
    text = build_embedding_text(product)
    product.text_embedding = generator.generate_text_embedding(text).tolist()
    # Image embedding unchanged — re-run only if primary_image changed
db.commit()
db.close()
```

---

### Phase 7: Validation & QC
*Estimated time: 2–3 hours*

```sql
-- Review high-confidence records
SELECT
    title, date, mmfashion_tags, mmfashion_confidence,
    claude_semantic_description
FROM products
WHERE mmfashion_status = 'processed'
AND mmfashion_confidence > 0.65
ORDER BY mmfashion_confidence DESC
LIMIT 20;

-- Flag conflicts between MMFashion and metadata
SELECT id, title, date, mmfashion_tags, claude_validation_notes
FROM products
WHERE claude_validation_notes LIKE '%conflict%'
   OR claude_validation_notes LIKE '%inconsistent%';

-- Confidence distribution
SELECT
    mmfashion_status,
    COUNT(*),
    ROUND(AVG(mmfashion_confidence)::numeric, 3) as avg_confidence
FROM products
GROUP BY mmfashion_status;
```

---

## Execution Order Summary

| Phase | Task | Time | Dependency |
|-------|------|------|------------|
| 1 | Environment + model setup | 2–4h | Nothing |
| 2 | Schema migration | 1–2h | Nothing |
| 3 | MMFashion batch (10 test records) | 1h | Phases 1+2 |
| 3b | MMFashion full batch (1,000 records) | Overnight | Phase 3 validated |
| 4 | Update Claude enrichment prompt | 2–3h | Phase 3b done |
| 5 | Re-enrich existing records via Claude | Overnight | Phase 4 |
| 6 | Regenerate Qdrant embeddings | 2–3h | Phase 5 |
| 7 | QC + threshold tuning | 2–3h | Phase 6 |

**Total active dev time: ~2 solid days.** Overnights handle the batch jobs.

---

## What to Build Toward

**Immediate:** Embedding enrichment — happens automatically as part of the pipeline. No additional work.

**Medium-term:** Explicit attribute overlap scoring alongside Qdrant's vector similarity, giving you the multi-signal bridge scoring described above. ~1–2 day build once the pipeline is running.

**Long-term:** Silhouette geometry comparison using landmark data — more research-y, would significantly differentiate Vintage Vestige from anything else in the space. Requires validating that MMFashion's landmark detection is reliable on your museum image types.

Start with the pipeline. Let the embedding enrichment run. Then look at actual bridge output quality and decide whether multi-signal scoring is worth the additional complexity. The data will tell you.