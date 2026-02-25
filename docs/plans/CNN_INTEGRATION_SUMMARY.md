# CNN Integration Summary
**Added to IIT 4.0 Plans on 2026-02-19**

## What Was Added

CNN-based visual attribute extraction has been integrated into both IIT 4.0 planning documents to address the current gap where all enrichment attributes come from Claude text analysis rather than direct computer vision.

---

## Updated Documents

### 1. IIT_4.0_INTEGRATION_PLAN.md (Comprehensive Plan)

**Location**: New section added before "Implementation Roadmap" (~line 1375)

**Content**: ~40 pages covering:

#### Overview
- **Motivation**: Why CNNs are needed (text-only enrichment gap)
- **IIT 4.0 Synergy**: How CNNs enhance all 4 IIT approaches
- **Architecture**: Vision path (CNN) + Text path (Claude) → Φ-based fusion

#### Phase 1: Multi-Task Attribute CNN
- Architecture: ResNet50 backbone with 5 task-specific heads
  - Silhouette (12 classes)
  - Neckline (8 classes)
  - Pattern (6 classes)
  - Length (5 classes)
  - Colors (RGB palette extraction)
- Training: Use Claude enrichment as ground truth
- Loss: Multi-task with Φ-guided weighting (weight tasks by Φ contribution)
- Code: Full PyTorch implementation provided

#### Phase 2: CLIP Fine-Tuning
- Method: Contrastive learning on (image, rich_text) pairs
- Goal: Improve CLIP embeddings for vintage fashion domain
- Expected: +0.08 increase in average Φ
- Code: Training loop with InfoNCE loss

#### Phase 3: Era Classification
- Dedicated CNN for historical era prediction
- Architecture: EfficientNet-B3 → 8 eras (1700s-1980s+)
- Training data: Met Museum (high-confidence ground truth)
- Integration: Compare CNN era vs. Claude era via Φ

#### Phase 4: Φ-Based Fusion
- Combine CNN and Claude predictions using integrated information
- High agreement → Φ=0.9 (consensus)
- Disagree + high CNN confidence → Φ=0.5-0.8 (vision primary)
- Low CNN confidence → Φ=0.3 (text primary)
- Code: Complete fusion algorithm with semantic similarity

#### Integration Points
- **Approach 1**: Add attribute Φ to ranking formula
- **Approach 2**: Train CNN only for high-Φ attributes
- **Approach 3**: Use CNN attributes in complex discovery
- **Approach 4**: Adaptive weighting based on CNN confidence

#### Implementation Details
- New Python modules: `scripts/cnn/` (models, training, inference, fusion)
- Database schema: `cnn_predictions`, `fused_attributes` tables
- Timeline: +2-4 weeks to IIT plan (12-14 weeks total)
- Validation: Accuracy targets, Φ improvement metrics, search quality A/B tests

---

### 2. IIT_REFERENCE.md (Quick-Start Guide)

**Location**: New section added before "Code Examples" (~line 379)

**Content**: ~8 pages of actionable quick-start guidance

#### Why Add CNNs?
- Problem: Attributes come from text, not vision
- Solution: Train CNNs for direct visual attribute prediction
- Benefit: Vision-text fusion using Φ

#### Quick Implementation Path

**Step 1: Prepare Training Data** (1 week)
```bash
python scripts/cnn/prepare_training_data.py \
  --products 1000 \
  --output data/cnn_training/ \
  --split 0.7/0.15/0.15
```

**Step 2: Train Multi-Task CNN** (1-2 weeks)
- Adapt Fashion-MNIST pattern to Fashionpedia taxonomy
- Expected accuracy: Silhouette 70%+, Neckline 60%+, Pattern 75%+
- Code snippet: FashionAttributeCNN class

**Step 3: Φ-Based Fusion** (1 week)
- Combine CNN + Claude using integrated information
- Code snippet: `fuse_attributes()` function

**Step 4: Integrate with Search** (1 week)
- Modify enrichment pipeline to use fused attributes
- Code snippet: Updated `enrich_product()` function

