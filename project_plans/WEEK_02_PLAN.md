# Week 2: Backend API & Search Engine
**Vintage Vestige Build Plan**

**Dates:** Week 2 of build  
**Focus:** Build FastAPI backend and deploy to production  
**Time Commitment:** 40 hours (full-time)  
**Budget:** $10-15 (Railway hosting + continued scraping)

---

## 🎯 Week 2 Mission

**Ship a production API that powers AI search.**

By Sunday night, you'll have a deployed REST API that anyone can call to search 5,000 vintage products. This API will power both your consumer app and seller tools.

---

## 📋 Daily Breakdown

### Monday: FastAPI Project Setup (6-8 hours)

**Morning: Project Structure**

- [ ] Create API directory structure:
```bash
cd vintage-vestige
mkdir api
cd api
mkdir endpoints models schemas utils
touch main.py config.py __init__.py
```

- [ ] Create `api/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Vintage Vestige API",
    description="AI-powered vintage fashion search",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Vintage Vestige API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] Test locally:
```bash
python api/main.py
# Visit http://localhost:8000
# Visit http://localhost:8000/docs (auto-generated API docs!)
```

**Afternoon: Search Endpoints**

- [ ] Create `api/endpoints/search.py`:
```python
from fastapi import APIRouter, File, UploadFile, Query
from typing import Optional, List
import numpy as np
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["search"])

class SearchResult(BaseModel):
    id: str
    title: str
    price: float
    platform: str
    url: str
    primary_image: str
    era: Optional[str]
    style_tags: Optional[List[str]]
    score: float

@router.get("/text", response_model=List[SearchResult])
async def search_text(
    q: str = Query(..., description="Search query"),
    era: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = 20
):
    """Search by text query"""
    
    # Import here to avoid circular imports
    from embeddings.generator import EmbeddingGenerator
    from storage.vector_db import VectorDB
    from storage.database import SessionLocal, Product
    
    # Generate query embedding
    generator = EmbeddingGenerator()
    query_vector = generator.generate_text_embedding(q)
    
    # Search Qdrant
    vector_db = VectorDB()
    results = vector_db.search_similar(
        collection='vintage_text',
        query_vector=query_vector,
        limit=limit * 2  # Get more, then filter
    )
    
    # Apply filters
    filtered = []
    for r in results:
        # Price filter
        if price_min and r['price'] < price_min:
            continue
        if price_max and r['price'] > price_max:
            continue
        # Era filter  
        if era and r.get('era') != era:
            continue
            
        filtered.append(SearchResult(**r, score=r['_score']))
        
        if len(filtered) >= limit:
            break
    
    return filtered

@router.post("/image", response_model=List[SearchResult])
async def search_image(
    image: UploadFile = File(...),
    limit: int = 20
):
    """Search by uploaded image"""
    
    import tempfile
    from PIL import Image
    from embeddings.generator import EmbeddingGenerator
    from storage.vector_db import VectorDB
    
    # Save uploaded image temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        content = await image.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Generate embedding
    generator = EmbeddingGenerator()
    query_vector = generator.generate_image_embedding(tmp_path)
    
    # Search
    vector_db = VectorDB()
    results = vector_db.search_similar(
        collection='vintage_images',
        query_vector=query_vector,
        limit=limit
    )
    
    return [SearchResult(**r, score=r['_score']) for r in results]

@router.get("/hybrid", response_model=List[SearchResult])
async def search_hybrid(
    q: Optional[str] = None,
    image_url: Optional[str] = None,
    era: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    limit: int = 20
):
    """Hybrid search: combine text and image"""
    
    from embeddings.generator import EmbeddingGenerator
    from storage.vector_db import VectorDB
    
    generator = EmbeddingGenerator()
    vector_db = VectorDB()
    
    results = []
    
    # Text search
    if q:
        text_vector = generator.generate_text_embedding(q)
        text_results = vector_db.search_similar(
            collection='vintage_text',
            query_vector=text_vector,
            limit=limit
        )
        results.extend(text_results)
    
    # Image search
    if image_url:
        image_vector = generator.generate_image_embedding(image_url)
        image_results = vector_db.search_similar(
            collection='vintage_images',
            query_vector=image_vector,
            limit=limit
        )
        results.extend(image_results)
    
    # Merge and deduplicate
    seen = set()
    merged = []
    for r in results:
        if r['id'] not in seen:
            seen.add(r['id'])
            merged.append(r)
    
    # Re-rank by combined score
    merged.sort(key=lambda x: x['_score'], reverse=True)
    
    return [SearchResult(**r, score=r['_score']) for r in merged[:limit]]
