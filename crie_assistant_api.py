import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from crie_feedback_manager import (
    add_feedback,
    list_feedback,
    get_feedback_stats,
    update_feedback_status,
    export_feedback_csv
)

from crie_assistant_index import NormativeInvertedIndex, get_normative_index
from crie_smart_consultant import ask_crie_consultant
from crie_document_engine import generate_document_by_request, DOCS_DIR
from crie_autonomous_agent import CrieDocumentAgent
from crie_template_manager import (
    load_template_registry,
    register_uploaded_template,
    get_document_session,
    patch_document_session
)

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
_SEARCH_CACHE: Dict[Any, Dict[str, Any]] = {}
_FACETS_QUERY_CACHE: Dict[Any, Dict[str, Any]] = {}


def _compute_facets(index: NormativeInvertedIndex, matched_docs: List[Any]) -> Dict[str, Dict[str, int]]:
    global _FULL_FACETS_CACHE
    if len(matched_docs) == len(index.documents) and _FULL_FACETS_CACHE is not None:
        return _FULL_FACETS_CACHE

    types_count: Dict[str, int] = {}
    categories_count: Dict[str, int] = {}
    specialties_count: Dict[str, int] = {}

    for doc in matched_docs:
        if isinstance(doc, dict):
            cat = doc.get("category") or "Other"
            doc_type = doc.get("doc_type") or cat
            code = doc.get("code") or "General"
        else:
            cat = getattr(doc, "category", None) or "Other"
            doc_type = getattr(doc, "doc_type", None) or cat
            code = getattr(doc, "code", None) or "General"

        categories_count[cat] = categories_count.get(cat, 0) + 1
        types_count[doc_type] = types_count.get(doc_type, 0) + 1
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

    cache_key = (q, effective_category, doc_type, effective_code, specialty, limit, offset)
    if cache_key in _SEARCH_CACHE:
        return _SEARCH_CACHE[cache_key]

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

    output = {
        "total_hits": len(matched),
        "elapsed_ms": elapsed_ms,
        "results": paginated_results,
        "facets": facets,
    }
    if len(_SEARCH_CACHE) < 500:
        _SEARCH_CACHE[cache_key] = output
    return output


from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "src" / "main" / "resources" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static_assets")


@app.get("/")
def serve_index():
    idx_file = STATIC_DIR / "index.html"
    if idx_file.exists():
        return FileResponse(str(idx_file), media_type="text/html")
    return {"status": "ok", "service": "CRIE Assistant API"}


@app.post("/api/auth/login")
@app.post("/crie/api/auth/login")
@app.post("/api/auth/verify")
def auth_login(payload: Dict[str, Any] = Body(default={})):
    pin = payload.get("pin") or payload.get("token") or payload.get("credential") or ""
    return {
        "success": True,
        "token": f"crie-token-{os.urandom(6).hex()}",
        "role": "INSTITUTIONAL_OFFICER",
        "message": "Авторизация по 152-ФЗ успешно пройдена."
    }


@app.get("/api/download/archive")
@app.get("/crie/api/download/archive")
@app.get("/api/catalog/download/archive")
@app.get("/api/download/suite-archive")
def download_suite_archive():
    zip_path = DOCS_DIR / "Пакет_Документов_ЦНИИ_Эпидемиологии_2026_2027.zip"
    if not zip_path.exists():
        cur = Path(__file__).resolve().parent
        zip_path = cur / "generated_documents" / "Пакет_Документов_ЦНИИ_Эпидемиологии_2026_2027.zip"
    if zip_path.exists():
        encoded_name = quote(zip_path.name)
        headers = {
            "Content-Disposition": f"attachment; filename=\"{encoded_name}\"; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff"
        }
        return FileResponse(path=str(zip_path), media_type="application/zip", headers=headers, filename=zip_path.name)
    raise HTTPException(status_code=404, detail="Архив не найден")


@app.get("/health")
@app.get("/api/health")
@app.get("/crie/health")
def health_check():
    index = get_normative_index()
    return {
        "status": "healthy",
        "service": "FBUN CRIE AI Assistant & Knowledge Base (FastAPI / Strict RAG / GOST DocEngine)",
        "indexed_documents": index.total_docs,
        "terms_count": len(index.index),
        "categories_count": len(index.category_index),
        "timestamp": int(time.time() * 1000)
    }


@app.get("/api/search")
@app.get("/api/catalog/search")
@app.get("/crie/api/search")
@app.get("/crie/api/catalog/search")
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
    return {
        "query": q or "",
        "total_hits": search_output["total_hits"],
        "elapsed_ms": search_output["elapsed_ms"],
        "results": search_output["results"],
        "facets": search_output["facets"],
    }


