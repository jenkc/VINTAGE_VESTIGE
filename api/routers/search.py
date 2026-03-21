from fastapi import APIRouter, Depends, HTTPException
import base64
from io import BytesIO
from PIL import Image

from embeddings.generator import EmbeddingGenerator
from storage.vector_search import VectorSearch
from api.dependencies import get_vector_search, get_embedding_generator
from api.schemas.search import ( 
    TextSearchRequest, ImageSearchRequest, SearchResult, SearchResponse, SearchFilters
)

router = APIRouter(prefix="/search", tags=["search"])

def _build_filter_dict(filters: SearchFilters | None) -> dict | None:
    """Converts Pydantic SearchFilters model to a dict for SQL query parameters."""
    if not filters:
        return None
    d = {k: v for k, v in filters.model_dump(exclude_none=True).items()}
    return d if d else None

@router.post("/text", response_model=SearchResponse)
def search_text(
    body: TextSearchRequest,
    vs: VectorSearch = Depends(get_vector_search),
    emb: EmbeddingGenerator = Depends(get_embedding_generator),
):
    """Search products by text query."""
    text_vector = emb.generate_text_embedding(body.query)
    filters = _build_filter_dict(body.filters)
    hits = vs.search_text(text_vector, limit=body.limit, filters=filters)

    results = [SearchResult(
        id=hit["id"],
        score=hit["score"],
        title=hit.get("title", ""),
        category=hit.get("category"),
        primary_image=hit.get("primary_image"),
        era=hit.get("era"),
        decade=hit.get("decade"),
        style_tags=hit.get("style_tags", []),
        colors=hit.get("colors", []),
        material=hit.get("material"),
        garment_type=hit.get("garment_type"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
        display_title=hit.get("display_title"),
        designer=hit.get("designer"),
        production_mode=hit.get("production_mode"),
    ) for hit in hits]

    return SearchResponse(results=results, query=body.query, total=len(results))

@router.post("/image", response_model=SearchResponse)
def search_image(
    body: ImageSearchRequest,
    vs: VectorSearch = Depends(get_vector_search),
    emb: EmbeddingGenerator = Depends(get_embedding_generator),
):
    """Search products by image upload."""
    try:
        _, b64data = body.image.split(",", 1)
        raw = base64.b64decode(b64data)
        pil_image = Image.open(BytesIO(raw))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data")

    vector = emb.generate_image_embedding(pil_image)
    hits = vs.search_image(vector, limit=body.limit)

    results = [SearchResult(
        id=hit["id"],
        score=hit["score"],
        title=hit.get("title", ""),
        category=hit.get("category"),
        primary_image=hit.get("primary_image"),
        era=hit.get("era"),
        decade=hit.get("decade"),
        style_tags=hit.get("style_tags", []),
        colors=hit.get("colors", []),
        material=hit.get("material"),
        garment_type=hit.get("garment_type"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
        display_title=hit.get("display_title"),
        designer=hit.get("designer"),
        production_mode=hit.get("production_mode"),
    ) for hit in hits]

    return SearchResponse(results=results, query="[image]", total=len(results))