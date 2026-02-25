from fastapi import APIRouter, Depends
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from storage.database import get_db, Product
from api.schemas.filters import FilterOptions

router = APIRouter(tags=["filters"])

@router.get("/filters", response_model=FilterOptions)
def get_filters(db: Session = Depends(get_db)):
    """Query SELECT DISTINCT for each field, filter out nulls, sort."""
    eras = sorted([r[0] for r in db.query(Product.era).distinct() if r[0]])
    decades = sorted([r[0] for r in db.query(Product.decade).distinct() if r[0]])
    vibes = sorted([r[0] for r in db.query(Product.vibe).distinct() if r[0]])
    garment_types = sorted([r[0] for r in db.query(Product.garment_type).distinct() if r[0]])
    occasions = sorted([r[0] for r in db.query(Product.occasion).distinct() if r[0]])
    fit_styles = sorted([r[0] for r in db.query(Product.fit_style).distinct() if r[0]])
    cultures = sorted([r[0] for r in db.query(Product.culture).distinct() if r[0]])
    materials = sorted([r[0] for r in db.query(Product.material).distinct() if r[0]])

    return FilterOptions(
        eras=eras,
        decades=decades,
        vibes=vibes,
        garment_types=garment_types,
        occasions=occasions,
        fit_styles=fit_styles,
        cultures=cultures,
        materials=materials,
    )
