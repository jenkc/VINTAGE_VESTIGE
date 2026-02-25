# Vintage Vestige - Day 1 Development Plan
**FastAPI Backend + React Frontend MVP**

**Date:** January 20, 2026  
**Goal:** Working image and text search with deployed demo  
**Time Budget:** 6-8 hours coding time  
**Status:** Ready to start

---

## 🎯 Today's Mission

Build a working FastAPI backend that connects your existing vector search to a React frontend. By end of day, you should have:
- ✅ API with 2 endpoints working
- ✅ React app calling those endpoints
- ✅ Results displaying in browser
- ✅ Demo-ready for portfolio

---

## ⏰ Schedule Overview

**9:00 AM - 10:00 AM:** Upwork Morning Routine  
**10:00 AM - 12:00 PM:** FastAPI Backend Setup  
**12:00 PM - 1:00 PM:** Lunch + Test API  
**1:00 PM - 3:00 PM:** React Frontend Setup  
**3:00 PM - 5:00 PM:** Integration + Polish  
**5:00 PM - 6:00 PM:** Testing + Documentation  

---

## 📋 Phase 1: Morning Routine (9:00 AM - 10:00 AM)

### Upwork Job Applications

**Time Allocated:** 1 hour  
**Goal:** Apply to 2-3 fresh jobs

#### Checklist:
- [ ] Check email for Upwork alerts (saved searches)
- [ ] Review 5-10 fresh job postings (<6 hours old)
- [ ] Apply to 2-3 jobs that meet criteria:
  - [ ] <10 proposals
  - [ ] Client has $1K+ spent OR good reviews
  - [ ] Budget $20-35/hr
  - [ ] Skills match (web scraping, data extraction, Python)
- [ ] Track applications in spreadsheet:
  - [ ] Job title
  - [ ] Client name
  - [ ] Date applied
  - [ ] Budget/rate
  - [ ] Follow-up date

**Success Criteria:**
✅ 2-3 quality proposals submitted  
✅ Applications logged for tracking  
✅ Ready to focus on coding

**If no good jobs available:**
- Don't force it
- Move to Phase 2 early
- Check again at lunch

---

## 📋 Phase 2: FastAPI Backend (10:00 AM - 12:00 PM)

### Part A: Project Setup (30 minutes)

#### Checklist:
- [ ] Create project directory: `vintage-vestige-backend/`
- [ ] Set up virtual environment:
  ```bash
  cd vintage-vestige-backend
  python -m venv venv
  source venv/bin/activate  # Mac/Linux
  ```
- [ ] Install dependencies:
  ```bash
  pip install fastapi uvicorn python-multipart pillow
  pip install sentence-transformers transformers torch
  pip install qdrant-client psycopg2-binary python-dotenv
  ```
- [ ] Create requirements.txt:
  ```bash
  pip freeze > requirements.txt
  ```
- [ ] Create `.env` file for credentials:
  ```
  DATABASE_URL=postgresql://user:password@localhost/vintage_vestige
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  ```
- [ ] Create `.gitignore`:
  ```
  venv/
  __pycache__/
  .env
  *.pyc
  .DS_Store
  ```

**Deliverable:** Clean project structure ready for coding

---

### Part B: Core API Implementation (60 minutes)

#### File 1: `main.py` (FastAPI App)

**Checklist:**
- [ ] Create `main.py`
- [ ] Import FastAPI and required libraries
- [ ] Set up CORS middleware for React
- [ ] Define Pydantic models for responses
- [ ] Implement `/health` endpoint
- [ ] Implement `/api/search/image` endpoint
- [ ] Implement `/api/search/text` endpoint
- [ ] Add error handling to all endpoints
- [ ] Add logging for debugging

