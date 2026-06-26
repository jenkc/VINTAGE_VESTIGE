# KG_PHASE6_API_LAYER.md
# Phase 6 — FastAPI Graph Layer

**Duration:** 1 week  
**Status:** 🔲 Not Started — begins after Phase 5 (Neptune loaded, validation queries passing)  
**Deliverable:** New `/graph` router live alongside existing API, all endpoints tested  
**Last Updated:** March 2026 (v2.0)

---

## Context

The existing FastAPI backend has 13 endpoints across 4 routers: search, products,
bridges, filters. This phase adds a fifth router — `graph` — that speaks to Neptune
for traversal queries. The two database layers coexist permanently:

| Layer | Data Store | Connection | What it's for |
|---|---|---|---|
| Existing API | Supabase (pgvector) | SQLAlchemy Session via `get_db()` | Display data, flat lookups, vector search |
| New graph API | Neptune (openCypher) | Gremlin client via `get_neptune_client()` | Multi-step traversal, influence chains, movements |

**Both databases are open simultaneously in the same FastAPI process.** They use
completely different connection models. This is intentional and permanent.

---

## Dual-Connection Pattern — Critical Detail

This is the most important architectural fact in Phase 6. The existing codebase
uses a SQLAlchemy Session pattern:

```python
# Existing — Supabase via SQLAlchemy (unchanged)
def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

# Used in existing routers like:
@router.get("/products/{id}")
async def get_product(id: int, db: Session = Depends(get_db)):
    ...
```

Neptune uses a Gremlin websocket client — completely different:

```python
# New — Neptune via Gremlin (added in Phase 6)
@lru_cache(maxsize=1)
def get_neptune_client() -> client.Client:
    ...

# Used in graph router like:
@router.get("/graph/influence-chain/{garment_id}")
async def influence_chain(
    garment_id: int,
    neptune: client.Client = Depends(get_neptune_client)
):
    ...
```

These two dependencies are completely independent. A graph endpoint that needs
to supplement Neptune results with Supabase data (e.g., getting a product's
full metadata after traversal) can declare both:

```python
@router.get("/graph/influence-chain/{garment_id}")
async def influence_chain(
    garment_id: int,
    neptune: client.Client = Depends(get_neptune_client),
    db: Session = Depends(get_db)           # add when needed for Supabase join
):
    chain = get_influence_chain(neptune, garment_id)
    # enrich with Supabase data if needed
    return chain
```

---

## File Structure

```
api/
├── graph/
│   ├── __init__.py
│   ├── neptune.py          ← Neptune Gremlin client + all query functions
│   └── queries.py          ← Complex Cypher strings (keep separate from logic)
├── routers/
│   ├── graph.py            ← New /graph router (mirrors existing router pattern)
│   └── ...existing routers (unchanged)
└── schemas/
    ├── graph.py            ← Pydantic response models for graph endpoints
    └── ...existing schemas (unchanged)
```

---

## Checklist

### Neptune Client (`api/graph/neptune.py`)
- [ ] `get_neptune_client()` singleton using `@lru_cache(maxsize=1)`
- [ ] Uses `gremlin_python` driver with openCypher endpoint
- [ ] Connection string from `NEPTUNE_ENDPOINT` env var (added to `.env` in Phase 2)
- [ ] Graceful error if Neptune unreachable → returns 503, NOT 500
- [ ] `execute_cypher(client, query, params)` helper — takes client as argument (not global)
- [ ] All query functions implemented (each takes `neptune_client` as first arg):
  - [ ] `get_influence_chain(client, garment_id, depth, semantic_type)`
  - [ ] `get_design_movement(client, element_name, min_eras)`
  - [ ] `get_style_ancestry(client, garment_id, limit)`
  - [ ] `get_modern_echoes_graph(client, garment_id, limit)`
  - [ ] `get_cross_institutional_bridges(client, min_score, limit)`
  - [ ] `get_design_elements(client, sort_by, limit)`
  - [ ] `get_bridge_detail_graph(client, bridge_id)`

