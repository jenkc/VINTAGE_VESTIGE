Review everything we did in this session. Then:

1. **Update `docs/SESSION_LOG.md`:**
   - Add a dated entry at the top with:
     - What was accomplished (files created, modified, deleted — with paths)
     - Decisions made and why (even small ones like "chose X library over Y")
     - Problems encountered and how they were resolved (or left open)
     - What was attempted but didn't work
   - Update the "Current Priorities" and "What to Work on Next" sections to reflect where we actually left off, not where we planned to be
   - Update "Known Bugs / Gaps" if anything new surfaced

2. **Update `docs/PROJECT_STATE.md`:**
   - Refresh any sections affected by today's work
   - If data counts changed (new products, embeddings, bridges), re-run the queries and update the numbers
   - Move items between "not started" → "in progress" → "complete" as appropriate

3. **Update `docs/DECISIONS.md`:**
   - Add any new decisions from this session, even if they felt minor in the moment
   - If we reversed or revised a previous decision, note that with context

4. **Update `docs/DATA_INVENTORY.md`** (only if we changed data — ingested products, ran enrichment, computed bridges, modified Qdrant collections):
   - Re-run the relevant database/Qdrant queries
   - Update counts and coverage numbers

5. **Check if any other docs need updates** (`ARCHITECTURE.md`, `API_SPEC.md`) based on what we built or changed today. Only update if something material changed — don't touch them just to touch them.

6. **Give me a short summary** at the end: what we shipped, what's next, and anything I should know before the next session.