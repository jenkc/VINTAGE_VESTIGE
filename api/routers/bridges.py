from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from storage.database import get_db
from api.schemas.bridge import BridgeResult, BridgeListResponse, BridgeStats
from analysis.bridge_queries import get_top_bridges, get_bridge_detail, get_bridge_between, get_bridge_stats

router = APIRouter(prefix="/bridges", tags=["bridges"])


@router.get("/top", response_model=BridgeListResponse)
def top_bridges(
    connection_mode: str | None = None,     # shared_entity | lineage | visual_echo
    crossing_type: str | None = None,       # cross_culture | cross_category | cross_category_culture | same_context
    min_score: float | None = None,
    max_score: float | None = None,
    min_year_gap: int | None = None,
    directed: bool | None = None,
    sort: str = 'default',
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_top_bridges(
        db, connection_mode=connection_mode,
        crossing_type=crossing_type,
        min_score=min_score, max_score=max_score,
        min_year_gap=min_year_gap, directed=directed,
        sort=sort, limit=limit, offset=offset,
    )
    return result


@router.get("/stats", response_model=BridgeStats)
def bridge_stats(
    db: Session = Depends(get_db)
):
    return get_bridge_stats(db)


@router.get("/between/{a}/{b}", response_model=BridgeResult)
def bridge_between(
    a: int,
    b: int,
    db: Session = Depends(get_db)
):
    result = get_bridge_between(db, a, b)
    if not result:
        raise HTTPException(status_code=404, detail="Bridge not found")
    return BridgeResult.model_validate(result)


@router.get("/{bridge_id}", response_model=BridgeResult)
def bridge_detail(
    bridge_id: int,
    db: Session = Depends(get_db)
):
    result = get_bridge_detail(db, bridge_id)
    if not result:
        raise HTTPException(status_code=404, detail="Bridge not found")
    return BridgeResult.model_validate(result)
