"""Pydantic schemas for explore endpoints."""

from pydantic import BaseModel
from api.schemas.product import ProductSummary


class FunctionSummary(BaseModel):
    function: str
    count: int


class FunctionListResponse(BaseModel):
    functions: list[FunctionSummary]
    total: int


class FunctionDetailResponse(BaseModel):
    function: str
    products: list[ProductSummary]
    total: int
    limit: int
    offset: int
