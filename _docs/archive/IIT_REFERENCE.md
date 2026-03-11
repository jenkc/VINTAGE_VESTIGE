# IIT 4.0 Integration Reference
**For Post-MVP Implementation**

> This document provides a quick reference for implementing Integrated Information Theory (IIT) 4.0 concepts in Vintage Vestige after MVP deployment. It distills the comprehensive plan into actionable sections you can revisit as needed.

---

## Quick Navigation

- [Why IIT 4.0?](#why-iit-40)
- [Prerequisites](#prerequisites)
- [Core Concepts Cheat Sheet](#core-concepts-cheat-sheet)
- [Implementation Quick Start](#implementation-quick-start)
- [4 Approaches Overview](#4-approaches-overview)
- [CNN Integration](#cnn-integration)
- [Code Examples](#code-examples)
- [Validation Checklist](#validation-checklist)
- [Resources & References](#resources--references)

---

## Why IIT 4.0?

**Problem**: Your current search engine treats image and text embeddings independently. Users can't tell *why* a vintage dress matches "dark academia" or which attributes drove the match.

**Solution**: IIT 4.0 provides:
1. **Φ (Phi) Score**: Measures how well image and text *integrate* to define a product
2. **Explainability**: Shows which attributes (era, vibe, silhouette) create the match
3. **Emergent Patterns**: Discovers aesthetic "complexes" like "GothVictorian" from data
4. **Better Ranking**: Re-rank by integration quality, not just similarity

**Expected Impact**:
- +5-10% improvement on aesthetic/vibe queries
- Clear explanations: "This matched because image + text agree on Victorian era + lace + romantic vibe (Φ=0.82)"
- Novel discovery of ~20-30 coherent aesthetic clusters

---

## Prerequisites

Before starting IIT 4.0 integration, ensure:

✅ **MVP Deployed**:
- [ ] Basic text + image search working
- [ ] Claude enrichment pipeline running (23 fields)
- [ ] Qdrant vector DB with separate text/image collections
- [ ] ~1000+ products with embeddings

✅ **Search Quality Baseline Established**:
- [ ] Test suite with 14 standard queries
- [ ] Baseline scores recorded (see `tests/search_quality/test_search_quality.py`)
- [ ] Users can successfully find items with current system

✅ **Technical Infrastructure**:
- [ ] PostgreSQL with enrichment fields (era, vibe, silhouette, etc.)
- [ ] Embedding models: CLIP (512-dim) + MiniLM (384-dim)
- [ ] API endpoints for search functional

If any of these are missing, finish MVP first. IIT 4.0 *enhances* a working system; it can't fix a broken one.

---

## Core Concepts Cheat Sheet

### Φ (Integrated Information)

**What**: A number (0 to 1) measuring how much two modalities (image + text) create a unified representation beyond what each provides alone.

**Math**:
```
Φ(image, text) = I(image; text) - [H(image) + H(text)]
```
Where:
- `I(·;·)` = mutual information (how much they share)
- `H(·)` = entropy (individual uncertainty)
- High Φ = strong integration (image + text agree)
- Low Φ = weak integration (contradictory or redundant)

**Example**:
- Product: Victorian lace dress
- Image embedding: {lace texture, empire silhouette, cream color}
- Text embedding: {Victorian era, romantic vibe, lace material}
- **Φ = 0.82** (high) → image and text strongly agree on "Victorian romantic lace"

---

### Integration Axiom

**Theory**: Consciousness is unified, not scattered parts. You see a *scene*, not pixels.

**Application**: Search results should represent unified aesthetics ("dark academia"), not just {dark} + {Victorian} + {tweed} as separate matches.

**Implementation**: Identify which attribute combinations have high Φ (irreducible) vs. low Φ (just coincidence).

---

### Maximal Existence Principle

**Theory**: Among overlapping systems, only the one with highest Φ "truly exists."

**Application**: Your products have 23 enrichment fields, but not all matter equally:
- Era + Decade are redundant (low Φ gain)
- Silhouette + Neckline might be independent (medium Φ)
- Vibe + Colors might strongly integrate (high Φ)

**Implementation**: Include only the fields that maximize Φ in your rich text.

---

### Irreducible Complexes

**Theory**: A complex is a system where the whole > sum of parts.

**Application**: Some attribute combos create emergent meanings:
- `{Victorian, lace, empire_waistline, romantic}` → coherent aesthetic (Φ=0.82)
- `{Victorian, lace}` alone → incomplete (Φ=0.45)

**Implementation**: Discover these complexes from data, then enable "search by aesthetic complex."

---

## Implementation Quick Start

### Phase 0: Simple Φ Prototype (1-2 weeks)

**Goal**: Get Φ scores working with a fast approximation.

**Steps**:
1. **Train projection matrices** (CCA):
   ```bash
   python scripts/iit/train_projections.py
   # Output: models/phi_projections.pkl
   ```

2. **Create Φ calculator**:
   ```python
   # scripts/iit/phi_calculator.py
   class PhiCalculator:
       def calculate_phi(self, text_emb, image_emb):
           # Project to common space
           text_proj = self.text_projection @ text_emb
           image_proj = self.image_projection @ image_emb
           # Cosine similarity as Φ proxy
           phi = (cosine(text_proj, image_proj) + 1) / 2
           return phi
   ```

3. **Add Φ to search results**:
   ```python
   # scripts/storage/vector_db.py
   def search_with_phi(self, query, limit=10):
       results = self.search_similar(query, limit)
       for result in results:
           text_emb = get_text_embedding(result['id'])
           image_emb = get_image_embedding(result['id'])
           result['phi'] = phi_calculator.calculate_phi(text_emb, image_emb)
       return results
   ```

4. **Display Φ in UI**:
   ```tsx
   // vv-web/src/components/search/ProductCard.tsx
   <Badge variant={phi > 0.7 ? 'default' : 'secondary'}>
     Φ {(phi * 100).toFixed(0)}%
   </Badge>
   ```

**Validation**:
- Check Φ distribution: Should be roughly normal, centered ~0.5
- Manual check: Do high-Φ results feel more coherent?
- No search quality regression

---

### Phase 1: Φ-Weighted Ranking (2-3 weeks)

**Goal**: Use Φ to improve search quality.

**Implementation**:
```python
def search_with_phi_ranking(self, query, phi_weight=0.3, limit=10):
    results = self.search_similar(query, limit * 2)

    for result in results:
        phi = calculate_phi(result)
        cosine = result['score']
        result['final_score'] = (1 - phi_weight) * cosine + phi_weight * phi

    results.sort(key=lambda r: r['final_score'], reverse=True)
    return results[:limit]
```

**A/B Test**:
- Control: `phi_weight=0` (baseline)
- Treatment: `phi_weight=0.3`
- Measure: Vibe query scores, user engagement

**Expected**: +5-10% on vibe queries like "dark academia aesthetic"

---

### Phase 2: Attribute Attribution (1-2 weeks)

**Goal**: Show users *which* attributes drove the match.

**Implementation**:
```python
def explain_match(product, query):
    """Calculate Φ contribution per enrichment field"""
    attributions = {}

    for field in ['era', 'vibe', 'silhouette', 'colors', 'material']:
        # Φ with field
        phi_with = calculate_phi_with_fields(product, include=[field])
        # Φ without field
        phi_without = calculate_phi_with_fields(product, exclude=[field])
        # Attribution = difference
        attributions[field] = phi_with - phi_without

    # Top 3 contributors
    top_3 = sorted(attributions.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        'explanation': f"Matched for {top_3[0][0]}, {top_3[1][0]}, and {top_3[2][0]}",
        'attributions': attributions
    }
```

**UI Example**:
```
Victorian Lace Dress
Φ 82% (High Integration)

Why this matched:
• Silhouette (Φ=0.38): A-line shape
• Era (Φ=0.27): Victorian period
• Vibe (Φ=0.18): Romantic aesthetic
```

---

### Phase 3: Complex Discovery (2-3 weeks)

**Goal**: Find emergent aesthetic clusters.

**Implementation**:
```python
def discover_complexes(products, min_phi=0.65, min_support=10):
    complexes = []

    # Test combinations of 3-5 attributes
    for size in range(3, 6):
        for field_combo in combinations(SEMANTIC_FIELDS, size):
            # Find products with this combo
            matching = find_products_with_attributes(products, field_combo)

            if len(matching) < min_support:
                continue

            # Calculate average Φ
            avg_phi = mean([calculate_phi_for_fields(p, field_combo)
                           for p in matching])

            if avg_phi >= min_phi:
                complexes.append({
                    'name': generate_name(field_combo),
                    'attributes': field_combo,
                    'phi': avg_phi,
                    'products': matching
                })

    return complexes
```

**Output Example**:
```
Discovered: GothVictorian
  Φ = 0.82
  {era=Victorian, vibe=dark, colors=[black, burgundy], material=velvet}
  47 products

Discovered: RomanticCottagecore
  Φ = 0.78
  {vibe=romantic, colors=[cream, pink], silhouette=empire, material=lace}
  62 products
```

---

## 4 Approaches Overview

### Approach 1: Φ-Based Ranking ⭐ Start Here

**Priority**: HIGHEST
**Complexity**: LOW
**Impact**: MEDIUM-HIGH

**What**: Calculate Φ between image and text for each result, use it to re-rank.

**When to implement**: Immediately after MVP

**Files to modify**:
- `scripts/iit/phi_calculator.py` (new)
- `scripts/storage/vector_db.py` (+50 lines)
- `vv-web/src/types/index.ts` (+5 lines)
- `vv-web/src/components/search/PhiBadge.tsx` (new)

**Success metrics**:
- Φ distribution is meaningful (not all 0 or 1)
- +5-10% on vibe queries
- Users understand Φ explanation

---

### Approach 2: Maximal Attribute Selection

**Priority**: MEDIUM
**Complexity**: MEDIUM
**Impact**: MEDIUM

**What**: Use Φ to identify which enrichment fields matter most, optimize rich text.

**When to implement**: After Approach 1 validates that Φ correlates with quality

**Files to modify**:
- `scripts/iit/field_attribution.py` (new)
- `scripts/enrichment/claude.py` (modify prompt)
- `scripts/embedding_and_enrichment/enrich_and_reembed_all.py` (modify rich text)

**Success metrics**:
- Mean Φ increases +0.05-0.10
- Search quality improves +3-5%
- Identified 8-10 "core" fields vs. 15 "redundant" fields

---

### Approach 3: Emergent Complex Discovery

**Priority**: LOW-MEDIUM
**Complexity**: HIGH
**Impact**: HIGH (novel UX)

**What**: Discover aesthetic "complexes" from data, enable complex-based search.

**When to implement**: After Approach 2, when you have solid Φ infrastructure

**Files to modify**:
- `scripts/iit/complex_discovery.py` (new)
- `scripts/storage/database.py` (+1 table: discovered_complexes)
- `vv-web/src/app/complexes/page.tsx` (new page)

**Success metrics**:
- 20-30 meaningful complexes discovered
- User study: >80% agree complexes are coherent
- Complex search precision > generic search

---

### Approach 4: Adaptive Multi-Modal Weighting

**Priority**: LOW
**Complexity**: MEDIUM
**Impact**: MEDIUM

**What**: Adjust image vs. text weight based on query-specific Φ.

**When to implement**: After Approaches 1-3, as optimization

**Files to modify**:
- `scripts/iit/query_analyzer.py` (new)
- `scripts/storage/vector_db.py` (modify search logic)

**Success metrics**:
- Low-Φ queries improve +5%
- No regression on high-Φ queries

---

## CNN Integration

### Why Add CNNs?

**Current System**: All attributes (silhouette, neckline, pattern, colors) come from **Claude text analysis**, not computer vision.

**Problem**:
- Claude infers from text descriptions (title, metadata)
- Etsy/Depop listings have poor/incomplete text
- No visual verification of attributes
- CLIP is general-purpose, not fine-tuned for vintage fashion

**Solution**: Train CNNs to predict attributes **directly from images**, then fuse with Claude predictions using Φ.

---

### Quick Implementation Path

**Step 1: Prepare Training Data** (1 week)

Use your existing Claude enrichment as ground truth labels:

```bash
python scripts/cnn/prepare_training_data.py \
  --products 1000 \
  --output data/cnn_training/ \
  --split 0.7/0.15/0.15
```

Output:
```
data/cnn_training/
├── train/
│   ├── images/
│   └── labels.json  # {'product_id': 123, 'silhouette': 'A-line', ...}
├── val/
└── test/
```

---

**Step 2: Train Multi-Task CNN** (1-2 weeks)

Adapt Fashion-MNIST CNN pattern to your Fashionpedia taxonomy:

```python
# scripts/cnn/train_multitask.py

from torchvision import models
import torch.nn as nn

class FashionAttributeCNN(nn.Module):
    def __init__(self):
        super().__init__()
        # Use pretrained ResNet50 backbone
        backbone = models.resnet50(pretrained=True)
        self.features = nn.Sequential(*list(backbone.children())[:-1])

        # Multi-task heads
        self.silhouette_head = nn.Linear(2048, 12)  # 12 silhouettes
        self.neckline_head = nn.Linear(2048, 8)     # 8 necklines
        self.pattern_head = nn.Linear(2048, 6)      # 6 patterns

    def forward(self, x):
        features = self.features(x).flatten(1)
        return {
            'silhouette': self.silhouette_head(features),
            'neckline': self.neckline_head(features),
            'pattern': self.pattern_head(features)
        }

# Train with multi-task loss
model = FashionAttributeCNN()
# ... training loop ...
```

**Expected Accuracy**:
- Silhouette: 70%+
- Neckline: 60%+
- Pattern: 75%+

---

**Step 3: Φ-Based Fusion** (1 week)

Combine CNN and Claude predictions using integrated information:

```python
# scripts/cnn/fusion.py

def fuse_attributes(cnn_attrs, claude_attrs):
    """
    Fuse vision (CNN) and text (Claude) attributes using Φ
    """
    fused = {}

    for attr in ['silhouette', 'neckline', 'pattern']:
        cnn_value, cnn_conf = cnn_attrs[attr]
        claude_value = claude_attrs[attr]

        # High agreement → high Φ
        if cnn_value == claude_value:
            fused[attr] = {
                'value': cnn_value,
                'phi': 0.9,
                'source': 'consensus'
            }
        # Disagree but high CNN confidence
        elif cnn_conf > 0.7:
            phi = calculate_semantic_similarity(cnn_value, claude_value)
            fused[attr] = {
                'value': cnn_value,
                'phi': phi,
                'source': 'vision_primary',
                'text_alternative': claude_value
            }
        # Low CNN confidence, use Claude
        else:
            fused[attr] = {
                'value': claude_value,
                'phi': 0.3,
                'source': 'text_primary'
            }

    return fused
```

---

**Step 4: Integrate with Search** (1 week)

Use fused attributes in enrichment pipeline:

```python
# Modify scripts/enrichment/claude.py

def enrich_product(product):
    # Get Claude attributes (existing)
    claude_attrs = call_claude_api(product)

    # Get CNN attributes (new)
    cnn_attrs = cnn_model.predict(product.image)

    # Fuse using Φ
    fused_attrs = fuse_attributes(cnn_attrs, claude_attrs)

    # Use fused attributes in rich text
    rich_text = build_rich_text_from_fused(fused_attrs)

    return fused_attrs, rich_text
```

---

### IIT 4.0 Synergy

**Approach 1 (Φ-Based Ranking)**:
```python
# Add attribute-level Φ to ranking
phi_embeddings = calculate_phi(text_emb, image_emb)
phi_attributes = calculate_attribute_phi(cnn_attrs, claude_attrs)

final_score = 0.4 * cosine + 0.3 * phi_embeddings + 0.3 * phi_attributes
```

**Approach 2 (Maximal Attribute Selection)**:
- IIT identifies silhouette has highest Φ contribution (0.38)
- Train CNN with higher weight on silhouette task
- Prune low-Φ attribute heads (save computation)

**Approach 3 (Complex Discovery)**:
- Use CNN attributes in complex definitions
- Example: "GothVictorian" = {era=Victorian, CNN_colors=[black, burgundy], CNN_neckline=high}

**Approach 4 (Adaptive Weighting)**:
- High CNN confidence → weight vision more
- Low CNN confidence (blurry image) → weight text more

---

### File Structure

```
scripts/
├── cnn/
│   ├── models.py              # CNN architectures
│   ├── train_multitask.py     # Training script
│   ├── inference.py           # CNN inference on products
│   ├── fusion.py              # Φ-based fusion
│   └── prepare_training_data.py
└── iit/
    └── attribute_phi.py       # Attribute-level Φ calculation
```

---

### When to Implement

**Sequence**:
1. ✅ Deploy MVP
2. ✅ Implement IIT Approach 1 (Φ-Based Ranking)
3. ⭐ **Start CNN integration here** (parallel to Approach 2)
4. Use CNN predictions in Approaches 2-4

**Why parallel**: CNN training (1-2 weeks) can happen while you're validating Approach 1.

---

### Quick Validation

**Test 1: Accuracy**
```bash
python scripts/cnn/evaluate.py --model models/fashion_cnn.pth --test-set data/cnn_training/test/

# Expected:
# Silhouette: 72%
# Neckline: 63%
# Pattern: 78%
```

**Test 2: Φ Improvement**
```python
# Before CNN (text-only)
phi_before = calculate_avg_phi(products, text_only=True)  # ~0.52

# After CNN fusion
phi_after = calculate_avg_phi(products, with_cnn=True)  # ~0.60

# Improvement: +0.08 ✓
```

**Test 3: Search Quality**
```bash
pytest tests/search_quality/test_search_quality.py --with-cnn

# Expect vibe queries: +5-8% improvement
```

---

### Common Issues

**Issue 1: Low CNN Accuracy**

Cause: Insufficient training data, domain mismatch

Fix:
- Use data augmentation (flip, rotate, color jitter)
- Try EfficientNet instead of ResNet (more efficient)
- Lower expectations: 60-70% is realistic for fine-grained fashion attributes

---

**Issue 2: CNN/Claude Disagreement**

Cause: Different information sources (vision vs. text)

Fix:
- This is expected! Use Φ to handle disagreement
- High Φ = trust consensus
- Low Φ = flag for human review or use high-confidence source

---

**Issue 3: CNN Slow Inference**

Cause: ResNet50 is heavyweight

Fix:
- Switch to MobileNet or EfficientNet-B0 (faster)
- Batch inference (process 32 images at once)
- Cache CNN predictions in database

---

### Resources

**Fashion-MNIST Tutorial**: https://www.kaggle.com/code/gpreda/cnn-with-tensorflow-keras-for-fashion-mnist
- Shows basic CNN architecture for fashion classification
- Adapt this pattern to your 12 silhouettes, 8 necklines, 6 patterns

**Fashionpedia Dataset**: https://fashionpedia.github.io/home/index.html
- 46 categories, 294 attributes (your taxonomy)
- Can use as additional training data if needed

**Multi-Task Learning**:
- Share backbone (ResNet/EfficientNet)
- Separate heads for each attribute
- Weight losses by Φ contribution (from IIT Approach 2)

---

## Code Examples

### Simplified Φ Calculation (Fast Prototype)

```python
import numpy as np
from sklearn.cross_decomposition import CCA

# Step 1: Train projection matrices (one-time)
def train_projections(text_embeddings, image_embeddings):
    """
    Use CCA to find common semantic space

    Args:
        text_embeddings: (N, 384) array
        image_embeddings: (N, 512) array

    Returns:
        text_proj: (384, 256) projection matrix
        image_proj: (512, 256) projection matrix
    """
    cca = CCA(n_components=256)
    cca.fit(text_embeddings, image_embeddings)

    return cca.x_weights_, cca.y_weights_

# Step 2: Calculate Φ
def calculate_simple_phi(text_emb, image_emb, text_proj, image_proj):
    """
    Fast Φ approximation using cosine similarity in projected space

    Returns:
        phi: float in [0, 1]
    """
    # Project to common space
    text_common = text_proj.T @ text_emb  # (256,)
    image_common = image_proj.T @ image_emb  # (256,)

    # Cosine similarity
    cosine = np.dot(text_common, image_common) / (
        np.linalg.norm(text_common) * np.linalg.norm(image_common) + 1e-8
    )

    # Normalize to [0, 1]
    phi = (cosine + 1) / 2

    return phi
```

---

### Rigorous Φ Calculation (KSG Mutual Information)

```python
from sklearn.feature_selection import mutual_info_regression
from scipy.stats import entropy

def calculate_rigorous_phi(text_emb, image_emb, context_embeddings):
    """
    True IIT Φ using mutual information estimation

    Args:
        text_emb: (384,) single text embedding
        image_emb: (512,) single image embedding
        context_embeddings: (N, 384+512) batch for k-NN estimation

    Returns:
        phi: float, normalized to [0, 1]
    """
    # Concatenate for joint distribution
    joint = np.concatenate([text_emb, image_emb])  # (896,)

    # Estimate mutual information using k-NN
    # Note: Requires batch context for k-NN density estimation
    X = context_embeddings[:, :384]  # Text embeddings from batch
    Y = context_embeddings[:, 384:]  # Image embeddings from batch

    # MI estimation (simplified - production needs proper KSG)
    mi_estimate = mutual_info_regression(
        X.reshape(-1, 384),
        Y.reshape(-1, 512),
        n_neighbors=5
    ).mean()

    # Estimate individual entropies
    h_text = entropy(text_emb + 1e-8)  # Add epsilon for numerical stability
    h_image = entropy(image_emb + 1e-8)

    # Φ = I(X;Y) - [H(X) + H(Y)]
    phi_raw = mi_estimate - (h_text + h_image)

    # Normalize to [0, 1] using dataset statistics
    # (phi_min, phi_max should be calibrated on your dataset)
    phi_normalized = np.clip((phi_raw - phi_min) / (phi_max - phi_min), 0, 1)

    return phi_normalized
```

**Note**: The rigorous version requires batch context for k-NN estimation. For production, pre-compute and cache Φ scores for all products.

---

### Φ-Weighted Search

```python
class VectorDB:
    def search_with_phi(
        self,
        query_text: str,
        limit: int = 10,
        phi_weight: float = 0.3
    ):
        """
        Search with Φ-weighted ranking

        Args:
            query_text: Search query
            limit: Number of results
            phi_weight: Weight for Φ vs. cosine (0.0 = pure cosine, 1.0 = pure Φ)

        Returns:
            List of results with Φ scores and explanations
        """
        # Encode query
        query_emb = models.encode_text(query_text)

        # Search text collection (get 2x results for reranking)
        initial_results = self.search_similar(
            collection='vintage_text',
            query_vector=query_emb,
            limit=limit * 2
        )

        # Enrich with Φ scores
        enriched_results = []
        for result in initial_results:
            product_id = result['id']

            # Retrieve both embeddings
            text_emb = self.get_text_embedding(product_id)
            image_emb = self.get_image_embedding(product_id)

            # Calculate Φ
            phi = self.phi_calculator.calculate_phi(text_emb, image_emb)

            # Calculate final score
            cosine_score = result['score']
            final_score = (1 - phi_weight) * cosine_score + phi_weight * phi

            enriched_results.append({
                **result,
                'phi': phi,
                'cosine_score': cosine_score,
                'score': final_score,
                'integration_level': self._get_integration_level(phi)
            })

        # Sort by final score
        enriched_results.sort(key=lambda x: x['score'], reverse=True)

        return enriched_results[:limit]

    @staticmethod
    def _get_integration_level(phi: float) -> str:
        if phi > 0.7:
            return 'high'
        elif phi > 0.4:
            return 'medium'
        else:
            return 'low'
```

---

### Field Attribution (Explainability)

```python
def calculate_field_attributions(product_id: int) -> dict:
    """
    Calculate how much each enrichment field contributes to Φ

    Returns:
        {
            'silhouette': 0.38,
            'era': 0.27,
            'vibe': 0.18,
            ...
        }
    """
    product = get_product(product_id)
    image_emb = get_image_embedding(product_id)

    attributions = {}

    # Get baseline Φ with all fields
    rich_text_full = build_rich_text(product, include_all=True)
    text_emb_full = models.encode_text(rich_text_full)
    phi_baseline = phi_calculator.calculate_phi(text_emb_full, image_emb)

    # Ablation study: remove each field and measure Φ drop
    for field in ENRICHMENT_FIELDS:
        rich_text_ablated = build_rich_text(product, exclude=[field])
        text_emb_ablated = models.encode_text(rich_text_ablated)
        phi_ablated = phi_calculator.calculate_phi(text_emb_ablated, image_emb)

        # Attribution = Φ drop when field is removed
        attributions[field] = phi_baseline - phi_ablated

    return attributions

def build_explanation(attributions: dict, top_k: int = 3) -> str:
    """Generate human-readable explanation"""
    top_attrs = sorted(attributions.items(), key=lambda x: x[1], reverse=True)[:top_k]

    explanation_parts = []
    for field, score in top_attrs:
        explanation_parts.append(f"{field} (Φ={score:.2f})")

    return f"Matched for {', '.join(explanation_parts)}"
```

---

### Complex Discovery Algorithm

```python
from itertools import combinations
from collections import defaultdict

def discover_aesthetic_complexes(
    products: list,
    min_phi: float = 0.65,
    min_support: int = 10,
    max_size: int = 5
) -> list:
    """
    Discover irreducible aesthetic complexes

    Args:
        products: List of all products
        min_phi: Minimum Φ threshold
        min_support: Minimum number of products
        max_size: Maximum attributes per complex

    Returns:
        List of discovered complexes
    """
    semantic_fields = ['era', 'decade', 'vibe', 'silhouette', 'colors', 'material']
    complexes = []

    # Test all combinations of 3-5 attributes
    for size in range(3, max_size + 1):
        for field_combo in combinations(semantic_fields, size):
            # Find products matching this attribute combination
            matching_products = []
            for product in products:
                if has_attributes(product, field_combo):
                    matching_products.append(product)

            # Check support
            if len(matching_products) < min_support:
                continue

            # Calculate average Φ for this combination
            phi_scores = []
            for product in matching_products:
                phi = calculate_phi_for_attribute_combo(product, field_combo)
                phi_scores.append(phi)

            avg_phi = np.mean(phi_scores)

            # Check if this is a high-Φ complex
            if avg_phi >= min_phi:
                # Extract attribute values from exemplar
                exemplar = matching_products[0]
                attribute_values = {
                    field: getattr(exemplar, field)
                    for field in field_combo
                }

                complex = {
                    'name': generate_complex_name(attribute_values),
                    'fields': list(field_combo),
                    'attributes': attribute_values,
                    'phi': avg_phi,
                    'support': len(matching_products),
                    'exemplar_ids': [p.id for p in matching_products[:10]]
                }
                complexes.append(complex)

    # Filter out subsets (if superset has similar Φ)
    complexes = filter_redundant_complexes(complexes, phi_threshold=0.05)

    # Sort by Φ
    complexes.sort(key=lambda c: c['phi'], reverse=True)

    return complexes

def generate_complex_name(attributes: dict) -> str:
    """Generate aesthetic name from attributes"""
    # Example: {era: Victorian, vibe: dark} → GothVictorian
    # This is simplified - production should use better naming
    name_parts = []
    if 'vibe' in attributes:
        name_parts.append(attributes['vibe'].title())
    if 'era' in attributes:
        name_parts.append(attributes['era'].title())

    return ''.join(name_parts) or 'UnnamedComplex'
```

---

## Validation Checklist

### Phase 0: Φ Infrastructure

- [ ] Projection matrices trained on dataset
- [ ] Φ calculator returns values in [0, 1]
- [ ] Φ distribution is roughly normal (mean ~0.5, std ~0.2)
- [ ] High-Φ products subjectively feel coherent
- [ ] Low-Φ products show image/text disagreement

**Quick Test**:
```python
# Calculate Φ for 100 random products
phis = [calculate_phi(p) for p in random.sample(products, 100)]

print(f"Mean: {np.mean(phis):.2f}")  # Expect: 0.4-0.6
print(f"Std: {np.std(phis):.2f}")    # Expect: 0.15-0.25
print(f"Min: {np.min(phis):.2f}")    # Expect: >0.05
print(f"Max: {np.max(phis):.2f}")    # Expect: <0.95

# Manual check
top_5_phi = sorted(products, key=lambda p: p.phi, reverse=True)[:5]
# Review: Do these feel coherent?
```

---

### Phase 1: Search Quality

- [ ] Φ-weighted ranking implemented
- [ ] A/B test shows improvement on vibe queries (+5-10%)
- [ ] No regression on era/culture queries
- [ ] Category precision improves or maintains

**A/B Test Template**:
```python
def run_ab_test(queries, control_fn, treatment_fn, n_trials=10):
    results = {'control': [], 'treatment': []}

    for query in queries:
        for _ in range(n_trials):
            if random.random() < 0.5:
                score = control_fn(query)['avg_score']
                results['control'].append(score)
            else:
                score = treatment_fn(query)['avg_score']
                results['treatment'].append(score)

    improvement = np.mean(results['treatment']) - np.mean(results['control'])
    p_value = stats.ttest_ind(results['treatment'], results['control']).pvalue

    return {
        'improvement': improvement,
        'p_value': p_value,
        'significant': p_value < 0.05
    }

# Run test
vibe_queries = [
    "dark academia aesthetic",
    "cottagecore pastoral dress",
    "old money elegance"
]

test_results = run_ab_test(
    vibe_queries,
    control_fn=lambda q: search(q, phi_weight=0),
    treatment_fn=lambda q: search(q, phi_weight=0.3)
)

print(f"Improvement: {test_results['improvement']:.1%}")
print(f"Significant: {test_results['significant']}")
```

---

### Phase 2: User Explainability

- [ ] Φ badge displayed in UI
- [ ] Tooltip explanation is clear
- [ ] User study: >70% understand Φ meaning
- [ ] Field attributions are intuitive

**User Study Script**:
```
Show user a search result with Φ badge:

"Victorian Lace Dress - Φ 82%"
Tooltip: "High integration - image and text strongly agree"

Questions:
1. What do you think the Φ score means?
2. Does it help you trust this result?
3. Would you like to see more/less information?
```

---

### Phase 3: Complex Discovery

- [ ] 20-30 complexes discovered
- [ ] Manual review: Complexes are coherent
- [ ] User study: >80% agree products "belong together"
- [ ] Complex search works

**Manual Review Checklist**:
For each discovered complex:
1. Review 10 exemplar products
2. Check: Do they share a coherent aesthetic?
3. Check: Is the name appropriate?
4. Check: Φ score is justified

---

## Resources & References

### IIT 4.0 Theory

**Core Papers**:
- Tononi et al. (2016): "Integrated Information Theory: From consciousness to its physical substrate"
- Oizumi et al. (2014): "From the phenomenology to the mechanisms of consciousness: IIT 4.0"

**Key Concepts**:
- Φ measures irreducibility of a system
- Maximal complex = highest Φ among overlapping systems
- Φ-structure corresponds to phenomenal structure

### Implementation References

**Mutual Information Estimation**:
- MINE (Belghazi et al., 2018): Neural estimation of MI
- KSG Estimator (Kraskov et al., 2004): k-NN based non-parametric MI
- `sklearn.feature_selection.mutual_info_regression`

**Canonical Correlation Analysis (CCA)**:
- `sklearn.cross_decomposition.CCA`
- Use for learning common projection space between modalities

### Your Codebase

**Key Files**:
```
Embeddings:
  scripts/embeddings/models.py              # CLIP + MiniLM models
  scripts/embeddings/generator.py           # Embedding generation

Vector DB:
  scripts/storage/vector_db.py              # Qdrant interface
  scripts/storage/database.py               # PostgreSQL schema

Enrichment:
  scripts/enrichment/claude.py              # Claude API integration
  scripts/enrichment/fashionpedia_taxonomy.py  # 46 categories, 294 attributes

Search Quality:
  tests/search_quality/test_search_quality.py  # Baseline scores

Frontend:
  vv-web/src/types/index.ts                 # SearchResult interface
  vv-web/src/lib/api.ts                     # API client
  vv-web/src/components/ui/Badge.tsx        # Badge component (reuse for Φ)
```

---

## Quick Decision Tree

**"Should I implement IIT 4.0 now?"**

```
Is your MVP deployed and working?
├─ No → Finish MVP first
└─ Yes → Do you have 1000+ products with embeddings?
    ├─ No → Get more data first
    └─ Yes → Do you have baseline search quality metrics?
        ├─ No → Establish baseline first
        └─ Yes → START WITH APPROACH 1 (Φ-Based Ranking)
```

**"Which approach should I start with?"**

```
Start: Approach 1 (Φ-Based Ranking)
  ↓
  Validates that Φ correlates with quality?
  ├─ No → Re-examine Φ calculation, try rigorous MI
  └─ Yes → Proceed to Approach 2 (Attribute Selection)
      ↓
      Improves search quality?
      ├─ No → Iterate on field selection logic
      └─ Yes → Proceed to Approach 3 (Complex Discovery)
          ↓
          Discovers coherent aesthetics?
          ├─ No → Adjust min_phi threshold
          └─ Yes → Proceed to Approach 4 (Adaptive Weighting)
```

**"How do I know if it's working?"**

1. **Φ Distribution Check**: Mean ~0.5, not all 0 or all 1
2. **Search Quality**: +5-10% on vibe queries
3. **User Feedback**: Users understand explanations
4. **Coherence Check**: High-Φ results feel unified

---

## Common Pitfalls

### 1. Φ Calculation Returns All Zeros

**Cause**: Embeddings are orthogonal in projected space

**Fix**:
- Check projection matrices are learned from your dataset
- Ensure text and image embeddings are from same products during training
- Try larger projection dimension (384 instead of 256)

---

### 2. Φ-Weighted Ranking Hurts Quality

**Cause**: Φ doesn't correlate with relevance on your dataset

**Fix**:
- Lower phi_weight (try 0.1-0.2 instead of 0.3)
- Check if Φ is measuring the right thing (compare high-Φ vs low-Φ manually)
- Consider rigorous MI instead of simple Φ

---

### 3. Discovered Complexes Are Nonsensical

**Cause**: min_phi threshold too low, or spurious correlations

**Fix**:
- Raise min_phi to 0.70-0.75
- Increase min_support to 15-20 products
- Filter by human review: keep only coherent complexes

---

### 4. Users Don't Understand Φ Score

**Cause**: "Integrated information" is abstract

**Fix**:
- Use simpler language: "Match Confidence" instead of "Φ"
- Color-code: Green (high), Yellow (medium), Red (low)
- Focus on explanation, not the number: "Image and text agree on Victorian lace"

---

## Next Steps When Ready

1. **Read the full plan**: `docs/IIT_4.0_INTEGRATION_PLAN.md`
2. **Start Phase 0**: Train projection matrices
3. **Implement simple Φ**: 1-2 week prototype
4. **Validate**: Check Φ distribution and manual quality
5. **A/B test**: Φ-weighted ranking vs. baseline
6. **Iterate**: Based on results, proceed to Approach 2

**First Command to Run**:
```bash
# Train CCA projections on your current dataset
python scripts/iit/train_projections.py \
  --products 1000 \
  --output models/phi_projections.pkl
```

---

## Questions?

**Theoretical Questions**: See full plan section "IIT 4.0 Theoretical Framework"

**Implementation Questions**: See code examples above or full plan section "Technical Specifications"

**Validation Questions**: See "Validation & Metrics" in full plan

**Not sure where to start?**: Begin with Approach 1, Phase 0 (Simple Φ Prototype)

---

**Document Version**: 1.0 (Post-MVP Reference)
**Last Updated**: 2026-02-19
**See Also**: `docs/IIT_4.0_INTEGRATION_PLAN.md` (comprehensive 100+ page plan)
