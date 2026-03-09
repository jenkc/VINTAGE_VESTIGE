from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from storage.database import get_db
from api.schemas.explore import FunctionListResponse, FunctionDetailResponse, FunctionSummary
from api.schemas.product import ProductSummary
from analysis.product_queries import get_all_social_functions, get_products_by_function

router = APIRouter(prefix="/explore", tags=["explore"])


@router.get("/functions", response_model=FunctionListResponse)
def list_functions(db: Session = Depends(get_db)):
    """All social functions with product counts."""
    functions = get_all_social_functions(db)
    return FunctionListResponse(
        functions=[FunctionSummary(**f) for f in functions],
        total=len(functions),
    )


@router.get("/functions/{function}", response_model=FunctionDetailResponse)
def function_detail(
    function: str,
    culture: str | None = None,
    era: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Products for a given social function, filterable by culture/era."""
    result = get_products_by_function(
        db, function, culture=culture, era=era, limit=limit, offset=offset
    )
    return FunctionDetailResponse(
        function=function,
        products=[ProductSummary.model_validate(p) for p in result["products"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )
