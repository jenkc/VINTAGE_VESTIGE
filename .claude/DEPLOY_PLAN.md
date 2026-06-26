# Vintage Vestige — Ship It Checklist

**From:** Mira (implementation planner)
**For:** Jen
**Date:** 2026-05-28
**Goal:** VV leaves your machine and reaches a live URL. **Shipping it once is the win.** Not perfect, not the KG, not pretty — *live and searchable.* That's the whole game today.

---

## Read this first (30 seconds)

You ship in five phases: **Pre-flight → Backend (Railway) → Frontend (Vercel) → Smoke test → Done.** Realistic total is **a half-day** (~3–4 hours), not the 75 minutes the old plan implied — and the honest reason for the gap is a thing I found that the plan got wrong. Read the next box before you touch anything.

### ⚠️ Heads-up: a gap between the deploy plan and the actual repo

I grep'd the real `Team_Inbox/VINTAGE_VESTIGE/` repo before writing this, and the `DEPLOYMENT_PLAN.md` is **lying to you in three places** (not on purpose — it was written aspirationally and the files never got created):

| Plan says | Reality on disk | What it means for you |
|---|---|---|
| **D-4.1 Dockerfile ✅ DONE** | **No `Dockerfile` exists anywhere in the repo** | Railway has nothing to build. You'll either create the Dockerfile (the plan has the exact contents — see Phase 0) **or** skip Docker entirely and let Railway auto-detect Python. |
| **D-4.3 `.dockerignore` ✅ DONE** | **No `.dockerignore` exists** | Only matters if you go the Dockerfile route. |
| (implied — Docker `COPY requirements.txt`) | **No `requirements.txt` exists anywhere** | This is the real blocker. Railway can't install your Python deps without it, whether you use Docker *or* buildpacks. **You have to produce this file first.** It's Phase 0, Step 1. |

Good news: none of this is hard, and none of it is code I'd be stealing from you — it's config and a dependency freeze, the deploy plumbing every project needs once. The thing that *was* genuinely uncertain (the heavy Docker build) is exactly why I'm steering you toward the simpler path below. **Don't panic when Railway can't find a Dockerfile — that's expected, and Phase 2 tells you what to click.**

What I verified is *correct* in the repo (so you can trust it): `api/main.py` reads `ALLOWED_ORIGINS` from env ✓, the frontend reads `NEXT_PUBLIC_API_URL` ✓, the search endpoint really is `POST /search/text` ✓, `/health` returns `{"status": "ok"}` ✓, the FastAPI entrypoint is `api.main:app` ✓.

---

## A decision you make once, up front: Docker or no Docker?

The Docker image is the one place a half-day could become a multi-day stall — it's ~2–3GB because of PyTorch, and **it has never been built once** (D-4.2 was never checked off). So I'm giving you the lower-risk path as the **main line**, and the Docker path as a clearly-marked fallback.

- **Main line (recommended): let Railway auto-detect Python via buildpacks (Nixpacks).** No Dockerfile needed. Railway sees a Python project + `requirements.txt`, builds it itself. Fewer moving parts, and you skip the untested 2–3GB image entirely. This is the path the checklist below follows.
- **Fallback (only if buildpacks fail): the Dockerfile route.** The plan already has the exact Dockerfile contents (`DEPLOYMENT_PLAN.md` § D-4.1). You'd create that file plus `.dockerignore`, test the build locally first, *then* deploy. The Docker mini-section near the end walks this.

Pick the main line. Only drop to the fallback if Phase 2 fails in the specific way I describe.

---

## What is explicitly OUT of scope today

Write these on a sticky note. If you feel the itch to "just fix one thing" mid-deploy, **you do not touch it — you write it on the parking-lot list at the bottom of this file and keep going.** That itch is the exact reflex that's kept VV off the internet for three months.

