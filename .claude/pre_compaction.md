Context window is getting long. Before compaction hits, save state NOW:

1. **Update `docs/SESSION_LOG.md` with everything from this session so far:**
   - What we've accomplished up to this point (files created, modified, deleted — with paths)
   - Decisions made and reasoning
   - What we were in the middle of when this save happened — be specific:
     - Which file were we editing?
     - What was the next step?
     - Any partial work that isn't committed/saved yet?
   - Problems we hit and how we solved them (or didn't)
   - Mark this entry clearly as a MID-SESSION SAVE so post-compaction recovery knows we're resuming, not starting a new day

2. **If there's any in-progress code that isn't saved to a file yet**, save it now — even if it's incomplete. Add a comment at the top like `# WIP — [what this is supposed to do next]` so we can pick it back up.

3. **Update `docs/PROJECT_STATE.md`** only if we've completed something that changes the status of a component (moved something from planned → in progress → done, or discovered something broken).

4. **Don't bother with:** DECISIONS.md, ARCHITECTURE.md, API_SPEC.md, DATA_INVENTORY.md — we'll catch those up at end of day. Focus on saving what we need to resume seamlessly.

5. **Last line of the SESSION_LOG entry should be:** `RESUME POINT: [one sentence describing exactly what to do next]`

Speed matters here — save state, don't polish prose.