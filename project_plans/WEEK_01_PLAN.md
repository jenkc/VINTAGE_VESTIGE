# Week 1: Core Infrastructure Setup
**Vintage Vestige Build Plan**

**Dates:** Week of December 30, 2024  
**Focus:** Get the scraping, embedding, and storage pipeline working  
**Time Commitment:** 40 hours (full-time)  
**Budget:** $15-30 (Claude API usage)

---

## 🎯 Week 1 Mission

**Build the AI engine that powers everything.**

By Sunday night, you'll have 2,000 vintage products searchable by AI similarity. That's the foundation for both your consumer product AND seller tools.

---

## 📋 Daily Breakdown

### Monday: Environment Setup (4-5 hours)

**Morning Tasks:**
- [x] Domain purchased ✅ (vintagevestige.com - DONE!)
- [ ] Install PostgreSQL
  - Mac: `brew install postgresql@14`
  - Start: `brew services start postgresql@14`
- [ ] Install Docker Desktop
- [ ] Start Qdrant: `docker run -d -p 6333:6333 qdrant/qdrant`
- [ ] Verify both running:
  - `psql --version` (should show PostgreSQL 14.x)
  - Visit http://localhost:6333/dashboard (Qdrant UI)

**Afternoon Tasks:**
- [ ] Create project structure:
```bash
mkdir vintage-vestige
cd vintage-vestige
mkdir scrapers embeddings storage enrichment tests data
touch config.py requirements.txt .env .gitignore
```

- [ ] Create requirements.txt:
```txt
requests==2.31.0
beautifulsoup4==4.12.2
sentence-transformers==2.2.2
torch==2.1.0
pillow==10.1.0
qdrant-client==1.7.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
anthropic==0.8.1
python-dotenv==1.0.0
pydantic==2.5.0
tenacity==8.2.3
tqdm==4.66.1
fastapi==0.104.1
uvicorn==0.24.0
```

- [ ] Set up virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

**End of Day Goal:** 
✅ All tools installed and running  
✅ Project structure created  
✅ Dependencies installed

**Common Issues:**
- PostgreSQL won't start → Check if another instance is running
- Qdrant port conflict → Use different port: `docker run -p 6334:6333`
- Pip install fails → Update pip: `pip install --upgrade pip`

---

### Tuesday: Database & First Scrape (5-6 hours)

**Morning: Database Setup**

- [ ] Create `.env` file:
```env
DATABASE_URL=postgresql://localhost/vintage_vestige
ANTHROPIC_API_KEY=sk-ant-your-key-here
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

- [ ] Create `storage/database.py` (copy from project plan)
- [ ] Initialize database:
```bash
createdb vintage_vestige
python -c "from storage.database import init_db; init_db()"
```

- [ ] Verify tables created:
```bash
psql vintage_vestige
\dt  # Should show 'products' table
\d products  # Should show all columns
\q
```

**Afternoon: First Scrape**

- [ ] Create `scrapers/base.py` (copy from plan)
- [ ] Create `scrapers/depop.py` (copy from plan)
- [ ] Test with 10 products:
```python
from scrapers.depop import DepopScraper

scraper = DepopScraper()
products = scraper.scrape_search_page("vintage dress", page=1)
print(f"Found {len(products)} products")
print(products[0])  # Verify structure
```

- [ ] Store in database:
```python
from storage.database import SessionLocal, Product

db = SessionLocal()
for product_data in products[:10]:
    product = Product(**product_data)
    db.add(product)
db.commit()
```

- [ ] Verify in database:
```bash
psql vintage_vestige -c "SELECT id, title, price FROM products LIMIT 5;"
```

**End of Day Goal:**
✅ Database created with products table  
✅ 10 test products scraped and stored  
✅ Pipeline works end-to-end

**Troubleshooting:**
- Database connection errors → Check DATABASE_URL in .env
- Scraper returns empty list → Depop may have changed structure
- Products not saving → Check for unique constraint violations

---

### Wednesday: Embedding Generation (6-7 hours)

**Morning: Model Setup**

- [ ] Create `embeddings/models.py` (copy from plan)
- [ ] Create `embeddings/generator.py` (copy from plan)
- [ ] Test model loading:
```python
from embeddings.models import models

