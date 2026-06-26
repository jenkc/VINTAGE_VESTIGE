# Vintage Vestige: 4-5 Week Complete Implementation Plan

**Goal:** Ship the full fashion knowledge graph with cross-source bridges, demonstrating innovation in AI product design.

**Timeline:** March 3 - April 4, 2026 (5 weeks) **Total Effort:** ~100-120 hours (~20-25 hours/week) **Cost:** ~$10 (Claude API for narratives)

---

## Week 1: Backend Core + Bridge Intelligence

**Focus:** The moat. Build what makes this defensible.

### Monday-Tuesday (8-10 hours): FastAPI Foundation

**Create `api/main.py`:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.search import router as search_router
from api.products import router as products_router

app = FastAPI(title="Vintage Vestige API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Create `api/models.py`** (Pydantic response models):

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class ProductResponse(BaseModel):
    id: int
    title: str
    platform: str
    era: Optional[str]
    category: Optional[str]
    style_tags: Optional[List[str]]
    primary_image: Optional[str]
    ai_description: Optional[str]
    
class SearchResponse(BaseModel):
    results: List[ProductResponse]
    total: int
    
class StyleBridgeResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    bridge_score: float
    structural_score: float
    shared_attributes: Dict[str, str]
    bridge_narrative: Optional[str]
    bridge_type: str
    product: ProductResponse
    
class BridgeResponse(BaseModel):
    modern_echoes: List[StyleBridgeResponse]
    historical_ancestors: List[StyleBridgeResponse]
    style_siblings: List[StyleBridgeResponse]
```

**Create `api/search.py`:**

```python
from fastapi import APIRouter, HTTPException, File, UploadFile
from api.models import SearchResponse
from storage.vector_db import VectorDB
from storage.database import SessionLocal, Product

router = APIRouter()
vdb = VectorDB()

@router.post("/search/text")
async def search_text(query: str, limit: int = 20):
    # Text embedding search
    # Return results with product metadata
    pass

@router.post("/search/image")
async def search_image(file: UploadFile, limit: int = 20):
    # Image embedding search
    # Return results with product metadata
    pass
```

**Create `api/products.py`:**

```python
from fastapi import APIRouter, HTTPException
from api.models import ProductResponse, BridgeResponse
from storage.database import SessionLocal, Product
from storage.bridges import get_modern_echoes, get_style_ancestry, get_style_siblings

router = APIRouter()

@router.get("/products/{product_id}")
async def get_product(product_id: int):
    # Fetch product from database
    # Return with full details
    pass

@router.get("/bridges/{product_id}")
async def get_bridges(product_id: int):
    # Get all three bridge types
    # Return formatted response
    pass
```

**Deliverable:** FastAPI skeleton running locally on port 8000

---

### Wednesday (6-8 hours): Bridge Computation Core

**Priority 1: Fix Qdrant payloads (1-2 hours)**

Create `scripts/database/backfill_qdrant_platform.py`:

```python
from storage.vector_db import VectorDB
from storage.database import SessionLocal, Product

db = SessionLocal()
vdb = VectorDB()
products = db.query(Product).filter(Product.embedded_at != None).all()

print(f"Backfilling platform field for {len(products)} products...")

for product in products:
    payload_patch = {"platform": product.platform}
    for collection in [vdb.image_collection, vdb.text_collection]:
        try:
            vdb.client.set_payload(
                collection_name=collection,
                payload=payload_patch,
                points=[product.id]
            )
        except Exception as e:
            pass  # point may not exist in this collection
            
print("Backfill complete!")
db.close()
```

Run it, verify platform field exists in Qdrant.

**Priority 2: Add StyleBridge model (30 min)**

Add to `storage/database.py`:

```python
from sqlalchemy import UniqueConstraint

class StyleBridge(Base):
    __tablename__ = 'style_bridges'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), 
                      nullable=False, index=True)
    target_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), 
                      nullable=False, index=True)

    text_similarity = Column(Float, nullable=False)
    image_similarity = Column(Float, nullable=True)
    structural_score = Column(Float, nullable=False)
    bridge_score = Column(Float, nullable=False)

    shared_attributes = Column(Text, nullable=True)  # JSON string
    bridge_type = Column(String, nullable=True)
    bridge_narrative = Column(Text, nullable=True)

    # IIT 4.0 future-proofing (nullable — populated post-MVP)
    phi_score = Column(Float, nullable=True)             # Φ integration score for this bridge pair
    cnn_structural_score = Column(Float, nullable=True)  # structural score using CNN-verified attributes

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', name='uq_bridge_pair'),
    )