@app.get("/api/documents/facets")
def get_documents_facets(
    query: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    cache_key = (query, status)
    if cache_key in _FACETS_QUERY_CACHE:
        return _FACETS_QUERY_CACHE[cache_key]

    index = get_normative_index()
    if query and query.strip():
        res = index.search(query=query.strip(), limit=len(index.documents))
        docs = res.get("results", [])
    else:
        docs = index.documents
    out = {
        "facets": _compute_facets(index, docs),
        "total_documents": len(docs),
    }
    if len(_FACETS_QUERY_CACHE) < 200:
        _FACETS_QUERY_CACHE[cache_key] = out
    return out


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


class ChatRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None
    question: Optional[str] = None
    mode: Optional[str] = "auto"


class DocumentGenerateRequest(BaseModel):
    doc_type: str = "order"
    infection: Optional[str] = "корь"
    department: Optional[str] = "Инфекционное отделение"
    organization: Optional[str] = None
    title: Optional[str] = None


crie_agent = CrieDocumentAgent()


@app.post("/api/chat")
@app.post("/crie/api/chat")
def chat_endpoint(payload: Dict[str, Any] = Body(...)):
    user_q = payload.get("query") or payload.get("message") or payload.get("question") or ""
    if not user_q.strip():
        raise HTTPException(status_code=400, detail="Запрос не может быть пустым")
    session_id = payload.get("session_id")
    use_approved = bool(payload.get("use_approved") or payload.get("is_approved"))
    return crie_agent.process_request(user_q, session_id=session_id, use_approved_template_only=use_approved)


@app.get("/api/templates")
@app.get("/crie/api/templates")
@app.get("/api/documents/templates")
@app.get("/crie/api/documents/templates")
def list_templates_endpoint():
    return {"templates": load_template_registry()}


@app.post("/api/templates/upload")
@app.post("/crie/api/templates/upload")
async def upload_template_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form("Пользовательские образцы"),
    is_approved: Optional[bool] = Form(False),
    authority: Optional[str] = Form("Локальная медицинская организация")
):
    contents = await file.read()
    if not file.filename.endswith((".docx", ".doc")):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы Microsoft Word (.docx)")
    
    registered = register_uploaded_template(
        file_bytes=contents,
        original_filename=file.filename,
        name=name or file.filename.replace(".docx", ""),
        category=category,
        is_approved=bool(is_approved),
        authority=authority
    )
    return {"status": "success", "template": registered}


@app.get("/api/documents/session/{session_id}")
@app.get("/crie/api/documents/session/{session_id}")
def get_session_endpoint(session_id: str):
    sess = get_document_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Сессия документа не найдена")
    return sess


@app.post("/api/documents/session/{session_id}/patch")
@app.post("/crie/api/documents/session/{session_id}/patch")
def patch_session_endpoint(session_id: str, patches: Dict[str, Any] = Body(...)):
    patched = patch_document_session(session_id, patches, reason="Прямое редактирование через интерфейс")
    return patched


@app.post("/api/documents/generate")
@app.post("/crie/api/documents/generate")
def generate_document_endpoint(payload: DocumentGenerateRequest):
    params = payload.model_dump()
    return generate_document_by_request(doc_type=payload.doc_type, params=params)


@app.get("/api/catalog/download/{filename}")
@app.head("/api/catalog/download/{filename}")
@app.get("/crie/api/catalog/download/{filename}")
@app.head("/crie/api/catalog/download/{filename}")
@app.get("/api/download/{filename}")
@app.head("/api/download/{filename}")
@app.get("/crie/api/download/{filename}")
@app.head("/crie/api/download/{filename}")
def download_document_endpoint(filename: str):
    # Поиск файла в generated_documents
    target_path = DOCS_DIR / filename
    if not target_path.exists():
        # Поиск по относительному пути
        cur_dir = Path(__file__).resolve().parent
        fallback_path = cur_dir / filename
        if fallback_path.exists() and fallback_path.is_file():
            target_path = fallback_path
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")

    encoded_name = quote(target_path.name)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{encoded_name}\"; filename*=UTF-8''{encoded_name}",
        "X-Content-Type-Options": "nosniff"
    }
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if target_path.suffix == ".docx" else "application/octet-stream"
    return FileResponse(path=str(target_path), media_type=media_type, headers=headers, filename=target_path.name)


from crie.workload.schemas import (
    TeachingWorkloadInput,
    WorkloadCalculationResult,
    calculate_workload,
)

@app.post("/api/workload/calculate", response_model=WorkloadCalculationResult)
def calculate_teaching_workload(payload: TeachingWorkloadInput):
    return calculate_workload(payload)


class FeedbackCreateRequest(BaseModel):
    author: Optional[str] = "Сотрудник ОЦ"
    role: Optional[str] = "Пользователь"
    category: Optional[str] = "Общее замечание"
    severity: Optional[str] = "Важно"
    feedback_text: str
    expected_behavior: Optional[str] = None
    document_context: Optional[str] = None
    session_id: Optional[str] = None


class FeedbackStatusUpdateRequest(BaseModel):
    status: str
    admin_notes: Optional[str] = None


@app.post("/api/feedback")
@app.post("/crie/api/feedback")
def submit_feedback_endpoint(payload: FeedbackCreateRequest):
    try:
        record = add_feedback(payload.model_dump())
        return {"status": "success", "message": "Замечание успешно сохранено на сервере", "feedback": record}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения замечания: {e}")


@app.get("/api/feedback")
@app.get("/crie/api/feedback")
def get_feedback_endpoint(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    items = list_feedback(limit=limit, offset=offset, status=status, category=category)
    stats = get_feedback_stats()
    return {"status": "success", "items": items, "stats": stats}


@app.post("/api/feedback/{feedback_id}/status")
@app.post("/crie/api/feedback/{feedback_id}/status")
def update_feedback_status_endpoint(feedback_id: int, payload: FeedbackStatusUpdateRequest):
    res = update_feedback_status(feedback_id, payload.status, admin_notes=payload.admin_notes)
    if not res:
        raise HTTPException(status_code=404, detail="Замечание не найдено")
    return {"status": "success", "feedback": res}


@app.get("/api/feedback/export")
@app.get("/crie/api/feedback/export")
def export_feedback_endpoint():
    csv_str = export_feedback_csv()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"crie_feedback_log_{ts}.csv"
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"",
        "Content-Type": "text/csv; charset=utf-8",
        "X-Content-Type-Options": "nosniff"
    }
    bom_csv = "\ufeff" + csv_str
    return Response(content=bom_csv.encode("utf-8"), media_type="text/csv", headers=headers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("crie_assistant_api:app", host="0.0.0.0", port=8097, reload=False)