# This will download models (~500MB total, takes 5-10 min)
print(f"CLIP model loaded: {models.clip}")
print(f"Text model loaded: {models.text}")
```

**What's happening:** First time loading downloads models to `~/.cache/torch/`. Future loads are instant.

**Afternoon: Generate First Embeddings**

- [ ] Test with one product:
```python
from storage.database import SessionLocal, Product
from embeddings.generator import EmbeddingGenerator

db = SessionLocal()
product = db.query(Product).first()

generator = EmbeddingGenerator()
embeddings = generator.generate_product_embeddings({
    'primary_image': product.primary_image,
    'title': product.title,
    'description': product.description
})

print(f"Image embedding shape: {embeddings['image_embedding'].shape}")
print(f"Text embedding shape: {embeddings['text_embedding'].shape}")
```

**Expected output:**
```
Image embedding shape: (512,)
Text embedding shape: (384,)
```

- [ ] Create `storage/vector_db.py` (copy from plan)
- [ ] Store embeddings in Qdrant:
```python
from storage.vector_db import VectorDB

vector_db = VectorDB()
vector_db.upsert_product(
    product_id=str(product.id),
    embeddings=embeddings,
    metadata={
        'title': product.title,
        'price': product.price,
        'platform': product.platform,
        'url': product.url,
        'primary_image': product.primary_image
    }
)
```

- [ ] Verify in Qdrant dashboard: http://localhost:6333/dashboard

**End of Day Goal:**
✅ Models loaded successfully  
✅ Can generate embeddings from images and text  
✅ Embeddings stored in Qdrant  
✅ Can view vectors in dashboard

**Performance Notes:**
- First embedding generation: ~5 seconds (model loading)
- Subsequent: ~1-2 seconds per product
- Image download is usually the slowest part

---

### Thursday: Scale to 500 Products (6-8 hours)

**Morning: Pipeline Integration**

- [ ] Create `pipeline.py` (copy from plan)
- [ ] Test with 50 products:
```python
from pipeline import VintagePipeline

pipeline = VintagePipeline()
pipeline.run(
    platforms=['depop'],
    queries=['vintage dress'],
    max_products_per_query=50
)
```

**Watch for:**
- Progress bar showing products processed
- Any errors logged to console
- Database growing (check with `SELECT COUNT(*) FROM products;`)

**Afternoon: Full Scrape**

- [ ] Define 5 search queries:
```python
queries = [
    'vintage dress 70s',
    'grunge flannel 90s', 
    'y2k baby tee',
    'prairie dress',
    'vintage denim jacket'
]
```

- [ ] Run full pipeline (100 products per query = 500 total):
```python
pipeline.run(
    platforms=['depop'],
    queries=queries,
    max_products_per_query=100
)
```

**This will take 2-4 hours** (scraping is slow, be patient)

- [ ] Monitor progress:
```bash
# In another terminal, watch database grow:
watch -n 30 'psql vintage_vestige -c "SELECT COUNT(*) FROM products;"'
```

**Evening: Verify Results**

- [ ] Check database:
```sql
psql vintage_vestige

SELECT COUNT(*) FROM products;  -- Should be ~500
SELECT COUNT(*) FROM products WHERE embedded_at IS NOT NULL;  -- Should match
SELECT era, COUNT(*) FROM products GROUP BY era;  -- See distribution
```

- [ ] Test similarity search:
```python
from embeddings.generator import EmbeddingGenerator
from storage.vector_db import VectorDB

generator = EmbeddingGenerator()
vector_db = VectorDB()

# Upload a test image URL
test_image = "https://i.etsystatic.com/..." 
query_vector = generator.generate_image_embedding(test_image)

# Find similar
results = vector_db.search_similar(
    collection='vintage_images',
    query_vector=query_vector,
    limit=10
)

for r in results:
    print(f"{r['title']} - Score: {r['score']:.3f}")
```

**End of Day Goal:**
✅ 500 products in database  
✅ All have embeddings in Qdrant  
✅ Similarity search returns relevant results  
✅ No major errors in pipeline

**Expected Issues:**
- Some images 404 (that's ok, skip them)
- Duplicate products (check external_id before inserting)
- Qdrant collection not found (auto-created on first upsert)

---

### Friday: Claude Integration & Quality Testing (6-8 hours)

**Morning: Claude Setup**

- [ ] Create `enrichment/claude.py`:
```python
import anthropic
import requests
import base64
import json
from config import settings