```

Run: `python -c "from storage.database import init_db; init_db()"`

**Priority 3: Start bridge computation script (4-6 hours)**

Create `scripts/analysis/compute_bridges.py` - this is the big one.

Key functions:

- `compute_structural_score(a: Product, b: Product)` → (score, shared_attrs)
- `compute_bridge_score(text_sim, image_sim, structural_score)` → weighted composite
- `find_cross_source_bridges(historical_items, modern_items)` → candidate pairs
- `bulk_insert_bridges(bridge_records)` → database insertion

**Algorithm flow:**

```python
# 1. Load all enriched products
db = SessionLocal()
all_products = db.query(Product).filter(Product.enriched_at != None).all()

# 2. Split by platform
historical = [p for p in all_products if p.platform in ['met_museum', 'smithsonian']]
modern = [p for p in all_products if p.platform == 'fashionpedia']

# 3. For each historical item:
for hist_item in historical:
    # Query Qdrant for similar modern items
    text_candidates = vdb.search_similar(
        text=hist_item.ai_description, 
        collection='vintage_text',
        filter_by={'platform': 'fashionpedia'},
        limit=20
    )
    
    image_candidates = []
    if hist_item.primary_image:
        image_candidates = vdb.search_similar(
            image_path=hist_item.primary_image,
            collection='vintage_images', 
            filter_by={'platform': 'fashionpedia'},
            limit=20
        )
    
    # Merge candidates, compute structural scores
    candidates = merge_dedupe(text_candidates, image_candidates)
    
    bridges = []
    for candidate in candidates:
        struct_score, shared = compute_structural_score(hist_item, candidate)
        if struct_score < 0.15:
            continue
            
        bridge_score = compute_bridge_score(
            text_sim=candidate.text_similarity,
            image_sim=candidate.image_similarity,
            structural=struct_score
        )
        
        bridges.append({
            'source_id': hist_item.id,
            'target_id': candidate.id,
            'text_similarity': candidate.text_similarity,
            'image_similarity': candidate.image_similarity,
            'structural_score': struct_score,
            'bridge_score': bridge_score,
            'shared_attributes': json.dumps(shared),
            'bridge_type': 'historical_to_modern'
        })
    
    # Keep top 10 by bridge_score
    bridges.sort(key=lambda x: x['bridge_score'], reverse=True)
    bulk_insert_bridges(bridges[:10])

# 4. Repeat in reverse (modern → historical)
# Similar logic with bridge_type = 'modern_to_historical'
```

**Deliverable:** Bridge computation script that runs without errors

---

### Thursday-Friday (6-8 hours): Run Bridges + Generate Narratives

**Priority 1: Execute bridge computation (2-3 hours)**

Run the script on full 1,000-item dataset:

```bash
python scripts/analysis/compute_bridges.py
```

Expected: ~5,000-10,000 bridge rows created

Debug issues, verify results manually:

- Check a few bridges make sense
- Look at bridge_score distribution
- Verify shared_attributes are meaningful

**Priority 2: Generate bridge narratives (4-5 hours)**

Add to `enrichment/claude.py`:

```python
def generate_bridge_narrative(
    source_product: Product, 
    target_product: Product,
    shared_attributes: dict
) -> str:
    """Generate one-sentence bridge narrative (≤30 words)"""
    
    prompt = f"""You are a fashion historian. Write ONE sentence (≤30 words) 
    explaining the design connection between these garments:

    Historical item: {source_product.title} ({source_product.era})
    Modern item: {target_product.title}
    
    Shared design elements: {', '.join(shared_attributes.keys())}
    
    Focus on the design DNA they share. Be specific and evocative.
    ONE SENTENCE ONLY."""
    
    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text.strip()
```

Create `scripts/analysis/generate_bridge_narratives.py`:

```python
from storage.database import SessionLocal, StyleBridge, Product
from enrichment.claude import generate_bridge_narrative
import json
import time

db = SessionLocal()

# Get bridges with score > 0.5 and no narrative yet
bridges = db.query(StyleBridge).filter(
    StyleBridge.bridge_score > 0.5,
    StyleBridge.bridge_narrative == None
).limit(1500).all()

print(f"Generating narratives for {len(bridges)} bridges...")