**Code Template:**
```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import base64
from io import BytesIO
from PIL import Image

app = FastAPI(
    title="Vintage Vestige API",
    description="AI-powered vintage fashion search",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response Models
class Product(BaseModel):
    id: int
    title: str
    image_url: str
    price: float
    era: str | None = None
    category: str | None = None
    similarity: float
    url: str

class SearchResponse(BaseModel):
    results: List[Product]
    count: int
    query_time_ms: float

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Vintage Vestige API is running",
        "version": "1.0.0"
    }

# TODO: Implement search endpoints (see below)
```

**Deliverable:** `main.py` with basic structure

---

#### File 2: `models.py` (Embedding Functions)

**Checklist:**
- [ ] Create `models.py`
- [ ] Move existing CLIP embedding code here
- [ ] Move existing text embedding code here
- [ ] Add function to load models (cached)
- [ ] Test functions independently

**Code Structure:**
```python
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

class EmbeddingModels:
    def __init__(self):
        self.clip_model = None
        self.clip_processor = None
        self.text_model = None
    
    def load_models(self):
        """Load models once and cache"""
        if self.clip_model is None:
            # Load CLIP for image embeddings
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        if self.text_model is None:
            # Load sentence transformer for text
            self.text_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    def generate_image_embedding(self, image: Image.Image):
        """Generate 512-dim CLIP embedding from PIL Image"""
        # Your existing CLIP code
        pass
    
    def generate_text_embedding(self, text: str):
        """Generate 384-dim text embedding from string"""
        # Your existing text embedding code
        pass

# Global instance
embedding_models = EmbeddingModels()
```

**Deliverable:** Reusable embedding functions

---

#### File 3: `vector_search.py` (Qdrant Operations)

**Checklist:**
- [ ] Create `vector_search.py`
- [ ] Move Qdrant connection code here
- [ ] Implement search function
- [ ] Add PostgreSQL product lookup
- [ ] Format results for API response

**Code Structure:**
```python
from qdrant_client import QdrantClient
import psycopg2
import os
from typing import List

class VectorSearch:
    def __init__(self):
        self.qdrant = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        self.db_conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    
    def search_similar(self, embedding: List[float], collection: str, top_k: int = 20):
        """
        Search Qdrant for similar items
        Returns list of product IDs with similarity scores
        """
        # Your existing Qdrant search code
        pass
    
    def get_product_details(self, product_ids: List[int]):
        """
        Fetch full product details from PostgreSQL
        """
        # Your existing PostgreSQL query
        pass

# Global instance
vector_search = VectorSearch()
```

**Deliverable:** Clean vector search abstraction

---

### Part C: Connect Everything (30 minutes)

**Checklist:**
- [ ] Import models and vector_search in `main.py`
- [ ] Implement image search endpoint fully:
  ```python
  @app.post("/api/search/image", response_model=SearchResponse)
  async def search_by_image(file: UploadFile = File(...)):
      import time
      start = time.time()
      
      try:
          # Read and process image
          contents = await file.read()
          image = Image.open(BytesIO(contents))
          
          # Generate embedding
          embedding = embedding_models.generate_image_embedding(image)
          
          # Search
          results = vector_search.search_similar(
              embedding, 
              collection="vintage_images",
              top_k=20
          )
          
          query_time = (time.time() - start) * 1000
          
          return SearchResponse(
              results=results,
              count=len(results),
              query_time_ms=round(query_time, 2)
          )
      except Exception as e:
          raise HTTPException(status_code=500, detail=str(e))
  ```
- [ ] Implement text search endpoint fully
- [ ] Test each endpoint independently

**Deliverable:** Working API endpoints

---

### Part D: Test the API (30 minutes)

**Checklist:**
- [ ] Start the server:
  ```bash
  uvicorn main:app --reload
  ```
- [ ] Verify server starts without errors
- [ ] Visit http://localhost:8000/docs
- [ ] Test `/health` endpoint (should return status)
- [ ] Test `/api/search/text` with sample query
- [ ] Test `/api/search/image` with sample image
- [ ] Verify results format matches SearchResponse model
- [ ] Check response times (<1 second)
- [ ] Fix any bugs found