#### IIT 4.0 Synergy Examples
- Concrete code showing how CNNs enhance each of 4 approaches
- Formula: `final_score = 0.4 * cosine + 0.3 * phi_embeddings + 0.3 * phi_attributes`

#### When to Implement
- Sequence: MVP → IIT Approach 1 → **Start CNN here** (parallel to Approach 2)
- Why parallel: CNN training (1-2 weeks) happens while validating Approach 1

#### Quick Validation
- Test 1: Accuracy evaluation script
- Test 2: Φ improvement (expect +0.08)
- Test 3: Search quality (+5-8% on vibe queries)

#### Common Issues & Fixes
- Low CNN accuracy → data augmentation, try EfficientNet
- CNN/Claude disagreement → expected, use Φ to handle
- Slow inference → switch to MobileNet, batch processing

#### Resources
- Fashion-MNIST tutorial link
- Fashionpedia dataset link
- Multi-task learning guidance

---

## Key Concepts

### Multi-Modal Φ (Integrated Information)

**Before CNNs**:
```
Φ = integration between text_embedding and image_embedding
```

**After CNNs**:
```
Φ_embeddings = integration(text_emb, image_emb)
Φ_attributes = integration(cnn_attrs, claude_attrs)
final_Φ = weighted_average(Φ_embeddings, Φ_attributes)
```

### Vision-Text Attribute Fusion

| Agreement | CNN Confidence | Φ Score | Decision |
|-----------|----------------|---------|----------|
| Match | Any | 0.9 | Consensus |
| Differ | High (>0.7) | 0.5-0.8 | Vision primary, flag text alternative |
| Differ | Low (<0.7) | 0.3 | Text primary |

### Φ-Guided CNN Training

**Traditional**: Train all tasks with equal weight

**Φ-Guided**: Weight tasks by Φ contribution
```python
# IIT Approach 2 identifies:
# silhouette Φ_contrib = 0.38 (high)
# neckline Φ_contrib = 0.15 (medium)
# pattern Φ_contrib = 0.08 (low)

# Set CNN loss weights proportionally
weights = {
    'silhouette': 0.38 / sum_phi,  # Higher weight
    'neckline': 0.15 / sum_phi,
    'pattern': 0.08 / sum_phi      # Lower weight
}
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ PRODUCT IMAGE                                                   │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────┐    ┌──────────────┐
│ CLIP    │    │ Multi-Task   │
│ (512d)  │    │ CNN          │
└────┬────┘    └──────┬───────┘
     │                │
     │                ├─→ Silhouette (12 classes)
     │                ├─→ Neckline (8 classes)
     │                ├─→ Pattern (6 classes)
     │                ├─→ Length (5 classes)
     │                └─→ Colors (RGB)
     │                │
     │         ┌──────┴──────────┐
     │         │ Vision Attrs    │
     │         │ + Confidence    │
     │         └──────┬──────────┘
     │                │
┌────┴────────────────┴────┐
│ Φ-BASED INTEGRATION      │
│                           │
│ • Φ(image_emb, text_emb) │
│ • Φ(cnn_attrs, claude_attrs) │
│                           │
│ → Final enrichment        │
└───────────────────────────┘
```

---

## Expected Outcomes

### Quantitative Improvements

| Metric | Before CNN | After CNN | Improvement |
|--------|------------|-----------|-------------|
| Attribute accuracy | 65% (Claude only) | 75-80% (Fused) | +10-15% |
| Average Φ | 0.52 | 0.60 | +0.08 |
| Vibe query scores | Baseline | Baseline + 5-10% | +5-10% |
| Search precision | 68% | 73% | +5% |

### Qualitative Improvements

1. **Visual Verification**: Attributes confirmed by both vision and text (high Φ)
2. **Robustness**: Works with poor text descriptions (Etsy/Depop listings)
3. **Explainability**: "Matched because image shows empire waistline (CNN: 92%) and text confirms romantic vibe (Claude)"
4. **Confidence Scores**: Per-attribute Φ scores show where vision and text agree/disagree

