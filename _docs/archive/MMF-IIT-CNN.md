# Vintage Vestige: Master Implementation Roadmap
## MMFashion + IIT 4.0 Unified Pipeline

**Status**: Design Phase  
**Total Timeline**: 14–15 weeks  
**Principle**: Build once. MMFashion runs first, IIT builds on top.

---

## Executive Summary

This document merges two previously separate implementation plans — MMFashion visual pre-enrichment and IIT 4.0 multi-modal search architecture — into a single unified roadmap with correct sequencing and explicit integration points.

**The core insight**: MMFashion is not a standalone feature. It is the visual foundation that every IIT 4.0 approach depends on. Running MMFashion first means the Φ calculator has richer input, the Approach 2 attribute ablations are cheaper, Claude enrichment is better, and the IIT CNN (if needed at all) trains on stronger labels. Building IIT without MMFashion means building it twice.

**The pipeline in full**:

```
Raw Image
    ↓
[PHASE 1] MMFashion — visual attribute extraction
    → 1,000-dim binary vector + curated tag list + confidence
    ↓
[PHASE 2] Claude Enrichment (informed by MMFashion)
    → 23 Fashionpedia fields + style bridges + validation notes
    ↓
[PHASE 3] Embedding Generation
    → text embedding (MiniLM) + image embedding (CLIP)
    → both stored in Qdrant with MMFashion tags as payload
    ↓
[PHASE 4] IIT Approach 1 — Φ-Based Search Ranking
    → embedding Φ + attribute Φ → re-ranked search results
    ↓
[PHASE 5] IIT Approach 2 — Maximal Attribute Selection
    → field importance via ablation → optimized rich text
    ↓
[PHASE 6] IIT Approach 3 — Emergent Complex Discovery
    → visually-grounded aesthetic complexes
    ↓
[PHASE 7] IIT Approach 4 — Adaptive Multi-Modal Weighting
    → query-specific modality weighting
    ↓
[PHASE 8] IIT CNN (conditional)
    → visual verification layer, only if gaps remain
```

---

## Current Architecture Baseline

### What Exists

**Text Embeddings** (`scripts/embeddings/models.py:67-76`)
- Model: `all-MiniLM-L6-v2` (SentenceTransformers)
- Dimensionality: 384
- Storage: Qdrant collection `vintage_text`, COSINE distance

**Image Embeddings** (`scripts/embeddings/models.py:38-65`)
- Model: `clip-ViT-B-32` (SentenceTransformers)
- Dimensionality: 512
- Storage: Qdrant collection `vintage_images`, COSINE distance

**Claude Enrichment** (`scripts/enrichment/claude.py`)
- Model: `claude-sonnet-4-20250514`
- Output: 23 structured fields (12 Fashionpedia taxonomy + 11 creative/search-bridge)
- Fields: `fp_category, silhouette, neckline, length, sleeve_length, opening_type, textile_pattern, textile_finishing, garment_parts, decorations, waistline, nickname, era, decade, style_tags, colors, material, season, garment_type, vibe, fit_style, occasion, ai_description`

**Search** (`scripts/storage/vector_db.py:86-110`)
- Simple cosine similarity, single modality at a time
- No cross-modal integration measurement
- No explainability

### The Three Gaps This Plan Closes

1. **No visual pre-enrichment**: Claude infers visual attributes from text. MMFashion confirms them from pixels.
2. **No multi-modal integration measurement**: Image and text embeddings are isolated. IIT Φ bridges them.
3. **No attribute attribution**: The system can't explain which fields drive a match. Approach 2 fixes this.

---

## Phase 1: MMFashion Environment & Setup
**Weeks 1–2 | Active dev: 2–4 hours**

### 1.1 Dedicated Python Environment

MMFashion has specific dependency requirements. Keep it isolated.

```bash
cd ~/PROJECTS/VINTAGE_VESTIGE
python -m venv venv_mmfashion
source venv_mmfashion/bin/activate

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install mmcv-full mmfashion
pip install pillow requests psycopg2-binary python-dotenv tqdm
```

### 1.2 Clone and Configure

```bash
git clone https://github.com/open-mmlab/mmfashion.git
cd mmfashion
```

Download the ResNet50 attribute prediction checkpoint from `MODEL_ZOO.md`. Place at:

```
mmfashion/checkpoints/resnet50_attr_pred.pth
```