**Success Criteria:**
✅ API running on localhost:8000  
✅ `/docs` page loads and shows all endpoints  
✅ Both search endpoints return valid results  
✅ Response times under 1 second  
✅ No Python errors in console

**Deliverable:** Verified working API

---

## 🍽️ Lunch Break (12:00 PM - 1:00 PM)

Take a real break. Step away from computer.

**Optional:**
- [ ] Share API `/docs` screenshot on Twitter/LinkedIn
- [ ] Write down any bugs or improvements noted

---

## 📋 Phase 3: React Frontend (1:00 PM - 3:00 PM)

### Part A: Project Setup (20 minutes)

**Checklist:**
- [ ] Create React app:
  ```bash
  npx create-react-app vintage-vestige-frontend
  cd vintage-vestige-frontend
  ```
- [ ] Install dependencies:
  ```bash
  npm install axios react-router-dom
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
- [ ] Configure Tailwind in `tailwind.config.js`:
  ```javascript
  module.exports = {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
      extend: {
        colors: {
          cream: '#F5F1E8',
          'dusty-rose': '#D4A5A5',
          'deep-teal': '#2C5F6F',
          'burnt-orange': '#D87744',
          charcoal: '#3A3A3A',
        }
      },
    },
    plugins: [],
  }
  ```
- [ ] Add Tailwind to `src/index.css`:
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;
  ```
- [ ] Test app runs: `npm start`

**Deliverable:** React app running on localhost:3000

---

### Part B: Components (60 minutes)

#### Component 1: SearchPage.jsx (Main page)

**Checklist:**
- [ ] Create `src/components/SearchPage.jsx`
- [ ] Add image upload component
- [ ] Add image preview
- [ ] Add text search input
- [ ] Add loading states
- [ ] Style with Tailwind (use cream background, dusty-rose accents)

**Key Features:**
```jsx
function SearchPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Handle image upload
  // Handle text search
  // Navigate to results
  
  return (
    <div className="min-h-screen bg-cream">
      {/* Upload area */}
      {/* Text search */}
      {/* CTA button */}
    </div>
  );
}
```

**Deliverable:** Search interface component

---

#### Component 2: ResultsPage.jsx (Results grid)

**Checklist:**
- [ ] Create `src/components/ResultsPage.jsx`
- [ ] Grid layout (4 columns desktop, 2 mobile)
- [ ] ProductCard sub-component
- [ ] Loading skeleton
- [ ] Empty state
- [ ] "Back to search" button

**Key Features:**
```jsx
function ResultsPage() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Fetch results from API
  }, []);
  
  return (
    <div className="min-h-screen bg-cream p-8">
      <button>← Back to Search</button>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {results.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}
```

**Deliverable:** Results display component

---

#### Component 3: ProductCard.jsx (Individual product)

**Checklist:**
- [ ] Create `src/components/ProductCard.jsx`
- [ ] Image with loading state
- [ ] Title (truncated if long)
- [ ] Price + currency
- [ ] Era badge
- [ ] Similarity score
- [ ] "View on [platform]" link
- [ ] Hover effects

**Styling:**
- Card has subtle shadow
- Image takes 60% of card height
- Text info below image
- Era badge: small pill in dusty-rose
- Similarity: small text in deep-teal

**Deliverable:** Reusable product card

---

### Part C: API Integration (40 minutes)

**Checklist:**
- [ ] Create `src/api/vintageApi.js`:
  ```javascript
  import axios from 'axios';
  
  const API_BASE_URL = 'http://localhost:8000';
  
  export const searchByImage = async (imageFile) => {
    const formData = new FormData();
    formData.append('file', imageFile);
    
    const response = await axios.post(
      `${API_BASE_URL}/api/search/image`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    
    return response.data;
  };
  
  export const searchByText = async (query) => {
    const response = await axios.post(
      `${API_BASE_URL}/api/search/text`,
      { query, top_k: 20 }
    );
    
    return response.data;
  };
  ```
- [ ] Use API functions in SearchPage
- [ ] Pass results to ResultsPage via React Router state
- [ ] Handle errors gracefully
- [ ] Add loading indicators