def enrich_vintage_item(image_url, title, description):
    """Use Claude to classify vintage item"""
    
    # Download image
    response = requests.get(image_url)
    image_data = base64.b64encode(response.content).decode('utf-8')
    
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    prompt = f"""Analyze this vintage fashion item.

Title: {title}
Description: {description}

Provide structured metadata as JSON:
{{
  "era": "1970s",  // Specific decade
  "style_tags": ["bohemian", "prairie"],  // 3-5 style descriptors
  "category": "dress",  // dress, jacket, jeans, etc
  "vibe": "Romantic bohemian prairie aesthetic",  // 1-2 sentences
  "colors": ["brown", "cream"],
  "materials": ["cotton"],
  "condition": "excellent",  // mint, excellent, good, fair
  "rich_description": "Full detailed description..."
}}

Return ONLY the JSON, no other text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]
    )
    
    # Parse JSON response
    response_text = message.content[0].text
    if response_text.startswith("```json"):
        response_text = response_text.split("```json")[1].split("```")[0]
    
    return json.loads(response_text.strip())
```

- [ ] Test with one product:
```python
from storage.database import SessionLocal, Product
from enrichment.claude import enrich_vintage_item

db = SessionLocal()
product = db.query(Product).first()

result = enrich_vintage_item(
    product.primary_image,
    product.title,
    product.description
)

print(json.dumps(result, indent=2))
```

**Expected output:**
```json
{
  "era": "1970s",
  "style_tags": ["bohemian", "prairie", "floral"],
  "category": "dress",
  "vibe": "Romantic 70s prairie dress with feminine details",
  "colors": ["brown", "cream", "floral"],
  "materials": ["cotton"],
  "condition": "excellent",
  "rich_description": "Beautiful 1970s prairie dress..."
}
```

**Afternoon: Batch Enrichment**

- [ ] Enrich 50 products:
```python
from tqdm import tqdm

db = SessionLocal()
products = db.query(Product).filter(Product.enriched_at == None).limit(50).all()

for product in tqdm(products, desc="Enriching"):
    try:
        result = enrich_vintage_item(
            product.primary_image,
            product.title,
            product.description or ""
        )
        
        # Update database
        product.era = result['era']
        product.style_tags = result['style_tags']
        product.category = result['category']
        product.ai_description = result['rich_description']
        product.colors = result['colors']
        product.materials = result['materials']
        product.condition = result.get('condition')
        product.enriched_at = datetime.utcnow()
        
        db.commit()
        
        # Generate enriched embedding
        enriched_emb = generator.generate_text_embedding(
            product.ai_description
        )
        
        # Store in Qdrant
        vector_db.upsert_product(
            product_id=str(product.id),
            embeddings={'enriched_embedding': enriched_emb},
            metadata={...}
        )
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        continue
```

**Cost:** ~$1 for 50 products (monitor your usage)

**Evening: Quality Validation**

- [ ] Manual review of 10 enriched products:
```python
enriched = db.query(Product).filter(Product.enriched_at != None).limit(10).all()

for p in enriched:
    print(f"\nTitle: {p.title}")
    print(f"Claude says: {p.era}, {p.category}")
    print(f"Tags: {p.style_tags}")
    print(f"Image: {p.primary_image}")
    print("Is this accurate? (check the image)")
```

- [ ] Track accuracy:
  - Era correct: __ / 10
  - Category correct: __ / 10  
  - Style tags relevant: __ / 10
  - **Goal: 80%+ accuracy**

- [ ] If accuracy is low:
  - Improve Claude prompt
  - Add more context/examples
  - Try different model (Opus for higher accuracy)

**End of Day Goal:**
✅ Claude integration working  
✅ 50 products enriched with AI metadata  
✅ 80%+ accuracy on era/category  
✅ Enriched embeddings in Qdrant  
✅ Cost monitored (~$1 spent)

---

### Weekend: Scale to 2,000 Products (8-10 hours)

**Saturday: Mass Scraping**

- [ ] Expand query list to 20 queries:
```python
queries = [
    # 70s
    'vintage dress 70s',
    'prairie dress 1970s',
    '70s bohemian',
    'gunne sax dress',
    
    # 80s  
    'vintage 80s dress',
    '80s power suit',
    'vintage 80s jacket',
    
    # 90s
    'grunge flannel 90s',
    '90s slip dress',
    'vintage 90s denim',
    '90s minimalist',
    
    # Y2K/2000s
    'y2k baby tee',
    'y2k dress',
    '2000s vintage',
    
    # General
    'vintage denim jacket',
    'vintage band tee',
    'vintage leather jacket',
    'vintage maxi dress',
    'vintage blazer',
    'vintage accessories'
]
```

- [ ] Run overnight scrape:
```python
pipeline.run(
    platforms=['depop'],
    queries=queries,
    max_products_per_query=100  # 20 queries × 100 = 2,000 products
)
```

**This will take 4-6 hours** - let it run while you do other things

- [ ] Monitor progress periodically
- [ ] Check for errors in logs

**Sunday: Enrichment & Verification**

- [ ] Batch enrich 200 more products:
```python
# Run in batches to manage cost
products = db.query(Product).filter(
    Product.enriched_at == None
).limit(200).all()

# Enrich in batches of 50
for i in range(0, 200, 50):
    batch = products[i:i+50]
    # ... enrich batch ...
    print(f"Batch {i//50 + 1}/4 complete")
```

**Cost:** ~$4 for 200 products

- [ ] Database backup:
```bash
pg_dump vintage_vestige > backup_week1.sql
```

- [ ] Final verification:
```sql
-- Total products
SELECT COUNT(*) FROM products;  -- Should be ~2,000

-- With embeddings  
SELECT COUNT(*) FROM products WHERE embedded_at IS NOT NULL;

-- Enriched
SELECT COUNT(*) FROM products WHERE enriched_at IS NOT NULL;

-- By era
SELECT era, COUNT(*) FROM products 
WHERE era IS NOT NULL 
GROUP BY era 
ORDER BY COUNT(*) DESC;

-- By category
SELECT category, COUNT(*) FROM products 
WHERE category IS NOT NULL 
GROUP BY category;
```

- [ ] Test search quality with 10 different queries:
```python
test_queries = [
    "70s prairie dress",
    "grunge flannel", 
    "y2k baby tee",
    "minimalist black",
    "vintage denim"
]

for query in test_queries:
    print(f"\nQuery: {query}")
    vector = generator.generate_text_embedding(query)
    results = vector_db.search_similar(
        collection='vintage_text',
        query_vector=vector,
        limit=5
    )
    for r in results[:3]:
        print(f"  - {r['title']} ({r['score']:.2f})")
```

- [ ] Document issues in `NOTES.md`:
  - What works well?
  - What needs improvement?
  - Search accuracy subjective assessment

**End of Weekend Goal:**
✅ 2,000+ products indexed  
✅ All have image + text embeddings  
✅ 200+ have AI enrichment  
✅ Search returns relevant results (70%+ accuracy)  
✅ Database backed up  
✅ Ready for Week 2 (API development)

---

## 📊 Week 1 Success Metrics

**Quantitative:**
- [ ] 2,000+ products in database
- [ ] 2,000+ image embeddings in Qdrant
- [ ] 2,000+ text embeddings in Qdrant
- [ ] 200+ products with Claude enrichment
- [ ] Search response time < 2 seconds
- [ ] 80%+ accuracy on era classification (manual check)

**Qualitative:**
- [ ] Similarity search "feels right" (returns similar items)
- [ ] Pipeline runs without crashes
- [ ] You understand every component
- [ ] Comfortable debugging issues

**Infrastructure:**
- [ ] PostgreSQL running reliably
- [ ] Qdrant dashboard accessible
- [ ] Code organized and documented
- [ ] Database backed up

---

## 💰 Week 1 Budget

**Actual Costs:**
- Claude API: $5-10 (250 enrichments × ~$0.02 each)
- **Total: $5-10**

**Free:**
- PostgreSQL (local)
- Qdrant (local Docker)
- CLIP/embedding models (open source)
- Development tools

---

## 🚨 Common Issues & Solutions

### "CLIP model download is stuck"
**Solution:** It's 500MB, takes 5-10 minutes. Check internet connection. Cancel and retry if frozen >30 min.

### "PostgreSQL won't start"
**Solution:** 
```bash
# Check if already running
ps aux | grep postgres

# Stop existing instance
brew services stop postgresql

# Start fresh
brew services start postgresql@14
```

### "Qdrant collection not found"
**Solution:** Collections auto-create on first upsert. Just run the code, it will create.

### "Image download fails (404)"
**Solution:** This is normal, some images are deleted. Catch the exception and skip:
```python
try:
    embedding = generator.generate_image_embedding(url)
except:
    print(f"Skipping image: {url}")
    continue
```

### "Claude API rate limit"
**Solution:** Add delay between calls:
```python
import time
time.sleep(1)  # 1 second between requests
```

### "Out of memory"
**Solution:** Process in smaller batches, restart Python process between batches:
```python
# Instead of all at once
for i in range(0, total, 50):
    batch = products[i:i+50]
    process_batch(batch)
```

---

## 🎯 What You're Learning This Week

**Technical Skills:**
- Vector embeddings (CLIP, sentence transformers)
- Vector databases (Qdrant)
- Web scraping (ethical, at scale)
- Database design (PostgreSQL)
- AI API integration (Claude)
- Python data pipelines

**Conceptual:**
- How similarity search works
- Embedding space and cosine similarity
- AI classification vs human tagging
- Data pipeline architecture
- Error handling at scale

**This is production AI/ML engineering.** Real skills, real value.

---

## 💪 Motivation & Mindset

### When It Feels Slow:
> "You're building the foundation. Every great product starts here."

Rome wasn't built in a day. Neither is a search engine.

### When Claude Classification Seems Inaccurate:
> "80% accuracy is actually good for AI. You'll improve it over time."

Remember: Human taggers on Depop/Etsy are often wrong too.

### When You Hit Errors:
> "Every error is a learning opportunity. Debug, fix, improve."

You're getting better at this with every bug you solve.

### When 2,000 Products Feels Like Nothing:
> "Gem started somewhere. Depop started somewhere. You're starting now."

2,000 products is MORE than enough to validate search quality.

### End of Week Reflection:
> "I have a searchable database of 2,000 vintage items powered by AI. That's not nothing. That's real."

**Be proud of what you built this week.**

---

## 📝 End of Week 1 Checklist

Before moving to Week 2, verify:

**Infrastructure:**
- [ ] PostgreSQL running and accessible
- [ ] Qdrant running at localhost:6333
- [ ] Python environment working
- [ ] All dependencies installed

**Data:**
- [ ] 2,000+ products in database
- [ ] Images downloaded or accessible
- [ ] All products have embeddings
- [ ] 200+ products enriched by Claude
- [ ] Database backed up

**Code:**
- [ ] All files in proper directory structure
- [ ] Config.py with settings
- [ ] .env with API keys (not committed to git!)
- [ ] Pipeline runs without errors
- [ ] Tests pass

**Quality:**
- [ ] Search returns relevant results
- [ ] Era classification 80%+ accurate
- [ ] No major bugs blocking progress
- [ ] You understand the codebase

**Documentation:**
- [ ] README.md with setup instructions
- [ ] Notes on what works/doesn't work
- [ ] Issues documented for later

**Mental:**
- [ ] You feel accomplished (you should!)
- [ ] You understand the architecture
- [ ] You're ready for Week 2
- [ ] You're still excited (important!)

---

## 🎉 Celebration Time

**What you built this week:**
- 🔍 AI-powered search engine (basic version)
- 🤖 Claude classification system
- 💾 Production database with 2,000 items
- 🧠 Vector embedding pipeline
- 📊 Quality metrics and validation

**What this is worth:**
- **For a business:** Foundation for $100k+ product
- **For a job:** Portfolio piece worth $150k+ salary
- **For you:** Proof you can build real AI products

**You did this in ONE WEEK.**

Take Sunday evening off. Rest. Be proud.

**Monday morning, Week 2 starts: Building the API.** 🚀

---

## 📌 Week 2 Preview

**Next week you'll:**
- Build FastAPI backend
- Create search endpoints (text, image, hybrid)
- Deploy to production (Railway/Render)
- Make it accessible via public API
- Test search quality at scale

**By end of Week 2:**
You'll have a deployed, working API that anyone can call.

**Rest up. You earned it.** 💪

---

**Week 1 Status: COMPLETE ✅**

*Now go celebrate with your daughter. You built something real.* ❤️