```

- [ ] Add to main.py:
```python
from api.endpoints import search

app.include_router(search.router)
```

- [ ] Test endpoints:
```bash
# Start server
python api/main.py

# In another terminal, test:
curl "http://localhost:8000/search/text?q=grunge+flannel"
```

**End of Day Goal:**
✅ FastAPI server running  
✅ Search endpoints working  
✅ Can search by text, image, or both  
✅ Auto-generated docs at /docs

---

### Tuesday: Product Endpoints & Optimization (6-8 hours)

**Morning: Product Detail Endpoint**

- [ ] Create `api/endpoints/products.py`:
```python
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"])

class ProductDetail(BaseModel):
    id: str
    title: str
    description: Optional[str]
    price: float
    platform: str
    url: str
    images: List[str]
    primary_image: str
    era: Optional[str]
    style_tags: Optional[List[str]]
    category: Optional[str]
    colors: Optional[List[str]]
    materials: Optional[List[str]]
    ai_description: Optional[str]

@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: str):
    """Get product details by ID"""
    
    from storage.database import SessionLocal, Product
    
    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductDetail(
        id=str(product.id),
        title=product.title,
        description=product.description,
        price=product.price,
        platform=product.platform,
        url=product.url,
        images=product.images,
        primary_image=product.primary_image,
        era=product.era,
        style_tags=product.style_tags,
        category=product.category,
        colors=product.colors,
        materials=product.materials,
        ai_description=product.ai_description
    )

@router.get("/{product_id}/similar", response_model=List[SearchResult])
async def get_similar_products(product_id: str, limit: int = 10):
    """Find similar products"""
    
    from storage.database import SessionLocal, Product
    from storage.vector_db import VectorDB
    
    db = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get product's embedding from Qdrant
    vector_db = VectorDB()
    point = vector_db.qdrant.retrieve(
        collection_name='vintage_images',
        ids=[product_id]
    )[0]
    
    # Search for similar
    results = vector_db.search_similar(
        collection='vintage_images',
        query_vector=point.vector,
        limit=limit + 1  # +1 because result includes itself
    )
    
    # Remove the product itself
    results = [r for r in results if r['id'] != product_id]
    
    return results[:limit]
```

- [ ] Add to main.py:
```python
from api.endpoints import products

app.include_router(products.router)
```

**Afternoon: Performance Optimization**

- [ ] Add caching with Redis (optional but recommended):
```python
# In api/main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost:6379")
    FastAPICache.init(RedisBackend(redis), prefix="vintage-cache")

# In search.py, add caching:
from fastapi_cache.decorator import cache

@router.get("/text")
@cache(expire=3600)  # Cache for 1 hour
async def search_text(...):
    ...
```

- [ ] Add request validation and error handling:
```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal server error: {str(exc)}"}
    )
```

- [ ] Add rate limiting (optional):
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.get("/text")
@limiter.limit("100/minute")  # 100 requests per minute
async def search_text(request: Request, ...):
    ...
```

- [ ] Performance testing:
```bash
# Install wrk
brew install wrk

# Test search endpoint
wrk -t4 -c100 -d30s http://localhost:8000/search/text?q=vintage
```

**Goal:** < 1 second average response time

**End of Day Goal:**
✅ Product detail endpoint working  
✅ Similar products endpoint working  
✅ Caching implemented (optional)  
✅ Error handling robust  
✅ API responds in < 1 second

---

### Wednesday: Deployment Preparation (6-8 hours)

**Morning: Production Database Setup**

- [ ] Sign up for Railway: https://railway.app
- [ ] Create new project: "Vintage Vestige"
- [ ] Add PostgreSQL service:
  - Click "New"
  - Select "Database"
  - Choose "PostgreSQL"
  - Wait for provisioning (~2 min)