**Deliverable:** Working API connection

---

## 📋 Phase 4: Integration & Polish (3:00 PM - 5:00 PM)

### Part A: End-to-End Testing (45 minutes)

**Checklist:**
- [ ] Backend running: `uvicorn main:app --reload`
- [ ] Frontend running: `npm start`
- [ ] Test complete flow:
  - [ ] Upload image → See results
  - [ ] Text search → See results
  - [ ] Click product → Opens external link
  - [ ] Back button → Returns to search
- [ ] Test edge cases:
  - [ ] Very large image
  - [ ] Invalid file type
  - [ ] Empty search query
  - [ ] Network error handling
- [ ] Test on mobile screen size (Chrome DevTools)
- [ ] Fix all bugs found

**Success Criteria:**
✅ Image upload works end-to-end  
✅ Text search works end-to-end  
✅ Results display correctly  
✅ Links open properly  
✅ Mobile responsive  
✅ No console errors

**Deliverable:** Bug-free user flow

---

### Part B: Polish & UX (45 minutes)

**Visual Polish Checklist:**
- [ ] Add loading skeletons (gray boxes while images load)
- [ ] Add empty state with helpful message
- [ ] Add error state with retry button
- [ ] Smooth transitions between pages
- [ ] Image lazy loading
- [ ] Responsive breakpoints tested
- [ ] Typography hierarchy clear
- [ ] Colors match branding doc

**UX Improvements:**
- [ ] Disable search button while loading
- [ ] Show "Searching..." feedback
- [ ] Display result count: "Found 12 items"
- [ ] Add "Powered by AI" badge
- [ ] Image preview before upload
- [ ] Clear uploaded image button

**Deliverable:** Polished, professional interface

---

### Part C: Performance Check (30 minutes)

**Checklist:**
- [ ] Measure search response time (should be <1 sec)
- [ ] Check image file size limits (handle large files)
- [ ] Optimize large images before sending to API
- [ ] Add compression if needed:
  ```javascript
  // In SearchPage.jsx
  const compressImage = async (file) => {
    // Resize to max 1024px using canvas
    // Convert to JPEG with 85% quality
    return compressedFile;
  };
  ```
- [ ] Test with 5+ different images
- [ ] Verify all images in results load properly
- [ ] Check for any memory leaks

**Success Criteria:**
✅ Search completes in <2 seconds total  
✅ Images load smoothly  
✅ No performance issues on older hardware  
✅ Works on Safari, Chrome, Firefox

**Deliverable:** Fast, reliable app

---

## 📋 Phase 5: Documentation & Demo (5:00 PM - 6:00 PM)

### Part A: Code Documentation (20 minutes)

**Checklist:**
- [ ] Update README.md in backend:
  ```markdown
  # Vintage Vestige API
  
  AI-powered vintage fashion search backend.
  
  ## Setup
  1. Install dependencies: `pip install -r requirements.txt`
  2. Configure .env file
  3. Run: `uvicorn main:app --reload`
  
  ## API Endpoints
  - POST /api/search/image - Upload image, get similar items
  - POST /api/search/text - Text query, get results
  - GET /health - Health check
  
  ## Tech Stack
  - FastAPI
  - CLIP embeddings (512-dim)
  - Qdrant vector database
  - PostgreSQL
  ```
- [ ] Update README.md in frontend:
  ```markdown
  # Vintage Vestige Frontend
  
  React app for vintage fashion search.
  
  ## Setup
  1. Install: `npm install`
  2. Run: `npm start`
  3. Backend must be running on localhost:8000
  
  ## Features
  - Image upload search
  - Text search
  - Results grid
  - Mobile responsive
  ```
- [ ] Add inline comments to complex code sections
- [ ] Document any quirks or limitations

**Deliverable:** Clear documentation

---

### Part B: Demo Preparation (20 minutes)

