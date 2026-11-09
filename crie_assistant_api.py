"""CRIE Assistant API Service.

Provides endpoints for:
- Knowledge base corpus retrieval and search
- AI Assistant question answering / guidance
- Academic workload calculation
- Official order (.docx) generation conforming to GOST R 7.0.97-2016
"""

import json
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.docx_order_generator import build_order_docx, ORDER_TEMPLATES, ROSPOTREBNADZOR_HEADER_LINES

app = FastAPI(
    title="CRIE Assistant API",
    description="FBUN Central Research Institute of Epidemiology Educational Center Assistant & Knowledge Base",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StudentItem(BaseModel):
    identifier: str = Field(..., description="Anonymous identifier like ORD-2026-001 or ASP-2026-001")
    details: Optional[str] = Field(None, description="Score, specialization, or category details")


class OrderGenerationRequest(BaseModel):
    order_type: str = Field("enrollment", description="Type of order: enrollment, gia_admission, scholarship")
    order_number: Optional[str] = Field("124-ОД", description="Official order number")
    order_date: Optional[str] = Field("01 сентября 2026 г.", description="Order registration date")
    city: Optional[str] = Field("г. Москва", description="City / location")
    title_override: Optional[str] = Field(None, description="Custom subject/title line")
    specialty_code: Optional[str] = Field("31.08.36", description="Specialty code")
    specialty_name: Optional[str] = Field("Эпидемиология", description="Specialty name")
    protocol_num: Optional[str] = Field("1", description="Meeting protocol number")
    protocol_date: Optional[str] = Field("30 августа 2026 г.", description="Meeting protocol date")
    start_date: Optional[str] = Field("01 сентября 2026", description="Effective commencement date")
    students: Optional[List[StudentItem]] = Field(None, description="List of candidate identifiers (152-FZ compliant)")
    custom_items: Optional[List[str]] = Field(None, description="Optional replacement for order directive clauses")
    signatory_title: Optional[str] = Field("Директор института", description="Title of signing official")
    signatory_name: Optional[str] = Field("В.Г. Акимкин", description="Full/abbreviated name of signing official")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "crie-assistant-api"}


@app.get("/api/orders/types")
def list_order_types():
    """Returns supported order categories and default metadata."""
    types = []
    for key, val in ORDER_TEMPLATES.items():
        types.append({
            "id": key,
            "title": val["title"],
            "action_word": val.get("action_word", "ПРИКАЗЫВАЮ:"),
        })
    return {"order_types": types}


@app.post("/api/orders/generate")
def generate_order(request: OrderGenerationRequest):
    """Generates a .docx official order conforming to GOST R 7.0.97-2016."""
    valid_types = set(ORDER_TEMPLATES.keys())
    if request.order_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid order_type '{request.order_type}'. Supported types: {sorted(list(valid_types))}",
        )

    students_dicts = [s.model_dump() for s in request.students] if request.students else None

    try:
        doc_stream = build_order_docx(
            order_type=request.order_type,
            order_number=request.order_number or "124-ОД",
            order_date=request.order_date or "01 сентября 2026 г.",
            city=request.city or "г. Москва",
            title_override=request.title_override,
            specialty_code=request.specialty_code or "31.08.36",
            specialty_name=request.specialty_name or "Эпидемиология",
            protocol_num=request.protocol_num or "1",
            protocol_date=request.protocol_date or "30 августа 2026 г.",
            start_date=request.start_date or "01 сентября 2026",
            students=students_dicts,
            custom_items=request.custom_items,
            signatory_title=request.signatory_title or "Директор института",
            signatory_name=request.signatory_name or "В.Г. Акимкин",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Order generation failed: {str(exc)}")

    filename = f"order_{request.order_type}_{request.order_number.replace('/', '_').replace(' ', '_')}.docx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return StreamingResponse(doc_stream, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)
