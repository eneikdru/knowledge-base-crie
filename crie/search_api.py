from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from crie.search_service import (
    DOCUMENT_CATALOG,
    SYNONYMS,
    get_document_by_id,
    search_documents,
)

router = APIRouter(prefix="/api", tags=["Search & Knowledge Base"])


class SearchItem(BaseModel):
    id: str
    title: str
    category: str
    specialty_code: str
    specialty_name: Optional[str] = None
    doc_type: Optional[str] = None
    academic_year: Optional[str] = None
    excerpt: str
    tags: List[str] = []
    score: int
    updated_at: Optional[str] = None


class FacetCounts(BaseModel):
    categories: Dict[str, int]
    specialties: Dict[str, int]


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[SearchItem]
    facets: FacetCounts
    query_expansion: List[str]


class ValidationErrorItem(BaseModel):
    field: str
    message: str
    code: str


class StructuredValidationErrorResponse(BaseModel):
    error: str
    message: str
    guidance: str
    errors: List[ValidationErrorItem]


@router.get(
    "/search",
    response_model=SearchResponse,
    responses={
        422: {
            "model": StructuredValidationErrorResponse,
            "description": "Structured error for empty or invalid query payload with corrective guidance.",
        }
    },
)
def search_endpoint(
    q: str = Query(..., description="Search query keywords"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    specialty_code: Optional[str] = Query(None, description="Optional specialty code filter (e.g. 31.08.36)"),
    limit: int = Query(20, ge=1, le=100, description="Results page size"),
    offset: int = Query(0, ge=0, description="Results offset"),
):
    trimmed_q = q.strip()
    if not trimmed_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Unprocessable Entity",
                "message": "Query string parameter 'q' must not be empty or whitespace.",
                "guidance": "Provide at least one keyword (e.g., 'ГИА', 'Эпидемиология', 'нагрузка', 'ФОС', 'РПД').",
                "errors": [
                    {
                        "field": "q",
                        "message": "Empty query provided.",
                        "code": "EMPTY_QUERY",
                    }
                ],
            },
        )

    if len(trimmed_q) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Unprocessable Entity",
                "message": "Query string parameter 'q' must be at least 2 characters in length.",
                "guidance": "Enter a meaningful term with 2 or more characters.",
                "errors": [
                    {
                        "field": "q",
                        "message": "Query too short.",
                        "code": "QUERY_TOO_SHORT",
                    }
                ],
            },
        )

    results = search_documents(
        query=trimmed_q,
        category=category,
        specialty_code=specialty_code,
        limit=limit,
        offset=offset,
    )
    return results


@router.get("/search/synonyms", response_model=Dict[str, List[str]])
def get_synonyms_endpoint():
    return SYNONYMS


@router.get("/documents/{doc_id}")
def get_document_details(doc_id: str):
    doc = get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{doc_id}' not found.",
        )
    return doc