- [ ] Get connection string:
  - Click on PostgreSQL service
  - Go to "Connect" tab
  - Copy "Postgres Connection URL"

- [ ] Migrate data to production:
```bash
# Export from local
pg_dump vintage_vestige > local_backup.sql

# Import to Railway (replace with your Railway DB URL)
psql postgresql://user:pass@host:port/railway < local_backup.sql
```

**Afternoon: Qdrant Cloud Setup**

- [ ] Sign up for Qdrant Cloud: https://cloud.qdrant.io
- [ ] Create cluster:
  - Free tier: 1GB storage
  - Select region closest to you
  - Wait for provisioning (~5 min)

- [ ] Get API credentials:
  - Click on cluster
  - Copy "Cluster URL" and "API Key"

- [ ] Migrate vectors to cloud:
```python
from qdrant_client import QdrantClient

# Local client
local = QdrantClient(host="localhost", port=6333)

# Cloud client
cloud = QdrantClient(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key"
)

# Get collections
collections = ['vintage_images', 'vintage_text', 'vintage_enriched']

for collection in collections:
    # Get all points from local
    points = local.scroll(
        collection_name=collection,
        limit=10000
    )[0]
    
    # Upload to cloud
    cloud.upsert(
        collection_name=collection,
        points=points
    )
    
    print(f"Migrated {len(points)} points to {collection}")
```

**Evening: Environment Configuration**

- [ ] Create `.env.production`:
```env
DATABASE_URL=postgresql://user:pass@railway.host:port/railway
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
ANTHROPIC_API_KEY=sk-ant-your-key
ENVIRONMENT=production
```

- [ ] Update `config.py` to read from environment:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    qdrant_url: str
    qdrant_api_key: str
    anthropic_api_key: str
    environment: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] Create `Procfile` for deployment:
```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

- [ ] Create `requirements.txt` for production:
```
# Add to existing requirements.txt
gunicorn==21.2.0
psycopg2-binary==2.9.9
```

**End of Day Goal:**
✅ Production database created and migrated  
✅ Qdrant Cloud set up and migrated  
✅ Environment variables configured  
✅ Deployment files ready

---

### Thursday: Deploy to Production (6-8 hours)

**Morning: Railway Deployment**

- [ ] In Railway project, add new service:
  - Click "New"
  - Select "GitHub Repo" (or "Empty Service")
  - Choose "Deploy from GitHub"

- [ ] Connect GitHub (if using):
  - Create GitHub repo for vintage-vestige
  - Push code: 
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/vintage-vestige.git
git push -u origin main
```

- [ ] Configure Railway service:
  - Set root directory: `/`
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

- [ ] Add environment variables in Railway:
  - Go to service > Variables tab
  - Add each variable from `.env.production`

- [ ] Deploy:
  - Railway auto-deploys on push
  - Watch logs for errors
  - Wait for "Deployed" status

- [ ] Get public URL:
  - Railway provides: `https://vintage-vestige-production.up.railway.app`
  - Test: `curl https://your-url.railway.app/health`

**Afternoon: Testing Production API**

- [ ] Test all endpoints:
```bash
# Health check
curl https://your-api-url/health

# Text search
curl "https://your-api-url/search/text?q=vintage+dress"

# Get product
curl https://your-api-url/products/{some-product-id}
```

- [ ] Load testing:
```bash
wrk -t4 -c50 -d30s "https://your-api-url/search/text?q=vintage"
```

**Goal:** Handle 50 concurrent users, < 2 second response

- [ ] Monitor errors in Railway logs
- [ ] Fix any deployment issues

**Evening: Documentation & API Keys**

- [ ] Create API documentation at `/docs`
  - Already auto-generated by FastAPI!
  - Visit: `https://your-api-url/docs`

- [ ] Create simple landing page for API:
```python
# In api/main.py
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vintage Vestige API</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 50px auto; }
            code { background: #f4f4f4; padding: 2px 6px; }
        </style>
    </head>
    <body>
        <h1>🔍 Vintage Vestige API</h1>
        <p>AI-powered vintage fashion search</p>
        
        <h2>Endpoints:</h2>
        <ul>
            <li><code>GET /search/text?q=vintage+dress</code></li>
            <li><code>POST /search/image</code></li>
            <li><code>GET /products/{id}</code></li>
        </ul>
        
        <p><a href="/docs">📖 Full API Documentation</a></p>
    </body>
    </html>
    """
```

