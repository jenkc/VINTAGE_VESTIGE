from fastapi import APIRouter, Depends
import base64
from io import BytesIO
from PIL import Image
from qdrant_client.models import Filter, FieldCondition, MatchValue

from embeddings.generator import EmbeddingGenerator
from storage.vector_db import VectorDB
from api.dependencies import get_vector_db, get_embedding_generator
from api.schemas.search import TextSearchRequest, ImageSearchRequest, SearchResult, SearchResponse, SearchFilters

router = APIRouter(prefix="/search", tags=["search"])

def _build_qdrant_filter(filters: SearchFilters | None) -> Filter | None:
    if not filters:
        return None
    qdrant_conditions = []
    for field, value in filters.model_dump(exclude_none=True).items():
        qdrant_conditions.append(
            FieldCondition(
                key=field,
                match=MatchValue(value=value)
            )
        )
    if not qdrant_conditions:
        return None
    return Filter(must=qdrant_conditions)

@router.post("/text", response_model=SearchResponse)
def search_text(
    body: TextSearchRequest, 
    vdb = Depends(get_vector_db), 
    emb = Depends(get_embedding_generator)
):
    """Search for similar products based on text query."""
    # Generate embedding: 
    text_vector = emb.generate_text_embedding(body.query)
    # Build Qdrant filter from SearchFilters
    qfilter = _build_qdrant_filter(body.filters)
    # Search Qdrant
    hits = vdb.search_similar(vdb.text_collection, text_vector, query_filter=qfilter, limit=body.limit)
    # Map Qdrant hits to SearchResult list
    results = [SearchResult(
        id=hit["product_id"],
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
        vibe=hit.get("vibe"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
    ) for hit in hits]

    return SearchResponse(results=results, query=body.query, total=len(results))


@router.post("/image", response_model=SearchResponse)
def search_image(
    body: ImageSearchRequest,
    vdb: VectorDB = Depends(get_vector_db),
    emb: EmbeddingGenerator = Depends(get_embedding_generator),
):
    # Decode base64 data URL → PIL Image
    header, b64data = body.image.split(",", 1)
    raw = base64.b64decode(b64data)
    pil_image = Image.open(BytesIO(raw))

    # Generate CLIP embedding (512-dim)
    vector = emb.generate_image_embedding(pil_image)

    # Search vintage_images
    hits = vdb.search_similar(vdb.image_collection, vector, limit=body.limit)

    # Map hits → SearchResult (same as text search)
    results = [SearchResult(
        id=hit["product_id"],
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
        vibe=hit.get("vibe"),
        fit_style=hit.get("fit_style"),
        occasion=hit.get("occasion"),
        ai_description=hit.get("ai_description"),
        culture=hit.get("culture"),
        object_date=hit.get("object_date"),
        price=hit.get("price"),
    ) for hit in hits]

    return SearchResponse(results=results, query="[image]", total=len(results))