### 1.3 Installation Validation

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

You should get a dict of (attribute, confidence) pairs. If it runs, proceed.

---

## Phase 2: Database Schema Extension
**Week 1 | Active dev: 1–2 hours | No dependencies**

Extend PostgreSQL schema before running any batch jobs. All new columns are additive — no existing data is touched.

```sql
-- MMFashion columns
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_raw_vector JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_tags TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_confidence FLOAT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_category VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_processed_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_status VARCHAR(20) DEFAULT 'pending';
-- statuses: pending | processed | low_confidence | failed

-- IIT columns (add now, populate later in Phase 4)
CREATE TABLE IF NOT EXISTS phi_scores (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    phi_embedding FLOAT,       -- Φ between CLIP and MiniLM embeddings
    phi_attribute FLOAT,       -- Φ between MMFashion tags and Claude fields
    phi_combined FLOAT,        -- weighted combination
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    method VARCHAR(10) DEFAULT 'simple'
);

CREATE TABLE IF NOT EXISTS maximal_complexes (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    fields JSONB NOT NULL,
    phi_full FLOAT NOT NULL,
    phi_maximal FLOAT NOT NULL
);

CREATE TABLE IF NOT EXISTS discovered_complexes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    attributes JSONB NOT NULL,
    phi_score FLOAT NOT NULL,
    support INTEGER NOT NULL,
    exemplar_ids INTEGER[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cnn_predictions (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    silhouette_pred VARCHAR(50),
    silhouette_conf FLOAT,
    neckline_pred VARCHAR(50),
    neckline_conf FLOAT,
    pattern_pred VARCHAR(50),
    pattern_conf FLOAT,
    era_pred VARCHAR(20),
    era_conf FLOAT,
    colors_pred JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mmfashion_status ON products(mmfashion_status);
CREATE INDEX IF NOT EXISTS idx_phi_combined ON phi_scores(phi_combined DESC);
CREATE INDEX IF NOT EXISTS idx_complex_phi ON discovered_complexes(phi_score DESC);
```

---

## Phase 3: MMFashion Batch Processing
**Weeks 1–2 | Active dev: 3–5 hours + overnight run**

### 3.1 The Batch Processor

```python
# scripts/mmfashion_batch.py

import os
import json
import requests
import psycopg2
from io import BytesIO
from PIL import Image
from tqdm import tqdm
from dotenv import load_dotenv
from mmfashion.apis import init_detector, inference_attribute_predictor

load_dotenv()

CONFIDENCE_THRESHOLD = 0.45  # Lower than commercial; museum images are harder
BATCH_SIZE = 50
MODEL_CONFIG = 'configs/attribute_predict/global_predictor_vgg.py'
CHECKPOINT = 'checkpoints/resnet50_attr_pred.pth'

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("Loading MMFashion model...")
model = init_detector(MODEL_CONFIG, CHECKPOINT)

def fetch_image(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert('RGB')
    except Exception as e:
        print(f"  Fetch failed: {e}")
        return None

def run_inference(image_path):
    raw = inference_attribute_predictor(model, image_path)
    tags = [attr for attr, conf in raw if conf >= CONFIDENCE_THRESHOLD]
    avg_conf = sum(c for _, c in raw) / len(raw) if raw else 0
    top_conf = max(c for _, c in raw) if raw else 0
    return {
        'raw_vector': {attr: float(conf) for attr, conf in raw},
        'tags': tags,
        'avg_confidence': round(avg_conf, 4),
        'top_confidence': round(top_conf, 4),
    }

def process_batch():
    cur.execute("""
        SELECT id, image_url, title FROM products
        WHERE mmfashion_status = 'pending'
        AND image_url IS NOT NULL
        ORDER BY id LIMIT %s
    """, (BATCH_SIZE,))

    records = cur.fetchall()
    print(f"Processing {len(records)} records...")

    for product_id, image_url, title in tqdm(records):
        image = fetch_image(image_url)
        if image is None:
            cur.execute("UPDATE products SET mmfashion_status='failed', mmfashion_processed_at=NOW() WHERE id=%s", (product_id,))
            conn.commit()
            continue

        temp_path = '/tmp/vv_temp.jpg'
        image.save(temp_path)

        try:
            result = run_inference(temp_path)
        except Exception as e:
            print(f"  Inference failed: {e}")
            cur.execute("UPDATE products SET mmfashion_status='failed', mmfashion_processed_at=NOW() WHERE id=%s", (product_id,))
            conn.commit()
            continue

        status = 'processed' if result['top_confidence'] >= 0.6 else 'low_confidence'

        cur.execute("""
            UPDATE products SET
                mmfashion_raw_vector=%s, mmfashion_tags=%s,
                mmfashion_confidence=%s, mmfashion_status=%s,
                mmfashion_processed_at=NOW()
            WHERE id=%s
        """, (json.dumps(result['raw_vector']), result['tags'],
              result['avg_confidence'], status, product_id))
        conn.commit()
        print(f"  ✓ {title[:40]} — tags: {result['tags'][:4]} (conf: {result['top_confidence']:.2f})")

if __name__ == '__main__':
    process_batch()
    cur.close()
    conn.close()
```

