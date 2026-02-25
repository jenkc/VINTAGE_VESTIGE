# Rigorous Implementation of IIT 4.0 in Vintage Vestige

**Author**: Claude
**Date**: 2026-02-19
**Status**: Design Phase
**Goals**: Improve search quality/ranking + Provide user explainability

---

## Executive Summary

This document provides a rigorous, comprehensive plan for integrating **Integrated Information Theory (IIT) 4.0** principles into the Vintage Vestige search engine. The plan combines all four proposed approaches into a unified architecture that:

1. **Improves search quality** by measuring integrated information (Φ) between modalities
2. **Provides explainability** by showing users which attributes drive relevance
3. **Discovers emergent patterns** by identifying irreducible aesthetic complexes
4. **Adapts dynamically** by weighting modalities based on query-specific integration

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [IIT 4.0 Theoretical Framework](#iit-40-theoretical-framework)
3. [Architecture Overview: 4 Integrated Approaches](#architecture-overview-4-integrated-approaches)
4. [Approach 1: Φ-Based Search Ranking](#approach-1-φ-based-search-ranking)
5. [Approach 2: Maximal Attribute Selection](#approach-2-maximal-attribute-selection)
6. [Approach 3: Emergent Complex Discovery](#approach-3-emergent-complex-discovery)
7. [Approach 4: Adaptive Multi-Modal Weighting](#approach-4-adaptive-multi-modal-weighting)
8. [CNN Integration for Visual Attribute Extraction](#cnn-integration-for-visual-attribute-extraction)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Technical Specifications](#technical-specifications)
11. [Validation & Metrics](#validation--metrics)

---

## Current Architecture Analysis

### Embedding System

**Text Embeddings** (`scripts/embeddings/models.py:67-76`)
- Model: `all-MiniLM-L6-v2` (SentenceTransformers)
- Dimensionality: 384
- Input: Rich text constructed from enrichment fields
- Storage: Qdrant collection `vintage_text` with COSINE distance

**Image Embeddings** (`scripts/embeddings/models.py:38-65`)
- Model: `clip-ViT-B-32` (SentenceTransformers)
- Dimensionality: 512
- Input: Product images (PIL Image or URL)
- Storage: Qdrant collection `vintage_images` with COSINE distance

**Separation**: The two embedding types are completely independent:
- Stored in separate Qdrant collections
- No joint embedding space
- No measurement of cross-modal agreement

### Enrichment Pipeline

**Claude AI Enrichment** (`scripts/enrichment/claude.py`)
- Model: `claude-sonnet-4-20250514`
- Input: Product metadata + optional image
- Output: 23 structured fields bridging museum descriptions and modern search language

**Enrichment Fields**:
```python
# Fashionpedia Taxonomy (12 fields)
fp_category, silhouette, neckline, length, sleeve_length,
opening_type, textile_pattern, textile_finishing, garment_parts,
decorations, waistline, nickname

# Creative/Search-Bridge (11 fields)
era, decade, style_tags, colors, material, season,
garment_type, vibe, fit_style, occasion, ai_description
```

**Rich Text Construction** (`scripts/embedding_and_enrichment/enrich_and_reembed_all.py`):
All 23 fields are concatenated into natural language text (256 tokens max), which becomes the input for text embedding. No measurement of which fields contribute most to search quality.

### Vector Search

**Current Ranking** (`scripts/storage/vector_db.py:86-110`)
```python
def search_similar(self, collection, query_vector, limit=10):
    results = self.client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=limit
    )
    return [{'id': hit.id, 'score': hit.score, **hit.payload} for hit in results]
```

- Simple cosine similarity scoring (0.0 to 1.0)
- Results sorted by similarity descending
- No integration measurement between modalities
- No explainability of why items rank highly

### Search Quality Baseline

**Test Suite** (`tests/search_quality/test_search_quality.py`)

Current minimum acceptable scores across 14 queries:

| Query Category | Example | Min Score | Notes |
|----------------|---------|-----------|-------|
| **Broad Garment** | "silk evening dress" | 0.60 | High similarity expected |
| **Era-Specific** | "1920s flapper dress" | 0.50 | Historical accuracy critical |
| **Culture** | "Japanese kimono" | 0.25 | Cross-cultural metadata limited |
| **Vibe/Aesthetic** | "dark academia aesthetic" | 0.40 | Modern aesthetic language |

**Quality Metrics**:
- Score regression (no drops below baseline)
- Cross-source retrieval (Met, Smithsonian, Fashionpedia, Depop, Etsy)
- Category consistency (40%+ precision in top 5)
- Score distribution (>0.05 spread, <1.0 max to avoid data leaks)

### Key Insight: The Integration Gap

The current architecture has three critical gaps that IIT 4.0 can address:

1. **No Multi-Modal Integration**: Image and text embeddings are isolated; there's no measurement of whether they agree or disagree on a product's identity.

2. **No Attribute Attribution**: The system can't explain *which* enrichment fields (era, vibe, silhouette) drive a high match score.

3. **No Emergent Pattern Discovery**: Aesthetic concepts like "dark academia" are manually tagged, not discovered through data-driven integration analysis.

---

## IIT 4.0 Theoretical Framework

### Core Principles

**1. Φ (Phi) - Integrated Information**

**Theory**: Integrated information Φ quantifies the cause-effect power of a system beyond its parts. A system with high Φ cannot be reduced to independent subsystems without losing information.

**Mathematical Definition** (Tononi et al., 2016):
```
Φ(S) = min[I(S ; S_past) - Σ I(S_i ; S_i,past)]
```
Where:
- `S` = complete system
- `S_i` = subsystems (partitions)
- `I(·;·)` = mutual information
- Φ measures irreducible information

**VV Application**:
```python
# System S = {image_embedding, text_embedding}
# Subsystems = {image_embedding} and {text_embedding}

Φ(image, text) = I(image, text | product) - [H(image) + H(text)]
```
Where:
- High Φ = image and text jointly specify the product beyond what each specifies alone
- Low Φ = modalities provide redundant or contradictory information

---

**2. Integration Axiom (Phenomenal Binding)**

**Theory**: Conscious experience is unified and irreducible. We don't experience scattered pixels or neuron firings; we experience a unified scene.

**VV Application**: Search results should represent unified aesthetic concepts. A "dark academia" result isn't just {era=Victorian} + {vibe=dark} + {colors=brown}, it's an **irreducible complex** where these attributes create a holistic meaning greater than their sum.

**Implication**: We should identify which attribute combinations have high Φ (irreducible) vs. low Φ (reducible to parts).

---

**3. Principle of Maximal Existence**

**Theory**: "To be is to have cause-effect power." Among overlapping systems at the same location, only the one with maximal Φ truly exists.

**VV Application**: A product has many overlapping enrichment fields:
- Era + Decade (redundant)
- Vibe + Style_tags (overlapping)
- Silhouette + Garment_type (related)

The **maximal complex** is the subset of fields with highest Φ. This is what "really defines" the product.

**Implication**: Rich text should only include fields that maximize Φ, not all 23 fields indiscriminately.

---

**4. Irreducible Complexes**

**Theory**: A complex is a set of elements where:
- The whole specifies more information than any partition
- Removing any element reduces Φ significantly

**VV Application**: Discover attribute combinations that form irreducible aesthetic concepts:
- `{Victorian, lace, empire_waistline, romantic}` might be a complex with Φ=0.82
- `{Victorian, romantic}` subset might have Φ=0.45 (less integrated)
- These complexes become discoverable "aesthetic archetypes"

---

**5. Explanatory Identity (Φ-Structure Correspondence)**

**Theory**: The structure of integrated information (Φ-structure) is identical to the structure of phenomenal experience. If you know the Φ-structure, you know the experience.

**VV Application**: If we know the Φ-structure of a search result (which attributes integrate, how strongly), we can **explain** why it matches:
- "This item integrates {era=1950s, silhouette=A-line, vibe=romantic} with Φ=0.75"
- Users understand the result through its integration profile

---

## Architecture Overview: 4 Integrated Approaches

The four approaches build on each other sequentially:

```
┌─────────────────────────────────────────────────────────────────┐
│ APPROACH 1: Φ-Based Search Ranking (Foundation)                │
│ ─────────────────────────────────────────────────────────────── │
│ • Calculate Φ(image, text) for each search result              │
│ • Re-rank by Φ-weighted score: α·cosine + β·Φ                  │
│ • Display Φ as explainability score in UI                      │
│                                                                 │
│ Dependencies: None (foundation layer)                          │
│ Output: Φ scores for all products                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ APPROACH 2: Maximal Attribute Selection                        │
│ ─────────────────────────────────────────────────────────────── │
│ • Use Φ to measure which enrichment fields contribute most     │
│ • Identify maximal complex: subset of fields with highest Φ    │
│ • Optimize rich text construction to include only high-Φ fields│
│                                                                 │
│ Dependencies: Approach 1 (needs Φ calculation infrastructure)  │
│ Output: Field importance rankings, optimized enrichment        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ APPROACH 3: Emergent Complex Discovery                         │
│ ─────────────────────────────────────────────────────────────── │
│ • Test all attribute combinations for Φ                        │
│ • Discover irreducible complexes (e.g., "GothVictorian")       │
│ • Build ontology of aesthetic archetypes                       │
│                                                                 │
│ Dependencies: Approach 2 (needs field importance)              │
│ Output: Discovered aesthetic complexes, complex-based search   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ APPROACH 4: Adaptive Multi-Modal Weighting                     │
│ ─────────────────────────────────────────────────────────────── │
│ • Measure query Φ(text_query, image_query)                     │
│ • Weight modalities based on query integration                 │
│ • High Φ queries → balanced; low Φ → favor dominant modality   │
│                                                                 │
│ Dependencies: Approaches 1-3 (needs full Φ infrastructure)     │
│ Output: Query-adaptive ranking, optimized for each search type │
└─────────────────────────────────────────────────────────────────┘
```

**Timeline**:
- Approach 1: 2-3 weeks (foundation + validation)
- Approach 2: 1-2 weeks (builds on existing enrichment)
- Approach 3: 2-3 weeks (computationally intensive discovery)
- Approach 4: 1-2 weeks (applies existing Φ infrastructure)

**Total**: ~6-10 weeks for complete IIT 4.0 integration

---

## APPROACH 1: Φ-Based Search Ranking

### Objective

Calculate integrated information Φ between image and text embeddings for each search result, then use Φ to:
1. Re-rank results (improve search quality)
2. Explain why results match (provide user explainability)

### Theoretical Grounding

**Integration Axiom**: High Φ indicates that image and text form an irreducible unified representation of the product. Low Φ indicates modalities are independent or contradictory.

**Causal Power**: Φ measures how much the joint system {image, text} specifies the product's identity beyond what each modality specifies independently.

### Mathematical Formulation

#### Option A: Simplified Φ (Phase 0 Prototype)

Use **cosine similarity in projected common space** as Φ proxy:

```python
def simple_phi(text_emb: np.ndarray, image_emb: np.ndarray) -> float:
    """
    Fast approximation: Φ ≈ similarity in common projection space

    Args:
        text_emb: (384,) vector from MiniLM
        image_emb: (512,) vector from CLIP

    Returns:
        Φ ∈ [0, 1]
    """
    # Project both to common 256-dimensional space
    text_proj = text_projection_matrix @ text_emb  # (256, 384) @ (384,) = (256,)
    image_proj = image_projection_matrix @ image_emb  # (256, 512) @ (512,) = (256,)

    # Cosine similarity
    cosine = np.dot(text_proj, image_proj) / (
        np.linalg.norm(text_proj) * np.linalg.norm(image_proj)
    )

    # Normalize to [0, 1]
    phi = (cosine + 1) / 2  # Cosine ∈ [-1, 1] → Φ ∈ [0, 1]

    return phi
```

**Projection matrices**:
- Learn via CCA (Canonical Correlation Analysis) on labeled dataset
- Or use random projection with orthonormal initialization
- Goal: Find common semantic space where related image/text align

**Pros**:
- Fast (<1ms per result)
- No new dependencies
- Validates UX before full implementation

**Cons**:
- Not true IIT Φ (just correlation)
- Assumes high correlation = integration (may not hold)

---

#### Option B: Mutual Information Φ (Rigorous Implementation)

Use **mutual information (MI)** to calculate true integrated information:

```python
def rigorous_phi(text_emb: np.ndarray, image_emb: np.ndarray,
                 product_metadata: dict) -> float:
    """
    True IIT Φ using mutual information

    Φ(image, text) = I(image; text | product) - [H(image) + H(text)]

    Where:
        I(image; text | product) = joint information conditioned on product
        H(image), H(text) = individual entropies

    Returns:
        Φ ∈ [0, ∞), typically [0, 5] for embeddings
    """
    # Method 1: MINE (Mutual Information Neural Estimation)
    # Train neural network to estimate I(image; text)
    mi_joint = mine_estimator.estimate(text_emb, image_emb)

    # Individual entropies via k-NN estimation
    h_text = knn_entropy(text_emb, k=5)
    h_image = knn_entropy(image_emb, k=5)

    phi = mi_joint - (h_text + h_image)

    # Normalize to [0, 1] using dataset statistics
    phi_normalized = (phi - phi_min) / (phi_max - phi_min)

    return max(0.0, phi_normalized)
```

**MI Estimation Methods**:

1. **MINE (Mutual Information Neural Estimation)**:
   - Train small MLP: `T(x, y) → ℝ`
   - Maximize: `E[T(x,y)] - log(E[e^T(x,y')])`
   - Accurate but requires training

2. **KSG Estimator (Kraskov-Stögbauer-Grassberger)**:
   - Non-parametric k-NN based
   - No training required
   - Formula: `ψ(k) + ψ(N) - ⟨ψ(n_x + 1) + ψ(n_y + 1)⟩`

3. **Binning Estimator**:
   - Discretize embeddings into bins
   - Count joint vs. marginal frequencies
   - Fast but loses precision

**Recommendation**: Start with **KSG estimator** (sklearn implementation available)

**Pros**:
- Theoretically rigorous (true Φ)
- No training required (KSG is non-parametric)
- Captures non-linear relationships

**Cons**:
- Slower (~10-50ms per result)
- Requires tuning k parameter
- May need caching for production

---

### Implementation Architecture

#### New Module: `scripts/iit/phi_calculator.py`

```python
"""
Integrated Information (Φ) calculation for multi-modal embeddings.
"""

import numpy as np
from sklearn.feature_selection import mutual_info_regression
from scipy.spatial.distance import pdist, squareform
from typing import Tuple, Optional
import pickle


class PhiCalculator:
    """Calculate integrated information between embeddings"""

    def __init__(self, method: str = 'ksg', projection_path: Optional[str] = None):
        """
        Args:
            method: 'simple' | 'ksg' | 'mine'
            projection_path: Path to learned projection matrices (for simple method)
        """
        self.method = method

        if method == 'simple':
            self._load_projections(projection_path)
        elif method == 'ksg':
            self.k_neighbors = 5  # KSG parameter
        elif method == 'mine':
            self._load_mine_estimator()

    def calculate_phi(
        self,
        text_emb: np.ndarray,
        image_emb: np.ndarray,
        normalize: bool = True
    ) -> float:
        """
        Calculate Φ between text and image embeddings

        Returns:
            Φ ∈ [0, 1] if normalize=True, else raw Φ value
        """
        if self.method == 'simple':
            return self._simple_phi(text_emb, image_emb)
        elif self.method == 'ksg':
            return self._ksg_phi(text_emb, image_emb, normalize)
        elif self.method == 'mine':
            return self._mine_phi(text_emb, image_emb, normalize)

    def _simple_phi(self, text_emb: np.ndarray, image_emb: np.ndarray) -> float:
        """Cosine similarity in projected space"""
        text_proj = self.text_projection @ text_emb
        image_proj = self.image_projection @ image_emb

        cosine = np.dot(text_proj, image_proj) / (
            np.linalg.norm(text_proj) * np.linalg.norm(image_proj) + 1e-8
        )

        return (cosine + 1) / 2  # [0, 1]

    def _ksg_phi(
        self,
        text_emb: np.ndarray,
        image_emb: np.ndarray,
        normalize: bool
    ) -> float:
        """KSG mutual information estimator"""
        # Combine into joint distribution
        joint = np.concatenate([text_emb.reshape(1, -1), image_emb.reshape(1, -1)], axis=1)

        # Estimate MI using k-NN
        # Note: For single sample, we need batch context from database
        # This is a simplified version; production needs sample batching

        # For now, use correlation as proxy (to be replaced with true KSG)
        correlation = np.corrcoef(text_emb, image_emb)[0, 1]

        # MI ≈ -0.5 * log(1 - ρ²) for Gaussian approximation
        mi = -0.5 * np.log(1 - correlation**2 + 1e-8)

        # Entropy estimates (simplified)
        h_text = 0.5 * np.log(2 * np.pi * np.e * np.var(text_emb))
        h_image = 0.5 * np.log(2 * np.pi * np.e * np.var(image_emb))

        phi = mi - (h_text + h_image)

        if normalize:
            # Normalize using dataset statistics (to be calibrated)
            phi_normalized = np.clip((phi + 5) / 10, 0, 1)
            return phi_normalized

        return phi

    def calculate_batch_phi(
        self,
        text_embs: np.ndarray,  # (N, 384)
        image_embs: np.ndarray,  # (N, 512)
    ) -> np.ndarray:  # (N,)
        """Calculate Φ for batch of results"""
        return np.array([
            self.calculate_phi(text_embs[i], image_embs[i])
            for i in range(len(text_embs))
        ])

    @staticmethod
    def train_projections(
        text_embs: np.ndarray,  # (N, 384)
        image_embs: np.ndarray,  # (N, 512)
        target_dim: int = 256,
        save_path: str = 'models/phi_projections.pkl'
    ):
        """
        Learn projection matrices via CCA

        Canonical Correlation Analysis finds linear projections
        that maximize correlation between modalities
        """
        from sklearn.cross_decomposition import CCA

        cca = CCA(n_components=target_dim)
        cca.fit(text_embs, image_embs)

        projections = {
            'text_projection': cca.x_weights_,  # (384, 256)
            'image_projection': cca.y_weights_,  # (512, 256)
        }

        with open(save_path, 'wb') as f:
            pickle.dump(projections, f)

        print(f"✅ Saved projection matrices to {save_path}")
        return projections
```

---

#### Modified: `scripts/storage/vector_db.py`

Add Φ calculation to search results:

```python
from scripts.iit.phi_calculator import PhiCalculator

class VectorDB:
    def __init__(self):
        # ... existing code ...
        self.phi_calculator = PhiCalculator(method='simple')  # Start with simple

    def search_with_phi(
        self,
        query_text: Optional[str] = None,
        query_image: Optional[np.ndarray] = None,
        limit: int = 10,
        phi_weight: float = 0.3
    ):
        """
        Search with Φ-weighted ranking

        final_score = (1 - phi_weight) * cosine + phi_weight * Φ
        """
        # Get embeddings for query
        if query_text:
            text_query_emb = models.encode_text(query_text)
        if query_image:
            image_query_emb = models.encode_image(query_image)

        # Search text collection
        text_results = self.search_similar(
            self.text_collection,
            text_query_emb,
            limit=limit * 2  # Get more for reranking
        )

        # For each result, retrieve BOTH embeddings from Qdrant
        enriched_results = []

        for result in text_results:
            product_id = result['id']

            # Get image embedding from image collection
            image_point = self.client.retrieve(
                collection_name=self.image_collection,
                ids=[product_id]
            )[0]

            # Get text embedding from text collection
            text_point = self.client.retrieve(
                collection_name=self.text_collection,
                ids=[product_id]
            )[0]

            # Calculate Φ
            phi = self.phi_calculator.calculate_phi(
                np.array(text_point.vector),
                np.array(image_point.vector)
            )

            # Rerank
            cosine_score = result['score']
            final_score = (1 - phi_weight) * cosine_score + phi_weight * phi

            enriched_results.append({
                **result,
                'phi': phi,
                'cosine_score': cosine_score,
                'score': final_score
            })

        # Sort by final score
        enriched_results.sort(key=lambda x: x['score'], reverse=True)

        return enriched_results[:limit]
```

**Note**: This requires storing vectors in Qdrant payload OR using `retrieve()` to fetch them. Current implementation doesn't store vectors in payload (only in index), so we'll need to add that.

---

#### Frontend Integration

**TypeScript Types** (`vv-web/src/types/index.ts`):

```typescript
export interface SearchResult {
  // ... existing fields ...

  // New IIT 4.0 fields
  phi?: number;  // Integrated information score [0, 1]
  cosine_score?: number;  // Original cosine similarity
  explainability?: {
    phi_score: number;
    integration_level: 'high' | 'medium' | 'low';
    top_attributes: Array<{
      name: string;
      contribution: number;  // Future: Approach 2
    }>;
    explanation: string;
  };
}
```

**API Response** (modify backend to return):

```json
{
  "results": [
    {
      "id": 123,
      "title": "Vintage 1950s A-Line Dress",
      "score": 0.78,
      "cosine_score": 0.72,
      "phi": 0.85,
      "explainability": {
        "phi_score": 0.85,
        "integration_level": "high",
        "explanation": "Image and text strongly agree on 1950s aesthetic and A-line silhouette"
      },
      ...
    }
  ]
}
```

**UI Component** (`vv-web/src/components/search/PhiBadge.tsx`):

```tsx
import { Badge } from '@/components/ui/Badge';

interface PhiBadgeProps {
  phi: number;
  showTooltip?: boolean;
}

export function PhiBadge({ phi, showTooltip = true }: PhiBadgeProps) {
  // Color code by integration level
  const variant = phi > 0.7 ? 'default' : phi > 0.4 ? 'secondary' : 'outline';
  const integrationLevel = phi > 0.7 ? 'High' : phi > 0.4 ? 'Medium' : 'Low';

  const explanation = phi > 0.7
    ? 'Image and text strongly agree'
    : phi > 0.4
    ? 'Moderate multi-modal agreement'
    : 'Low integration - consider refining search';

  return (
    <div className="relative group">
      <Badge variant={variant} className="cursor-help">
        Φ {(phi * 100).toFixed(0)}%
      </Badge>

      {showTooltip && (
        <div className="absolute hidden group-hover:block bg-vintage-charcoal text-vintage-cream text-xs rounded p-2 w-48 -top-20 left-0 z-10">
          <div className="font-semibold">{integrationLevel} Integration</div>
          <div className="mt-1">{explanation}</div>
        </div>
      )}
    </div>
  );
}
```

---

### Validation Plan

#### Phase 0: Simplified Φ Validation (Week 1-2)

**Goals**:
1. Implement simple Φ (cosine in projected space)
2. Train projection matrices on existing dataset
3. Validate that Φ correlates with perceived result quality

**Steps**:
1. Train CCA projections on 1000 products
2. Calculate Φ for all products
3. Manual evaluation: Do high-Φ results "feel" more coherent?
4. Statistical validation: Does Φ correlate with existing quality metrics?

**Metrics**:
- Φ distribution across dataset (expect: normal distribution centered ~0.5)
- Correlation with category precision (expect: positive correlation)
- User study: 20 queries, ask users to rate coherence, check if high-Φ results rated higher

---

#### Phase 1: Search Quality Validation (Week 2-3)

**Goals**:
1. Implement Φ-weighted ranking
2. A/B test against baseline cosine ranking
3. Measure improvement on vibe queries

**Steps**:
1. Modify `search_with_phi()` to support `phi_weight` parameter
2. Run existing test suite with `phi_weight=0.3`
3. Compare scores to baseline

**Metrics**:
- **Primary**: Vibe query scores (goal: +5-10% improvement)
- **Secondary**: Category precision in top 5 (goal: +5% improvement)
- **Regression check**: Era/culture queries should not degrade

**A/B Test Setup**:
- Control: `phi_weight=0` (baseline cosine)
- Treatment: `phi_weight=0.3`
- Sample: 14 standard queries × 10 trials each

---

#### Phase 2: Rigorous Φ Implementation (Week 3-4)

**Goals**:
1. Implement KSG mutual information estimator
2. Replace simple Φ with rigorous Φ
3. Validate theoretical alignment

**Steps**:
1. Implement `_ksg_phi()` with proper batch context
2. Calculate Φ for 100 products using both methods
3. Compare: simple Φ vs. rigorous Φ (expect correlation >0.7)

**Metrics**:
- Φ_simple vs. Φ_rigorous: Pearson correlation (goal: >0.7)
- Computational performance: <50ms per result (goal)
- Search quality: Does rigorous Φ improve over simple Φ? (hypothesis: marginal gain)

---

### Dependencies

**Python Packages**:
```toml
# Add to pyproject.toml
[tool.poetry.dependencies]
scikit-learn = "^1.3.0"  # For CCA, MI estimation
scipy = "^1.11.0"  # For entropy, pdist
numpy = "^1.24.0"  # Already present
```

**Optional (for MINE estimator)**:
```toml
torch = "^2.0.0"
pytorch-lightning = "^2.0.0"
```

---

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Φ doesn't correlate with quality | High | Start with simple Φ; validate before full implementation |
| Computational cost too high | Medium | Cache Φ scores; pre-compute for all products |
| Projection matrices overfit | Medium | Use cross-validation; regularize CCA |
| User confusion about Φ metric | Low | Provide clear tooltips; use color coding |

---

## APPROACH 2: Maximal Attribute Selection

### Objective

Use Φ to identify which enrichment fields contribute most to integrated information, then optimize rich text construction to include only high-Φ fields (Principle of Maximal Existence).

### Theoretical Grounding

**Maximal Existence Principle**: Among overlapping enrichment fields (era, decade, vibe, style_tags, silhouette, etc.), only the subset with maximal Φ "truly exists" as the product's defining identity.

**Mereological Resolution**: Low-Φ fields don't add causal power; they're either redundant or contradictory. Removing them should improve search quality.

### Methodology

#### Step 1: Field Attribution Analysis

For each product, measure Φ contribution of each enrichment field:

```python
def measure_field_contribution(product: Product, field_name: str) -> float:
    """
    Calculate how much a field contributes to Φ

    Method: Ablation study
    - Φ_full = Φ with all fields in rich text
    - Φ_ablated = Φ without this field in rich text
    - Contribution = Φ_full - Φ_ablated
    """
    # Build rich text with all fields
    rich_text_full = build_rich_text(product, include_all=True)
    text_emb_full = models.encode_text(rich_text_full)
    image_emb = get_image_embedding(product.id)
    phi_full = phi_calculator.calculate_phi(text_emb_full, image_emb)

    # Build rich text without this field
    rich_text_ablated = build_rich_text(product, exclude=[field_name])
    text_emb_ablated = models.encode_text(rich_text_ablated)
    phi_ablated = phi_calculator.calculate_phi(text_emb_ablated, image_emb)

    contribution = phi_full - phi_ablated
    return contribution
```

Run this for all 23 enrichment fields across 100-1000 products.

**Output**: Field importance ranking

Example:
```
Field Importance (averaged across dataset):
1. silhouette: Φ_contrib = 0.12
2. era: Φ_contrib = 0.10
3. vibe: Φ_contrib = 0.09
4. colors: Φ_contrib = 0.08
5. decade: Φ_contrib = 0.03  (redundant with era)
6. style_tags: Φ_contrib = 0.02  (redundant with vibe)
...
```

---

#### Step 2: Maximal Complex Identification

For each product, identify the minimal subset of fields that achieves >95% of max Φ:

```python
def find_maximal_complex(product: Product, threshold: float = 0.95) -> list[str]:
    """
    Greedy search for maximal complex

    1. Start with empty set
    2. Add field with highest marginal Φ contribution
    3. Repeat until Φ > threshold * Φ_full
    """
    all_fields = list(ENRICHMENT_FIELDS)
    selected_fields = []

    # Get full Φ as reference
    phi_full = get_phi_with_fields(product, all_fields)
    target_phi = threshold * phi_full

    current_phi = 0
    while current_phi < target_phi and all_fields:
        # Find field with highest marginal contribution
        best_field = None
        best_gain = 0

        for field in all_fields:
            phi_with_field = get_phi_with_fields(product, selected_fields + [field])
            gain = phi_with_field - current_phi

            if gain > best_gain:
                best_gain = gain
                best_field = field

        if best_field:
            selected_fields.append(best_field)
            all_fields.remove(best_field)
            current_phi += best_gain
        else:
            break

    return selected_fields
```

**Output**: Per-product maximal complex

Example:
```
Product 123 (Victorian lace dress):
  Maximal complex: [silhouette, era, material, decorations]
  Φ_full = 0.82
  Φ_maximal = 0.80 (97.5% of full)
  Excluded fields: [decade, style_tags, season, fit_style, ...]
```

---

#### Step 3: Optimized Rich Text Construction

Modify `build_rich_text()` to use only maximal complex fields:

```python
def build_rich_text_optimized(product: Product, use_maximal: bool = True) -> str:
    """
    Build rich text using Φ-optimized field selection
    """
    if use_maximal:
        # Use pre-computed maximal complex
        if hasattr(product, 'maximal_complex'):
            fields = product.maximal_complex
        else:
            # Fall back to top 8 fields by global importance
            fields = TOP_PHI_FIELDS[:8]
    else:
        # Use all fields (baseline)
        fields = ALL_ENRICHMENT_FIELDS

    # Build natural language text from selected fields
    text_parts = []

    if 'ai_description' in fields and product.ai_description:
        text_parts.append(product.ai_description)

    if 'era' in fields and product.era:
        text_parts.append(f"{product.era} era")

    if 'silhouette' in fields and product.silhouette:
        text_parts.append(f"{product.silhouette} silhouette")

    # ... continue for other fields ...

    return ' '.join(text_parts)[:256]  # Truncate to 256 tokens
```

---

### Integration with Enrichment Pipeline

Modify Claude enrichment to focus on high-Φ fields:

```python
# In scripts/enrichment/claude.py

ENRICHMENT_PROMPT = """
Analyze this fashion item and return structured metadata.

PRIORITY FIELDS (focus here - these create strongest semantic integration):
- silhouette: The overall shape/cut
- era: Historical period
- vibe: Aesthetic feeling (romantic, edgy, minimal, etc.)
- colors: Dominant colors
- material: Primary fabric/material

SECONDARY FIELDS (include if relevant):
- decade, style_tags, pattern, decorations

Return JSON with these fields...
"""
```

This uses discovered field importance to improve prompt engineering.

---

### Validation Plan

**Hypothesis**: Using maximal complex fields improves Φ and search quality vs. using all fields.

**Test**:
1. Re-embed 1000 products using optimized rich text
2. Compare Φ distribution: optimized vs. baseline
3. Run search quality test suite
4. Measure: Do vibe queries improve?

**Expected Results**:
- Mean Φ: +0.05 to +0.10 (higher integration)
- Vibe query scores: +3-5% improvement
- Text embedding quality: More focused, less noise

---

## APPROACH 3: Emergent Complex Discovery

### Objective

Discover irreducible aesthetic "complexes"—combinations of attributes with high Φ that represent unified style concepts (e.g., "GothVictorian", "MinimalScandi", "RomanticCottagecore").

### Theoretical Grounding

**Irreducible Complex**: A set of attributes where removing any element significantly reduces Φ. These complexes are emergent patterns in the data, not pre-defined categories.

**Phenomenal Binding**: Users experience "dark academia" as a unified aesthetic, not as {era=Victorian} + {vibe=dark} + {colors=brown} independently. Complexes capture this unified structure.

### Methodology

#### Step 1: Combinatorial Φ Analysis

Test all meaningful attribute combinations for Φ:

```python
def discover_complexes(
    products: list[Product],
    min_support: int = 10,  # Minimum products with this combination
    min_phi: float = 0.65  # Minimum Φ to be considered complex
) -> list[Complex]:
    """
    Discover attribute combinations with high Φ
    """
    complexes = []

    # Generate candidate combinations
    # Focus on semantic fields: era, decade, vibe, silhouette, colors, material
    semantic_fields = ['era', 'decade', 'vibe', 'silhouette', 'colors', 'material']

    # Test combinations of size 2-5
    from itertools import combinations

    for size in range(2, 6):
        for field_combo in combinations(semantic_fields, size):
            # Find products with this combination
            matching_products = find_products_with_attributes(products, field_combo)

            if len(matching_products) < min_support:
                continue

            # Calculate average Φ for this combination
            phi_scores = []
            for product in matching_products:
                phi = calculate_phi_for_fields(product, field_combo)
                phi_scores.append(phi)

            avg_phi = np.mean(phi_scores)

            if avg_phi >= min_phi:
                complex = Complex(
                    fields=field_combo,
                    phi=avg_phi,
                    support=len(matching_products),
                    exemplars=matching_products[:5]  # Top 5 examples
                )
                complexes.append(complex)

    # Filter: Remove subsets if superset has similar Φ
    # e.g., if {Victorian, lace} has Φ=0.70 and {Victorian, lace, empire} has Φ=0.72,
    # keep only the larger complex
    complexes = filter_subsets(complexes, phi_threshold=0.05)

    return sorted(complexes, key=lambda c: c.phi, reverse=True)
```

**Output**: Discovered aesthetic complexes

Example:
```
Discovered Complexes (N=23):

1. GothVictorian
   Fields: {era=Victorian, vibe=dark, colors=[black, burgundy], material=velvet}
   Φ = 0.82
   Support = 47 products
   Exemplars: [Product(id=234), Product(id=456), ...]

2. RomanticCottagecore
   Fields: {vibe=romantic, colors=[cream, pink, sage], silhouette=empire, material=lace}
   Φ = 0.78
   Support = 62 products

3. MinimalModern
   Fields: {decade=2010s, vibe=minimal, colors=[white, black], silhouette=straight}
   Φ = 0.75
   Support = 38 products

...
```

---

#### Step 2: Complex Ontology Construction

Build a searchable ontology of discovered complexes:

```python
class ComplexOntology:
    """
    Ontology of discovered aesthetic complexes
    """
    def __init__(self, complexes: list[Complex]):
        self.complexes = complexes
        self.complex_index = self._build_index()

    def _build_index(self):
        """Create inverted index: attribute_value → list[Complex]"""
        index = defaultdict(list)

        for complex in self.complexes:
            for field, value in complex.attributes.items():
                if isinstance(value, list):
                    for v in value:
                        index[f"{field}:{v}"].append(complex)
                else:
                    index[f"{field}:{value}"].append(complex)

        return index

    def search_complexes(self, query_attributes: dict) -> list[Complex]:
        """
        Find complexes matching query attributes

        Example:
            query_attributes = {'vibe': 'dark', 'era': 'Victorian'}
            → Returns [GothVictorian, DarkAcademia, ...]
        """
        candidate_complexes = set()

        for field, value in query_attributes.items():
            matching = self.complex_index.get(f"{field}:{value}", [])
            candidate_complexes.update(matching)

        # Rank by overlap and Φ
        scored = []
        for complex in candidate_complexes:
            overlap = sum(
                complex.attributes.get(k) == v
                for k, v in query_attributes.items()
            )
            score = overlap * complex.phi
            scored.append((complex, score))

        return [c for c, s in sorted(scored, key=lambda x: x[1], reverse=True)]
```

---

#### Step 3: Complex-Based Search

Enable users to search by discovered aesthetic complexes:

```python
def search_by_complex(complex_name: str, limit: int = 10):
    """
    Search for products matching a discovered complex

    Args:
        complex_name: e.g., "GothVictorian", "RomanticCottagecore"

    Returns:
        Products sorted by complex membership strength
    """
    # Get complex definition
    complex = ontology.get_complex(complex_name)

    # Build query from complex attributes
    query_text = build_query_from_complex(complex)
    # e.g., "Victorian dark aesthetic with velvet fabric and burgundy colors"

    # Search using normal text search
    results = vector_db.search_text(query_text, limit=limit)

    # Re-rank by complex alignment
    for result in results:
        alignment_score = calculate_complex_alignment(result, complex)
        result['complex_score'] = alignment_score
        result['score'] = 0.5 * result['score'] + 0.5 * alignment_score

    return sorted(results, key=lambda r: r['score'], reverse=True)
```

---

### UI Integration

**Complex Discovery Page**:
```
╔═══════════════════════════════════════════════════════════╗
║ Discovered Aesthetic Complexes                            ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║  [GothVictorian]  Φ=0.82  (47 items)                      ║
║  Victorian era × Dark aesthetic × Velvet & Burgundy       ║
║  [View Items →]                                            ║
║                                                            ║
║  [RomanticCottagecore]  Φ=0.78  (62 items)                ║
║  Romantic vibe × Pastoral × Lace & Cream colors           ║
║  [View Items →]                                            ║
║                                                            ║
║  [ArtDecoGlam]  Φ=0.76  (31 items)                        ║
║  1920s × Geometric patterns × Gold & Black                ║
║  [View Items →]                                            ║
║                                                            ║
╚═══════════════════════════════════════════════════════════╝
```

---

### Validation Plan

**Manual Validation**:
1. Review top 20 discovered complexes
2. Check: Do they represent coherent aesthetic concepts?
3. User study: Show users products from a complex, ask if they "belong together"

**Quantitative Validation**:
- Intra-complex Φ > Inter-complex Φ (clusters are distinct)
- Complex search precision > generic search precision
- User engagement: Do users explore complex pages?

---

## APPROACH 4: Adaptive Multi-Modal Weighting

### Objective

Dynamically adjust the weight of image vs. text embeddings based on which modality creates higher Φ for each specific query.

### Theoretical Grounding

**Maximal Existence**: For each query, only the modality combination with highest Φ truly "exists" as the search entity.

**Non-Locality**: The "search entity" shifts between image-heavy and text-heavy based on query integration, not fixed identity.

### Methodology

#### Step 1: Query Φ Analysis

For each query, measure integration between text and (potential) image:

```python
def analyze_query_phi(query_text: str, query_image: Optional[Image] = None) -> float:
    """
    Measure query integration

    Cases:
    1. Text-only query → Φ = 0 (no image, no integration)
    2. Image-only query → Φ = 0 (no text, no integration)
    3. Text + Image query → Φ = I(text; image)
    4. Text query with synthesized image → Φ = I(text; DALL-E(text))
    """
    if query_text and query_image:
        # User provided both
        text_emb = models.encode_text(query_text)
        image_emb = models.encode_image(query_image)
        phi_query = phi_calculator.calculate_phi(text_emb, image_emb)

    elif query_text and not query_image:
        # Synthesize image from text (optional)
        # For now, infer Φ from query characteristics
        phi_query = infer_query_modality_balance(query_text)

    else:
        phi_query = 0.0

    return phi_query


def infer_query_modality_balance(query_text: str) -> float:
    """
    Estimate query Φ without image

    High-Φ queries (visual + semantic):
    - "1920s flapper dress" (clear visual + era)
    - "red silk evening gown" (color + material + type)

    Low-Φ queries (abstract/text-heavy):
    - "nostalgic feeling"
    - "dark academia aesthetic"
    """
    # Heuristic: Check for visual keywords
    visual_keywords = ['color', 'pattern', 'silk', 'lace', 'embroidered', 'floral', 'striped']
    semantic_keywords = ['vibe', 'aesthetic', 'feeling', 'mood', 'style']

    visual_score = sum(kw in query_text.lower() for kw in visual_keywords)
    semantic_score = sum(kw in query_text.lower() for kw in semantic_keywords)

    # Balanced query → high Φ
    # Semantic-only query → low Φ
    if visual_score > 0 and semantic_score > 0:
        return 0.7  # High integration
    elif visual_score > 0:
        return 0.5  # Medium (visual-heavy)
    elif semantic_score > 0:
        return 0.3  # Low (text-heavy)
    else:
        return 0.5  # Default
```

---

#### Step 2: Adaptive Weighting Function

Weight modalities based on query Φ:

```python
def adaptive_search(query_text: str, query_image: Optional[Image] = None, limit: int = 10):
    """
    Search with adaptive modality weighting
    """
    # Analyze query
    phi_query = analyze_query_phi(query_text, query_image)

    # Determine weights
    if phi_query > 0.6:
        # High integration → balanced weighting
        text_weight = 0.5
        image_weight = 0.5
    elif phi_query < 0.4:
        # Low integration → favor dominant modality
        # If text query, favor text; if image query, favor image
        if query_text and not query_image:
            text_weight = 0.8
            image_weight = 0.2
        elif query_image and not query_text:
            text_weight = 0.2
            image_weight = 0.8
        else:
            text_weight = 0.7
            image_weight = 0.3
    else:
        # Medium integration
        text_weight = 0.6
        image_weight = 0.4

    # Search both modalities
    text_emb = models.encode_text(query_text) if query_text else None
    image_emb = models.encode_image(query_image) if query_image else None

    if text_emb is not None:
        text_results = vector_db.search_similar('vintage_text', text_emb, limit=limit*2)
    else:
        text_results = []

    if image_emb is not None:
        image_results = vector_db.search_similar('vintage_images', image_emb, limit=limit*2)
    else:
        image_results = []

    # Merge and re-rank
    merged = merge_results(text_results, image_results, text_weight, image_weight)

    return merged[:limit]
```

---

### Validation Plan

**A/B Test**:
- Control: Fixed weighting (0.5 text, 0.5 image)
- Treatment: Adaptive weighting based on query Φ

**Queries to Test**:
- High-Φ: "red silk evening dress", "1920s flapper dress"
- Low-Φ: "dark academia aesthetic", "nostalgic feeling"

**Hypothesis**: Adaptive weighting improves low-Φ queries without hurting high-Φ queries.

---

## CNN Integration for Visual Attribute Extraction

### Motivation

**Current Gap**: Vintage Vestige relies entirely on CLIP embeddings (used as-is, no fine-tuning) for visual understanding. All attribute predictions (silhouette, neckline, pattern, colors, material) come from **Claude text analysis**, not direct computer vision.

**Problem**:
- Claude infers attributes from **text descriptions** (product title, museum metadata)
- For Etsy/Depop user-generated listings, text descriptions are often incomplete or inaccurate
- No visual verification of predicted attributes
- CLIP embeddings are general-purpose, not optimized for vintage fashion nuances

**Solution**: Integrate CNNs to extract visual attributes directly from images, creating a **vision-text hybrid** enrichment pipeline that maximizes Φ (integrated information).

### IIT 4.0 Synergy

CNN integration powerfully enhances all 4 IIT approaches:

1. **Approach 1 (Φ-Based Ranking)**:
   - Current Φ measures integration between text embedding and CLIP image embedding
   - With CNNs: Φ can also measure integration between **CNN-predicted attributes** (vision) and **Claude-predicted attributes** (text)
   - High vision-text attribute agreement → high Φ → high confidence result

2. **Approach 2 (Maximal Attribute Selection)**:
   - IIT identifies which enrichment fields maximize Φ (e.g., silhouette, era, vibe)
   - **Train CNNs specifically for high-Φ attributes**, ignore low-Φ attributes
   - Φ-guided CNN architecture: allocate model capacity to attributes that matter most for integration

3. **Approach 3 (Emergent Complex Discovery)**:
   - Discover aesthetic complexes using **both** vision-derived and text-derived attributes
   - Example: "GothVictorian" complex includes:
     - Vision: CNN detects {high_neckline, long_sleeves, black_fabric, velvet_texture}
     - Text: Claude infers {Victorian_era, dark_vibe, formal_occasion}
   - Complexes with high vision-text agreement have highest Φ

4. **Approach 4 (Adaptive Weighting)**:
   - Use CNN confidence scores to dynamically weight vision vs. text modalities
   - High CNN confidence → weight vision more
   - Low CNN confidence (e.g., blurry image) → weight text more

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ VISION PATH (CNN-Based Attribute Extraction)                   │
│ ─────────────────────────────────────────────────────────────── │
│ Product Image                                                   │
│      ↓                                                          │
│ Multi-Task CNN                                                  │
│      ├─→ Silhouette Classifier (12 classes)                    │
│      ├─→ Neckline Classifier (8 classes)                       │
│      ├─→ Pattern Classifier (6 classes)                        │
│      ├─→ Color Extractor (RGB palette)                         │
│      └─→ Era Classifier (8 eras) [Optional]                    │
│      ↓                                                          │
│ Vision-Derived Attributes: {silhouette: A-line, neckline: ...} │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TEXT PATH (Claude-Based Semantic Analysis)                     │
│ ─────────────────────────────────────────────────────────────── │
│ Product Metadata (title, description, museum text)             │
│      ↓                                                          │
│ Claude API (with optional image context)                       │
│      ↓                                                          │
│ Text-Derived Attributes: {silhouette: empire, vibe: romantic}  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ INTEGRATION LAYER (Φ-Based Fusion)                             │
│ ─────────────────────────────────────────────────────────────── │
│ • Calculate Φ between vision and text attributes               │
│ • High agreement → use consensus                               │
│ • Low agreement → flag for review or use high-confidence source│
│ • Generate final enrichment with Φ scores per attribute        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1: Multi-Task Attribute CNN

**Objective**: Train a single CNN with multiple output heads to predict Fashionpedia taxonomy attributes.

**Architecture** (Inspired by Fashion-MNIST CNN pattern):

```python
"""
Multi-task CNN for fashion attribute prediction
Based on ResNet50 backbone with custom heads
"""

import torch
import torch.nn as nn
from torchvision import models

class FashionAttributeCNN(nn.Module):
    def __init__(self):
        super().__init__()

        # Backbone: Pretrained ResNet50
        backbone = models.resnet50(pretrained=True)
        self.features = nn.Sequential(*list(backbone.children())[:-1])  # Remove final FC

        # Shared feature dimension
        feature_dim = 2048

        # Task-specific heads
        self.silhouette_head = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 12)  # 12 silhouette classes
        )

        self.neckline_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 8)  # 8 neckline classes
        )

        self.pattern_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 6)  # 6 pattern classes
        )

        self.length_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 5)  # 5 length classes (floor, midi, knee, above-knee, mini)
        )

        # Color embedding (regression to RGB palette)
        self.color_head = nn.Sequential(
            nn.Linear(feature_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 15)  # Top 5 colors × 3 RGB channels
        )

    def forward(self, x):
        # Extract shared features
        features = self.features(x)
        features = features.view(features.size(0), -1)  # Flatten

        # Multi-task predictions
        return {
            'silhouette': self.silhouette_head(features),
            'neckline': self.neckline_head(features),
            'pattern': self.pattern_head(features),
            'length': self.length_head(features),
            'colors': self.color_head(features).view(-1, 5, 3)  # (batch, 5 colors, RGB)
        }
```

**Training Data**: Use Claude enrichment as ground truth labels
- 1000+ products with existing Claude-generated attributes
- Split: 70% train, 15% validation, 15% test
- Handle missing labels gracefully (not all products have all attributes)

**Loss Function**: Multi-task learning with weighted losses

```python
def multitask_loss(predictions, targets, weights=None):
    """
    Combined loss for all tasks

    Args:
        predictions: dict of {'silhouette': logits, 'neckline': logits, ...}
        targets: dict of ground truth labels
        weights: dict of task weights (optional)
    """
    if weights is None:
        weights = {
            'silhouette': 1.0,  # High importance (Φ analysis shows it's critical)
            'neckline': 0.8,
            'pattern': 0.6,
            'length': 0.7,
            'colors': 0.5
        }

    losses = {}

    # Classification tasks
    for task in ['silhouette', 'neckline', 'pattern', 'length']:
        if task in targets and targets[task] is not None:
            losses[task] = F.cross_entropy(
                predictions[task],
                targets[task]
            ) * weights[task]

    # Color regression
    if 'colors' in targets and targets['colors'] is not None:
        losses['colors'] = F.mse_loss(
            predictions['colors'],
            targets['colors']
        ) * weights['colors']

    # Total loss
    total_loss = sum(losses.values())

    return total_loss, losses
```

**Φ-Guided Task Weighting**: After Approach 2 (Maximal Attribute Selection) identifies high-Φ attributes, adjust task weights:

```python
# Example: IIT analysis shows silhouette has Φ_contrib = 0.38, neckline = 0.15
# Set weights proportional to Φ contribution
weights = {
    'silhouette': 0.38 / sum(phi_contribs),
    'neckline': 0.15 / sum(phi_contribs),
    ...
}
```

---

### Phase 2: CLIP Fine-Tuning on Vintage Fashion

**Objective**: Improve CLIP embeddings by fine-tuning on vintage fashion domain with Claude-enriched text.

**Method**: Contrastive learning with (image, rich_text) pairs

```python
"""
Fine-tune CLIP on vintage fashion using contrastive loss
"""

from transformers import CLIPModel, CLIPProcessor
import torch.nn.functional as F

class VintageCLIP:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    def contrastive_loss(self, image_embeddings, text_embeddings, temperature=0.07):
        """
        InfoNCE contrastive loss

        Pull together (image_i, text_i) pairs
        Push apart (image_i, text_j) for i != j
        """
        # Normalize embeddings
        image_embeddings = F.normalize(image_embeddings, dim=-1)
        text_embeddings = F.normalize(text_embeddings, dim=-1)

        # Compute similarity matrix
        logits = torch.matmul(image_embeddings, text_embeddings.T) / temperature

        # Labels: diagonal is positive pairs
        labels = torch.arange(len(image_embeddings)).to(logits.device)

        # Symmetric loss (image→text + text→image)
        loss_i2t = F.cross_entropy(logits, labels)
        loss_t2i = F.cross_entropy(logits.T, labels)

        return (loss_i2t + loss_t2i) / 2

    def train_step(self, images, rich_texts):
        """
        Single training step

        Args:
            images: batch of product images
            rich_texts: batch of enriched text descriptions
        """
        # Encode
        inputs = self.processor(
            text=rich_texts,
            images=images,
            return_tensors="pt",
            padding=True
        )

        outputs = self.model(**inputs)

        # Contrastive loss
        loss = self.contrastive_loss(
            outputs.image_embeds,
            outputs.text_embeds
        )

        return loss
```

**Training Setup**:
- **Data**: 1000+ (image, rich_text) pairs where rich_text is Claude-enriched description
- **Epochs**: 10-20 (monitor validation Φ)
- **Learning rate**: 1e-5 (low to avoid catastrophic forgetting)
- **Batch size**: 32
- **Validation metric**: Average Φ on held-out set (should increase with fine-tuning)

**Expected Outcome**: Fine-tuned CLIP embeddings have higher Φ (better integration with text) than pretrained CLIP.

---

### Phase 3: Era Classification from Visual Cues

**Objective**: Train CNN to predict historical era from garment photographs.

**Why Separate from Multi-Task CNN**: Era prediction is highly specialized; may benefit from dedicated architecture.

**Architecture**:

```python
class EraClassifier(nn.Module):
    def __init__(self):
        super().__init__()

        # Use EfficientNet-B3 for efficiency
        backbone = models.efficientnet_b3(pretrained=True)
        self.features = backbone.features

        # Custom classifier
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(1536, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 8)  # 8 eras: 1700s, 1800s, 1920s, 1930s, 1950s, 1960s, 1970s, 1980s+
        )

    def forward(self, x):
        features = self.features(x)
        return self.classifier(features)
```

**Training Data**:
- **High-confidence subset**: Metropolitan Museum items with verified dates
- **Augmentation**: Horizontal flip, slight rotation, color jitter (vintage photos vary in color accuracy)

**Validation Strategy**:
- Test on Smithsonian items (different museum, different photographic styles)
- Report top-1 and top-3 accuracy (era classification is challenging; top-3 is more realistic)

**Integration with IIT**:
```python
# Compare CNN era prediction with Claude era inference
vision_era = era_classifier.predict(image)  # "1950s"
text_era = claude_enrichment['era']  # "Art Deco" (1930s)

# Calculate Φ between vision and text for this attribute
if eras_match(vision_era, text_era):
    era_phi = 0.8  # High agreement
else:
    era_phi = 0.2  # Low agreement → flag for review
```

---

### Phase 4: Visual-Text Attribute Fusion

**Objective**: Combine CNN predictions with Claude predictions using Φ as fusion weight.

**Fusion Strategy**:

```python
def fuse_attributes(vision_attrs, text_attrs, confidence_threshold=0.7):
    """
    Fuse vision and text attributes using Φ-based weighting

    Args:
        vision_attrs: dict from CNN {'silhouette': ('A-line', 0.92), ...}
        text_attrs: dict from Claude {'silhouette': 'empire', ...}
        confidence_threshold: minimum CNN confidence to trust vision

    Returns:
        fused_attrs: dict with Φ scores per attribute
    """
    fused = {}

    for attr_name in vision_attrs:
        vision_value, vision_conf = vision_attrs[attr_name]
        text_value = text_attrs.get(attr_name)

        # Case 1: High agreement
        if vision_value == text_value:
            fused[attr_name] = {
                'value': vision_value,
                'source': 'consensus',
                'phi': 0.9,  # High integration
                'vision_conf': vision_conf
            }

        # Case 2: High vision confidence, disagree with text
        elif vision_conf > confidence_threshold:
            # Calculate Φ between vision and text modalities for this attribute
            attr_phi = calculate_attribute_phi(vision_value, text_value, attr_name)

            if attr_phi > 0.5:
                # Moderate integration → use vision but flag
                fused[attr_name] = {
                    'value': vision_value,
                    'source': 'vision_primary',
                    'phi': attr_phi,
                    'vision_conf': vision_conf,
                    'text_alternative': text_value
                }
            else:
                # Low integration → conflict, use text (Claude has broader context)
                fused[attr_name] = {
                    'value': text_value,
                    'source': 'text_fallback',
                    'phi': attr_phi,
                    'vision_conf': vision_conf,
                    'vision_alternative': vision_value
                }

        # Case 3: Low vision confidence, use text
        else:
            fused[attr_name] = {
                'value': text_value,
                'source': 'text_primary',
                'phi': 0.3,  # Low vision confidence → low integration
                'vision_conf': vision_conf
            }

    return fused
```

**Φ Calculation for Attribute Agreement**:

```python
def calculate_attribute_phi(vision_value, text_value, attr_name):
    """
    Measure integrated information between vision and text for a single attribute

    High Φ = values semantically align (even if not exact match)
    Low Φ = values contradict
    """
    # Exact match
    if vision_value == text_value:
        return 0.95

    # Semantic similarity using embedding space
    vision_emb = attribute_encoder.encode(f"{attr_name}: {vision_value}")
    text_emb = attribute_encoder.encode(f"{attr_name}: {text_value}")

    similarity = cosine_similarity(vision_emb, text_emb)

    # Map similarity to Φ
    # High similarity → high Φ (attributes integrate well)
    # Low similarity → low Φ (contradiction)
    phi = (similarity + 1) / 2  # Cosine ∈ [-1, 1] → Φ ∈ [0, 1]

    return phi
```

---

### Implementation Files

**New Python Modules**:

```
scripts/
├── cnn/
│   ├── __init__.py
│   ├── models.py                    # FashionAttributeCNN, EraClassifier
│   ├── train_multitask.py           # Training script for attribute CNN
│   ├── train_era.py                 # Training script for era classifier
│   ├── fine_tune_clip.py            # CLIP fine-tuning script
│   ├── inference.py                 # CNN inference on product images
│   └── fusion.py                    # Φ-based vision-text fusion
├── iit/
│   ├── phi_calculator.py            # Existing Φ calculation
│   └── attribute_phi.py             # New: Attribute-level Φ
└── embeddings/
    └── models.py                    # Update: add fine-tuned CLIP option
```

**Training Data Preparation**:

```
scripts/
└── cnn/
    └── prepare_training_data.py     # Extract images + Claude labels → train/val/test splits
```

**Database Schema Extensions**:

```sql
-- Store CNN predictions alongside Claude enrichment
CREATE TABLE cnn_predictions (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    silhouette_pred VARCHAR(50),
    silhouette_conf FLOAT,
    neckline_pred VARCHAR(50),
    neckline_conf FLOAT,
    pattern_pred VARCHAR(50),
    pattern_conf FLOAT,
    era_pred VARCHAR(20),
    era_conf FLOAT,
    colors_pred JSONB,  -- Array of RGB values
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store fusion results
CREATE TABLE fused_attributes (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    silhouette VARCHAR(50),
    silhouette_phi FLOAT,
    silhouette_source VARCHAR(20),  -- 'consensus' | 'vision_primary' | 'text_primary'
    neckline VARCHAR(50),
    neckline_phi FLOAT,
    neckline_source VARCHAR(20),
    -- ... repeat for other attributes ...
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### Integration with IIT 4.0 Approaches

**Approach 1 (Φ-Based Ranking)**:
- Add CNN-based Φ calculation: `phi_vision_text = calculate_attribute_phi_aggregate(cnn_preds, claude_attrs)`
- Final ranking score: `α * cosine + β * phi_embeddings + γ * phi_attributes`

**Approach 2 (Maximal Attribute Selection)**:
- Use Φ analysis to identify high-value attributes (e.g., silhouette)
- Train CNN heads **only** for high-Φ attributes (prune low-Φ tasks)
- Example: If Φ analysis shows `neckline` has low Φ contribution, remove neckline head

**Approach 3 (Emergent Complex Discovery)**:
- Discover complexes using **both** CNN and Claude attributes
- Filter complexes by vision-text Φ: only keep complexes with high attribute agreement
- Example: "GothVictorian" requires vision confirms {dark_colors, high_neckline, long_length}

**Approach 4 (Adaptive Weighting)**:
- If CNN confidence is high → weight vision embeddings more
- If CNN confidence is low (blurry image) → weight text embeddings more
- Dynamic fusion: `vision_weight = f(cnn_confidence, attribute_phi)`

---

### Validation Plan

**Phase 1 Validation (Multi-Task CNN)**:

1. **Accuracy Metrics**:
   - Silhouette: Top-1 accuracy >70% (challenging due to fine-grained classes)
   - Neckline: Top-1 accuracy >60%
   - Pattern: Top-1 accuracy >75% (easier, fewer classes)
   - Era: Top-3 accuracy >65%

2. **Φ Improvement**:
   - Measure average Φ before CNN (text-only enrichment)
   - Measure average Φ after CNN (fused enrichment)
   - **Hypothesis**: Fused enrichment increases Φ by +0.05-0.10

3. **Search Quality**:
   - Run test suite with CNN-enriched products
   - **Hypothesis**: Vibe queries improve +3-5% (CNN provides visual grounding for aesthetics)

**Phase 2 Validation (Fine-Tuned CLIP)**:

1. **Embedding Quality**:
   - Compare pretrained CLIP vs. fine-tuned CLIP on vintage fashion retrieval
   - Measure: Precision@5, Recall@10 on held-out set

2. **Φ Comparison**:
   - Pretrained CLIP: Average Φ = 0.52
   - Fine-tuned CLIP: Average Φ = ? (expect >0.60)

3. **User Study**:
   - Show users search results from both models
   - Ask: Which results feel more coherent? (expect fine-tuned wins >65% of time)

**Phase 3 Validation (Era Classifier)**:

1. **Accuracy on Met Museum** (clean labels): >80%
2. **Accuracy on Etsy/Depop** (noisy labels): >50% (harder, user-generated content)
3. **Φ Agreement**: Calculate era Φ (vision vs. text) across dataset

---

### Timeline Integration with IIT Roadmap

**Original IIT Timeline**: 10-12 weeks

**With CNN Integration**:

| Week | IIT Phase | CNN Phase |
|------|-----------|-----------|
| 1-3 | Approach 1: Φ-Based Ranking | Prepare training data, train multi-task CNN |
| 4-5 | Validate Φ, A/B test | Integrate CNN predictions, measure Φ improvement |
| 5-7 | Approach 2: Maximal Attribute Selection | Φ-guided task weighting, prune low-Φ CNN heads |
| 7-10 | Approach 3: Emergent Complex Discovery | Use CNN attributes in complex discovery |
| 10-12 | Approach 4: Adaptive Weighting | Fine-tune CLIP (optional), final validation |

**Total Timeline**: 12-14 weeks (CNN adds 2-4 weeks to comprehensive plan)

---

### Expected Outcomes

**Quantitative**:
- +10-15% attribute prediction accuracy (CNN + Claude > Claude alone)
- +0.05-0.10 increase in average Φ (vision-text integration)
- +5-10% improvement on vibe/aesthetic queries

**Qualitative**:
- Visual verification of enrichment attributes
- Reduced reliance on text descriptions (important for Etsy/Depop)
- Explainability: "This matched because image shows empire waistline (CNN: 92% confidence) and text confirms romantic vibe"

**Research**:
- Validation of IIT 4.0 in multi-modal fashion search
- Novel Φ-based vision-text fusion approach
- Emergent aesthetic complexes grounded in both vision and semantics

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

**Milestone**: Approach 1 (Φ-Based Ranking) working with simple Φ

**Deliverables**:
- `scripts/iit/phi_calculator.py` with simple Φ implementation
- Modified `vector_db.py` with `search_with_phi()`
- Frontend PhiBadge component
- Projection matrices trained on dataset
- Validation: Φ distribution analysis, manual quality check

**Success Criteria**:
- Φ scores calculated for all 1000 products
- Φ distribution is meaningful (not all 0 or all 1)
- High-Φ results subjectively feel more coherent

---

### Phase 2: Search Quality (Weeks 3-5)

**Milestone**: Φ-weighted ranking improves vibe query scores

**Deliverables**:
- A/B test infrastructure
- Φ-weighted ranking in production API
- Search quality metrics dashboard
- User explainability UI (tooltips, badges)

**Success Criteria**:
- Vibe query scores improve +5-10%
- No regression on era/culture queries
- User study: >70% understand Φ explanation

---

### Phase 3: Attribute Optimization (Weeks 5-7)

**Milestone**: Approach 2 (Maximal Attribute Selection) deployed

**Deliverables**:
- Field attribution analysis script
- Maximal complex identification per product
- Optimized rich text construction
- Re-embedding pipeline with new rich text

**Success Criteria**:
- Mean Φ increases +0.05-0.10
- Search quality improves +3-5% on vibe queries
- Reduced text embedding noise

---

### Phase 4: Complex Discovery (Weeks 7-10)

**Milestone**: Approach 3 (Emergent Complexes) live in UI

**Deliverables**:
- Complex discovery algorithm
- Complex ontology database
- Complex search API endpoints
- "Discover Aesthetics" UI page

**Success Criteria**:
- 20-30 meaningful complexes discovered
- User study: >80% agree complexes are coherent
- Complex search precision > generic search precision

---

### Phase 5: Adaptive Weighting (Weeks 10-12)

**Milestone**: Approach 4 (Adaptive Weighting) in production

**Deliverables**:
- Query Φ analysis
- Adaptive weighting function
- A/B test results
- User engagement metrics

**Success Criteria**:
- Low-Φ queries improve +5%
- High-Φ queries maintain quality
- Overall user engagement increases

---

## Technical Specifications

### Database Schema Extensions

**New Table: `phi_scores`**
```sql
CREATE TABLE phi_scores (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    phi_score FLOAT NOT NULL,
    cosine_score FLOAT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method VARCHAR(10) DEFAULT 'simple'  -- 'simple' | 'ksg' | 'mine'
);

CREATE INDEX idx_phi_score ON phi_scores(phi_score DESC);
```

**New Table: `maximal_complexes`**
```sql
CREATE TABLE maximal_complexes (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    fields JSONB NOT NULL,  -- ['silhouette', 'era', 'vibe']
    phi_full FLOAT NOT NULL,
    phi_maximal FLOAT NOT NULL,
    efficiency FLOAT GENERATED ALWAYS AS (phi_maximal / phi_full) STORED
);
```

**New Table: `discovered_complexes`**
```sql
CREATE TABLE discovered_complexes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    attributes JSONB NOT NULL,  -- {'era': 'Victorian', 'vibe': 'dark', ...}
    phi_score FLOAT NOT NULL,
    support INTEGER NOT NULL,  -- Number of products
    exemplar_ids INTEGER[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_complex_phi ON discovered_complexes(phi_score DESC);
```

---

### API Endpoints

**New Endpoints**:

```
POST /api/search/phi
{
  "query": "dark academia aesthetic",
  "phi_weight": 0.3,
  "limit": 12
}
Response: SearchResponse with phi scores

GET /api/complexes
Response: { "complexes": [Complex, ...] }

GET /api/complexes/{name}
Response: { "complex": Complex, "products": [Product, ...] }

POST /api/search/complex
{
  "complex_name": "GothVictorian",
  "limit": 12
}
Response: SearchResponse
```

---

### Configuration

**New Config File**: `config/iit.yaml`

```yaml
phi_calculator:
  method: simple  # simple | ksg | mine
  projection_path: models/phi_projections.pkl
  ksg_k: 5
  normalize: true

search:
  phi_weight: 0.3  # Default Φ weight in ranking
  use_adaptive: false  # Enable adaptive weighting
  cache_phi: true

maximal_complex:
  threshold: 0.95  # 95% of full Φ
  min_fields: 3
  max_fields: 8

complex_discovery:
  min_support: 10  # Minimum products per complex
  min_phi: 0.65  # Minimum Φ to be complex
  max_size: 5  # Maximum attributes per complex
```

---

## Validation & Metrics

### Quantitative Metrics

**Primary Metrics**:
1. **Vibe Query Improvement**: +5-10% on baseline scores
2. **Category Precision**: Top-5 category match rate
3. **Φ-Quality Correlation**: Pearson(Φ, user_rating) > 0.4

**Secondary Metrics**:
1. **Mean Φ**: Dataset average Φ score
2. **Φ Distribution**: Should be normal, centered ~0.5
3. **Computational Performance**: <50ms per result

### Qualitative Validation

**User Studies**:
1. **Φ Explanation**: 20 users, 10 queries each
   - Question: "Does the Φ score help you understand why this item matched?"
   - Goal: >70% say yes

2. **Complex Coherence**: 15 users, 5 complexes each
   - Show 10 products from a complex
   - Question: "Do these items belong together aesthetically?"
   - Goal: >80% agreement

3. **Search Quality**: 30 users, free exploration
   - Compare Φ-weighted vs. baseline
   - Measure: Click-through rate, dwell time, satisfaction rating

---

### A/B Testing Framework

```python
class ABTest:
    def __init__(self, name: str, control: callable, treatment: callable):
        self.name = name
        self.control = control
        self.treatment = treatment
        self.results = {'control': [], 'treatment': []}

    def run(self, queries: list[str], n_trials: int = 10):
        for query in queries:
            for _ in range(n_trials):
                # Randomly assign
                if random.random() < 0.5:
                    result = self.control(query)
                    self.results['control'].append(result)
                else:
                    result = self.treatment(query)
                    self.results['treatment'].append(result)

    def analyze(self):
        control_scores = [r['score'] for r in self.results['control']]
        treatment_scores = [r['score'] for r in self.results['treatment']]

        improvement = np.mean(treatment_scores) - np.mean(control_scores)
        p_value = stats.ttest_ind(treatment_scores, control_scores).pvalue

        return {
            'improvement': improvement,
            'p_value': p_value,
            'significant': p_value < 0.05
        }
```

---

## Conclusion

This plan provides a rigorous, comprehensive roadmap for integrating IIT 4.0 into Vintage Vestige. The four approaches build sequentially, each adding theoretical depth and practical value:

1. **Φ-Based Ranking** establishes the foundation for measuring integrated information
2. **Maximal Attribute Selection** optimizes the enrichment pipeline using Φ
3. **Emergent Complex Discovery** reveals hidden aesthetic structures in the data
4. **Adaptive Weighting** applies Φ dynamically for query-specific optimization

**Timeline**: 10-12 weeks for full implementation

**Expected Outcomes**:
- Search quality improvement: +5-10% on vibe queries
- User explainability: Φ scores and attribute attribution
- Novel discovery: 20-30 emergent aesthetic complexes
- Theoretical validation: IIT 4.0 principles in a real-world system

**Next Steps**:
1. Review and approve plan
2. Begin Phase 1: Implement simple Φ calculator
3. Train projection matrices on existing dataset
4. Validate Φ distribution and correlation with quality

---

**Questions for Clarification**:
1. Do you want to start with simplified Φ (Phase 0) or go straight to rigorous KSG implementation?
2. What's the acceptable computational budget per search result? (<50ms? <100ms?)
3. Should complex discovery be automatic or require manual curation?
4. Any specific aesthetic complexes you'd like to see discovered as validation?