**Checklist:**
- [ ] Take screenshots:
  - [ ] Search page (both upload and text)
  - [ ] Results grid (desktop view)
  - [ ] Results grid (mobile view)
  - [ ] Individual product card
  - [ ] API docs page (localhost:8000/docs)
- [ ] Record 2-minute demo video (optional but recommended):
  - [ ] Show upload image
  - [ ] Show results appearing
  - [ ] Click through to product
  - [ ] Show text search
  - [ ] Show mobile view
- [ ] Create quick demo script:
  ```
  "Vintage Vestige uses AI to search vintage fashion visually.
  Upload any photo [demo upload]
  Get similar items instantly [show results]
  No vintage expertise needed."
  ```

**Deliverable:** Portfolio-ready assets

---

### Part C: Git & Backup (20 minutes)

**Checklist:**
- [ ] Initialize git repos:
  ```bash
  # Backend
  cd vintage-vestige-backend
  git init
  git add .
  git commit -m "Initial commit: FastAPI backend with image/text search"
  
  # Frontend
  cd ../vintage-vestige-frontend
  git init
  git add .
  git commit -m "Initial commit: React frontend with search UI"
  ```
- [ ] Create GitHub repos (public for portfolio)
- [ ] Push code:
  ```bash
  git remote add origin [your-repo-url]
  git branch -M main
  git push -u origin main
  ```
- [ ] Update repo descriptions
- [ ] Add topics/tags: fastapi, react, ai, vector-search, fashion

**Deliverable:** Code backed up on GitHub

---

## ✅ End of Day Checklist

### Critical Path Items (Must Complete):
- [ ] FastAPI backend running with 2 endpoints
- [ ] React frontend displaying search interface
- [ ] Image search works end-to-end
- [ ] Text search works end-to-end
- [ ] Code pushed to GitHub
- [ ] Screenshots taken

### Nice to Have (If Time Permits):
- [ ] Demo video recorded
- [ ] Deployed to staging (Railway + Vercel)
- [ ] Added to portfolio website
- [ ] Posted on LinkedIn

---

## 📊 Success Metrics

**By end of day, you should have:**
- ✅ Working MVP with both search modes
- ✅ <2 second total search time
- ✅ Clean, professional UI
- ✅ Portfolio-ready screenshots
- ✅ Code on GitHub
- ✅ Demo ready to share

**What this demonstrates to employers:**
- Full-stack capability (React + Python)
- AI integration (CLIP embeddings, vector search)
- Product thinking (solved real problem)
- Execution speed (working MVP in 1 day)
- Modern tech stack (FastAPI, React, AI)

---

## 🚨 If You Get Stuck

**Backend Issues:**
- CORS errors → Check allow_origins in CORSMiddleware
- Model loading slow → Models load once at startup, cache after
- Qdrant connection fails → Verify Qdrant is running: `docker ps`
- PostgreSQL errors → Check .env DATABASE_URL

**Frontend Issues:**
- API calls fail → Check backend is running on port 8000
- CORS blocked → Add frontend URL to backend CORS config
- Images not loading → Check image_url format in API response
- Upload fails → Check file size limit, file type validation

**Time Management:**
- Running behind? → Skip text search, focus on image search only
- Way behind? → Use API docs page as "frontend" demo for today
- Ahead of schedule? → Add era filter or improve styling

---

## 📝 Evening Reflection (6:00 PM)

**Before closing your laptop:**
- [ ] List what worked well today
- [ ] Note any bugs or issues to fix tomorrow
- [ ] Identify what took longer than expected
- [ ] Update your task list for tomorrow
- [ ] Celebrate what you built! 🎉

---

## 🎯 Tomorrow's Plan (Preview)

**Day 2 Goals:**
- Deploy backend to Railway
- Deploy frontend to Vercel
- Expand dataset to 500+ products
- Add to portfolio website
- Update LinkedIn with live demo link

---

**END OF DAY 1 PLAN**

**Remember:** The goal is working > perfect. Ship the MVP today, polish tomorrow.

**You've got this!** 💪