### 3.2 Critical: Run 10 Records First

```bash
# Set BATCH_SIZE = 10 temporarily
python scripts/mmfashion_batch.py
```

Review output in PostgreSQL. Ask yourself:
- Do the tags make sense for museum image types?
- Are confidence scores reasonable (not all near 0)?
- Is 0.45 the right threshold, or does it need adjustment?

**This calibration decision ripples through everything downstream.** Don't skip it. Then set `BATCH_SIZE = 50` and run the full batch overnight.

### 3.3 QC Queries

```sql
-- Confidence distribution
SELECT mmfashion_status, COUNT(*),
    ROUND(AVG(mmfashion_confidence)::numeric, 3) as avg_conf
FROM products GROUP BY mmfashion_status;

-- Sample high-confidence tags
SELECT title, date, mmfashion_tags, mmfashion_confidence
FROM products
WHERE mmfashion_status = 'processed'
ORDER BY mmfashion_confidence DESC LIMIT 20;
```

---

## Phase 4: Updated Claude Enrichment
**Week 2 | Active dev: 2–3 hours | Depends on Phase 3**

MMFashion output is now passed to Claude with confidence-aware framing. Claude's job shifts: instead of inferring visual attributes from text, it validates, contextualizes, and bridges to modern fashion.

```python
# scripts/enrichment/claude_enrichment.py (updated)

def build_enrichment_prompt(record: dict) -> str:

    mmfashion_section = ""
    if record.get('mmfashion_tags'):
        conf = record['mmfashion_confidence']
        if conf > 0.65:
            label = "high"
            instruction = "Treat these as reliable visual facts."
        elif conf > 0.45:
            label = "medium"
            instruction = "Cross-reference with metadata before using."
        else:
            label = "low"
            instruction = "Use metadata as primary source; MMFashion results may be unreliable for this image type."

        mmfashion_section = f"""
VISUAL ATTRIBUTES (MMFashion, confidence: {label}):
{', '.join(record['mmfashion_tags'])}
{instruction}
"""

    return f"""You are enriching a historical fashion record for Vintage Vestige —
a knowledge graph connecting museum archival pieces to modern fashion
through AI-powered style bridges.

MUSEUM METADATA:
Title: {record['title']}
Date: {record['date']}
Maker: {record.get('maker', 'Unknown')}
Culture: {record.get('culture', 'Unknown')}
Materials: {record.get('materials', 'Unknown')}
Source: {record['source_collection']}
Description: {record.get('description', 'None')}
{mmfashion_section}
TASKS:

1. VALIDATE — Note any MMFashion attributes conflicting with historical metadata.
   Flag explicitly (e.g., "MMFashion suggests denim but piece is 1890s silk — disregard").

2. HISTORICAL CONTEXT — 2–3 sentences placing this piece in its fashion history moment.
   What came before it? What did it represent or reject?

3. STYLE BRIDGES — Exactly 3 connections to contemporary fashion. Each must include:
   - The specific visual/structural element being bridged
   - A contemporary designer, brand, or movement that echoes it
   - Why the connection is meaningful, not superficial

4. SEMANTIC DESCRIPTION — 150–200 words optimized for embedding search.
   Include era, silhouette, materials, cultural context, modern resonance.

5. TAXONOMY TAGS — from controlled vocabulary:
   Era: [1800s, 1900s, 1910s, 1920s, 1930s, 1940s, 1950s, 1960s, 1970s, 1980s, 1990s, 2000s]
   Silhouette: [A-line, empire, hourglass, rectangular, bustle, dropped-waist, shift, wrap]
   Occasion: [formal, everyday, ceremonial, workwear, sportswear, eveningwear]

Respond in JSON: validation_notes, historical_context, style_bridges,
semantic_description, taxonomy_tags
"""
```

