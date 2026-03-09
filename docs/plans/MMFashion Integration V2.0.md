# MMFashion Integration Plan: Vintage Vestige
## Version 2.0 — Updated for current project state

**Start after:** Supabase migration Steps 12–20 complete  
**Last revised:** March 2026  
**Active stack:** Supabase PostgreSQL + pgvector, SQLAlchemy ORM, FastAPI, Next.js  
**No Qdrant. No local Postgres. No psycopg2. Single venv.**

---

## What This Plan Actually Does

MMFashion runs visual attribute detection on your product images and produces
structured output like:

```
[("dropped-waist", 0.82), ("sleeveless", 0.79), ("sheer-overlay", 0.61),
 ("floral-pattern", 0.55), ("beaded", 0.71)]
```

This plan uses that output in two ways:

**1. Fill gaps in existing Fashionpedia taxonomy fields**
Your `structural_score` already does Jaccard overlap on fields like `silhouette`,
`neckline`, `waistline`, `length`. Many of these are null — especially on museum
records where the original description is sparse. MMFashion populates them from
visual evidence. The scoring formula doesn't change. Bridges get better because
more fields are populated.

**2. Feed visual vocabulary into Claude's enrichment prompt**
Claude re-enriches each product with MMFashion attributes in the prompt. The
resulting `enriched_text` contains specific, falsifiable visual language. That
text gets re-embedded. Bridges improve because the vectors now encode visual
argument structure, not just metadata prose.

**What this is NOT:**
A separate parallel scoring system alongside the existing one. The original plan
proposed that. Your `structural_score` already IS the explicit overlap layer —
adding a duplicate is unnecessary complexity.

---

## How MMFashion Tags Map to Existing Fields

MMFashion's attribute vocabulary maps to fields you already score against:

| MMFashion output | Maps to existing field | Scoring weight |
|---|---|---|
| silhouette terms (A-line, empire, shift) | `silhouette` | 0.15 |
| neckline terms (V-neck, crew, cowl) | `neckline` | 0.08 |
| waist terms (empire, dropped, natural) | `waistline` | 0.07 |
| length terms (floor, midi, mini) | `length` | 0.07 |
| sleeve terms (sleeveless, long, puff) | `sleeve_length` | 0.05 |
| fabric/surface terms (beaded, embroidered) | `decorations` | 0.10 |
| construction terms (sheer, layered) | `textile_finishing` | 0.10 |
| pattern terms (floral, geometric, stripe) | `textile_pattern` | 0.05 |

MMFashion tags that don't map to an existing field (e.g. "vintage-inspired",
"casual") go into `mmfashion_tags` for use in Claude's prompt and the KG's
`ARGUES_THROUGH` edges. They don't need a new scoring dimension.

---

## Bridge Score Formula — Unchanged

```
With image:    bridge_score = 0.40 × text_sim + 0.30 × image_sim + 0.30 × structural
Without image: bridge_score = 0.55 × text_sim + 0.45 × structural
```

`structural_score` gets better automatically because more fields are populated.
No formula changes needed.

---

## Execution Order

| Phase | Task | Time | Dependency |
|---|---|---|---|
| 0 | semantic_type classifier — first pass | 2h | Supabase migration done |
| 1 | Dependencies + model setup | 2–4h | Supabase migration done |
| 2 | Schema migration (Supabase) | 1h | Nothing |
| 3 | MMFashion batch — test (10 records) | 1h | Phases 1+2 |
| 3b | MMFashion batch — full run | Overnight | Phase 3 validated |
| 4 | Update Claude enrichment prompt (MMFashion + vibe vocabulary) | 2–3h | Phase 3b done |
| 5 | Re-enrich via Claude (MMFashion-processed records) | Overnight | Phase 4 |
| 6 | Regenerate pgvector embeddings | 2h | Phase 5 |
| 7 | Recompute bridges | 1h | Phase 6 |
| 7b | semantic_type classifier — second pass | 30min | Phase 7 |
| 8 | QC + threshold tuning | 2h | Phase 7b |

**Total active dev time: ~2.5 solid days.** Overnights handle batch jobs.

**Why two semantic_type passes:**
Phase 0 classifies your existing 7,324 bridges immediately after the Supabase
migration — so the field is populated for deploy and the UI can show bridge types
before MMFashion runs. Phase 7b re-runs the same script on the recomputed bridges
after MMFashion enrichment, catching any new or changed bridges. The script is
identical both times.

---

## Phase 0 — semantic_type Classifier (First Pass)
*Estimated time: 2 hours*

**Run immediately after Supabase migration Steps 12–20 are complete — before
anything else in this plan.** This populates `semantic_type` on all existing
bridges so the field is live for deploy and the UI can show bridge types without
waiting for MMFashion.