### Graph Schemas (`api/schemas/graph.py`)
- [ ] `InfluenceChainNode` — garment data at one step in chain
- [ ] `InfluenceChainEdge` — bridge data between steps
- [ ] `InfluenceChainResponse` — full chain with ordered nodes + edges
- [ ] `DesignMovementGarment` — garment + bridge within a movement
- [ ] `DesignMovementResponse` — element metadata + all garments across eras
- [ ] `DesignElementSummary` — name, bridge_count, aat_uri, era_span
- [ ] `CrossInstitutionalBridge` — source garment + bridge + target garment

### Graph Router (`api/routers/graph.py`)
- [ ] All endpoints registered with `/graph` prefix
- [ ] Consistent error handling: Neptune down → 503 with message, not 500
- [ ] Response times logged (Neptune serverless can cold-start 2–5s)
- [ ] Endpoints implemented:
  - [ ] `GET /graph/influence-chain/{garment_id}`
  - [ ] `GET /graph/design-movement/{element_name}`
  - [ ] `GET /graph/style-ancestry/{garment_id}`
  - [ ] `GET /graph/modern-echoes/{garment_id}`
  - [ ] `GET /graph/cross-institutional`
  - [ ] `GET /graph/design-elements`
  - [ ] `GET /graph/bridge/{bridge_id}`
- [ ] Router registered in `api/main.py` (one line: `app.include_router(graph_router)`)

### `api/main.py` update
- [ ] Import and include graph router (existing routers untouched)
- [ ] `NEPTUNE_ENDPOINT` added to env var validation on startup

### Integration Tests (`tests/integration/test_graph_endpoints.py`)
- [ ] Tests run against live Neptune (not mocked)
- [ ] All 7 endpoints return 200 with valid schema on known data
- [ ] Empty results handled gracefully: returns `[]` not 500
- [ ] Neptune unavailable: returns 503 not 500
- [ ] Test skipped gracefully if `NEPTUNE_ENDPOINT` not set (local dev without Neptune)

### Documentation
- [ ] All 7 graph endpoints visible in FastAPI auto-docs (`/docs`)
- [ ] `API_SPEC.md` updated with graph endpoints section
- [ ] `ARCHITECTURE.md` updated: Neptune added to database layer

---

## Implementation Reference

### Neptune Client + execute_cypher

```python
# api/graph/neptune.py
from gremlin_python.driver import client, serializer
from functools import lru_cache
from fastapi import HTTPException
import os, logging

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_neptune_client() -> client.Client:
    """
    Singleton Neptune Gremlin client.
    Completely separate from the SQLAlchemy Session used for Supabase.
    """
    endpoint = os.getenv("NEPTUNE_ENDPOINT")
    port = os.getenv("NEPTUNE_PORT", "8182")
    if not endpoint:
        raise RuntimeError("NEPTUNE_ENDPOINT not set in environment")
    return client.Client(
        f"wss://{endpoint}:{port}/gremlin",
        "g",
        message_serializer=serializer.GraphSONSerializersV2d0()
    )

def execute_cypher(neptune_client: client.Client, query: str, params: dict = None) -> list:
    """
    Execute an openCypher query against Neptune.
    Returns empty list on failure rather than crashing (caller decides response code).
    """
    try:
        result = neptune_client.submit(query, parameters=params or {})
        return result.all().result()
    except Exception as e:
        logger.error(f"Neptune query failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Graph database temporarily unavailable. Flat search still works."
        )
```

### Influence Chain Query

