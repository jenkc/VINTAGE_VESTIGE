# Vintage Vestige — Deployment Plan

**Created: 2026-03-06**
**Target: Production on Vercel (frontend) + Railway (API)**

---

## Pre-Deployment: Data Completeness

These must be done before any deployment work begins.

### D-0.1 Enrich All Products

**Status:** 4,234/4,234 enriched ✓
**Remaining:** 3,368 products (va_museum 1,856 + smithsonian 612 + fashionpedia 500 + met_museum 400)
**Estimated cost:** ~$85 | **Time:** ~5.5 hours

```bash
# Run in 100-item batches, review ERA summary after each
venv/bin/python tools/enrichment/enrich_remaining.py 100 --yes
# Review unrecognized_eras.csv, add aliases to era_taxonomy.py
# Repeat until all 3,368 done
```

**Deliverable:** All 4,234 products have `enriched_at IS NOT NULL`

**Verification:**
```sql
SELECT COUNT(*) FROM products WHERE enriched_at IS NULL;
-- Expected: 0
```

### D-0.2 Generate All Embeddings

**Status:** 866/4,234 have embeddings
**Remaining:** 3,368 products need text + image embeddings

```bash
venv/bin/python tools/embeddings/generate_all_embeddings.py
```

**Deliverable:** All enriched products have `text_embedding IS NOT NULL`

**Verification:**
```sql
SELECT
  COUNT(*) FILTER (WHERE text_embedding IS NOT NULL) as has_text,
  COUNT(*) FILTER (WHERE image_embedding IS NOT NULL) as has_image,
  COUNT(*) as total
FROM products;
-- Expected: ~4234, ~4234, 4234
```

### D-0.3 Recompute Bridges

With 4,234 enriched+embedded products (vs 866 before), bridge quality and quantity will improve dramatically.

```bash
venv/bin/python tools/analysis/compute_bridges.py
```

**Deliverable:** `style_bridges` table repopulated with new bridge set

### D-0.4 Generate Bridge Narratives

**Status:** 22/7,324 have narratives
**Remaining:** All bridges after recomputation

```bash
venv/bin/python tools/analysis/generate_narratives.py --batch-size=50
```

**Deliverable:** All (or most) bridges have `bridge_narrative IS NOT NULL`

### D-0.5 Run Full Test Suite

```bash
venv/bin/python -m pytest tests/ -v
```

**Deliverable:** All tests pass (unit, integration, data integrity)

---

## Phase 1: Environment & Secrets

### D-1.1 Create `.env.example`

Strip secrets from `.env`, leave placeholders:

```bash
# Database
DATABASE_URL=postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# Supabase Storage
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<your-service-role-key>
SUPABASE_STORAGE_BUCKET=product-images

# AI
ANTHROPIC_API_KEY=sk-ant-api03-...

# External APIs
SMITHSONIAN_API_KEY=<your-key>
```

**Deliverable:** `.env.example` committed, `.env` in `.gitignore`

### D-1.2 Tighten CORS  (DONE)

In `api/main.py`, replace `allow_origins=["*"]` with:

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Set `ALLOWED_ORIGINS=https://vintage-vestige.vercel.app,http://localhost:3000` in production env.

**Deliverable:** CORS restricted to known origins

### D-1.3 Add Environment-Based API URL to Frontend  (DONE)

In `vv-web/src/lib/constants.ts`, ensure the API base URL comes from an environment variable:

```typescript
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

**Deliverable:** Frontend can point to production API via env var

---

## Phase 2: Frontend Testing

### D-2.1 Install Vitest + Testing Library

```bash
cd vv-web
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react jsdom
```

Add to `package.json`:
```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Create `vv-web/vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

Create `vv-web/src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

**Deliverable:** `npm test` runs and exits cleanly (0 tests initially)

### D-2.2 Component Smoke Tests

Create tests for the most critical UI components:

| Test File | What It Tests |
|-----------|---------------|
| `src/components/ui/__tests__/Button.test.tsx` | Renders all variants, handles clicks |
| `src/components/ui/__tests__/Badge.test.tsx` | Renders with text |
| `src/components/ui/__tests__/ImageWithFallback.test.tsx` | Shows fallback on error |
| `src/components/search/__tests__/SearchBar.test.tsx` | Input changes, submit fires callback |
| `src/components/search/__tests__/ProductCard.test.tsx` | Renders title, image, platform badge |
| `src/components/bridge/__tests__/ScoreCircle.test.tsx` | Renders score value, correct color |
| `src/components/bridge/__tests__/BridgeCardCompact.test.tsx` | Renders source + target titles, score |