- ❌ The Knowledge Graph (Neptune, the whole KG plan) — parked.
- ❌ The bridges/Thread Pull/frontend refactor — not today.
- ❌ Any refactor, cleanup, rename, or "while I'm in here…"
- ❌ Custom domain, error monitoring, CI/CD (plan's Phases 6 & 7) — *all optional, all post-ship.*
- ❌ The frontend test files the plan lists as TODO (D-2.2 / D-2.3) — **not blocking a deploy.** Skip them.
- ❌ Making it look good. It already looks fine. Ship the version that exists.

---

## Phase 0 — Pre-flight (~45 min)

*Goal: produce the one missing file and confirm your accounts/secrets are ready, so the deploy phases don't stall on a surprise.*

- [ ] **Open a terminal in the VV repo root** (the folder with `api/` and `vv-web/` in it). Confirm with `ls` — you should see `api`, `vv-web`, `storage`, `embeddings`, `enrichment`, `analysis`.
- [ ] **Generate `requirements.txt`** (this is the missing-file blocker — do it first). From inside your Python venv, run:
  ```bash
  venv/bin/pip freeze > requirements.txt
  ```
  *Why:* Railway installs your Python deps from this file. Without it the backend build fails instantly. **Watch out:** `pip freeze` dumps *everything* in the venv. That's fine for shipping — don't hand-prune it now (that's a parking-lot task). Just confirm the file exists and that `fastapi`, `uvicorn`, `torch`, `sentence-transformers`, and `psycopg` show up in it (`grep -iE "fastapi|uvicorn|torch|sentence-transformers|psycopg" requirements.txt`). Done-signal: the file exists and those names appear.
- [ ] **Confirm `.env` is NOT going to get committed.** Run `cat .gitignore | grep -i env`. If `.env` isn't listed, add a line `.env` to `.gitignore`. *Why:* your `DATABASE_URL` and service keys live in `.env`; pushing them to a public GitHub repo leaks your database. **Do not skip this one.**
- [ ] **Commit and push the repo to GitHub** (Railway and Vercel both deploy *from GitHub*, not your laptop). `git add -A && git commit -m "prep for deploy" && git push`. Done-signal: your latest commit (including the new `requirements.txt`) is visible on github.com. **Watch out:** if `git push` complains there's no remote yet, you'll need to create the GitHub repo first and `git remote add origin <url>` — budget 10 extra min if so.
- [ ] **Have your secrets in front of you.** Open `.env` and copy these four values somewhere you can paste from in a minute: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_STORAGE_BUCKET`. You'll paste them into Railway. (`ANTHROPIC_API_KEY` is *not* needed to serve search — skip it.)
- [ ] **Make sure you can log into [railway.app](https://railway.app) and [vercel.com](https://vercel.com)** with your GitHub account. If you've never signed up, do it now — it's "Login with GitHub" on both. Done-signal: you're staring at an empty dashboard on each.

**Phase 0 done when:** `requirements.txt` exists and is pushed to GitHub, `.env` is gitignored, and both dashboards are open.

---

## Phase 1 — Deploy the backend to Railway (~60–90 min, this is the risky one)

*Goal: a live API URL where `/health` returns ok. This phase carries the only real risk (the heavy Python build), so it gets the most attention and the fallback section.*

- [ ] **In Railway, create a new project → "Deploy from GitHub repo" → pick your VV repo.**
- [ ] **Set the root directory to `/`** (repo root — that's where `api/` and `requirements.txt` live). In Railway this is under the service's **Settings → Root Directory**.
- [ ] **Tell Railway how to start the server.** Railway's Python buildpack may not guess your entrypoint. In **Settings → Deploy → Custom Start Command**, set:
  ```
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  ```
  *Why:* this is the exact entrypoint I confirmed in `api/main.py` (`app` lives in `api.main`). **Watch out:** use `$PORT` (Railway injects it), not a hardcoded `8000`. This is the #1 reason a FastAPI deploy boots but returns "no response."
- [ ] **Add the four environment variables** (Settings → Variables): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_STORAGE_BUCKET` — paste the values from your `.env`. Add one more: `ALLOWED_ORIGINS` — leave it as `http://localhost:3000` *for now*; you'll come back and add the Vercel URL in Phase 2.
- [ ] **Deploy and watch the build logs.** This is the moment the heavy build either works or doesn't. Expect it to take **5–15 minutes** (torch is big). Don't refresh-panic; watch the log stream.
- [ ] **Read the outcome.** See the table below for what "working" vs "too big / failing" looks like and what to do.

### 🐳 The Docker / heavy-build risk — what failure looks like and your fallback

This is the one place the half-day could blow up. Here's how to read it instead of spiraling:

| What you see in Railway logs | What it means | What to do |
|---|---|---|
| Build succeeds, deploy "Active", `/health` returns ok | 🎉 You're past the risk. Skip to Phase 2. | Nothing — celebrate, move on. |
| `Could not find requirements.txt` / `Nixpacks build failed` | Railway didn't detect Python | Confirm root dir is `/` and `requirements.txt` is at the repo root *and pushed*. Re-deploy. |
| Build runs a long time then **fails on `pip install torch`** (out of memory / image too large / build timeout) | The 2–3GB build is choking Railway's builder — *this is the predicted risk* | **Fallback A (try first, 5 min):** in `requirements.txt`, the `torch` line — pin it to the CPU-only build to save ~1GB. The plan flags this in § D-4.1. Replace the `torch==x.y.z` line with the CPU wheel index per [PyTorch's site](https://pytorch.org/get-started/locally/) (select CPU). Re-push, re-deploy. |
| Fallback A still fails the build | Builder genuinely can't handle the image on the current plan | **Fallback B:** switch to the Dockerfile route — create the Dockerfile from `DEPLOYMENT_PLAN.md` § D-4.1 verbatim and a `.dockerignore` from § D-4.3, **build it locally first** (`docker build -t vv-api .` then `docker run -p 8000:8000 --env-file .env vv-api` and `curl localhost:8000/health`). If it runs locally, push the Dockerfile; Railway will use it. *Why local-first:* you debug a 2–3GB build once, on your machine, with fast feedback — not in 15-min Railway cycles. |
| Build succeeds but `/health` times out or 502s | Server isn't binding to Railway's port | Check the start command uses `$PORT`, not `8000`. This is almost always it. |

**Hard stop rule:** if you've burned ~90 minutes on this phase and the build still won't go, *stop and write it down* — don't grind. Drop me a note (`Team_Inbox/mira/`) with the failing log lines and I'll re-cut this phase. A stuck build is a known, solvable thing, not a dead end.

- [ ] **Once the build is up, verify the API is alive.** Railway gives you a public URL (Settings → Networking → "Generate Domain" if there isn't one). Then:
  ```bash
  curl https://<your-railway-url>/health
  ```
  Done-signal: you get back `{"status": "ok"}`.
- [ ] **Verify search actually returns data** (this proves the DB connection works, not just the server):
  ```bash
  curl https://<your-railway-url>/search/text -X POST \
    -H "Content-Type: application/json" \
    -d '{"query": "silk evening gown", "limit": 3}'
  ```
  Done-signal: you get back a JSON list of products, not an error. **If this errors but `/health` worked,** it's almost always a bad `DATABASE_URL` env var — recheck the paste.

**Phase 1 done when:** a public Railway URL returns `{"status": "ok"}` on `/health` AND returns real results on `/search/text`. **Copy that Railway URL — you need it in Phase 2.**

---

## Phase 2 — Deploy the frontend to Vercel (~20 min)

*Goal: a public website URL that loads and talks to your live API. This phase is low-risk — Next.js on Vercel is the smoothest path in the whole stack.*

- [ ] **In Vercel, "Add New Project" → import your VV GitHub repo.**
- [ ] **Set the root directory to `vv-web`** (not the repo root — the Next.js app lives in `vv-web/`). Vercel asks this during import.
- [ ] **Framework: confirm it auto-detected "Next.js."** It will. Leave build/output settings default.
- [ ] **Add one environment variable:** `NEXT_PUBLIC_API_URL` = your Railway URL from Phase 1 (e.g. `https://vv-api-production.up.railway.app`, **no trailing slash**). *Why:* I confirmed `vv-web/src/lib/constants.ts` reads exactly this var; without it the site calls `localhost:8000` and every search fails silently in production.
- [ ] **Deploy.** Next.js builds fast (~2–4 min). Done-signal: Vercel shows "Ready" and gives you a `https://<something>.vercel.app` URL.
- [ ] **Close the CORS loop (don't skip — search breaks without it).** Go *back to Railway* → Variables → set `ALLOWED_ORIGINS` to your new Vercel URL, e.g. `https://vintage-vestige.vercel.app,http://localhost:3000`. Railway redeploys automatically. *Why:* your API currently only trusts `localhost`; the browser will block the Vercel site's requests until the API says it trusts that origin. **This is the classic "works in curl, broken in browser" trap — pre-empted here.**

**Phase 2 done when:** the Vercel URL loads the homepage in your browser AND Railway's `ALLOWED_ORIGINS` includes the Vercel URL.

---

## Phase 3 — Smoke test (~30 min)

*Goal: prove a real human can use it. Click through it like a stranger would. These are from the plan's D-5.3 table, trimmed to what proves "it shipped."*

- [ ] **Homepage loads** — visit your Vercel URL. Hero + featured content render, no blank page.
- [ ] **Search works (THE money test)** — type "silk dress" into the search bar. Results appear with images. *If results are empty but curl worked in Phase 1, it's the CORS step you just did — open browser dev tools (F12) → Console; a CORS error there confirms it.*
- [ ] **Product detail loads** — click any result. The product page renders with image + metadata.
- [ ] **Images load** — confirm product images actually show (they come from Supabase Storage). A few broken ones are fine; a *wall* of broken images means `SUPABASE_URL`/bucket env var is off.
- [ ] **Mobile doesn't explode** — resize the browser to ~375px wide. Layout stacks, nothing overflows horribly. (Cosmetic glitches → parking lot, not a blocker.)

**Phase 3 done when:** you, on the public URL, typed a search and saw real products with images.

---

## ✅ DEFINITION OF DONE — you shipped

**VV is shipped the moment both of these are true on the *public* URLs (not localhost):**

1. **The Vercel URL loads** in a browser you're not logged into.
2. **One real search returns real results with images.**

That's it. That's the win. The thing has left your machine and is on the internet where someone else can use it. **Three months of "almost" ends at this checkbox.** Put the URL somewhere you'll see it — it goes on job applications.

- [ ] **🏁 VV IS LIVE.** ← check this and you're done for real.
- [ ] *(Optional, 2 min)* Send yourself the live URL in a message, or text it to someone. Make it real.
- [ ] *(Optional)* Tell Larry it's live so I can mark the deploy done in the project tracker.

---

## Parking lot — the "I want to fix one thing" list

When the itch hits mid-deploy, it goes **here**, and you keep moving. None of this blocks shipping:

- [ ] Trim `requirements.txt` to only what's needed (CPU-only torch, drop dev deps) — *post-ship optimization.*
- [ ] Frontend test files (plan's D-2.2 / D-2.3) — *nice, not blocking.*
- [ ] CI/CD GitHub Action (plan's D-6.1).
- [ ] Custom domain + error monitoring (plan's D-7.x).
- [ ] Update the "Built With" text (plan still says Qdrant; it's pgvector now) — D-7.1.
- [ ] _(add your own as they hit — write, don't fix)_

---

## If you get stuck

A stuck deploy is normal and fixable — it is *not* a sign the project was a mistake. The two likely stall points are **(a)** the heavy Python build in Phase 1 (fallbacks are right there in the Docker box) and **(b)** CORS in Phase 2/3 (the loop-closing step pre-empts it). If either fights you for more than ~90 min, write down the exact error and drop it to `Team_Inbox/mira/` — I'll re-cut the affected phase. Plans are hypotheses; I revise without defending the stale version.

— Mira


# Vintage Vestige — Custom Domain Addendum to the Ship-It Checklist (0083)

**From:** Mira (implementation planner)
**For:** Jen
**Date:** 2026-06-02
**Reads on top of:** `0083_mira_vv-deploy-checklist.md` (your five-phase deploy flow)
**Goal:** fold `vintagevestige.com` into the existing deploy so the live site answers on *your* domain, not a `*.vercel.app` URL.

---

## Read this first (30 seconds)

You bought `vintagevestige.com` from Namecheap. Good — that's the one piece that makes VV feel like a real portfolio piece instead of a demo link.

**This is an addendum, not a new checklist.** You still run all five phases of 0083 exactly as written. The domain work is a *thin layer that slots in after the site is already live on the default URLs.* I'm calling out only the steps that change, so you run one coherent flow instead of diffing two documents.

**The golden rule for domains:** get it working on the ugly default URLs *first*, then attach the pretty domain. Never debug "is my app broken?" and "is my DNS broken?" at the same time — that's two unknowns multiplying. So: **finish 0083 Phase 3 (a real search works on the `.vercel.app` URL) before you touch anything below.** If 0083's Definition of Done isn't met yet, stop here and come back.

What I re-verified in the repo before writing this (so you can trust it):
- Backend reads `ALLOWED_ORIGINS` from env, comma-split — `api/main.py:9`. ✓
- Frontend reads `NEXT_PUBLIC_API_URL` from env — `vv-web/src/lib/constants.ts:1-2`. ✓
- There is **no** existing custom-domain or extra CORS config anywhere in the repo — so nothing in code needs to change. This is all dashboard + env work. ✓

One concept you'll need, defined once: **DNS** is the phone book that maps `vintagevestige.com` → the server that actually answers. You edit it in Namecheap. Two record types matter here:
- **A record** — points a name straight at an IP address (used for the bare/"apex" domain `vintagevestige.com`).
- **CNAME record** — points one name at *another name* (used for `www.vintagevestige.com` → Vercel's hostname).

---

## The one decision to make up front: apex or www?

Pick which address is your "real" one. Both will work; you just decide which is canonical and which redirects.

- **Recommended: make `vintagevestige.com` (the apex, no `www`) your primary.** It's the cleaner thing to put on a résumé/portfolio, and Vercel will auto-redirect `www` → apex for you. This addendum assumes apex-primary.
- You'll still add *both* in Vercel so `www.vintagevestige.com` doesn't 404 — Vercel just treats one as the redirect target.

You make this choice once, in the Vercel step below. Don't overthink it.

---

## The API-subdomain decision (do you need `api.vintagevestige.com`?)

Your backend is on Railway at some `*.up.railway.app` URL (from 0083 Phase 1; Mel confirmed in `0097`/`0102` that VV deploys on Railway via buildpack — no Docker). The question: leave it on that default URL, or give it a pretty subdomain like `api.vintagevestige.com`?

| Option | What it costs you | What you gain |
|---|---|---|
| **Leave it on `*.up.railway.app`** (recommended) | Nothing — it already works | The API URL is invisible to humans; only your frontend code ever sees it. Visitors only ever see `vintagevestige.com`. |
| **Add `api.vintagevestige.com`** | One more CNAME in Namecheap, one more custom-domain step in Railway, one more thing that can break DNS-side, and a re-point of `NEXT_PUBLIC_API_URL` | A tidier-looking API URL that essentially no one but you will ever look at |

**My recommendation: skip the API subdomain.** VV is a portfolio piece, not a business. Recruiters and visitors hit `vintagevestige.com` and never see the API address — it lives only inside your frontend's `NEXT_PUBLIC_API_URL`. The subdomain is pure polish with a real failure surface attached, and it buys you nothing a hiring manager will notice. Keep the Railway default URL.

**The rest of this addendum assumes you took the recommendation** (frontend domain only, API stays on Railway's default). If you later decide you want `api.vintagevestige.com` anyway, there's a short optional section at the very bottom — but ignore it for now.

---

## What changes in your 0083 flow

Here's the whole picture before the steps, so you can see where this lands. Your 0083 phases are unchanged through Phase 3. The domain work inserts as **Phase 3.5**, and the Definition of Done gets a stricter line.

```
0083 Phase 0  Pre-flight ............................. UNCHANGED
0083 Phase 1  Backend → Railway ...................... UNCHANGED  (API stays on *.up.railway.app)
0083 Phase 2  Frontend → Vercel ...................... UNCHANGED  (deploy to the default .vercel.app URL first)
0083 Phase 3  Smoke test ............................. UNCHANGED  (prove a real search works BEFORE adding the domain)
─────────────────────────────────────────────────────────────
NEW  Phase 3.5  Attach the custom domain ............. ADDED      (this addendum)
0083 "Definition of Done" ............................ TIGHTENED  (now requires https://vintagevestige.com)
```

The only *existing* 0083 step that changes wording is the CORS step (Phase 2, the "Close the CORS loop" checkbox). I call out the exact change in Phase 3.5 below — don't go editing Phase 2 mid-run; just know the `ALLOWED_ORIGINS` value you set there is no longer the *final* value.

---

## NEW Phase 3.5 — Attach `vintagevestige.com` (~30–45 min of work + waiting)

*Goal: `https://vintagevestige.com` loads your already-working site. This phase is mostly waiting on DNS, not doing — budget patience, not effort.*

*Prerequisite: 0083 Phase 3 passed — a real search returned real results on your `.vercel.app` URL. Do not start otherwise.*

### Step 1 — Add the domain in Vercel (this comes first, on purpose)

You add the domain in Vercel *before* touching Namecheap, because Vercel will then *tell you the exact DNS records to create* — you copy its values rather than guessing mine.

- [ ] In Vercel, open your VV project → **Settings → Domains**.
- [ ] **Add `vintagevestige.com`** (the apex). Click Add.
- [ ] **Also add `www.vintagevestige.com`.** When Vercel asks, set it to **redirect to `vintagevestige.com`** (apex-primary, per the decision above).
- [ ] Vercel will now show one of two setups with **the exact records to create**. Screenshot or copy that panel — those values are the source of truth, not this doc. It'll be one of:
  - **A-record style:** an **A record** for the apex pointing at a Vercel IP (commonly `76.76.21.21`, but *use whatever Vercel shows you*), plus a **CNAME** for `www` → `cname.vercel-dns.com`.
  - **Nameserver style:** Vercel asks you to change Namecheap's nameservers to point at Vercel entirely. **Don't pick this one** unless Vercel forces it — changing nameservers hands all your DNS to Vercel and is more than a portfolio site needs. The A+CNAME route keeps Namecheap in control and is simpler to reason about. Stick with the records it shows for the apex/www unless it gives you no choice.

  *Why Vercel-first:* the IP and CNAME target can change over time; reading them off Vercel's own panel means you can never copy a stale value out of a checklist (including this one).

### Step 2 — Create the matching DNS records in Namecheap

- [ ] Log into Namecheap → **Domain List** → click **Manage** next to `vintagevestige.com` → open the **Advanced DNS** tab. (That's the tab where DNS records live — *not* the "Domain" tab.)
- [ ] **Heads-up — delete the parking records first.** A freshly-bought Namecheap domain ships with default "parking" records (often a CNAME on `www` → `parkingpage.namecheap.com` and a URL-redirect record on `@`). **Delete those** — if you leave them, they fight the records you're about to add and the domain will resolve to a Namecheap parking page instead of your site. This is the single most common Namecheap-first-domain gotcha.
- [ ] **Add the apex A record** using Vercel's value:
  - Type: **A Record**
  - Host: **`@`** (that's how Namecheap writes the bare/apex domain)
  - Value: **the IP Vercel showed you** (e.g. `76.76.21.21` — verify against Vercel)
  - TTL: **Automatic** is fine
- [ ] **Add the www CNAME record:**
  - Type: **CNAME Record**
  - Host: **`www`**
  - Value: **`cname.vercel-dns.com`** (or whatever target Vercel showed — copy it exactly, with no trailing dot issues; Namecheap handles the dot)
  - TTL: **Automatic**
- [ ] Save. **Watch out:** Namecheap sometimes auto-appends your domain to a CNAME value (turning `cname.vercel-dns.com` into `cname.vercel-dns.com.vintagevestige.com`). After saving, re-open the record and confirm the value is *exactly* what Vercel gave you. This silent mangling is a classic head-scratcher.

### Step 3 — Wait for DNS, let Vercel verify, let SSL provision

- [ ] **Go back to Vercel → Settings → Domains and wait for the checkmarks.** Vercel polls DNS and flips the domain from "Invalid Configuration" / "Pending" to **"Valid"** once it sees your records. **This is not instant.** DNS propagation can take anywhere from a few minutes to a few hours (occasionally longer). **Don't panic if it says invalid for the first 20–30 minutes — that's normal propagation lag, not a mistake on your part.** Go do something else and check back.
- [ ] **SSL is automatic — you do nothing.** Once Vercel sees valid DNS, it auto-provisions an HTTPS certificate for `vintagevestige.com`. You don't buy or install anything; `https://` just starts working a few minutes after the domain verifies. (If you load the site during the gap and the browser warns about the certificate, that's the cert still minting — wait, don't troubleshoot.)
- [ ] **Done-signal for this step:** Vercel shows `vintagevestige.com` as **Valid**, and `https://vintagevestige.com` loads your homepage in a browser.

### Step 4 — Fix CORS for the real domain (THIS is the step that breaks the app if you skip it)

This is the one that bites. Your site now loads at `https://vintagevestige.com`, but **search will silently fail** until the backend learns to trust that origin — the exact same "works in curl, broken in browser" CORS trap 0083 warned about, except now the trusted origin changed out from under you.

Back in 0083 Phase 2 you set Railway's `ALLOWED_ORIGINS` to your `.vercel.app` URL. That value is now **stale** — the browser is sending requests *from* `https://vintagevestige.com`, and the API doesn't trust it yet.

- [ ] **In Railway → your service → Variables, update `ALLOWED_ORIGINS`.** I verified the var name against `api/main.py:9` — it splits on commas with **no spaces** between entries, so format it exactly like this:
  ```
  https://vintagevestige.com,https://www.vintagevestige.com,http://localhost:3000
  ```
  *Why all three:* the apex is your primary; `www` is included so a `www` visit (before the redirect kicks in) still works; `localhost:3000` stays so your local dev keeps working. **Watch out — no spaces after the commas**, because `main.py` does a literal `.split(",")` and a leading space would make the origin `" https://www..."`, which won't match and search breaks. (You can drop the old `.vercel.app` entry or leave it; leaving it does no harm.)
- [ ] **Railway redeploys automatically** when you change a variable — but confirm it actually kicked off (watch for a new deploy in the Deployments tab). **A var change does nothing until the service restarts with the new value.** Wait for it to go "Active" again.
- [ ] **Does the *frontend* env var need to change?** **No** — because you kept the API on Railway's default URL (per the recommendation). `NEXT_PUBLIC_API_URL` in Vercel still points at the same `*.up.railway.app` URL it did in 0083 Phase 2. *Nothing on the frontend changes.* (The only world where you'd touch `NEXT_PUBLIC_API_URL` is if you added `api.vintagevestige.com` — see the optional section, which you're skipping.)

### Step 5 — Re-verify on the real domain

- [ ] **`https://vintagevestige.com` loads** the homepage, padlock (HTTPS) showing, no cert warning.
- [ ] **A real search returns real results *with images*** — type "silk dress" on `vintagevestige.com` (not the vercel URL). Results render with images. *If results are empty here but they worked on the `.vercel.app` URL in 0083 Phase 3, it's the CORS step you just did — open dev tools (F12) → Console; a CORS error naming `vintagevestige.com` confirms `ALLOWED_ORIGINS` didn't take (recheck for stray spaces, and that the Railway redeploy finished).*
- [ ] **`www.vintagevestige.com` redirects** to `vintagevestige.com` (or at least loads). Type it in to confirm.

**Phase 3.5 done when:** `https://vintagevestige.com` loads over HTTPS, and a real search there returns real products with images.

---

## ✅ TIGHTENED DEFINITION OF DONE

0083's Definition of Done was "the `.vercel.app` URL loads and one search returns results." Now that you own the domain, the finish line moves up to:

> **`https://vintagevestige.com` loads in a browser you're not logged into, over HTTPS, and one real search there returns real results with images.**

That's the new "VV is live." The thing isn't just on the internet — it's on the internet *at your own address*, which is the version that goes on a portfolio and a résumé.

- [ ] **🏁 VV IS LIVE AT vintagevestige.com.** ← the real finish line now.
- [ ] *(Optional)* Tell Larry it's live on the custom domain so the deploy can be marked done in the tracker.

---

## Parking lot — domain polish that is NOT blocking

Same rule as 0083: the itch goes here, you keep moving. None of this blocks the win above.

- [ ] `api.vintagevestige.com` subdomain — *recommended-against; pure polish.* (Optional section below if you ever want it.)
- [ ] Email on the domain (e.g. `hello@vintagevestige.com`) — separate from web hosting, totally optional, not needed for a portfolio site.
- [ ] A custom 404 / branding pass on the domain — cosmetic, post-ship.

---

## OPTIONAL (skip for now) — if you ever decide you DO want `api.vintagevestige.com`

You're not doing this today, but so the decision is reversible without me re-cutting anything, here's the shape. Only touch this *after* the Definition of Done above is met and `vintagevestige.com` is solidly live.

1. **Railway → your service → Settings → Networking → Custom Domain → add `api.vintagevestige.com`.** Railway will show you a **CNAME target** to point at.
2. **Namecheap → Advanced DNS → add a CNAME:** Host `api`, Value = the target Railway showed you.
3. **Wait for DNS + Railway's auto-SSL**, same waiting game as the frontend.
4. **Re-point the frontend:** in **Vercel → your project → Settings → Environment Variables**, change `NEXT_PUBLIC_API_URL` from the `*.up.railway.app` URL to `https://api.vintagevestige.com` (no trailing slash). **Then trigger a Vercel redeploy** — env var changes don't apply to the running site until you redeploy. (`NEXT_PUBLIC_*` vars are baked in at build time, so a redeploy is mandatory, not optional, here.)
5. **CORS is unaffected** — `ALLOWED_ORIGINS` is about what origin the *browser* requests come from (`vintagevestige.com`), not where the API lives, so you don't change it for this.

That's the whole thing. But again — for a portfolio piece, don't. The Railway default URL is invisible and works.

---

## If you get stuck

Two likely stall points, both normal and fixable:
- **DNS "won't verify."** It's almost always (a) propagation lag — wait longer; or (b) a leftover Namecheap parking record fighting your new one — re-check Advanced DNS and delete the defaults; or (c) Namecheap mangling the CNAME value — re-open the record and confirm it's *exactly* Vercel's target.
- **Site loads but search is dead on the new domain.** It's CORS — `ALLOWED_ORIGINS` on Railway, watch for stray spaces, and confirm the redeploy finished.

If either fights you for more than ~45 min, write down the exact symptom (and a screenshot of the Vercel Domains panel / Railway Variables) and drop it to `Team_Inbox/mira/` — I'll re-cut this phase. Plans are hypotheses; I revise without defending the stale version.

— Mira