**End of Day Goal:**
✅ API deployed to production  
✅ Public URL accessible  
✅ All endpoints working  
✅ < 2 second response time  
✅ Auto-generated docs available

---

### Friday: Continue Scraping & Scaling (6-8 hours)

**Morning: Expand to 5,000 Products**

- [ ] Add more search queries (30 total):
```python
queries = [
    # 70s
    'vintage 70s dress', 'prairie dress', 'gunne sax',
    '70s maxi dress', 'bohemian 1970s', 'vintage crochet',
    
    # 80s
    'vintage 80s dress', '80s power suit', 'vintage blazer 80s',
    '80s sequin', 'vintage 80s jacket', 'retro 80s',
    
    # 90s
    'grunge flannel', '90s slip dress', 'vintage 90s denim',
    '90s minimalist', 'vintage band tee 90s', '90s clubkid',
    
    # Y2K
    'y2k baby tee', 'y2k dress', '2000s vintage',
    'y2k denim', 'early 2000s top', 'y2k going out',
    
    # General categories
    'vintage leather jacket', 'vintage denim jacket',
    'vintage maxi dress', 'vintage blazer', 'vintage coat',
    'vintage accessories', 'vintage bag', 'vintage jewelry'
]
```

- [ ] Run scraping pipeline:
```python
from pipeline import VintagePipeline

pipeline = VintagePipeline()
pipeline.run(
    platforms=['depop'],
    queries=queries,
    max_products_per_query=100
)
```

**This will take 3-4 hours** - run and monitor

**Afternoon: Etsy Scraper (Optional)**

- [ ] Build Etsy scraper:
```python
# scrapers/etsy.py
from .base import BaseScraper
import requests
from bs4 import BeautifulSoup

class EtsyScraper(BaseScraper):
    def __init__(self):
        super().__init__("etsy")
        self.base_url = "https://www.etsy.com"
    
    def scrape_search_page(self, query, page=1):
        url = f"{self.base_url}/search?q={query}&page={page}"
        
        soup = self._get_with_retry(url)
        products = []
        
        # Parse Etsy's HTML structure
        for item in soup.select('.v2-listing-card'):
            try:
                title = item.select_one('.v2-listing-card__title').text.strip()
                price = item.select_one('.currency-value').text.strip()
                link = item.select_one('a')['href']
                image = item.select_one('img')['src']
                
                products.append(self._normalize_product({
                    'title': title,
                    'price': float(price),
                    'url': link if link.startswith('http') else f"{self.base_url}{link}",
                    'primary_image': image,
                    'images': [image],
                    'description': None  # Need to scrape individual pages for this
                }))
            except Exception as e:
                print(f"Error parsing Etsy item: {e}")
                continue
        
        return products
```

- [ ] Test Etsy scraper:
```python
from scrapers.etsy import EtsyScraper

scraper = EtsyScraper()
products = scraper.scrape_search_page("vintage dress", page=1)
print(f"Found {len(products)} Etsy products")
```

- [ ] Add to pipeline:
```python
pipeline.run(
    platforms=['depop', 'etsy'],  # Both!
    queries=queries,
    max_products_per_query=50  # Split between platforms
)
```

**Evening: Quality Check**

- [ ] Verify 5,000 products:
```sql
psql $DATABASE_URL

SELECT COUNT(*) FROM products;  -- Should be ~5,000
SELECT platform, COUNT(*) FROM products GROUP BY platform;
SELECT era, COUNT(*) FROM products WHERE era IS NOT NULL GROUP BY era;
```

- [ ] Test search quality with production API:
```bash
# Try 20 different searches
curl "https://your-api-url/search/text?q=grunge+flannel&limit=10"
curl "https://your-api-url/search/text?q=prairie+dress&era=1970s"
curl "https://your-api-url/search/text?q=y2k+baby+tee&price_max=50"
```

- [ ] Manually review results:
  - Are they relevant?
  - Are filters working?
  - Is ranking good?

**End of Day Goal:**
✅ 5,000+ products in production database  
✅ Etsy scraper working (optional)  
✅ Search quality validated  
✅ API handling traffic well