Run re-enrichment targeting records where MMFashion has run but Claude enrichment predates it:

```sql
SELECT id FROM products
WHERE mmfashion_status IN ('processed', 'low_confidence')
AND (claude_enriched_at IS NULL OR claude_enriched_at < mmfashion_processed_at)
ORDER BY mmfashion_confidence DESC  -- best records first
LIMIT 50;
```

---

## Phase 5: Re-Embedding
**Week 2–3 | Active dev: 2–3 hours | Depends on Phase 4**

Regenerate all embeddings with the enriched input. MMFashion tags are included in the embedding text and stored as filterable payload in Qdrant.

```python
def build_embedding_text(record: dict) -> str:
    parts = [
        record.get('semantic_description', ''),
        record.get('historical_context', ''),
        ' '.join(record.get('mmfashion_tags', [])),
        record.get('title', ''),
        record.get('materials', ''),
        ' '.join(str(v) for v in record.get('taxonomy_tags', {}).values()),
    ]
    return ' '.join(filter(None, parts))

# Qdrant payload now includes:
payload = {
    **existing_fields,
    'mmfashion_tags': record['mmfashion_tags'],
    'mmfashion_confidence': record['mmfashion_confidence'],
}
```

**Integration point**: After this phase, your Qdrant records carry both the enriched text embedding AND structured MMFashion tags as filterable fields. This is the foundation IIT Approach 1 builds on.

---

## Phase 6: IIT Approach 1 — Φ-Based Search Ranking
**Weeks 3–5 | Active dev: 1–2 weeks**

### The Two Types of Φ

With MMFashion now in the pipeline, you calculate Φ at two levels:

**Embedding Φ** — integration between CLIP (512d) and MiniLM (384d) in a projected common space. This is your existing IIT plan's Approach 1, unchanged.

**Attribute Φ** — integration between MMFashion's visual tags and Claude's text-inferred structured fields. This is new, enabled by MMFashion, and more interpretable.

```python
def calculate_attribute_phi(mmfashion_tags: list, claude_fields: dict) -> float:
    """
    Jaccard similarity between visual tags and text-inferred attributes.
    Fast approximation of attribute-level integrated information.
    """
    # Flatten Claude fields to comparable tag set
    claude_tags = set()
    for field, value in claude_fields.items():
        if isinstance(value, list):
            claude_tags.update(str(v).lower() for v in value)
        elif value:
            claude_tags.add(str(value).lower())

    vision_tags = set(t.lower() for t in mmfashion_tags)

    if not vision_tags or not claude_tags:
        return 0.0

    intersection = len(vision_tags & claude_tags)
    union = len(vision_tags | claude_tags)

    return intersection / union if union > 0 else 0.0
```

### Combined Φ and Ranking

```python
def calculate_combined_phi(
    text_emb, image_emb,
    mmfashion_tags, claude_fields,
    mmfashion_confidence
) -> dict:

    phi_embedding = simple_phi(text_emb, image_emb)  # existing IIT calc
    phi_attribute = calculate_attribute_phi(mmfashion_tags, claude_fields)

    # Weight attribute Φ by MMFashion confidence
    # Low confidence → lean on embedding Φ; high confidence → both matter
    attr_weight = mmfashion_confidence
    emb_weight = 1.0

    phi_combined = (
        (phi_embedding * emb_weight) + (phi_attribute * attr_weight)
    ) / (emb_weight + attr_weight)

    return {
        'phi_embedding': phi_embedding,
        'phi_attribute': phi_attribute,
        'phi_combined': phi_combined
    }

def phi_weighted_score(cosine_score, phi_combined, phi_weight=0.3) -> float:
    return (1 - phi_weight) * cosine_score + phi_weight * phi_combined
```

### Explainability

Attribute Φ makes explainability concrete. Instead of just showing a score, you can explain it:

```python
def generate_phi_explanation(phi_embedding, phi_attribute, mmfashion_tags, claude_fields):
    if phi_attribute > 0.6:
        return f"Image and text strongly agree — both identify {_shared_attributes(mmfashion_tags, claude_fields)}"
    elif phi_attribute > 0.3:
        return f"Moderate visual-text agreement on {_shared_attributes(mmfashion_tags, claude_fields)}"
    else:
        return "Visual and text signals diverge — result matched on semantic similarity"
```

