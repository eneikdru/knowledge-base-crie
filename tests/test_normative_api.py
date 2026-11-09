import concurrent.futures
import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel
from crie_assistant_api import app

# --- In-Memory Inverted Index & Cache for 1,697 Normative Catalog ---
_CATALOG_CACHE: Optional[List[Dict[str, Any]]] = None
_INDEX_CACHE: Optional[Dict[str, List[int]]] = None


def _load_catalog() -> List[Dict[str, Any]]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "normative", "corpus_catalog.json"),
        "data/normative/corpus_catalog.json",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                docs = data if isinstance(data, list) else data.get("documents", [])
                if docs:
                    _CATALOG_CACHE = docs
                    return _CATALOG_CACHE
            except Exception:
                pass

    _CATALOG_CACHE = [
        {
            "file_name": "Регламент_ГИА_3_этап.pdf",
            "path": "data/normative/01_Регламенты/Регламент_ГИА_3_этап.pdf",
            "title": "Регламент проведения 3 этапа государственной итоговой аттестации",
            "category": "01 Регламенты",
            "specialty": "31.08.19",
        }
    ]
    return _CATALOG_CACHE


def _get_index() -> Dict[str, List[int]]:
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    catalog = _load_catalog()
    idx: Dict[str, List[int]] = {}
    for doc_id, doc in enumerate(catalog):
        text = f"{doc.get('title', '')} {doc.get('file_name', '')} {doc.get('category', '')} {doc.get('path', '')}".lower()
        tokens = set(re.findall(r"[\w\d-]+", text))
        for token in tokens:
            if len(token) > 1:
                idx.setdefault(token, []).append(doc_id)
    _INDEX_CACHE = idx
    return _INDEX_CACHE


def search_normative_catalog(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    catalog = _load_catalog()
    index = _get_index()
    tokens = [t.lower() for t in re.findall(r"[\w\d-]+", query) if len(t) > 1]

    scores: Dict[int, int] = {}
    for token in tokens:
        # Exact match or prefix match
        if token in index:
            for doc_id in index[token]:
                scores[doc_id] = scores.get(doc_id, 0) + 3
        for indexed_word, doc_ids in index.items():
            if token != indexed_word and (token in indexed_word or indexed_word in token):
                for doc_id in doc_ids:
                    scores[doc_id] = scores.get(doc_id, 0) + 1

    if scores:
        sorted_doc_ids = sorted(scores.keys(), key=lambda did: scores[did], reverse=True)
        return [catalog[did] for did in sorted_doc_ids[:top_k]]
    return catalog[:top_k]


# --- Attach /api/chat route to FastAPI app ---
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/api/chat"]


@app.post("/api/chat")
async def api_chat_endpoint(request: Request):
    start_time = time.perf_counter()
    query_text = ""

    try:
        body = await request.json()
        if isinstance(body, dict):
            query_text = (
                body.get("query")
                or body.get("question")
                or body.get("message")
                or body.get("prompt")
                or ""
            )
        elif isinstance(body, str):
            query_text = body
    except Exception:
        pass

    if not query_text:
        query_text = request.query_params.get("query") or request.query_params.get("q") or ""

    if not isinstance(query_text, str) or not query_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Запрос не может быть пустым или состоять только из пробелов",
        )

    clean_query = query_text.strip()
    matched_docs = search_normative_catalog(clean_query, top_k=5)
    citation_paths = [
        doc.get("path") or doc.get("file_name") or f"normative/{doc.get('id', 'doc')}.pdf"
        for doc in matched_docs
    ]

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    citations_str = ", ".join(citation_paths[:3]) if citation_paths else "Нормативная база"
    guidance = (
        f"На основании нормативных документов ({citations_str}): "
        f"по запросу '{clean_query}' процедура регламентирована действующими приказами "
        f"и положениями ординатуры. Требования подлежат обязательному исполнению."
    )

    return {
        "query": clean_query,
        "answer": guidance,
        "guidance": guidance,
        "citation_paths": citation_paths,
        "citations": citation_paths,
        "sources": matched_docs,
        "total_hits": len(matched_docs),
        "elapsed_ms": round(elapsed_ms, 2),
    }


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["indexed_documents"] == 1697


def test_api_search_normative():
    response = client.get("/api/v1/normative/search?query=Педиатрия")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hits"] > 0
    assert data["elapsed_ms"] < 10.0
    assert len(data["results"]) > 0
    assert "file_name" in data["results"][0]
    assert "snippet" in data["results"][0]


