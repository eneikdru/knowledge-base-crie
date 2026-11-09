import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from crie_assistant_index import get_normative_index

app = FastAPI(
    title="CRIE Assistant API",
    description="FastAPI knowledge base and sovereign assistant platform for Central Research Institute of Epidemiology (FBUN CNII Epidemiology)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    get_normative_index()


@app.get("/health")
def health_check() -> Dict[str, Any]:
    index = get_normative_index()
    return {
        "status": "healthy",
        "indexed_documents": index.total_docs,
        "categories_count": len(index.category_index)
    }


@app.get("/api/v1/normative/search")
def search_normative(
    query: str = Query("", description="Search query (discipline, code, abbreviation, keyword)"),
    category: Optional[str] = Query(None, description="Filter by normative category"),
    code: Optional[str] = Query(None, description="Filter by specialty code (e.g. 31.08.19)"),
    specialty: Optional[str] = Query(None, description="Filter by specialty name"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return")
) -> Dict[str, Any]:
    index = get_normative_index()
    result = index.search(
        query=query,
        category=category,
        code=code,
        specialty=specialty,
        limit=limit
    )
    return result


@app.get("/api/v1/normative/categories")
def get_normative_categories() -> Dict[str, Any]:
    index = get_normative_index()
    return {
        "categories": index.get_categories()
    }


@app.get("/api/v1/normative/specialties")
def get_normative_specialties() -> Dict[str, Any]:
    index = get_normative_index()
    return {
        "specialties": index.get_specialties()
    }


class WorkloadCalculationRequest(BaseModel):
    lectures_hours: float = Field(0.0, ge=0.0)
    seminars_hours: float = Field(0.0, ge=0.0)
    practice_hours: float = Field(0.0, ge=0.0)
    aspirant_guidance_hours: float = Field(0.0, ge=0.0)
    gek_hours: float = Field(0.0, ge=0.0)
    norm_rate_per_year: float = Field(800.0, ge=500.0, le=1200.0)


@app.post("/api/v1/workload/calculate")
def calculate_workload(req: WorkloadCalculationRequest) -> Dict[str, Any]:
    total_hours = (
        req.lectures_hours
        + req.seminars_hours
        + req.practice_hours
        + req.aspirant_guidance_hours
        + req.gek_hours
    )
    stake_fraction = round(total_hours / req.norm_rate_per_year, 2)
    status = "normal"
    if stake_fraction > 1.2:
        status = "overload"
    elif stake_fraction < 0.25:
        status = "underload"

    return {
        "total_hours": total_hours,
        "norm_rate_per_year": req.norm_rate_per_year,
        "stake_fraction": stake_fraction,
        "status": status
    }