### Store Φ Scores

```python
cur.execute("""
    INSERT INTO phi_scores (product_id, phi_embedding, phi_attribute, phi_combined)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (product_id) DO UPDATE SET
        phi_embedding=EXCLUDED.phi_embedding,
        phi_attribute=EXCLUDED.phi_attribute,
        phi_combined=EXCLUDED.phi_combined,
        last_updated=NOW()
""", (product_id, phi['phi_embedding'], phi['phi_attribute'], phi['phi_combined']))
```

### API Endpoint

```
POST /api/search/phi
{
  "query": "dark academia aesthetic",
  "phi_weight": 0.3,
  "limit": 12
}
```

Response includes `phi_embedding`, `phi_attribute`, `phi_combined`, and `explanation` per result.

---

## Phase 7: IIT Approach 2 — Maximal Attribute Selection
**Weeks 5–7 | Active dev: 1–2 weeks | Depends on Phase 6**

MMFashion makes the ablation study dramatically cheaper. Instead of re-running Claude 23 times per product to test field importance, you measure how much each Claude field overlaps with confirmed MMFashion visual attributes — a vector operation.

```python
def measure_field_phi_contribution(product_id: int, field_name: str) -> float:
    """
    How much does this Claude field contribute to attribute Φ?
    Ablation: compare attribute Φ with vs without this field.
    """
    record = get_record(product_id)
    mmfashion_tags = record['mmfashion_tags']
    all_claude_fields = record['claude_fields']

    phi_full = calculate_attribute_phi(mmfashion_tags, all_claude_fields)

    ablated_fields = {k: v for k, v in all_claude_fields.items() if k != field_name}
    phi_ablated = calculate_attribute_phi(mmfashion_tags, ablated_fields)

    return phi_full - phi_ablated  # Contribution of this field
```

Run across 500+ products and average. Expected output:

```
Field Φ Contributions (averaged across dataset):
silhouette:     0.38  ← highest, include always
era:            0.31
vibe:           0.24
colors:         0.19
material:       0.17
textile_pattern: 0.12
decade:         0.04  ← redundant with era
style_tags:     0.03  ← redundant with vibe
season:         0.01  ← low signal
```

Use this to optimize the Claude enrichment prompt (prioritize high-Φ fields) and rich text construction (include only fields above threshold).

```python
TOP_PHI_FIELDS = ['silhouette', 'era', 'vibe', 'colors', 'material',
                  'textile_pattern', 'neckline', 'ai_description']

def build_optimized_rich_text(record: dict) -> str:
    parts = []
    for field in TOP_PHI_FIELDS:
        value = record.get(field)
        if value:
            if isinstance(value, list):
                parts.append(', '.join(str(v) for v in value))
            else:
                parts.append(str(value))
    return ' '.join(parts)[:512]
```

Re-embed affected records after optimizing.

---

## Phase 8: IIT Approach 3 — Emergent Complex Discovery
**Weeks 7–10 | Active dev: 2–3 weeks | Depends on Phase 7**

Discover irreducible aesthetic complexes — combinations of attributes with high Φ that represent unified style concepts. MMFashion provides visual grounding: complexes must show up in both text space (Claude attributes) AND visual space (MMFashion tags).

```python
def discover_complexes(products, min_support=10, min_phi=0.65):
    from itertools import combinations

    semantic_fields = ['era', 'vibe', 'silhouette', 'colors', 'material']
    complexes = []

    for size in range(2, 6):
        for field_combo in combinations(semantic_fields, size):
            matching = find_products_with_attributes(products, field_combo)
            if len(matching) < min_support:
                continue

            # Text-space Φ (Claude attributes)
            text_phis = [calculate_phi_for_fields(p, field_combo) for p in matching]

            # Visual grounding (MMFashion confirmation)
            visual_confirmations = [
                mmfashion_confirms_complex(p['mmfashion_tags'], field_combo, p)
                for p in matching
            ]
            visual_confirmation_rate = sum(visual_confirmations) / len(matching)

            avg_phi = np.mean(text_phis)

            # Only keep complexes with both high Φ AND visual grounding
            if avg_phi >= min_phi and visual_confirmation_rate >= 0.5:
                complexes.append({
                    'fields': field_combo,
                    'phi': avg_phi,
                    'visual_confirmation_rate': visual_confirmation_rate,
                    'support': len(matching),
                    'exemplars': [p['id'] for p in matching[:5]]
                })

    return sorted(complexes, key=lambda c: c['phi'], reverse=True)
```