### Schema migration

```sql
ALTER TABLE style_bridges
ADD COLUMN IF NOT EXISTS semantic_type VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_bridges_semantic_type
ON style_bridges(semantic_type);
```

Add to `StyleBridge` model in `storage/database.py`:

```python
semantic_type = Column(String(50), nullable=True)
```

### Classifier script

```python
# scripts/classify_semantic_types.py
import json
from storage.database import get_session, StyleBridge

def classify_semantic_type(bridge) -> str:
    btype  = bridge.bridge_type or ''
    score  = bridge.bridge_score or 0
    tsim   = bridge.text_similarity or 0
    struct = bridge.structural_score or 0
    attrs  = json.loads(bridge.shared_attributes or '{}')

    if 'silhouette' in attrs and btype == 'cross_era':
        return 'SILHOUETTE_TRANSMISSION'
    if btype == 'cross_era' and score > 0.6 and tsim > 0.85:
        return 'CULTURAL_CITATION'
    if btype == 'cross_vibe' and score > 0.6:
        return 'COUNTER_ARGUMENT'
    if btype == 'cross_era' and 'material' in attrs:
        return 'MATERIAL_ECHO'
    if btype in ['cross_category', 'near_era'] and struct > 0.5:
        return 'PARALLEL_EMERGENCE'
    if btype == 'same_era' and struct > 0.7:
        return 'STRUCTURAL_SIBLING'
    if btype == 'cross_era':
        return 'CONSTRUCTION_INHERITANCE'
    return 'STRUCTURAL_SIBLING'  # safe default

def run():
    with get_session() as db:
        bridges = db.query(StyleBridge).all()
        for bridge in bridges:
            bridge.semantic_type = classify_semantic_type(bridge)
        db.commit()
        print(f"Classified {len(bridges)} bridges")

        # Distribution check
        from sqlalchemy import func
        dist = db.query(
            StyleBridge.semantic_type,
            func.count(StyleBridge.id)
        ).group_by(StyleBridge.semantic_type).all()
        for stype, count in sorted(dist, key=lambda x: -x[1]):
            print(f"  {stype}: {count}")

if __name__ == '__main__':
    run()
```

```bash
venv/bin/python scripts/classify_semantic_types.py
```

Expected output: all 7,324 bridges classified, distribution across 8 types printed.
Verify the distribution looks reasonable — STRUCTURAL_SIBLING should not be > 50%
of all bridges (if it is, the rule conditions may need tightening).

This script runs again as Phase 7b with identical code, on the recomputed bridges.

---

## Phase 1 — Dependencies + Model Setup
*Estimated time: 2–4 hours*

**Add to your existing venv — do not create a separate one.**

```bash
cd ~/path/to/vintage-vestige
source venv/bin/activate

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install mmcv-full
pip install mmfashion
```

