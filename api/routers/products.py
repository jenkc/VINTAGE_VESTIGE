from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from storage.database import get_db, Product
from api.schemas.product import ProductDetail
from api.schemas.bridge import BridgeListResponse
from analysis.bridge_queries import get_bridges_for_product, get_modern_echoes, get_style_ancestry, get_style_siblings

router = APIRouter(prefix="/products", tags=["products"])
    
@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get full details for a single product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductDetail.model_validate(product)

@router.get("/{product_id}/bridges", response_model=BridgeListResponse)
def product_bridges(
    product_id: int,
    bridge_type: str | None = None,
    min_score: float | None = None,
    limit: int = 12,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_bridges_for_product(db, product_id, bridge_type=bridge_type, min_score=min_score, limit=limit, offset=offset)
    return BridgeListResponse.model_validate(result)

@router.get("/{product_id}/modern-echoes", response_model=BridgeListResponse)
def product_modern_echoes(
    product_id: int,
    min_score: float | None = None,
    limit: int = 12,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_modern_echoes(db, product_id, min_score=min_score, limit=limit, offset=offset)
    return BridgeListResponse.model_validate(result)


@router.get("/{product_id}/style-ancestry", response_model=BridgeListResponse)
def product_style_ancestry(
    product_id: int,
    min_score: float | None = None,
    limit: int = 12,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_style_ancestry(db, product_id, min_score=min_score, limit=limit, offset=offset)
    return BridgeListResponse.model_validate(result)

@router.get("/{product_id}/style-siblings", response_model=BridgeListResponse)
def product_style_siblings(
    product_id: int,
    min_score: float | None = None,
    limit: int = 12,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    result = get_style_siblings(db, product_id, min_score=min_score, limit=limit, offset=offset)
    return BridgeListResponse.model_validate(result)