```python
def get_influence_chain(
    neptune_client: client.Client,
    garment_id: int,
    depth: int = 3,
    semantic_type: str = None
) -> list:
    type_filter = (
        f"AND b1.semantic_type = '{semantic_type}' AND b2.semantic_type = '{semantic_type}'"
        if semantic_type else ""
    )
    query = f"""
        MATCH path = (start:Garment {{id: $garment_id}})
          -[:CONNECTED_VIA]->(b1:Bridge)
          -[:CONNECTS]->(g2:Garment)
          -[:CONNECTED_VIA]->(b2:Bridge)
          -[:CONNECTS]->(g3:Garment)
        WHERE b1.score > 0.55 {type_filter}
          AND b2.score > 0.55
        RETURN
          start.title AS title_1, start.era AS era_1,
          start.image_url AS img_1, start.platform AS platform_1,
          b1.narrative AS narrative_1, b1.semantic_type AS type_1, b1.score AS score_1,
          g2.title AS title_2, g2.era AS era_2,
          g2.image_url AS img_2, g2.platform AS platform_2,
          b2.narrative AS narrative_2, b2.semantic_type AS type_2, b2.score AS score_2,
          g3.title AS title_3, g3.era AS era_3,
          g3.image_url AS img_3, g3.platform AS platform_3
        ORDER BY (b1.score + b2.score) DESC
        LIMIT 5
    """
    return execute_cypher(neptune_client, query, {
        "garment_id": f"garment_{garment_id}"
    })
```

### Design Movement Query

```python
def get_design_movement(
    neptune_client: client.Client,
    element_name: str,
    min_eras: int = 2
) -> list:
    query = """
        MATCH (de:DesignElement {name: $element_name})
          <-[:ARGUES_THROUGH]-(b:Bridge)
          -[:CONNECTS]->(g:Garment)
          -[:FROM_ERA]->(era:Era)
        WITH de, g, b, era
        ORDER BY era.start_year ASC
        WITH de,
             collect(DISTINCT era.name) AS eras,
             collect({
               garment_title: g.title,
               garment_era: g.era,
               garment_platform: g.platform,
               garment_image: g.image_url,
               bridge_score: b.score,
               bridge_narrative: b.narrative,
               bridge_type: b.semantic_type
             }) AS garments
        WHERE size(eras) >= $min_eras
        RETURN de.name AS element, de.category AS category,
               de.aat_uri AS aat_uri, eras, garments
    """
    return execute_cypher(neptune_client, query, {
        "element_name": element_name,
        "min_eras": min_eras
    })
```

### Cross-Institutional Bridge Query

```python
def get_cross_institutional_bridges(
    neptune_client: client.Client,
    min_score: float = 0.65,
    limit: int = 20
) -> list:
    """
    The query that proves the paper's argument.
    These connections cannot exist in any single museum's database.
    """
    query = """
        MATCH (g1:Garment {platform: 'met_museum'})
          -[:CONNECTED_VIA]->(b:Bridge)
          -[:CONNECTS]->(g2:Garment {platform: 'smithsonian'})
        WHERE b.score >= $min_score
        MATCH (b)-[:ARGUES_THROUGH]->(de:DesignElement)
        RETURN
          g1.title AS met_title, g1.era AS met_era, g1.image_url AS met_image,
          b.score AS score, b.narrative AS narrative, b.semantic_type AS semantic_type,
          g2.title AS smithsonian_title, g2.era AS smithsonian_era,
          g2.image_url AS smithsonian_image,
          collect(de.name) AS shared_elements
        ORDER BY b.score DESC
        LIMIT $limit
    """
    return execute_cypher(neptune_client, query, {
        "min_score": min_score,
        "limit": limit
    })
```

### Style Ancestry Query (graph version — richer than existing Supabase version)