---

## Implementation Timeline

**Integrated with IIT 4.0 Plan**:

| Week | IIT Phase | CNN Phase |
|------|-----------|-----------|
| 1-3 | Approach 1: Φ-Based Ranking | Prepare data, train multi-task CNN |
| 4-5 | Validate Φ, A/B test | Integrate CNN, measure Φ improvement |
| 5-7 | Approach 2: Maximal Attr Selection | Φ-guided task weighting, prune heads |
| 7-10 | Approach 3: Complex Discovery | Use CNN attrs in complexes |
| 10-12 | Approach 4: Adaptive Weighting | Fine-tune CLIP (optional) |

**Total**: 12-14 weeks (CNN adds 2-4 weeks)

---

## Files to Create

### New Python Modules

```
scripts/
├── cnn/
│   ├── __init__.py
│   ├── models.py                 # FashionAttributeCNN, EraClassifier
│   ├── train_multitask.py        # Training script
│   ├── train_era.py              # Era classifier training
│   ├── fine_tune_clip.py         # CLIP fine-tuning
│   ├── inference.py              # CNN inference
│   ├── fusion.py                 # Φ-based fusion
│   └── prepare_training_data.py  # Data preparation
├── iit/
│   ├── phi_calculator.py         # Existing
│   └── attribute_phi.py          # NEW: Attribute-level Φ
└── embeddings/
    └── models.py                 # UPDATE: Add fine-tuned CLIP option
```

### Database Schema

```sql
-- CNN predictions
CREATE TABLE cnn_predictions (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    silhouette_pred VARCHAR(50),
    silhouette_conf FLOAT,
    neckline_pred VARCHAR(50),
    neckline_conf FLOAT,
    pattern_pred VARCHAR(50),
    pattern_conf FLOAT,
    length_pred VARCHAR(50),
    length_conf FLOAT,
    era_pred VARCHAR(20),
    era_conf FLOAT,
    colors_pred JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fused attributes (vision + text)
CREATE TABLE fused_attributes (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    silhouette VARCHAR(50),
    silhouette_phi FLOAT,
    silhouette_source VARCHAR(20),  -- 'consensus' | 'vision_primary' | 'text_primary'
    neckline VARCHAR(50),
    neckline_phi FLOAT,
    neckline_source VARCHAR(20),
    pattern VARCHAR(50),
    pattern_phi FLOAT,
    pattern_source VARCHAR(20),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Next Steps

1. **Read Full Plans**:
   - `docs/IIT_4.0_INTEGRATION_PLAN.md` - Section: "CNN Integration for Visual Attribute Extraction"
   - `docs/IIT_REFERENCE.md` - Section: "CNN Integration"

2. **After MVP Deployment**:
   - Start with IIT Approach 1 (Φ-Based Ranking)
   - **Parallel**: Begin CNN training (use existing Claude labels)
   - Integrate CNN predictions after 1-2 weeks

3. **First Command**:
   ```bash
   python scripts/cnn/prepare_training_data.py \
     --products 1000 \
     --output data/cnn_training/
   ```

4. **Validation**:
   - Check CNN accuracy >70% on silhouette
   - Measure Φ improvement >+0.05
   - Run search quality tests (expect +5-10% on vibes)

---

## References

**Fashion-MNIST Tutorial**: https://www.kaggle.com/code/gpreda/cnn-with-tensorflow-keras-for-fashion-mnist
- Basic CNN pattern for fashion classification
- Adapt to Fashionpedia taxonomy (12 silhouettes, 8 necklines, etc.)

**Full IIT 4.0 Plan**: `docs/IIT_4.0_INTEGRATION_PLAN.md`
- Comprehensive 100+ page plan with theory, code, validation

**Quick Reference**: `docs/IIT_REFERENCE.md`
- Actionable quick-start guide for post-MVP

**This Summary**: Overview of CNN additions to both documents

---

**Document Version**: 1.0
**Date**: 2026-02-19
**Status**: Design complete, ready for post-MVP implementation