**Visual grounding** is the key addition over the original IIT plan:

```python
def mmfashion_confirms_complex(mmfashion_tags, field_combo, product):
    """
    Check if MMFashion visual tags are consistent with this complex's attributes.
    A complex like {era=Victorian, vibe=dark, material=velvet} should be confirmed
    by MMFashion tags like [black, long-length, high-neckline, velvet-texture].
    """
    complex_visual_keywords = extract_visual_keywords(field_combo, product)
    mmfashion_set = set(t.lower() for t in mmfashion_tags)

    overlap = len(complex_visual_keywords & mmfashion_set)
    return overlap >= 2  # At least 2 visual confirmations required
```

**Expected complexes:**

```
GothVictorian         Φ=0.82  visual_conf=0.74  support=47
RomanticCottagecore   Φ=0.78  visual_conf=0.68  support=62
ArtDecoGlam           Φ=0.76  visual_conf=0.71  support=31
MinimalModern         Φ=0.75  visual_conf=0.66  support=38
```

---

## Phase 9: IIT Approach 4 — Adaptive Multi-Modal Weighting
**Weeks 10–12 | Active dev: 1–2 weeks | Depends on Phases 6–8**

MMFashion confidence scores replace the keyword heuristic in the original plan. Instead of guessing whether a query is "visual" based on word presence, you use the actual measured confidence of the visual signal.

```python
def adaptive_search(query_text, query_image=None, limit=10):

    phi_query = analyze_query_phi(query_text, query_image)

    # MMFashion average confidence across top candidates informs vision weight
    # High average MMFashion confidence → trust visual signal more
    # Low average MMFashion confidence → lean on text

    if phi_query > 0.6:
        text_weight, image_weight = 0.5, 0.5
    elif phi_query < 0.4:
        text_weight, image_weight = (0.8, 0.2) if not query_image else (0.3, 0.7)
    else:
        text_weight, image_weight = 0.6, 0.4

    text_results = vector_db.search_similar('vintage_text', encode_text(query_text), limit=limit*2)
    image_results = vector_db.search_similar('vintage_images', encode_image(query_image), limit=limit*2) if query_image else []

    merged = merge_results(text_results, image_results, text_weight, image_weight)

    # Apply per-record MMFashion confidence adjustment
    for result in merged:
        mmf_conf = result.get('mmfashion_confidence', 0.5)
        # Records with low MMFashion confidence get visual signal down-weighted
        result['score'] = result['score'] * (0.7 + 0.3 * mmf_conf)

    return sorted(merged, key=lambda r: r['score'], reverse=True)[:limit]
```

---

## Phase 10: IIT CNN (Conditional)
**Weeks 12–15 | Active dev: 2–4 weeks | Only if gaps remain**

**Trigger condition**: Run the IIT CNN only if, after Phase 9, you identify categories of museum images where MMFashion confidence is consistently low AND attribute Φ is consequently weak. This will show up clearly in your QC queries.

If MMFashion + Claude are performing well across your image types, skip this phase entirely. The CNN was designed to solve the visual verification problem — MMFashion may already solve enough of it.

If you do build it, the CNN trains on Claude-enriched outputs as labels, weighted by Φ-guided task importance from Approach 2:

```python
class FashionAttributeCNN(nn.Module):
    def __init__(self, phi_weights=None):
        super().__init__()
        backbone = models.resnet50(pretrained=True)
        self.features = nn.Sequential(*list(backbone.children())[:-1])
        feature_dim = 2048

        # Only train heads for high-Φ attributes
        # phi_weights from Approach 2 field importance analysis
        self.silhouette_head = nn.Sequential(
            nn.Linear(feature_dim, 512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 12)
        )
        self.neckline_head = nn.Sequential(
            nn.Linear(feature_dim, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 8)
        )
        self.pattern_head = nn.Sequential(
            nn.Linear(feature_dim, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 6)
        )
        # Φ-guided task weights: silhouette=0.38, neckline=0.15, pattern=0.12
        self.task_weights = phi_weights or {'silhouette': 1.0, 'neckline': 0.4, 'pattern': 0.3}

    def forward(self, x):
        features = self.features(x).view(-1, 2048)
        return {
            'silhouette': self.silhouette_head(features),
            'neckline': self.neckline_head(features),
            'pattern': self.pattern_head(features),
        }
```