MMFashion itself is cloned separately (it's a research codebase, not a pip package):

```bash
# Clone alongside your project, not inside it
git clone https://github.com/open-mmlab/mmfashion.git ~/mmfashion
cd ~/mmfashion
```

Download the ResNet50 attribute prediction checkpoint from `MODEL_ZOO.md`:

```
~/mmfashion/
  checkpoints/
    resnet50_attr_pred.pth
```

Validate installation:

```python
# scripts/mmfashion_test.py
import sys
sys.path.insert(0, os.path.expanduser('~/mmfashion'))

from mmfashion.apis import init_detector, inference_attribute_predictor

model = init_detector(
    'configs/attribute_predict/global_predictor_vgg.py',
    'checkpoints/resnet50_attr_pred.pth'
)

# Test with any product image URL from Supabase Storage
import requests
from PIL import Image
from io import BytesIO

url = "https://tusswxlrdoamintvswjs.supabase.co/storage/v1/object/public/product-images/1.jpg"
img = Image.open(BytesIO(requests.get(url).content)).convert('RGB')
img.save('/tmp/test.jpg')

result = inference_attribute_predictor(model, '/tmp/test.jpg')
print(result)
# Should return list of (attribute, confidence) tuples
```

---

## Phase 2 — Schema Migration (Supabase)
*Estimated time: 1 hour*

Run via SQLAlchemy migration or direct Supabase SQL editor:

```sql
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_raw_output JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_tags TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_confidence FLOAT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_processed_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS mmfashion_status VARCHAR(20) DEFAULT 'pending';
-- statuses: pending | processed | low_confidence | failed

CREATE INDEX IF NOT EXISTS idx_mmfashion_status ON products(mmfashion_status);
```

Then add the columns to the SQLAlchemy `Product` model in `storage/database.py`:

```python
from sqlalchemy import ARRAY, String, JSON

# Add to Product class:
mmfashion_raw_output    = Column(JSON,             nullable=True)
mmfashion_tags          = Column(ARRAY(String),    nullable=True)
mmfashion_confidence    = Column(Float,            nullable=True)
mmfashion_processed_at  = Column(DateTime,         nullable=True)
mmfashion_status        = Column(String(20),       default='pending')
```

**Note on field population strategy:** Phase 3 stores raw MMFashion output in
`mmfashion_tags` and `mmfashion_raw_output`. Phase 4 (Claude re-enrichment) is
where MMFashion tags get *mapped* into existing Fashionpedia fields (`silhouette`,
`neckline`, etc.) — Claude does the mapping as part of enrichment, not the batch
script. This keeps the batch script simple and lets Claude handle the vocabulary
translation.

---

## Phase 3 — MMFashion Batch Processor
*Estimated time: 1 hour setup, overnight run*

```python
# scripts/mmfashion_batch.py

import os
import sys
import json
import requests
from io import BytesIO
from PIL import Image
from tqdm import tqdm
from datetime import datetime, timezone

sys.path.insert(0, os.path.expanduser('~/mmfashion'))

from mmfashion.apis import init_detector, inference_attribute_predictor
from storage.database import get_session, Product

CONFIDENCE_THRESHOLD = 0.45
BATCH_SIZE = 50
MODEL_CONFIG = os.path.expanduser('~/mmfashion/configs/attribute_predict/global_predictor_vgg.py')
CHECKPOINT   = os.path.expanduser('~/mmfashion/checkpoints/resnet50_attr_pred.pth')
TEMP_IMAGE   = '/tmp/vv_mmfashion_temp.jpg'

def fetch_image(url: str):
    """Download from Supabase Storage URL or external museum URL."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert('RGB')
    except Exception as e:
        print(f"  ✗ Image fetch failed: {e}")
        return None

def run_inference(model, image_path: str) -> dict:
    raw = inference_attribute_predictor(model, image_path)
    tags = [attr for attr, conf in raw if conf >= CONFIDENCE_THRESHOLD]
    confidences = [conf for _, conf in raw]
    return {
        'raw_output': {attr: round(float(conf), 4) for attr, conf in raw},
        'tags': tags,
        'avg_confidence': round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        'top_confidence': round(max(confidences), 4) if confidences else 0.0,
    }

def process_batch(batch_size: int = BATCH_SIZE):
    print("Loading MMFashion model...")
    model = init_detector(MODEL_CONFIG, CHECKPOINT)
    print("Model loaded.\n")

    with get_session() as db:
        products = db.query(Product).filter(
            Product.mmfashion_status == 'pending',
            Product.primary_image.isnot(None),
        ).order_by(Product.id).limit(batch_size).all()

        print(f"Processing {len(products)} records...")

        for product in tqdm(products):
            print(f"\n→ [{product.id}] {product.title[:60]}")

            image = fetch_image(product.primary_image)
            if image is None:
                product.mmfashion_status = 'failed'
                product.mmfashion_processed_at = datetime.now(timezone.utc)
                db.commit()
                continue

            image.save(TEMP_IMAGE)

            try:
                result = run_inference(model, TEMP_IMAGE)
            except Exception as e:
                print(f"  ✗ Inference failed: {e}")
                product.mmfashion_status = 'failed'
                product.mmfashion_processed_at = datetime.now(timezone.utc)
                db.commit()
                continue

            status = 'processed' if result['top_confidence'] >= 0.6 else 'low_confidence'

            product.mmfashion_raw_output    = result['raw_output']
            product.mmfashion_tags          = result['tags']
            product.mmfashion_confidence    = result['avg_confidence']
            product.mmfashion_status        = status
            product.mmfashion_processed_at  = datetime.now(timezone.utc)
            db.commit()

            print(f"  ✓ {status} | tags: {result['tags'][:5]} | conf: {result['top_confidence']:.2f}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    process_batch(args.batch_size)
```

**Run test batch first:**

```bash
venv/bin/python scripts/mmfashion_batch.py --batch-size 10
```

Review results in Supabase SQL editor before scaling:

```sql
SELECT id, title, mmfashion_tags, mmfashion_confidence, mmfashion_status
FROM products
WHERE mmfashion_status != 'pending'
ORDER BY id
LIMIT 10;
```

If tags look reasonable, run the full batch:

```bash
venv/bin/python scripts/mmfashion_batch.py --batch-size 2000
# Runs overnight; safe to interrupt and resume (status tracking handles it)
```

---

## Phase 4 — Update Claude Enrichment Prompt
*Estimated time: 2–3 hours*

Two things change in `enrichment/claude.py` at the same time: MMFashion attributes
enter the prompt, and the `vibe` field gets replaced with a controlled vocabulary.
Both are prompt changes. Both require the same re-enrichment pass. Do them together.

### 4a — Schema update for new vibe fields

The current `vibe` column is a single `VARCHAR`. Replace it with three structured
fields that carry more signal for bridges and the KG:

```sql
ALTER TABLE products ADD COLUMN IF NOT EXISTS core_vibes TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS bridge_vibes TEXT[];
ALTER TABLE products ADD COLUMN IF NOT EXISTS vibe_scores JSONB;
-- Keep the existing vibe column for now as fallback; deprecate after re-enrichment
```

Add to `Product` model in `storage/database.py`:

```python
core_vibes    = Column(ARRAY(String), nullable=True)  # primary aesthetic terms
bridge_vibes  = Column(ARRAY(String), nullable=True)  # terms that bridge to other eras
vibe_scores   = Column(JSON,          nullable=True)  # {term: confidence_float}
```

### 4b — Updated enrichment prompt

The controlled vibe vocabulary replaces open-ended vibe generation. Claude now
picks from a defined list organized across four axes — Volume/Silhouette, Ornament/
Surface, Body Relationship, Cultural Register — each term carrying an explicit
aesthetic argument rather than just a label. This produces consistent terms that
cluster meaningfully in vector space, become DesignElement nodes in the KG, and
make bridge narratives more argumentative. A garment can hold terms from multiple
axes simultaneously. The `core_vibes` limit is raised to 1–3 terms (from 1–2)
to accommodate multi-axis assignments.

```python
# enrichment/claude.py — updated build_enrichment_prompt()

# Controlled vibe vocabulary — consistent across all products
# Four axes: Volume/Silhouette, Ornament/Surface, Body Relationship, Cultural Register
# Each term carries an explicit aesthetic argument — use this framing in descriptions.
VIBE_VOCABULARY = """
CONTROLLED VIBE VOCABULARY (pick only from these terms):

Each term is followed by its definition and the aesthetic argument it makes.
Assign terms that reflect what the garment is ARGUING, not just what it looks like.

AXIS 1 — Volume and Silhouette
(The garment's relationship to the body through shape and mass)

  - Exaggerated Volume     — structural mass exceeds functional necessity; the outline
                             is the subject, not the body beneath. Panniers, crinolines,
                             puff sleeves, Comme des Garçons padding.
                             The argument: the garment itself is the subject.

  - Column Minimalism      — unbroken vertical line, body-skimming or body-revealing,
                             no structural intervention between fabric and form.
                             Fortuny, 1960s shift, The Row.
                             The argument: the body is sufficient.

  - Empire Suspension      — high waistline releases the body below; fabric falls from
                             a single gathering point beneath the bust. Neoclassical,
                             Regency, 1910s reform dress, certain 1960s revivals.
                             The argument: liberation from below.

  - Constructed Armor      — rigid or semi-rigid structure holds the body in a
                             predetermined shape; garment as exoskeleton. Stays,
                             corsetry, McQueen tailoring, Thom Browne.
                             The argument: the body must be managed.

  - Draped Fluidity        — fabric organized by gravity and body movement, not
                             structure; no fixed silhouette. Greek chiton, Vionnet
                             bias cut, Issey Miyake pleats.
                             The argument: the body and fabric are in conversation.

  - Layered Accumulation   — multiple garments or fabric weights building depth;
                             no single silhouette readable. Medieval layering,
                             Rei Kawakubo, certain folk traditions.
                             The argument: identity is cumulative.

AXIS 2 — Ornament and Surface
(What the garment does at its surface — decoration, material, texture)

  - Maximalist Ornament    — surface decoration exceeds structural function; the
                             ornament is the primary aesthetic event. Rococo
                             embroidery, Valentino couture, Victorian beading.
                             The argument: excess is meaning.

  - Austere Restraint      — deliberate removal of decoration; surface communicates
                             through absence. Quaker dress, Japanese minimalism,
                             Jil Sander.
                             The argument: restraint is its own statement.

  - Handcraft Visibility   — surface makes its own making visible; evidence of human
                             labor is the aesthetic content. Arts and Crafts dress,
                             folk embroidery, contemporary slow fashion.
                             The argument: the hand that made this matters.

  - Material Luxury        — communication through inherent material richness, not
                             applied decoration. Heavy silk, rare fur, fine wool,
                             certain contemporary leather goods.
                             The argument: substance speaks louder than ornament.

  - Pattern as Language    — surface organized by repeating motifs carrying cultural
                             or symbolic content. Tartan, toile, ikat, Liberty prints.
                             The argument: pattern is a form of speech.

  - Transparency and Revelation — deliberate use of sheer or open materials to
                             suggest or reveal what is beneath. Victorian lace,
                             1970s chiffon, contemporary mesh.
                             The argument: concealment and revelation are simultaneous.

AXIS 3 — Body Relationship
(The ideological relationship the garment proposes between itself and the body)

  - Body Liberation        — designed to free the body from restriction; refuses
                             constraint. Reform dress, 1920s drop waist, 1970s
                             jersey, athletic crossover.
                             The argument: the body should move freely.

  - Body Transformation    — designed to reshape the body into a culturally preferred
                             form. Corsetry, padding, foundation garments, certain
                             contemporary shapewear aesthetics.
                             The argument: the natural body is insufficient.

  - Body Concealment       — deliberately obscures the body's form; refuses the gaze.
                             Certain religious dress, 1980s power suiting,
                             contemporary modest fashion, Balenciaga volume.
                             The argument: the body is private.

  - Body Display           — stages the body for viewing; makes it the subject of
                             attention. Court dress décolletage, 1950s swimwear,
                             contemporary bodycon.
                             The argument: the body is public.

AXIS 4 — Cultural Register
(The social and cultural argument — class, nature, ceremony, transgression)

  - Pastoral Naturalism    — invokes nature, rural life, or pre-industrial simplicity,
                             genuine or constructed. 18th century pastoral costume,
                             Arts and Crafts dress, 1970s folk revival, cottagecore.
                             The argument: nature is preferable to culture.

  - Ceremonial Formalism   — primary function is to mark ritual occasion, separate it
                             from the everyday. Court dress, ecclesiastical vestment,
                             wedding dress across cultures.
                             The argument: some moments require dedicated clothing.

  - Dark Romanticism       — aestheticizes melancholy, mortality, or the uncanny.
                             Victorian mourning dress, Gothic subculture, certain
                             Alexander McQueen, dark academia.
                             The argument: darkness is beautiful.

  - Transgressive Subversion — deliberately violates the sartorial norms of its
                             moment; uses dress as protest or provocation. Bloomers,
                             punk, early queer fashion, certain streetwear.
                             The argument: clothing can refuse.

  - Nostalgic Revival      — consciously quotes a previous era; the historical
                             reference is the primary aesthetic content. Victorian
                             revival in Edwardian dress, 1930s Hollywood glamour
                             revivals, contemporary vintage aesthetics.
                             The argument: the past was better, or at least richer.

  - Elite Distinction      — communicates social position through understatement,
                             quality, and codes legible only to insiders. Savile Row
                             tailoring, old money aesthetics, quiet luxury.
                             The argument: true status needs no announcement.

Assign:
  core_vibes:   1–3 terms (from any axis) that define this piece's primary arguments
  bridge_vibes: 1–2 terms most likely to find echoes across other eras — the argument
                this piece shares with garments centuries before or after it
  vibe_scores:  confidence for each assigned term (0.0–1.0)

Note on bridge_vibes: A term makes a good bridge_vibe when its argument is not
era-specific — when the same claim (e.g. "the body should move freely") has been
made in radically different historical moments. Axis 3 (Body Relationship) and
Axis 1 (Volume/Silhouette) terms tend to bridge well. Axis 4 (Cultural Register)
terms are often more era-specific and bridge less reliably.
"""

def build_enrichment_prompt(record: dict) -> str:

    mmfashion_section = ""
    if record.get('mmfashion_tags'):
        conf = record.get('mmfashion_confidence', 0)
        confidence_label = (
            "high — treat as reliable visual facts"      if conf > 0.65 else
            "medium — cross-reference with metadata"     if conf > 0.45 else
            "low — use metadata as primary source"
        )
        mmfashion_section = f"""
VISUAL ATTRIBUTES (MMFashion detection, confidence: {confidence_label}):
{', '.join(record['mmfashion_tags'])}
"""

    return f"""You are enriching a historical fashion record for Vintage Vestige,
a knowledge graph that connects museum archival pieces to modern fashion through
AI-powered style bridges.

MUSEUM METADATA:
Title: {record['title']}
Date: {record.get('object_date', 'Unknown')}
Culture/Origin: {record.get('culture', 'Unknown')}
Materials: {record.get('material', 'Unknown')}
Source: {record.get('platform', 'Unknown')}
Description: {record.get('description', 'None provided')}
{mmfashion_section}
{VIBE_VOCABULARY}
YOUR TASKS:

1. TAXONOMY FIELDS: Assign values to as many of these fields as possible.
   For fields where MMFashion attributes are present and reliable, prefer the
   visual evidence over inference from text.

   - silhouette: [A-line, empire, hourglass, rectangular, bustle, dropped-waist,
                  shift, wrap, column, ball-gown]
   - neckline: [V-neck, crew, cowl, square, off-shoulder, halter, boat, sweetheart]
   - waistline: [empire, natural, dropped, no-waist]
   - length: [floor, midi, knee, mini, cropped]
   - sleeve_length: [sleeveless, short, elbow, long, puff]
   - textile_pattern: [solid, floral, geometric, stripe, plaid, abstract, animal]
   - textile_finishing: list of applicable terms
   - garment_parts: list of components (bodice, skirt, collar, etc.)
   - decorations: list of embellishments (beaded, embroidered, ruffled, etc.)

   If a field genuinely cannot be determined, leave it null. Do not guess.

2. VIBE FIELDS: Using ONLY the controlled vocabulary above:
   - core_vibes: 1–3 terms (from any axis) that define this piece's primary arguments.
     A garment can argue simultaneously on multiple axes — assign terms that reflect
     what it is actually claiming, not just what it resembles.
   - bridge_vibes: 1–2 terms most likely to connect this piece to garments from other
     eras. Prefer Axis 1 (Volume/Silhouette) and Axis 3 (Body Relationship) terms —
     these arguments recur across centuries. Axis 4 (Cultural Register) terms are
     often era-specific and bridge less reliably.
   - vibe_scores: confidence for each term you assign (0.0–1.0)

3. CONFLICT NOTE: If any MMFashion attribute conflicts with the historical
   metadata (e.g. MMFashion says "denim" but the piece is 1890s silk), note it
   briefly in validation_notes.

4. ENRICHED DESCRIPTION: Write 150–200 words placing this piece in its fashion
   history moment, using the assigned vibe terms and specific visual vocabulary.
   This text gets embedded for semantic search — specificity matters more than
   prose quality.

5. STYLE BRIDGES: 3 connections to contemporary fashion. Each needs:
   - The specific visual/structural element being bridged
   - A contemporary designer, brand, or movement that echoes it
   - Why the connection is meaningful (reference bridge_vibes where applicable)

6. STYLE TAGS: 5–8 search-optimized tags
   OCCASION: [formal, everyday, ceremonial, workwear, sportswear, eveningwear]

Respond in JSON with keys:
silhouette, neckline, waistline, length, sleeve_length, textile_pattern,
textile_finishing, garment_parts, decorations,
core_vibes, bridge_vibes, vibe_scores,
style_tags, occasion, enriched_description, style_bridges, validation_notes
"""
```

### 4c — Update build_rich_text() to use new vibe fields

```python
# enrichment/claude.py — updated build_rich_text()

def build_rich_text(product) -> str:
    """
    Build embedding text from enriched product.
    Uses new vibe fields when available; falls back to legacy vibe string.
    """
    parts = [
        product.ai_description or '',
        f"{product.era} era" if product.era else '',
        f"{product.decade}" if product.decade else '',
        product.silhouette or '',
        product.neckline or '',
        product.waistline or '',
        product.length or '',
        product.sleeve_length or '',
        product.material or '',
        product.textile_pattern or '',
        ' '.join(json.loads(product.textile_finishing)) if product.textile_finishing else '',
        ' '.join(json.loads(product.garment_parts))     if product.garment_parts else '',
        ' '.join(json.loads(product.decorations))       if product.decorations else '',
        ' '.join(json.loads(product.style_tags))        if product.style_tags else '',
        # Vibe: use controlled vocabulary fields if available, fallback to legacy
        ' '.join(product.core_vibes)   if product.core_vibes   else (product.vibe or ''),
        ' '.join(product.bridge_vibes) if product.bridge_vibes else '',
        # MMFashion tags — any that didn't map to Fashionpedia fields
        ' '.join(product.mmfashion_tags) if product.mmfashion_tags else '',
    ]
    return ' '.join(filter(None, parts))[:512]  # MiniLM effective window
```


---

## Phase 5 — Re-Enrichment Batch
*Estimated time: 1 hour setup, runs overnight*

Re-enrich products that have MMFashion data but whose enrichment predates it
(or haven't been enriched yet).

```python
# scripts/re_enrich_mmfashion.py

from storage.database import get_session, Product
from enrichment.claude import ClaudeEnricher
from tqdm import tqdm

BATCH_SIZE = 100

def re_enrich():
    enricher = ClaudeEnricher()

    with get_session() as db:
        # Products with MMFashion data that need re-enrichment
        products = db.query(Product).filter(
            Product.mmfashion_status.in_(['processed', 'low_confidence']),
            # Either never enriched, or enriched before MMFashion ran
            (Product.enriched_at == None) |
            (Product.enriched_at < Product.mmfashion_processed_at)
        ).order_by(
            Product.mmfashion_confidence.desc()  # high-confidence records first
        ).limit(BATCH_SIZE).all()

        print(f"Re-enriching {len(products)} records...")

        for product in tqdm(products):
            record = {
                'title':            product.title,
                'object_date':      product.object_date,
                'culture':          product.culture,
                'material':         product.material,
                'platform':         product.platform,
                'description':      product.description,
                'mmfashion_tags':   product.mmfashion_tags,
                'mmfashion_confidence': product.mmfashion_confidence,
            }
            try:
                enricher.enrich_product(db, product, record)
                db.commit()
            except Exception as e:
                print(f"  ✗ [{product.id}] failed: {e}")
                db.rollback()

if __name__ == '__main__':
    re_enrich()
```

Run with high-confidence records first to validate quality before the full batch:

```bash
# Test on 10 records
venv/bin/python scripts/re_enrich_mmfashion.py  # BATCH_SIZE=10 first

# Review in Supabase SQL editor, then run full batch overnight
```

---

## Phase 6 — Regenerate pgvector Embeddings
*Estimated time: 2 hours*

**Important:** Regenerate embeddings from the Claude-enriched `enriched_text`,
not by directly appending `mmfashion_tags`. Claude has already woven the visual
attributes into coherent fashion language in Phase 5. Embedding that is better
than embedding a raw tag list.

```python
# scripts/regenerate_embeddings_mmfashion.py

from storage.database import get_session, Product
from embeddings.generator import EmbeddingGenerator
from tqdm import tqdm

def regenerate():
    generator = EmbeddingGenerator()

    with get_session() as db:
        # Only re-embed products that were re-enriched after MMFashion
        products = db.query(Product).filter(
            Product.mmfashion_status.in_(['processed', 'low_confidence']),
            Product.enriched_at.isnot(None),
            Product.mmfashion_processed_at.isnot(None),
            Product.enriched_at >= Product.mmfashion_processed_at
        ).all()

        print(f"Regenerating embeddings for {len(products)} products...")

        for product in tqdm(products):
            if not product.enriched_text:
                continue

            try:
                # Text embedding — from Claude-enriched text (includes MMFashion vocabulary)
                text_emb = generator.generate_text_embedding(product.enriched_text)
                product.text_embedding = text_emb.tolist()

                # Image embedding — only if primary_image changed (usually not needed)
                # Skip unless you have reason to believe image URLs changed

                db.commit()
            except Exception as e:
                print(f"  ✗ [{product.id}] failed: {e}")
                db.rollback()

if __name__ == '__main__':
    regenerate()
```

---

## Phase 7 — Recompute Bridges
*Estimated time: 1 hour*

Run `compute_bridges.py` on the full enriched + re-embedded dataset. This is the
same script you updated in Supabase migration Step 12 — no changes needed. It now
has richer structural fields to score against (more non-null values in `silhouette`,
`neckline`, etc.) and better text embeddings (MMFashion vocabulary in `enriched_text`).

```bash
venv/bin/python analysis/compute_bridges.py
```

Expected outcome:
- Bridge count comparable to current 7,324 (same `top_n` cap per product)
- Higher average `structural_score` (more fields populated = more overlap found)
- Bridge quality visibly better on products that previously had sparse taxonomy fields

---

## Phase 7b — semantic_type Classifier (Second Pass)
*Estimated time: 30 minutes*

Re-run the identical classifier script from Phase 0 on the recomputed bridges.
This catches:
- New bridges created during the recompute (new products from data growth)
- Bridges whose `shared_attributes` changed because Fashionpedia fields are now
  more populated post-MMFashion (a previously null `silhouette` field now has a
  value, which can flip a bridge from STRUCTURAL_SIBLING to SILHOUETTE_TRANSMISSION)

```bash
venv/bin/python scripts/classify_semantic_types.py
```

Same script as Phase 0. Check the distribution again — compare against Phase 0
output. You should see:
- Higher count of typed bridges (more bridges total after recompute)
- Shift away from STRUCTURAL_SIBLING toward more specific types (SILHOUETTE_TRANSMISSION,
  MATERIAL_ECHO, etc.) as previously null fields are now populated

---

## Phase 8 — QC + Threshold Tuning
*Estimated time: 2–3 hours*

### Check MMFashion coverage and confidence

```sql
-- Coverage and confidence distribution
SELECT
    mmfashion_status,
    COUNT(*) as count,
    ROUND(AVG(mmfashion_confidence)::numeric, 3) as avg_confidence
FROM products
GROUP BY mmfashion_status
ORDER BY count DESC;

-- How many more taxonomy fields are now populated vs. before?
SELECT
    COUNT(*) FILTER (WHERE silhouette IS NOT NULL)    as has_silhouette,
    COUNT(*) FILTER (WHERE neckline IS NOT NULL)      as has_neckline,
    COUNT(*) FILTER (WHERE waistline IS NOT NULL)     as has_waistline,
    COUNT(*) FILTER (WHERE length IS NOT NULL)        as has_length,
    COUNT(*) as total
FROM products
WHERE enriched_at IS NOT NULL;
-- Compare against pre-MMFashion baseline if you logged it
```

### Check bridge quality improvement

```sql
-- Structural score distribution before and after
-- Run after bridge recompute; compare avg structural_score
SELECT
    ROUND(AVG(structural_score)::numeric, 4) as avg_structural,
    ROUND(AVG(bridge_score)::numeric, 4)     as avg_bridge,
    COUNT(*) as total_bridges,
    COUNT(*) FILTER (WHERE structural_score > 0.5) as high_struct_bridges
FROM style_bridges;
```

### Spot-check bridge narratives

```sql
-- Sample bridges with high structural scores on previously sparse records
SELECT
    p1.title as source,
    p2.title as target,
    sb.structural_score,
    sb.bridge_score,
    sb.bridge_narrative,
    sb.shared_attributes
FROM style_bridges sb
JOIN products p1 ON sb.source_id = p1.id
JOIN products p2 ON sb.target_id = p2.id
WHERE sb.structural_score > 0.6
  AND p1.platform IN ('met_museum', 'smithsonian')
ORDER BY sb.structural_score DESC
LIMIT 20;
```

### Flag MMFashion/metadata conflicts

```sql
-- Claude flagged conflicts in validation_notes during re-enrichment
-- Check this field if you stored it (update schema if needed)
SELECT id, title, mmfashion_tags, mmfashion_confidence
FROM products
WHERE mmfashion_status = 'processed'
  AND mmfashion_confidence < 0.5
ORDER BY mmfashion_confidence ASC
LIMIT 20;
-- Low-confidence results may have introduced noise — review manually
```

---

## What Stays the Same

| Thing | Status |
|---|---|
| Bridge scoring formula | **Unchanged** — `structural_score` gets better, formula stays |
| `compute_bridges.py` | **Unchanged** — runs as-is after re-embedding |
| Qdrant / vector_db.py | **Gone** — pgvector handles everything |
| `text_embedding` + `image_embedding` columns | **Unchanged** — same schema, richer content |
| FastAPI bridge endpoints | **Unchanged** — serve better data automatically |
| Frontend bridge components | **Unchanged** — richer narratives render in existing UI |

---

## What Changes

| Thing | How it changes |
|---|---|
| `products` table | +5 new MMFashion columns, +3 new vibe columns (`core_vibes`, `bridge_vibes`, `vibe_scores`) |
| `style_bridges` table | +1 new column (`semantic_type`) |
| `enriched_text` | Now includes visual vocabulary from MMFashion via Claude |
| `vibe` field | Replaced by controlled vocabulary: `core_vibes` + `bridge_vibes` arrays |
| Fashionpedia fields (`silhouette`, `neckline`, etc.) | More populated — fewer nulls |
| `text_embedding` vectors | Richer — re-embedded from better `enriched_text` |
| Bridge narratives | More specific and falsifiable |
| `structural_score` distribution | Higher average — more fields to match against |
| `semantic_type` distribution | More specific types (less STRUCTURAL_SIBLING) after recompute |
| Claude enrichment prompt | Updated with MMFashion attributes + controlled vibe vocabulary |

---
![[MMFashion Integration V2.0]]
## Relationship to KG Plan

MMFashion completes before KG work begins. The KG's `ARGUES_THROUGH` edges connect
Bridge nodes to DesignElement nodes via the `shared_attributes` JSON on each bridge.
Richer `shared_attributes` (more populated Fashionpedia fields post-MMFashion) means
richer DesignElement vocabulary and more `ARGUES_THROUGH` edges — the KG is more
connected and more meaningful.

`mmfashion_tags` on the `products` table also becomes a direct source for DesignElement
extraction in KG Phase 3 (`extract_design_elements.py`) — alongside the existing
`shared_attributes` mining.

**Full sequence:**
```
Supabase migration complete (Steps 12–20)
    ↓
semantic_type classifier — first pass on existing 7,324 bridges  ← Phase 0 of this plan
    ↓
Data growth to ~1,500 enriched products
    ↓
MMFashion pipeline (Phases 1–8 of this plan)
  └─ Phase 7b: semantic_type classifier — second pass on recomputed bridges
    ↓
Deploy (Railway + Vercel)
    ↓
KG when multi-step bridge UI is planned
```

Note: `semantic_type` is no longer a separate pre-KG step — it's baked into
this plan at Phase 0 and Phase 7b. By the time you deploy, the column is
fully populated and up to date.