for i, bridge in enumerate(bridges):
    source = db.query(Product).get(bridge.source_id)
    target = db.query(Product).get(bridge.target_id)
    shared = json.loads(bridge.shared_attributes)
    
    try:
        narrative = generate_bridge_narrative(source, target, shared)
        bridge.bridge_narrative = narrative
        db.commit()
        
        if (i + 1) % 50 == 0:
            print(f"Progress: {i+1}/{len(bridges)}")
            
        time.sleep(0.5)  # Rate limiting
    except Exception as e:
        print(f"Error on bridge {bridge.id}: {e}")
        continue

db.close()
print("Narrative generation complete!")
```

Run it. Cost: ~$5. Time: 2-3 hours with rate limiting.

**Deliverable:** ~1,500 bridges with generated narratives

---

### Weekend: Bridge Query Utilities + API Endpoints

**Create `storage/bridges.py`:**

```python
from storage.database import SessionLocal, StyleBridge, Product
from typing import List

def get_modern_echoes(product_id: int, limit: int = 5) -> List[StyleBridge]:
    """Historical item → modern descendants"""
    db = SessionLocal()
    bridges = db.query(StyleBridge).filter(
        StyleBridge.source_id == product_id,
        StyleBridge.bridge_type == 'historical_to_modern'
    ).order_by(StyleBridge.bridge_score.desc()).limit(limit).all()
    
    # Eager load target products
    for bridge in bridges:
        bridge.product = db.query(Product).get(bridge.target_id)
    
    db.close()
    return bridges

def get_style_ancestry(product_id: int, limit: int = 5) -> List[StyleBridge]:
    """Modern item → historical ancestors"""
    db = SessionLocal()
    bridges = db.query(StyleBridge).filter(
        StyleBridge.target_id == product_id,
        StyleBridge.bridge_type == 'historical_to_modern'
    ).order_by(StyleBridge.bridge_score.desc()).limit(limit).all()
    
    for bridge in bridges:
        bridge.product = db.query(Product).get(bridge.source_id)
    
    db.close()
    return bridges

def get_style_siblings(product_id: int, limit: int = 10) -> List[StyleBridge]:
    """Structurally similar items across all eras"""
    # Implementation: Items that share high structural_score
    # regardless of bridge_type
    pass
```

**Implement bridge endpoints in `api/products.py`:**

```python
@router.get("/bridges/{product_id}", response_model=BridgeResponse)
async def get_bridges(product_id: int):
    modern_echoes = get_modern_echoes(product_id)
    historical_ancestors = get_style_ancestry(product_id)
    style_siblings = get_style_siblings(product_id)
    
    return BridgeResponse(
        modern_echoes=[format_bridge(b) for b in modern_echoes],
        historical_ancestors=[format_bridge(b) for b in historical_ancestors],
        style_siblings=[format_bridge(b) for b in style_siblings]
    )
```

**Deliverable:** Bridge API endpoints working

---

## Week 2: Frontend Implementation

**Focus:** Make the intelligence visible and usable.

### Monday-Tuesday (8-10 hours): Search Infrastructure

**Implement `src/components/search/SearchBar.tsx`:**

```typescript
'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { debounce } from '@/lib/utils'

export function SearchBar() {
  const [query, setQuery] = useState('')
  const router = useRouter()

  const handleSearch = debounce((q: string) => {
    if (q.trim()) {
      router.push(`/search?q=${encodeURIComponent(q)}&mode=text`)
    }
  }, 300)

  return (
    <div className="relative flex items-center gap-2 w-full max-w-2xl">
      <Input
        type="text"
        placeholder="Search for styles, eras, or garments..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          handleSearch(e.target.value)
        }}
        className="pr-10"
      />
      <Search className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
    </div>
  )
}
```

**Implement `src/components/search/ImageUpload.tsx`:**

```typescript
'use client'

import { useState } from 'react'
import { Upload, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { compressImage } from '@/lib/compress-image'
import { searchByImage } from '@/lib/api'
import { useRouter } from 'next/navigation'

export function ImageUpload() {
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleFile = async (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target?.result as string)
    reader.readAsDataURL(file)

    setLoading(true)
    try {
      const compressed = await compressImage(file)
      const results = await searchByImage(compressed)
      // Store results in state or pass via URL
      router.push(`/search?mode=image`)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md">
      {preview ? (
        <div className="relative">
          <img src={preview} alt="Upload preview" className="rounded-lg" />
          <Button
            size="icon"
            variant="destructive"
            onClick={() => setPreview(null)}
            className="absolute top-2 right-2"
          >
            <X />
          </Button>
        </div>
      ) : (
        <label className="border-2 border-dashed rounded-lg p-8 cursor-pointer hover:border-primary transition">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <div className="flex flex-col items-center gap-2">
            <Upload className="w-12 h-12 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Click to upload or drag image here
            </p>
          </div>
        </label>
      )}
      {loading && <p className="text-center mt-2">Searching...</p>}
    </div>
  )
}
```

**Create `src/lib/compress-image.ts`:**

```typescript
export async function compressImage(
  file: File,
  maxPx = 1024,
  quality = 0.85
): Promise<Blob> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, maxPx / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = img.width * scale
      canvas.height = img.height * scale
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => resolve(blob!), 'image/jpeg', quality)
    }
    img.src = URL.createObjectURL(file)
  })
}
```

**Implement `src/components/search/ProductCard.tsx`:**

```typescript
import { Product } from '@/types'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import Image from 'next/image'

