"""Pydantic schemas for the filters endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class FilterOptions(BaseModel):
    """Available filter options for the search UI.

    Matches the frontend FilterOptions TypeScript interface in
    vv-web/src/types/index.ts. Values are dynamically queried
    from the products table.
    """

    eras: list[str] = []
    decades: list[str] = []
    garment_types: list[str] = []
    occasions: list[str] = []
    fit_styles: list[str] = []
    cultures: list[str] = []
    materials: list[str] = []
    designers: list[str] = []
    production_modes: list[str] = []
