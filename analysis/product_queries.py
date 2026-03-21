"""Query helpers for product exploration endpoints."""

import json
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from storage.database import Product


def get_products_by_function(
    db: Session,
    function: str,
    culture: str | None = None,
    era: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Find products whose social_function JSON array contains the given value."""
    query = db.query(Product).filter(
        Product.social_function.isnot(None),
        text("social_function ::jsonb @> :fn_json ::jsonb").bindparams(
            fn_json=json.dumps([function])
        ),
    )

    if culture:
        query = query.filter(Product.culture == culture)
    if era:
        query = query.filter(Product.era == era)

    total = query.count()
    products = query.order_by(Product.era, Product.decade).offset(offset).limit(limit).all()

    return {
        "products": products,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_all_social_functions(db: Session) -> list[dict]:
    """List all distinct social_function values with product counts."""
    rows = db.execute(text("""
        SELECT val, COUNT(*) as cnt
        FROM products, jsonb_array_elements_text(social_function::jsonb) AS val
        WHERE social_function IS NOT NULL
        GROUP BY val
        ORDER BY cnt DESC
    """)).fetchall()

    return [{"function": row[0], "count": row[1]} for row in rows]
