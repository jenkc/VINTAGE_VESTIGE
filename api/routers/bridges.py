from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from storage.database import get_db
from api.schemas.bridge import BridgeResult, BridgeListResponse, BridgeStats
from analysis.bridge_queries import get_top_bridges, get_bridge_detail, get_bridge_between, get_bridge_stats

router = APIRouter(prefix="/bridges", tags=["bridges"])


@router.get("/top", response_model=BridgeListResponse)
def top_bridges(
    bridge_type: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    source_platform: str | None = None,
    target_platform: str | None = None,
    temporal_type: str | None = None,
    crossing_type: str | None = None,
    connection_mode: str | None = None,
    primary_axis: str | None = None,
    shared_function: str | None = None,
    sort: str = 'default',
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_top_bridges(
        db, bridge_type=bridge_type, min_score=min_score, max_score=max_score,
        source_platform=source_platform, target_platform=target_platform,
        temporal_type=temporal_type, crossing_type=crossing_type,
        connection_mode=connection_mode, primary_axis=primary_axis, shared_function=shared_function,
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