---

### Weekend: Optimization & Preparation for Week 3 (8-10 hours)

**Saturday: Search Quality Improvements**

- [ ] Implement better ranking algorithm:
```python
# In search.py
def rerank_results(results, query):
    """Re-rank results by multiple factors"""
    
    for r in results:
        score = r['_score']  # Base similarity score
        
        # Boost recent listings
        days_old = (datetime.now() - r['scraped_at']).days
        recency_boost = 1.0 - (days_old / 365) * 0.2
        
        # Boost if title matches query
        if query.lower() in r['title'].lower():
            score *= 1.3
        
        # Boost AI-enriched items
        if r.get('era'):
            score *= 1.1
        
        # Apply boosts
        r['final_score'] = score * recency_boost
    
    # Re-sort by final score
    results.sort(key=lambda x: x['final_score'], reverse=True)
    return results
```

- [ ] Add search analytics:
```python
# Track what people search for
@router.get("/text")
async def search_text(...):
    # Log search query
    log_search_query(q, user_id=None, results_count=len(results))
    
    return results

def log_search_query(query, user_id, results_count):
    """Save to database for analytics"""
    # Later: use this to improve search, find trending items
    pass
```

- [ ] Test improvements:
  - Run same 20 queries as Friday
  - Compare results before/after
  - Document improvements

**Sunday: Documentation & Week 3 Prep**

- [ ] Write API README:
```markdown
# Vintage Vestige API

## Base URL
https://vintage-vestige-api.railway.app

## Endpoints

### Search by Text
GET /search/text?q={query}&era={era}&price_min={min}&price_max={max}

Example:
GET /search/text?q=grunge+flannel&era=1990s&price_max=100

### Search by Image
POST /search/image
Content-Type: multipart/form-data

Body: image file

### Get Product Details
GET /products/{id}

### Find Similar Products
GET /products/{id}/similar

## Rate Limits
100 requests per minute

## Response Format
{
  "id": "uuid",
  "title": "string",
  "price": 89.99,
  "platform": "depop",
  "url": "https://...",
  "primary_image": "https://...",
  "era": "1990s",
  "style_tags": ["grunge", "flannel"],
  "score": 0.87
}
```

- [ ] Create `WEEK_2_RETROSPECTIVE.md`:
```markdown
# Week 2 Retrospective

## What Shipped
- FastAPI backend with search endpoints
- Deployed to Railway
- 5,000 products in production
- < 1 second search response time

## Metrics
- Products: 5,012
- API uptime: 99.8%
- Average search time: 750ms
- Platforms: Depop (4,200), Etsy (812)

## What Worked
- Railway deployment was smooth
- Qdrant Cloud migration easy
- FastAPI auto-docs are amazing

## What Didn't Work
- Etsy scraper hit rate limits
- Some image URLs 404'd
- Need better error handling

## Learnings
- Vector search at scale
- API design patterns
- Cloud deployment

## Next Week
- Build Next.js frontend
- Connect to this API
- Launch to public
```

- [ ] Plan Week 3 frontend work:
  - [ ] Sketch homepage design on paper
  - [ ] List components needed
  - [ ] Plan color scheme (cream, terracotta, olive)
  - [ ] Prepare vintage inspiration images

- [ ] Backup everything:
```bash
# Database
pg_dump $DATABASE_URL > production_backup_week2.sql

# Code
git add .
git commit -m "Week 2 complete: API deployed"
git push
```

**End of Weekend Goal:**
✅ Search quality improved  
✅ Documentation complete  
✅ Week 2 retrospective written  
✅ Week 3 planned  
✅ Everything backed up

---

## 📊 Week 2 Success Metrics

**Infrastructure:**
- [x] FastAPI backend deployed to production
- [x] PostgreSQL on Railway
- [x] Qdrant on Cloud
- [x] Public API accessible

**Data:**
- [x] 5,000+ products in database
- [x] All products have embeddings
- [x] Multiple platforms (Depop + Etsy)

**Performance:**
- [x] API responds in < 1 second (average)
- [x] Handles 50+ concurrent requests
- [x] 99%+ uptime
- [x] Search accuracy 70%+ (subjective)