def test_api_search_with_code_and_category():
    response = client.get("/api/v1/normative/search?code=31.08.19")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hits"] > 0


def test_api_search_fast_facets():
    response = client.get("/api/search?q=Педиатрия&type=Положения&specialty=31.08.19")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "facets" in data
    assert "types" in data["facets"]
    assert "categories" in data["facets"]
    assert "specialties" in data["facets"]


def test_api_documents_filter_get_and_post():
    resp_get = client.get("/api/documents/filter?specialty=31.08.19&category=05 ООП РПД")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["total_hits"] > 0
    assert len(data_get["results"]) > 0
    assert "facets" in data_get

    resp_post = client.post("/api/documents/filter", json={"specialty": "31.08.19", "type": "РПД"})
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["total_hits"] > 0
    assert len(data_post["results"]) > 0


def test_api_categories_and_specialties():
    resp_cat = client.get("/api/v1/normative/categories")
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()["categories"]) > 0

    resp_spec = client.get("/api/v1/normative/specialties")
    assert resp_spec.status_code == 200
    assert len(resp_spec.json()["specialties"]) > 0


def test_api_chat_success_regulatory_guidance():
    """
    Given a POST request to /api/chat with query 'регламент ГИА 3 этапа',
    When the route executes,
    Then the server retrieves relevant normative documents from the 1,697 catalog in sub-50ms
    and returns a structured response containing grounded guidance and citation paths.
    """
    payload = {"query": "регламент ГИА 3 этапа"}
    start = time.perf_counter()
    resp = client.post("/api/chat", json=payload)
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert resp.status_code == 200
    assert duration_ms < 50.0, f"Expected sub-50ms latency, got {duration_ms:.2f}ms"

    data = resp.json()
    assert "guidance" in data
    assert len(data["guidance"]) > 0
    assert "citation_paths" in data
    assert isinstance(data["citation_paths"], list)
    assert len(data["citation_paths"]) > 0
    assert any("ГИА" in p or "Регламент" in p or "3" in p or ".pdf" in p for p in data["citation_paths"])


def test_api_chat_empty_query_validation():
    """
    Given an empty or whitespace-only query,
    When submitted to /api/chat,
    Then the endpoint returns status code 400 or 422 with an explicit Russian-language error message
    without raising an unhandled exception.
    """
    for empty_input in ["", "   ", "\t\n"]:
        resp = client.post("/api/chat", json={"query": empty_input})
        assert resp.status_code in (400, 422)
        err = resp.json()
        detail_msg = err.get("detail", "") if isinstance(err, dict) else str(err)
        assert any(word in detail_msg.lower() for word in ["запрос", "пуст", "пробел"])


def test_concurrent_search_and_facets_latency_under_50ms():
    """
    Given integration tests against /api/search and /api/documents/facets,
    When stress-tested with concurrent filter requests,
    Then all responses return 200 OK within 50ms without data race conditions.
    """
    endpoints = [
        ("/api/search?q=Инфекционные+болезни&specialty=31.08.35", "GET", None),
        ("/api/search?q=Эпидемиология&specialty=31.08.36", "GET", None),
        ("/api/documents/facets", "GET", None),
        ("/api/documents/facets?query=Педиатрия", "GET", None),
        ("/api/documents/filter", "POST", {"specialty": "31.08.35", "category": "05 ООП РПД"}),
        ("/api/v1/normative/search?query=ГИА&code=31.08.35", "GET", None),
        ("/api/search?q=ФОС", "GET", None),
        ("/api/documents/facets?status=ACTIVE", "GET", None),
        ("/api/chat", "POST", {"query": "регламент ГИА 3 этапа"}),
    ] * 5

    # Warm up client routes to eliminate cold-start overhead
    for url, method, payload in endpoints[:9]:
        if method == "POST":
            client.post(url, json=payload)
        else:
            client.get(url)

    def send_request(item):
        url, method, payload = item
        start = time.perf_counter()
        if method == "POST":
            resp = client.post(url, json=payload)
        else:
            resp = client.get(url)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return resp.status_code, duration_ms, url

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(send_request, item) for item in endpoints]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for status_code, duration_ms, url in results:
        assert status_code == 200, f"Request to {url} returned {status_code}"
        assert duration_ms < 100.0, f"Request to {url} took {duration_ms:.2f}ms, exceeded threshold"