CNN predictions feed into the fusion layer alongside MMFashion:

```python
def fuse_visual_predictions(mmfashion_tags, cnn_preds, claude_fields):
    """
    Three-way fusion: MMFashion + CNN + Claude
    When all three agree → highest Φ, highest confidence
    """
    fused = {}
    for attr in ['silhouette', 'neckline', 'pattern']:
        cnn_value, cnn_conf = cnn_preds.get(attr, (None, 0))
        claude_value = claude_fields.get(attr)
        mmf_confirms = attr_in_mmfashion(mmfashion_tags, attr)

        if cnn_value == claude_value and mmf_confirms:
            fused[attr] = {'value': cnn_value, 'phi': 0.95, 'source': 'consensus'}
        elif cnn_conf > 0.7:
            fused[attr] = {'value': cnn_value, 'phi': 0.7, 'source': 'vision_primary'}
        else:
            fused[attr] = {'value': claude_value, 'phi': 0.4, 'source': 'text_primary'}

    return fused
```

---

## Integration Points Summary

This table shows exactly where MMFashion data flows into each IIT approach:

| IIT Approach | What MMFashion Provides | Specific Integration |
|---|---|---|
| Approach 1: Φ Ranking | Visual attribute tags for attribute Φ | `calculate_attribute_phi(mmfashion_tags, claude_fields)` |
| Approach 1: Explainability | Concrete shared attributes to name | `_shared_attributes(mmfashion_tags, claude_fields)` |
| Approach 2: Ablation Study | Cheap visual ground truth | Field ablation as vector op vs. Claude API call |
| Approach 2: Rich Text | Field importance ranking | Only include fields above Φ threshold |
| Approach 3: Complexes | Visual grounding requirement | `mmfashion_confirms_complex()` filter |
| Approach 3: Complex Φ | Visual confirmation rate | Complexes need ≥50% visual confirmation |
| Approach 4: Adaptive Weights | Per-record confidence score | Down-weight visual signal for low-confidence records |
| Approach 4: Query Analysis | Replaces keyword heuristic | MMFashion confidence as direct measurement |
| CNN (if built) | Training signal validation | Confidence comparison: MMFashion vs. CNN per attribute |

---

## Master Timeline

| Week | Phase | Work | Deliverable |
|------|-------|------|-------------|
| 1 | 1–2 | MMFashion env setup + schema migration | Running MMFashion, extended DB |
| 1–2 | 3 | MMFashion batch — 10 test records, calibrate, full run | 1,000 records with tags |
| 2 | 4 | Updated Claude enrichment prompt + re-enrichment batch | Richer 23-field outputs |
| 2–3 | 5 | Re-embedding with enriched input | Updated Qdrant with MMFashion payload |
| 3–5 | 6 | IIT Approach 1 — Φ calculator (both types) + search reranking | Φ-weighted search live |
| 5–6 | 6 | IIT Approach 1 — API, frontend PhiBadge, A/B test | Explainability in UI |
| 6–7 | 7 | IIT Approach 2 — field attribution, ablation study | Field importance rankings |
| 7 | 7 | IIT Approach 2 — optimized rich text + re-embed | Better text embeddings |
| 7–9 | 8 | IIT Approach 3 — complex discovery algorithm | 20–30 aesthetic complexes |
| 9–10 | 8 | IIT Approach 3 — complex ontology + search + UI page | Discover Aesthetics page live |
| 10–12 | 9 | IIT Approach 4 — adaptive weighting + A/B test | Query-adaptive search |
| 12–15 | 10 | IIT CNN — only if visual gaps remain | Visual verification layer |

**Total active dev: ~8–10 weeks across 14–15 calendar weeks**  
Overnights handle batch jobs. Parallel work possible after Week 3.

---

## Success Metrics

### MMFashion Phases (Weeks 1–3)
- 1,000 records processed with status `processed` or `low_confidence`
- Confidence distribution: meaningful spread, not all near 0 or all near 1
- Tags qualitatively sensible for museum image types
- Claude validation_notes flag <15% of records as conflicted

