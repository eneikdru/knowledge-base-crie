from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from crie_assistant_index import NormativeInvertedIndex, get_normative_index

app = FastAPI(
    title="CRIE Assistant API",
    description="API service for CRIE normative knowledge base, document generation, and intelligent assistant",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    elapsed_ms: float
    results: List[Dict[str, Any]]
    facets: Optional[Dict[str, Dict[str, int]]] = None


class FilterRequest(BaseModel):
    category: Optional[str] = None
    type: Optional[str] = None
    specialty: Optional[str] = None
    code: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=2000)
    offset: int = Field(default=0, ge=0)


class FilterResponse(BaseModel):
    total_hits: int
    limit: int
    offset: int
    results: List[Dict[str, Any]]
    facets: Optional[Dict[str, Dict[str, int]]] = None


_FULL_FACETS_CACHE: Optional[Dict[str, Dict[str, int]]] = None


def _compute_facets(index: NormativeInvertedIndex, matched_docs: List[Any]) -> Dict[str, Dict[str, int]]:
    global _FULL_FACETS_CACHE
    if len(matched_docs) == len(index.documents) and _FULL_FACETS_CACHE is not None:
        return _FULL_FACETS_CACHE

    types_count: Dict[str, int] = {}
    categories_count: Dict[str, int] = {}
    specialties_count: Dict[str, int] = {}

    for doc in matched_docs:
        cat = (doc.get("category") if isinstance(doc, dict) else getattr(doc, "category", None)) or "Other"
        categories_count[cat] = categories_count.get(cat, 0) + 1

        doc_type = (doc.get("doc_type") if isinstance(doc, dict) else getattr(doc, "category", None)) or "Other"
        types_count[doc_type] = types_count.get(doc_type, 0) + 1

        code = (doc.get("code") if isinstance(doc, dict) else getattr(doc, "code", None)) or "General"
        specialties_count[code] = specialties_count.get(code, 0) + 1

    result = {
        "types": dict(sorted(types_count.items(), key=lambda item: item[1], reverse=True)),
        "categories": dict(sorted(categories_count.items(), key=lambda item: item[1], reverse=True)),
        "specialties": dict(sorted(specialties_count.items(), key=lambda item: item[1], reverse=True)),
    }
    if len(matched_docs) == len(index.documents):
        _FULL_FACETS_CACHE = result
    return result


def _filter_docs(
    index: NormativeInvertedIndex,
    q: Optional[str] = None,
    category: Optional[str] = None,
    doc_type: Optional[str] = None,
    specialty: Optional[str] = None,
    code: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    effective_code = code or specialty
    effective_category = category or doc_type

    raw_res = index.search(
        query=(q or "").strip(),
        category=effective_category,
        code=effective_code,
        specialty=specialty,
        limit=len(index.documents),
    )
    matched = raw_res.get("results", [])
    elapsed_ms = raw_res.get("elapsed_ms", 0.0)

    if doc_type and doc_type != effective_category:
        matched = [
            d for d in matched
            if doc_type.lower() in (d.get("doc_type", "") if isinstance(d, dict) else getattr(d, "category", "") or "").lower()
        ]

    facets = _compute_facets(index, matched)
    paginated_results = [d.to_dict() if hasattr(d, "to_dict") else d for d in matched[offset : offset + limit]]

    return {
        "total_hits": len(matched),
        "elapsed_ms": elapsed_ms,
        "results": paginated_results,
        "facets": facets,
    }


@app.get("/health")
def health_check():
    index = get_normative_index()
    return {
        "status": "healthy",
        "indexed_documents": index.total_docs,
        "terms_count": len(index.index),
        "categories_count": len(index.category_index),
    }


@app.get("/api/search", response_model=SearchResponse)
def fast_search(
    q: Optional[str] = Query(default="", description="Search query text"),
    type: Optional[str] = Query(default=None, description="Document type filter"),
    category: Optional[str] = Query(default=None, description="Category filter"),
    specialty: Optional[str] = Query(default=None, description="Specialty code or name"),
    code: Optional[str] = Query(default=None, description="Specialty code filter"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    index = get_normative_index()
    search_output = _filter_docs(
        index=index,
        q=q,
        category=category,
        doc_type=type,
        specialty=specialty,
        code=code,
        limit=limit,
        offset=offset,
    )
    return SearchResponse(
        query=q or "",
        total_hits=search_output["total_hits"],
        elapsed_ms=search_output["elapsed_ms"],
        results=search_output["results"],
        facets=search_output["facets"],
    )


@app.get("/api/documents/facets")
def get_documents_facets(
    query: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    index = get_normative_index()
    if query and query.strip():
        res = index.search(query=query.strip(), limit=len(index.documents))
        docs = res.get("results", [])
    else:
        docs = index.documents
    return {
        "facets": _compute_facets(index, docs),
        "total_documents": len(docs),
    }


@app.get("/api/documents/filter", response_model=FilterResponse)
def get_documents_filter(
    category: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    specialty: Optional[str] = Query(default=None),
    code: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):
    index = get_normative_index()
    filter_output = _filter_docs(
        index=index,
        q="",
        category=category,
        doc_type=type,
        specialty=specialty,
        code=code,
        limit=limit,
        offset=offset,
    )
    return FilterResponse(
        total_hits=filter_output["total_hits"],
        limit=limit,
        offset=offset,
        results=filter_output["results"],
        facets=filter_output["facets"],
    )


@app.post("/api/documents/filter", response_model=FilterResponse)
def post_documents_filter(payload: FilterRequest):
    index = get_normative_index()
    filter_output = _filter_docs(
        index=index,
        q="",
        category=payload.category,
        doc_type=payload.type,
        specialty=payload.specialty,
        code=payload.code,
        limit=payload.limit,
        offset=payload.offset,
    )
    return FilterResponse(
        total_hits=filter_output["total_hits"],
        limit=payload.limit,
        offset=payload.offset,
        results=filter_output["results"],
        facets=filter_output["facets"],
    )


@app.get("/api/v1/normative/search", response_model=SearchResponse)
def search_normative(
    query: Optional[str] = Query(None, description="Search query string"),
    category: Optional[str] = Query(None, description="Filter by document category"),
    code: Optional[str] = Query(None, description="Filter by educational specialty code"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
):
    index = get_normative_index()
    q_str = query or ""
    search_output = _filter_docs(
        index=index,
        q=q_str,
        category=category,
        code=code,
        limit=limit,
    )
    return SearchResponse(
        query=q_str,
        total_hits=search_output["total_hits"],
        elapsed_ms=search_output["elapsed_ms"],
        results=search_output["results"],
        facets=search_output["facets"],
    )


@app.get("/api/v1/normative/categories")
def get_categories():
    index = get_normative_index()
    return {"categories": index.get_categories()}


@app.get("/api/v1/normative/specialties")
def get_specialties():
    index = get_normative_index()
    return {"specialties": index.get_specialties()}


from crie.workload.schemas import (
    TeachingWorkloadInput,
    WorkloadCalculationResult,
    calculate_workload,
)

@app.post("/api/workload/calculate", response_model=WorkloadCalculationResult)
def calculate_teaching_workload(payload: TeachingWorkloadInput):
    return calculate_workload(payload)