**Deliverable:** 7+ component test files, all passing

### D-2.3 Page-Level Integration Tests

| Test File | What It Tests |
|-----------|---------------|
| `src/app/__tests__/home.test.tsx` | Hero renders, "How It Works" section present |
| `src/app/__tests__/about.test.tsx` | About content renders |
| `src/app/search/__tests__/page.test.tsx` | Search bar renders, mock API returns results |

These will need API mocking (mock `fetch` or use MSW).

**Deliverable:** 3 page tests, all passing

### D-2.4 Build Verification

```bash
cd vv-web
npm run lint && npm run build && npm test
```

**Deliverable:** All three commands pass with exit code 0

---

## Phase 3: API Hardening

### D-3.1 Add Request Validation & Error Handling

Verify all endpoints return proper HTTP status codes:

| Scenario | Expected |
|----------|----------|
| `GET /products/99999` | 404 Not Found |
| `POST /search/text` with empty query | 422 Validation Error |
| `POST /search/image` with invalid base64 | 400 Bad Request |
| `GET /bridges/between/1/1` (same product) | 400 or empty result |

**Deliverable:** Consistent error responses across all 13 endpoints

### D-3.2 Add Rate Limiting (Optional)

If using Railway, their free tier has built-in rate limiting. Otherwise, add `slowapi`:

```bash
pip install slowapi
```

**Deliverable:** API won't fall over under moderate traffic

### D-3.3 API Integration Tests

```bash
venv/bin/python -m pytest tests/integration/test_api_smoke.py -v
```

Verify all 13 endpoints return 200 with valid data.

**Deliverable:** All API smoke tests pass

---

## Phase 4: Containerization

### D-4.1 Create Dockerfile for API

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for psycopg and torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY storage/ storage/
COPY embeddings/ embeddings/
COPY enrichment/ enrichment/
COPY analysis/ analysis/
COPY api/ api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Note:** The Docker image will be large (~2-3GB) because of PyTorch + sentence-transformers. Consider:
- Using `torch` CPU-only variant to save ~1GB
- Pre-downloading model weights into the image

### D-4.2 Test Docker Build Locally

```bash
docker build -t vintage-vestige-api .
docker run -p 8000:8000 --env-file .env vintage-vestige-api
curl http://localhost:8000/health
```

**Deliverable:** API runs in Docker, `/health` returns `{"status": "ok"}`

### D-4.3 Create `.dockerignore`

```
venv/
vv-web/
.git/
__pycache__/
*.pyc
tests/
docs/
tools/
*.dump
.claude/
```

**Deliverable:** Docker context is clean and small

---

## Phase 5: Deploy

### D-5.1 Deploy API to Railway

1. Create Railway project at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Set root directory to `/` (it will detect the Dockerfile)
4. Add environment variables:
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SUPABASE_STORAGE_BUCKET`
   - `ANTHROPIC_API_KEY` (only if you want live enrichment — not needed for serving)
   - `ALLOWED_ORIGINS=https://vintage-vestige.vercel.app`
5. Deploy

**Verification:**
```bash
curl https://<your-railway-url>/health
curl https://<your-railway-url>/search/text -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "silk evening gown", "limit": 3}'
```

**Deliverable:** API live at `https://<app>.railway.app`, health check passes

### D-5.2 Deploy Frontend to Vercel