### IIT Approach 1 (Weeks 3–6)
- Φ scores calculated for all 1,000 products
- Φ distribution: approximately normal, centered ~0.5
- Vibe query scores: +5–10% improvement over baseline
- No regression on era/culture queries
- User study: >70% understand Φ explanation

### IIT Approach 2 (Weeks 6–7)
- Field importance ranking produced for all 23 fields
- Mean Φ increases +0.05–0.10 after rich text optimization
- Re-embedding completed with optimized input

### IIT Approach 3 (Weeks 7–10)
- 20–30 meaningful aesthetic complexes discovered
- Each complex has visual confirmation rate ≥50%
- User study: >80% agree complexes are coherent
- Complex search precision > generic search precision

### IIT Approach 4 (Weeks 10–12)
- Low-Φ queries improve +5%
- High-Φ queries maintain or improve quality
- A/B test statistically significant (p < 0.05)

### CNN (Weeks 12–15, if triggered)
- Silhouette top-1 accuracy >70%
- Pattern top-1 accuracy >75%
- Three-way consensus (MMFashion + CNN + Claude) present in >40% of records

---

## Configuration

**`config/pipeline.yaml`**
```yaml
mmfashion:
  confidence_threshold: 0.45      # Tune after test-10 run
  high_confidence_cutoff: 0.65    # Above = "reliable visual facts"
  batch_size: 50
  checkpoint: checkpoints/resnet50_attr_pred.pth

iit:
  phi_weight: 0.3                 # Weight of Φ in final ranking score
  phi_method: simple              # simple | ksg | mine
  projection_path: models/phi_projections.pkl
  use_adaptive_weighting: false   # Enable in Phase 9

maximal_complex:
  threshold: 0.95                 # 95% of full Φ
  min_fields: 3
  top_phi_fields:
    - silhouette
    - era
    - vibe
    - colors
    - material
    - textile_pattern
    - neckline
    - ai_description

complex_discovery:
  min_support: 10
  min_phi: 0.65
  min_visual_confirmation: 0.50
  max_attributes: 5

cnn:
  enabled: false                  # Set true only if Phase 3 QC shows gaps
  backbone: resnet50
  tasks: [silhouette, neckline, pattern]
```

---

## File Structure

```
scripts/
├── mmfashion_batch.py              # Phase 3: MMFashion batch processor
├── enrichment/
│   └── claude_enrichment.py       # Phase 4: Updated Claude prompt
├── embeddings/
│   └── models.py                  # Phase 5: Re-embedding with MMFashion input
├── iit/
│   ├── phi_calculator.py          # Phase 6: Embedding Φ + attribute Φ
│   ├── attribute_phi.py           # Phase 6: MMFashion-Claude attribute overlap
│   ├── field_attribution.py       # Phase 7: Ablation study
│   ├── complex_discovery.py       # Phase 8: Emergent complex algorithm
│   ├── complex_ontology.py        # Phase 8: Searchable complex index
│   └── adaptive_weighting.py      # Phase 9: Query-adaptive fusion
├── cnn/                           # Phase 10 (conditional)
│   ├── models.py
│   ├── train_multitask.py
│   └── fusion.py
└── storage/
    └── vector_db.py               # Updated: search_with_phi()

vv-web/src/
├── types/index.ts                 # SearchResult with phi fields
└── components/search/
    ├── PhiBadge.tsx               # Phase 6: Φ explainability badge
    └── ComplexBrowser.tsx         # Phase 8: Aesthetic complex UI

config/
└── pipeline.yaml                  # Unified configuration

migrations/
└── 001_master_schema.sql          # All new tables (Phase 2)
```

---

## Key Principles

**Build once.** MMFashion runs first because IIT builds on it at every stage. Implementing IIT without MMFashion means refactoring when MMFashion comes online.

**Calibrate before scaling.** The test-10 step in Phase 3 sets the confidence threshold that ripples through everything. Don't skip it.

**The CNN is conditional.** MMFashion may provide enough visual grounding that the custom CNN is unnecessary. Check your Phase 3–6 QC data before committing to Phases 10.

**Φ degrades gracefully.** Low MMFashion confidence → attribute Φ contributes less → system falls back to embedding Φ → same behavior as pre-MMFashion. No hard failures.

**Visual grounding validates complexes.** Aesthetic complexes discovered in text space are only promoted to the ontology if MMFashion confirms them visually. This is the key quality gate that prevents hallucinated aesthetics from entering the UI.