**Code Quality:**
- [x] Clean endpoint structure
- [x] Error handling implemented
- [x] Auto-generated documentation
- [x] Production-ready configuration

---

## 💰 Week 2 Budget

**Actual Costs:**
- Railway (database + API hosting): $5/month
- Qdrant Cloud: $0 (free tier)
- Domain (already paid): $0
- Claude API (continued enrichment): $5-10
- **Total: $10-15/month**

---

## 🎓 What You Learned This Week

**Technical Skills:**
- FastAPI framework (routing, validation, docs)
- RESTful API design
- Cloud deployment (Railway)
- Database migration
- Production configuration
- API performance optimization
- Rate limiting and caching

**Conceptual:**
- API-first architecture
- Separation of concerns (API vs frontend)
- Production vs development environments
- Monitoring and logging
- API documentation best practices

**This is backend engineering.** Real production systems.

---

## 🚨 Common Issues & Solutions

### "Railway deployment failed"
**Solution:** Check logs in Railway dashboard. Common issues:
- Missing environment variables
- Wrong Python version (add `runtime.txt`)
- Dependency conflicts (pin versions in requirements.txt)

### "API returns 500 errors"
**Solution:** 
```python
# Add better error logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check Railway logs for stack traces
```

### "Qdrant connection timeout"
**Solution:** Check API key and URL in environment variables. Verify Qdrant cluster is running.

### "Database connection pool exhausted"
**Solution:** Increase pool size:
```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=10
)
```

### "Search is slow (>2 seconds)"
**Solution:**
- Add indexes to database
- Implement caching (Redis)
- Reduce Qdrant search limit
- Optimize re-ranking algorithm

---

## 💪 Motivation & Mindset

### When Deployment Fails:
> "Every developer struggles with deployment. You're not alone. Debug, fix, try again."

Railway logs are your friend. Read them carefully.

### When API Feels "Done":
> "An API is never done. You'll improve it forever. Ship now, iterate later."

Week 3 needs a working API, not a perfect one.

### When You Compare to Big Companies:
> "Google's first API was worse than this. Facebook's first API was worse. You're doing great."

Your API works. That's what matters.

### When Search Quality Isn't Perfect:
> "70% accuracy beats 0% accuracy. Ship it and improve it with real user feedback."

Perfect is the enemy of good.

### End of Week Reflection:
> "I have a deployed API serving AI-powered search to the world. That's incredible."

**Be proud. You built a production system in one week.**

---

## 📝 End of Week 2 Checklist

**Infrastructure:**
- [ ] API deployed to Railway
- [ ] Database on Railway
- [ ] Qdrant on Cloud
- [ ] All services healthy

**Endpoints:**
- [ ] `/search/text` working
- [ ] `/search/image` working
- [ ] `/search/hybrid` working
- [ ] `/products/{id}` working
- [ ] `/products/{id}/similar` working

**Performance:**
- [ ] < 1 second average response
- [ ] Handles 50+ concurrent users
- [ ] No critical errors in logs

**Data:**
- [ ] 5,000+ products
- [ ] Multiple platforms
- [ ] All embeddings generated

**Documentation:**
- [ ] README written
- [ ] API docs at /docs
- [ ] Week 2 retrospective complete

**Backup:**
- [ ] Database backed up
- [ ] Code pushed to GitHub
- [ ] Environment variables documented

---

## 🎉 Celebration Time

**What you built this week:**
- 🚀 Production API deployed to the cloud
- 🔍 AI-powered search accessible to anyone
- 📊 5,000 searchable vintage products
- ⚡ Sub-second response times
- 📖 Auto-generated API documentation

**What this means:**
- Anyone can now search vintage fashion with AI
- You have a working backend for your product
- You understand production deployments
- You're a full-stack developer now

**You did this in ONE WEEK.**

---

## 📌 Week 3 Preview

**Next week you'll:**
- Build Next.js frontend
- Create beautiful search interface
- Connect to your API
- Launch vintagevestige.com publicly
- Get your first 100 users

**By end of Week 3:**
Real people will be using your product.

**You're halfway to launch.** 🚀

---

**Week 2 Status: COMPLETE ✅**

*Rest this weekend. Monday you build the thing people will actually see.* 💪