```python
def get_style_ancestry(
    neptune_client: client.Client,
    garment_id: int,
    limit: int = 5
) -> list:
    """
    Graph version is richer than the existing /products/{id}/style-ancestry endpoint:
    - Includes DesignElement nodes (what argument connects them)
    - Includes semantic_type (what kind of connection)
    - Follows graph edges rather than querying style_bridges table directly
    """
    query = """
        MATCH (modern:Garment {id: $garment_id})
          -[:CONNECTED_VIA]->(b:Bridge)
          -[:CONNECTS]->(historical:Garment)
        WHERE historical.platform IN ['met_museum', 'smithsonian']
          AND b.score > 0.55
        MATCH (b)-[:ARGUES_THROUGH]->(de:DesignElement)
        RETURN
          historical.title AS title, historical.era AS era,
          historical.image_url AS image_url, historical.platform AS platform,
          b.score AS bridge_score, b.narrative AS narrative,
          b.semantic_type AS semantic_type,
          collect(de.name) AS design_elements
        ORDER BY b.score DESC
        LIMIT $limit
    """
    return execute_cypher(neptune_client, query, {
        "garment_id": f"garment_{garment_id}",
        "limit": limit
    })
```

---

## Graph Router Skeleton

```python
# api/routers/graph.py
from fastapi import APIRouter, Depends, Query
from gremlin_python.driver import client
from api.graph.neptune import (
    get_neptune_client,
    get_influence_chain, get_design_movement,
    get_style_ancestry, get_modern_echoes_graph,
    get_cross_institutional_bridges,
    get_design_elements, get_bridge_detail_graph
)
from api.schemas.graph import (
    InfluenceChainResponse, DesignMovementResponse,
    DesignElementSummary, CrossInstitutionalBridge
)

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/influence-chain/{garment_id}")
async def influence_chain(
    garment_id: int,
    semantic_type: str = Query(None),
    neptune: client.Client = Depends(get_neptune_client)
) -> InfluenceChainResponse:
    return get_influence_chain(neptune, garment_id, semantic_type=semantic_type)

@router.get("/design-movement/{element_name}")
async def design_movement(
    element_name: str,
    min_eras: int = Query(2, ge=2),
    neptune: client.Client = Depends(get_neptune_client)
) -> DesignMovementResponse:
    return get_design_movement(neptune, element_name, min_eras=min_eras)

@router.get("/cross-institutional")
async def cross_institutional(
    min_score: float = Query(0.65, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    neptune: client.Client = Depends(get_neptune_client)
) -> list[CrossInstitutionalBridge]:
    return get_cross_institutional_bridges(neptune, min_score=min_score, limit=limit)

# ... repeat pattern for remaining 4 endpoints
```

---

## Endpoint Reference

| Endpoint | Method | Params | Returns |
|---|---|---|---|
| `/graph/influence-chain/{garment_id}` | GET | `semantic_type` | 3-hop chain with narratives |
| `/graph/design-movement/{element_name}` | GET | `min_eras` | Garments through element, by era |
| `/graph/style-ancestry/{garment_id}` | GET | `limit` | Historical ancestors + design elements |
| `/graph/modern-echoes/{garment_id}` | GET | `limit` | Contemporary descendants + design elements |
| `/graph/cross-institutional` | GET | `min_score`, `limit` | Met ↔ Smithsonian bridges |
| `/graph/design-elements` | GET | `sort_by`, `limit` | Full DesignElement vocabulary |
| `/graph/bridge/{bridge_id}` | GET | — | Bridge detail with garments + elements |

---

## Performance Targets

| Endpoint | Target | Notes |
|---|---|---|
| `/graph/style-ancestry` | < 300ms | Simple 2-hop traversal |
| `/graph/influence-chain` | < 800ms | 3-hop traversal |
| `/graph/design-movement` | < 1000ms | Fan-out across all bridges |
| `/graph/cross-institutional` | < 500ms | Filtered traversal |
| `/graph/design-elements` | < 200ms | Node property scan |

Neptune serverless cold start can add 2–5 seconds on first request after idle.
Cache results with `functools.lru_cache` for repeated identical queries.

---

## Estimated Effort

| Task | Time |
|---|---|
| Neptune client + dual-connection wiring | 2 hours |
| All 7 query functions | 6 hours |
| Pydantic schemas | 2 hours |
| Router + endpoint wiring | 3 hours |
| Integration tests | 3 hours |
| Debug + performance tuning | 3 hours |
| **Total** | **~19 hours** |