1. Import repo to [vercel.com](https://vercel.com)
2. Set root directory to `vv-web`
3. Set framework to Next.js (auto-detected)
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://<your-railway-url>`
5. Deploy

**Verification:**
- Visit `https://vintage-vestige.vercel.app`
- Homepage loads with featured bridges
- Search returns results
- Product detail pages render with images from Supabase Storage

**Deliverable:** Frontend live at Vercel URL

### D-5.3 End-to-End Smoke Test

| Test | Steps | Expected |
|------|-------|----------|
| Homepage loads | Visit `/` | Hero, How It Works, Featured Bridges visible |
| Search works | Type "silk dress" in search bar | Results appear with images |
| Product detail | Click any result | Product page with image, metadata, ancestry |
| Bridge display | Check featured bridges on home | Scores, platform badges, era badges render |
| Image fallback | Find product with broken image | Gradient fallback shows, no broken img icon |
| Mobile layout | Resize to 375px width | Header collapses to hamburger, cards stack |
| API health | `curl /health` | `{"status": "ok"}` |
| API docs | Visit `/docs` | Swagger UI renders |

**Deliverable:** All 8 smoke tests pass manually

---

## Phase 6: CI/CD Pipeline

### D-6.1 GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pip install pytest
      - run: pytest tests/unit/ -v

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - working-directory: vv-web
        run: npm ci
      - working-directory: vv-web
        run: npm run lint
      - working-directory: vv-web
        run: npm run build
      - working-directory: vv-web
        run: npm test
```

**Note:** Integration tests that need Supabase credentials should NOT run in CI unless you add secrets to GitHub Actions settings.

**Deliverable:** CI runs on every push/PR, catches lint + type + test failures

---

## Phase 7: Post-Deploy Polish

### D-7.1 Update Documentation

| File | Change |
|------|--------|
| `vv-web/src/app/about/page.tsx` | Update "Built With" — change Qdrant to pgvector |
| `docs/PROJECT_STATE.md` | Update status, add deployment URLs |
| `docs/ARCHITECTURE.md` | Add deployment architecture section |

### D-7.2 Add Error Monitoring (Optional)

```bash
# Frontend
cd vv-web && npm install @sentry/nextjs

# Backend
pip install sentry-sdk[fastapi]
```

**Deliverable:** Errors in production are tracked and alertable

### D-7.3 Custom Domain (Optional)

- Point `vintagevestige.com` (or similar) to Vercel
- Set up CNAME for `api.vintagevestige.com` to Railway

---

## Checklist Summary

| # | Step | Category | Depends On | Est. Time |
|---|------|----------|------------|-----------|
| D-0.1 | Enrich all products | Data | — | 5.5 hrs |
| D-0.2 | Generate all embeddings | Data | D-0.1 | 1 hr |
| D-0.3 | Recompute bridges | Data | D-0.2 | 30 min |
| D-0.4 | Generate bridge narratives | Data | D-0.3 | 2-3 hrs |
| D-0.5 | Run full test suite | Data | D-0.4 | 5 min |
| D-1.1 | Create `.env.example` | Environment | — | 10 min |
| D-1.2 | Tighten CORS | Environment | — | 10 min |
| D-1.3 | Frontend API URL env var | Environment | — | 10 min |
| D-2.1 | Install Vitest + Testing Library | Frontend Tests | — | 15 min |
| D-2.2 | Component smoke tests (7 files) | Frontend Tests | D-2.1 | 1 hr |
| D-2.3 | Page integration tests (3 files) | Frontend Tests | D-2.1 | 1 hr |
| D-2.4 | Build verification | Frontend Tests | D-2.2, D-2.3 | 5 min |
| D-3.1 | API error handling audit | API | — | 30 min |
| D-3.2 | Rate limiting (optional) | API | — | 15 min |
| D-3.3 | API integration tests | API | — | 10 min |
| D-4.1 | Create Dockerfile | Container | — | 20 min |
| D-4.2 | Test Docker locally | Container | D-4.1 | 15 min |
| D-4.3 | Create `.dockerignore` | Container | — | 5 min |
| D-5.1 | Deploy API to Railway | Deploy | D-4.2 | 30 min |
| D-5.2 | Deploy frontend to Vercel | Deploy | D-1.3, D-5.1 | 15 min |
| D-5.3 | End-to-end smoke test | Deploy | D-5.1, D-5.2 | 30 min |
| D-6.1 | GitHub Actions CI | CI/CD | D-2.4 | 30 min |
| D-7.1 | Update docs | Polish | D-5.3 | 20 min |
| D-7.2 | Error monitoring (optional) | Polish | D-5.3 | 30 min |
| D-7.3 | Custom domain (optional) | Polish | D-5.2 | 15 min |

**Critical path:** D-0.1 → D-0.2 → D-0.3 → D-0.4 → D-0.5 → D-5.1 → D-5.2 → D-5.3

**Parallel work while enrichment runs (D-0.1):** D-1.x, D-2.x, D-3.x, D-4.x, D-6.1