interface ProductCardProps {
  product: Product
  similarity?: number
}

export function ProductCard({ product, similarity }: ProductCardProps) {
  return (
    <Link href={`/products/${product.id}`}>
      <Card className="overflow-hidden hover:shadow-lg transition">
        {product.primary_image && (
          <div className="aspect-[3/4] relative">
            <Image
              src={product.primary_image}
              alt={product.title}
              fill
              className="object-cover"
            />
          </div>
        )}
        <CardContent className="p-4">
          <h3 className="font-semibold line-clamp-2">{product.title}</h3>
          {product.era && (
            <Badge variant="secondary" className="mt-2">
              {product.era}
            </Badge>
          )}
          {similarity && (
            <p className="text-sm text-muted-foreground mt-2">
              {Math.round(similarity * 100)}% match
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
```

**Create `src/app/search/page.tsx`:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { searchByText } from '@/lib/api'
import { ProductCard } from '@/components/search/ProductCard'
import { Product } from '@/types'

export default function SearchPage() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q')
  const mode = searchParams.get('mode')
  
  const [results, setResults] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (query && mode === 'text') {
      searchByText(query).then(data => {
        setResults(data.results)
        setLoading(false)
      })
    }
  }, [query, mode])

  if (loading) return <div>Searching...</div>

  return (
    <div className="container py-12">
      <h1 className="text-3xl font-bold mb-8">
        Search Results for "{query}"
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {results.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  )
}
```

**Deliverable:** Working search page with text and image modes

---

### Wednesday-Thursday (10-12 hours): Product Detail + Bridge Display

**This is the showcase moment. The bridges make the product special.**

**Create `src/components/bridges/BridgeCard.tsx`:**

```typescript
import { StyleBridge } from '@/types'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import Image from 'next/image'

interface BridgeCardProps {
  bridge: StyleBridge
}

export function BridgeCard({ bridge }: BridgeCardProps) {
  const { product, bridge_narrative, shared_attributes, bridge_score } = bridge

  return (
    <Link href={`/products/${product.id}`}>
      <Card className="hover:shadow-lg transition">
        <div className="grid grid-cols-3 gap-4 p-4">
          <div className="aspect-[3/4] relative col-span-1">
            {product.primary_image && (
              <Image
                src={product.primary_image}
                alt={product.title}
                fill
                className="object-cover rounded"
              />
            )}
          </div>
          
          <div className="col-span-2 space-y-2">
            <h4 className="font-semibold line-clamp-2">{product.title}</h4>
            
            {product.era && (
              <Badge variant="secondary">{product.era}</Badge>
            )}
            
            {bridge_narrative && (
              <p className="text-sm text-muted-foreground italic">
                "{bridge_narrative}"
              </p>
            )}
            
            <div className="flex flex-wrap gap-1 mt-2">
              {Object.entries(shared_attributes).map(([key, value]) => (
                <Badge key={key} variant="outline" className="text-xs">
                  {value}
                </Badge>
              ))}
            </div>
            
            <p className="text-xs text-muted-foreground">
              {Math.round(bridge_score * 100)}% style match
            </p>
          </div>
        </div>
      </Card>
    </Link>
  )
}
```

**Create `src/app/products/[id]/page.tsx`:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getProduct, getBridges } from '@/lib/api'
import { Product, BridgeResponse } from '@/types'
import { Badge } from '@/components/ui/badge'
import { BridgeCard } from '@/components/bridges/BridgeCard'
import Image from 'next/image'

export default function ProductPage() {
  const params = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [bridges, setBridges] = useState<BridgeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const id = parseInt(params.id as string)
    
    Promise.all([
      getProduct(id),
      getBridges(id)
    ]).then(([productData, bridgeData]) => {
      setProduct(productData)
      setBridges(bridgeData)
      setLoading(false)
    })
  }, [params.id])

  if (loading) return <div>Loading...</div>
  if (!product) return <div>Product not found</div>

  return (
    <div className="container py-12">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-16">
        {/* Product Detail */}
        <div className="aspect-[3/4] relative">
          {product.primary_image && (
            <Image
              src={product.primary_image}
              alt={product.title}
              fill
              className="object-cover rounded-lg"
            />
          )}
        </div>
        
        <div className="space-y-6">
          <div>
            <h1 className="text-4xl font-bold mb-4">{product.title}</h1>
            
            <div className="flex flex-wrap gap-2 mb-6">
              {product.era && <Badge variant="secondary">{product.era}</Badge>}
              {product.category && <Badge>{product.category}</Badge>}
              {product.style_tags?.map(tag => (
                <Badge key={tag} variant="outline">{tag}</Badge>
              ))}
            </div>
            
            {product.ai_description && (
              <p className="text-lg text-muted-foreground leading-relaxed">
                {product.ai_description}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bridge Sections - THIS IS THE INNOVATION */}
      {bridges && (
        <>
          {/* Historical Ancestry */}
          {bridges.historical_ancestors.length > 0 && (
            <section className="mb-16">
              <h2 className="text-3xl font-bold mb-6">Style Ancestry</h2>
              <p className="text-muted-foreground mb-8">
                Historical garments that influenced this design
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {bridges.historical_ancestors.map(bridge => (
                  <BridgeCard key={bridge.id} bridge={bridge} />
                ))}
              </div>
            </section>
          )}

          {/* Modern Echoes */}
          {bridges.modern_echoes.length > 0 && (
            <section className="mb-16">
              <h2 className="text-3xl font-bold mb-6">Modern Echoes</h2>
              <p className="text-muted-foreground mb-8">
                Contemporary designs that echo this historical piece
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {bridges.modern_echoes.map(bridge => (
                  <BridgeCard key={bridge.id} bridge={bridge} />
                ))}
              </div>
            </section>
          )}

          {/* Style Siblings */}
          {bridges.style_siblings.length > 0 && (
            <section>
              <h2 className="text-3xl font-bold mb-6">Style Siblings</h2>
              <p className="text-muted-foreground mb-8">
                Related garments with similar design DNA
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {bridges.style_siblings.map(bridge => (
                  <BridgeCard key={bridge.id} bridge={bridge} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
```

**Update `src/lib/api.ts` to add bridge endpoint:**

```typescript
export async function getBridges(id: number): Promise<BridgeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/bridges/${id}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

**Add types to `src/types/index.ts`:**

```typescript
export interface StyleBridge {
  id: number
  source_id: number
  target_id: number
  bridge_score: number
  structural_score: number
  shared_attributes: Record<string, string>
  bridge_narrative: string | null
  bridge_type: string
  product: Product
}

export interface BridgeResponse {
  modern_echoes: StyleBridge[]
  historical_ancestors: StyleBridge[]
  style_siblings: StyleBridge[]
}
```

**Deliverable:** Product pages showing full bridge intelligence

---

### Friday (4-6 hours): Header, Footer, Polish

**Implement `src/components/layout/Header.tsx`:**

```typescript
import Link from 'next/link'
import { SearchBar } from '@/components/search/SearchBar'

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="text-2xl font-bold">
          Vintage Vestige
        </Link>
        
        <nav className="hidden md:flex items-center gap-6">
          <Link href="/search" className="text-sm hover:underline">
            Search
          </Link>
          <Link href="/about" className="text-sm hover:underline">
            About
          </Link>
        </nav>
      </div>
    </header>
  )
}
```

**Implement `src/components/layout/Footer.tsx`:**

```typescript
export function Footer() {
  return (
    <footer className="border-t py-12 mt-24">
      <div className="container">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h3 className="font-bold mb-4">Vintage Vestige</h3>
            <p className="text-sm text-muted-foreground">
              A fashion knowledge graph connecting 500 years of design history.
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Links</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/about">About</Link></li>
              <li><Link href="/search">Search</Link></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Built with</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>Claude API (Anthropic)</li>
              <li>CLIP Embeddings</li>
              <li>Qdrant Vector DB</li>
              <li>Next.js & FastAPI</li>
            </ul>
          </div>
        </div>
        
        <div className="mt-8 pt-8 border-t text-center text-sm text-muted-foreground">
          <p>© 2026 Vintage Vestige. Built by Jen Kim.</p>
        </div>
      </div>
    </footer>
  )
}
```

**Wire homepage CTAs in `src/app/page.tsx`:**

```typescript
// Find the CTA buttons, replace with:
<Link href="/search?mode=text">
  <Button size="lg">Start Searching</Button>
</Link>

<Link href="/search?mode=image">
  <Button size="lg" variant="outline">Upload Image</Button>
</Link>
```

**Create simple About page `src/app/about/page.tsx`:**

```typescript
export default function AboutPage() {
  return (
    <div className="container py-12 prose prose-lg max-w-3xl mx-auto">
      <h1>About Vintage Vestige</h1>
      
      <p>
        Vintage Vestige is a fashion knowledge graph that connects garments 
        across 500 years of design history. Using AI-powered analysis and 
        cross-source style bridges, we reveal how historical fashion influences 
        modern design.
      </p>
      
      <h2>How It Works</h2>
      
      <ul>
        <li>
          <strong>AI Enrichment:</strong> Claude analyzes each garment using 
          the Fashionpedia taxonomy (294 attributes)
        </li>
        <li>
          <strong>Semantic Search:</strong> CLIP embeddings enable visual and 
          text-based similarity search
        </li>
        <li>
          <strong>Style Bridges:</strong> Our algorithm identifies design DNA 
          shared between historical and modern pieces
        </li>
      </ul>
      
      <h2>Data Sources</h2>
      <ul>
        <li>Metropolitan Museum of Art</li>
        <li>Smithsonian Institution</li>
        <li>Fashionpedia Dataset</li>
      </ul>
    </div>
  )
}
```

**Deliverable:** Complete, navigable frontend

---

## Week 3: Deploy + Integration Testing

**Focus:** Make it live and bulletproof.

### Monday-Tuesday (8-10 hours): Backend Deployment

**Deploy to Railway (or Render):**

1. Create `requirements.txt` with all dependencies
2. Create `Procfile` or `railway.json`:

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn api.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

3. Set environment variables:
    
    - `DATABASE_URL` (Railway Postgres)
    - `ANTHROPIC_API_KEY`
    - `QDRANT_URL` (if using Qdrant Cloud, else run in same container)
4. Deploy and verify health endpoint
    

**Database migration on production:**

- Run `init_db()` to create tables
- Import product data (if not using Railway's persistent storage)
- Verify Qdrant collections exist

**Test all endpoints with production data:**

```bash
curl https://your-api.railway.app/health
curl https://your-api.railway.app/api/v1/products/1
curl -X POST https://your-api.railway.app/api/v1/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "dark academia dress", "limit": 10}'
```

**Deliverable:** Live API serving data

---

### Wednesday-Thursday (8-10 hours): Frontend Deployment + Integration

**Deploy to Vercel:**

1. Connect GitHub repo
2. Set environment variable:
    - `NEXT_PUBLIC_API_URL=https://your-api.railway.app`
3. Deploy

**End-to-end testing:**

- Test text search from multiple queries
- Test image upload (compress working?)
- Navigate to product detail pages
- Verify bridge panels load
- Test on mobile device
- Check loading states
- Verify error handling

**Fix inevitable integration issues:**

- CORS problems
- Image loading errors
- API timeout handling
- Missing error boundaries

**Performance check:**

- Search response time < 2 seconds
- Bridge query response < 1 second
- Images loading properly
- No console errors

**Deliverable:** Live, working demo at vintagevestige.com

---

### Friday (6-8 hours): Content + QA

**Create sample searches document:** Write 10-15 example searches that work well:

- "romantic edwardian dress"
- "dark academia aesthetic"
- "empire waist gown"
- "art nouveau evening wear"
- "victorian bustle dress"

**Test each one, screenshot results**

**QA Checklist:**

- [ ] Homepage loads, CTAs work
- [ ] Text search returns results
- [ ] Image upload works (test 5 images)
- [ ] Product detail pages load
- [ ] Bridge panels show related items
- [ ] Bridge narratives display correctly
- [ ] Shared attributes badges show
- [ ] Navigation works across all pages
- [ ] Mobile responsive (test on phone)
- [ ] No console errors
- [ ] Images load properly
- [ ] Error states handled gracefully

**Fix any bugs found**

**Deliverable:** Polished, tested demo

---

## Week 4: Documentation + Launch Content

**Focus:** Tell the story. Showcase the innovation.

### Monday-Wednesday (12-15 hours): Comprehensive Blog Post

**Title: "Building a Fashion Knowledge Graph: How I Connected 500 Years of Design History"**

**Structure (3,000-4,000 words):**

**I. The Problem (500 words)**

- Museum catalogs use archival language
- Modern search uses contemporary terms
- The gap between historical and modern fashion
- Why semantic search alone isn't enough

**II. The Architecture Decision (800 words)**

- Why a knowledge graph, not just search
- The three-layer architecture (data → intelligence → products)
- Cross-source bridges as the moat
- Fashionpedia taxonomy harmonization

**III. Building the Enrichment Pipeline (600 words)**

- Claude API for fashion semantics
- 294 Fashionpedia attributes
- Creative-only vs. full enrichment paths
- Examples of enriched data

**IV. The Bridge Algorithm (1,000 words) - SHOWCASE THIS**

- Why bridges matter (the innovation)
- Structural similarity scoring
- Text + image + taxonomy composite
- Example bridge with narrative
- Code snippets showing the algorithm

**V. Technical Implementation (600 words)**

- FastAPI backend architecture
- Qdrant vector database setup
- Next.js frontend with bridge display
- Performance considerations

**VI. What Makes This Different (400 words)**

- Comparison to generic search engines
- The knowledge graph moat
- Style DNA API potential (Phase 2 preview)
- Trend Oracle vision (Phase 4 preview)

**VII. Lessons Learned (300 words)**

- Input quality > model quality (from MindCap)
- Documentation discipline with AI collaboration
- Product thinking before technical optimization
- When to ship vs. when to refine

**Include:**

- Architecture diagrams
- Bridge computation flowchart
- Screenshots of bridge panels
- Example bridge narrative with shared attributes
- Code snippets (bridge scoring algorithm)
- Demo GIFs (search → results → bridge display)

**This post demonstrates:**

- Technical depth (algorithm design)
- Innovation (bridge intelligence)
- Product thinking (knowledge graph vs. search)
- Full-stack capability (API + frontend)
- AI integration (Claude enrichment)
- Clear communication

**Deliverable:** Publication-ready blog post

---

### Thursday (4-5 hours): Case Study Format

**Create portfolio case study page:**

**Vintage Vestige: Fashion Knowledge Graph**

**Overview (100 words)**

- One-sentence description
- Key technologies
- Links to live demo, GitHub, blog post

**The Challenge (150 words)**

- Problem statement
- Why existing solutions fail
- User need identified

**The Solution (200 words)**

- Knowledge graph architecture
- Cross-source bridges (the innovation)
- AI enrichment pipeline
- Technical stack

**Key Features (bullet points)**

- Semantic search (text + image)
- Style bridges connecting historical → modern
- AI-generated bridge narratives
- 294-attribute fashion taxonomy
- 1,000+ enriched items across 3 sources

**Technical Highlights (300 words)**

- Bridge computation algorithm
- Structural similarity scoring
- Claude API integration
- CLIP embeddings
- FastAPI + Next.js architecture

**Results & Impact**

- Working demo with X searches
- Y bridge connections computed
- Live at vintagevestige.com
- Demonstrates AI product design capability

**Screenshots:**

- Search results page
- Product detail with bridge panels
- Bridge card showing narrative + shared attributes
- Mobile view

**Deliverable:** Portfolio case study page for linuxgrrrl.com

---

### Friday (4-5 hours): Prepare for Launch

**Final checklist:**

- [ ] Blog post drafted and edited
- [ ] Case study page created
- [ ] Demo fully tested
- [ ] Sample searches documented
- [ ] Screenshots and GIFs captured
- [ ] Social preview images created
- [ ] About page polished
- [ ] GitHub repo cleaned up (README, docs)
- [ ] LinkedIn profile updated with project
- [ ] Upwork profile updated

**Create launch assets:**

- Social preview image (1200×630)
- Demo GIF (search → results → bridge display)
- Architecture diagram (polished)
- One-sentence pitch perfected

**Deliverable:** Ready to launch Monday morning

---

## Week 5: Position + Outreach

**Focus:** Get this in front of people who can hire you.

### Monday: Launch + Distribution

**Publish blog post:**

- Post on linuxgrrrl.com
- Cross-post to Dev.to with tags:
    - #ai #machinelearning #webdev #fashion #productdesign

**Update all profiles:**

**LinkedIn:**

- Add Vintage Vestige to Projects
- Headline: "AI Product Designer | Built Vintage Vestige (fashion knowledge graph) & MindCap"
- Featured section: Blog post + live demo link

**Upwork:**

- Headline: "AI Product Designer | I build intelligent features with thoughtful UX"
- Portfolio: Add Vintage Vestige case study
- Lead with: "Recently built a fashion knowledge graph connecting 500 years of design history..."

**GitHub:**

- Pin Vintage Vestige repo
- Comprehensive README with:
    - Architecture overview
    - Bridge algorithm explanation
    - Setup instructions
    - Link to live demo and blog post

**Share strategically (low-anxiety version):**

- Email 5 friends/former colleagues: "I built something I'm proud of: [link]"
- No social media required
- Let the work speak

**Deliverable:** Project live and discoverable

---

### Tuesday-Friday: AI Product Designer Positioning

**Update positioning documents:**

- Resume highlighting Vintage Vestige
- Cover letter template referencing it
- Proposal templates showcasing it

**Submit 10 targeted Upwork proposals:**

Search for:

- "AI integration"
- "semantic search"
- "product design"
- "ML product"

**Proposal template:**

```
Hi [Client],

I saw your post about [their AI need]. This aligns with work I recently completed on Vintage Vestige, a fashion knowledge graph that connects items across 500 years using AI.

The core challenge was similar to yours: [parallel to their problem]. 

My approach:
- Used Claude API for domain-specific enrichment
- Built cross-source intelligence layer using structural similarity
- Designed UX that makes complex AI understandable
- Full-stack implementation (FastAPI + Next.js)

Here's the technical writeup: [blog post link]
Live demo: vintagevestige.com

For your project, I'd approach it by [2-3 sentences showing you understand their needs].

Questions:
- [Clarifying question 1]
- [Clarifying question 2]

Portfolio: linuxgrrrl.com

Looking forward to discussing!
```

**Direct outreach to 5 companies:**

- Find Forward Deployed Engineer roles
- Find hiring managers on LinkedIn
- Send 1-2 sentence intro + link to project

**Track:**

- Proposals sent
- Responses received
- Interviews scheduled
- Projects landed

**Goal:** Land first AI Product Designer project by end of Week 5

---

## Success Metrics

**Technical:**

- [ ] 5,000-10,000 bridge rows computed
- [ ] 1,500+ bridge narratives generated
- [ ] API response time < 2 seconds
- [ ] Frontend fully functional on mobile
- [ ] Zero console errors in production

**Portfolio:**

- [ ] Live demo at public URL
- [ ] Comprehensive blog post (3,000+ words)
- [ ] Case study on portfolio site
- [ ] GitHub repo with documentation
- [ ] Updated LinkedIn + Upwork profiles

**Business:**

- [ ] 10 Upwork proposals sent
- [ ] 5 direct outreach messages sent
- [ ] 1+ interview scheduled
- [ ] Clear positioning as AI Product Designer

**Innovation Showcase:**

- [ ] Bridge algorithm clearly explained
- [ ] Visual demonstration of style bridges
- [ ] Blog post emphasizes the knowledge graph moat
- [ ] Case study highlights product thinking

---

## Cost Breakdown

|Item|Cost|
|---|---|
|Claude API (narrative generation)|~$5|
|Railway backend hosting|$5/mo|
|Vercel frontend hosting|$0 (free tier)|
|Domain (if new)|$15/year|
|**Total to launch**|**~$10-15**|

---

## What Makes This Plan Work

**1. Builds the actual moat first** (bridges = defensibility)

**2. Showcases innovation clearly** (blog post focuses on bridge intelligence)

**3. Creates multiple portfolio artifacts:**

- Live demo
- Technical blog post
- Case study
- GitHub repo

**4. Positions for AI Product Designer** (design + implementation + communication)

**5. Manageable scope** (21-32 hours for bridges, realistic timeline)

**6. Low-anxiety distribution** (no public posting required, strategic 1-1 outreach)

---

## When Things Go Wrong

**If bridges take longer than expected:**

- Ship without narratives first (bridges still valuable)
- Add narratives as v1.1

**If deployment issues:**

- Deploy backend only
- Test with curl, frontend later
- Don't block on hosting problems

**If you get stuck:**

- Focus on one week at a time
- Week 1 backend is highest priority
- Frontend can compress if needed

**If anxiety blocks Week 5 outreach:**

- Just update profiles and publish post
- Outreach can happen Week 6-7
- The work existing is more important than immediate promotion

---

**Ready to start?**

Tell me when you want to begin Week 1, and I'll be here to help debug, review code, make decisions, and keep you moving forward.

This is the portfolio piece that demonstrates you can build innovative AI products. Let's ship it.