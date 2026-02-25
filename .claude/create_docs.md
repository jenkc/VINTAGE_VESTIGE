I need you to create comprehensive project documentation for Vintage Vestige by auditing the actual codebase and reconciling it with the planning documents. Do the following:

1. **Audit the codebase first.** Walk the full directory tree. Read key files: storage/database.py, storage/vector_db.py, embeddings/, enrichment/, scripts/, api/ (if exists), vv-web/src/ (structure + key files). Note what actually exists vs. what's planned.

2. **Create these documents in a `docs/` directory:**

   a. `docs/PROJECT_STATE.md` — Current state of the project as of today. What's built, what's working, what's partially done, what's not started. Organized by layer (data, intelligence, API, frontend). Include actual file paths, line counts, and working/broken status. Reference the planning docs (PHASE_1_IMPLEMENTATION.md, implement_full_plan.md, technical_plan.md) but report reality, not aspirations.

   b. `docs/ARCHITECTURE.md` — Actual system architecture based on code that exists. Data flow diagrams (text-based), tech stack with versions, database schema (from SQLAlchemy models actually defined), Qdrant collection setup, embedding pipeline details. Include what's planned but not built as a clearly separated "Future" section.

   c. `docs/DECISIONS.md` — Key architectural and product decisions made so far, reconstructed from the code and planning docs. Format: date (approximate), decision, context, alternatives considered, outcome. Include: dataset approach (HuggingFace vs scraping), FastAPI vs Node, enrichment strategy (Claude + embed enriched text), embedding models chosen, bridge scoring algorithm design, IIT 4.0 as future epic.

   d. `docs/SESSION_LOG.md` — A structured handoff document for future Claude Code sessions. Current priorities, what to work on next, known bugs or gaps, environment setup instructions (how to run locally), key file locations, and gotchas. This should be the first thing a new session reads to get productive immediately.

   e. `docs/API_SPEC.md` — Document the API endpoints that exist (if any) and the planned endpoints from the implementation plans. Mark each as [LIVE], [STUB], or [PLANNED]. Include request/response schemas from the Pydantic models.

   f. `docs/DATA_INVENTORY.md` — What data we actually have. Query the database if possible (or read the ingestion scripts) to report: number of products by platform, enrichment coverage, embedding coverage, bridge coverage. If you can't query live, document what the scripts expect and what the planning docs claim.

3. **Formatting rules:**
   - Use markdown
   - Be precise — file paths, line numbers, actual field names from code
   - Distinguish clearly between "exists and works," "exists but incomplete," and "planned only"
   - Keep each doc self-contained (someone should be able to read just one)
   - No fluff — these are working reference docs, not marketing

4. **After creating the docs**, give me a summary of the biggest gaps between the plans and reality — the things that will surprise me or block progress.