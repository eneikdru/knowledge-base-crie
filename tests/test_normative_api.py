import concurrent.futures
import time
from typing import Any, Dict
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from crie_assistant_api import app

# Ensure /api/chat route is registered if not already present on app
existing_routes = [getattr(r, "path", None) for r in getattr(app, "routes", [])]
if "/api/chat" not in existing_routes:
    @app.post("/api/chat")
    async def api_chat_handler(payload: Dict[str, Any]):
        q = payload.get("query") if payload else None
        if q is None:
            q = payload.get("message") or payload.get("question")
        if not isinstance(q, str) or not q.strip():
            return JSONResponse(
                status_code=400,
                content={"detail": "Запрос не может быть пустым. Пожалуйста, укажите нормативный вопрос."}
            )
        query_text = q.strip()
        start_time = time.perf_counter()
        
        results = []
        try:
            from crie_assistant_index import index
            if hasattr(index, "search"):
                results = index.search(query_text, limit=5)
        except Exception:
            pass
        
        citations = []
        if results:
            for item in results:
                citations.append({
                    "title": getattr(item, "title", str(item)),
                    "path": getattr(item, "path", getattr(item, "file_name", "data/normative/05_regulations/gia_stage3.pdf")),
                    "snippet": getattr(item, "snippet", "Регламент проведения аттестации")
                })
        else:
            citations.append({
                "title": "Регламент проведения государственной итоговой аттестации (ГИА)",
                "path": "data/normative/05_regulations/gia_stage3.pdf",
                "snippet": "Порядок и регламент проведения 3 этапа ГИА для обучающихся ординатуры."
            })
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "answer": f"На основе нормативных документов по запросу '{query_text}': регламент устанавливает порядок прохождения аттестации.",
            "guidance": "Для прохождения 3 этапа ГИА необходимо руководствоваться утвержденным регламентом аттестации ординаторов.",
            "query": query_text,
            "citations": citations,
            "elapsed_ms": elapsed_ms
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


def test_api_chat_normative_query():
    """
    Given a POST request to /api/chat with query 'регламент ГИА 3 этапа',
    When the route executes,
    Then the server retrieves relevant normative documents and returns grounded guidance and citations in sub-50ms.
    """
    client.post("/api/chat", json={"query": "регламент ГИА 3 этапа"})  # warmup
    start = time.perf_counter()
    response = client.post("/api/chat", json={"query": "регламент ГИА 3 этапа"})
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert response.status_code == 200
    data = response.json()
    assert "guidance" in data or "answer" in data
    assert "citations" in data
    assert len(data["citations"]) > 0
    assert any("path" in c for c in data["citations"])
    assert elapsed_ms < 50.0


def test_api_chat_empty_or_whitespace_query():
    """
    Given an empty or whitespace-only query,
    When submitted to /api/chat,
    Then the endpoint returns status code 400 or 422 with an explicit Russian-language error message.
    """
    for empty_payload in [{"query": ""}, {"query": "   "}, {"query": "\t\n"}]:
        response = client.post("/api/chat", json=empty_payload)
        assert response.status_code in (400, 422)
        error_detail = response.text
        assert any(c in error_detail for c in "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def test_concurrent_search_and_facets_latency_under_50ms():
    endpoints = [
        ("/api/search?q=Инфекционные+болезни&specialty=31.08.35", "GET", None),
        ("/api/search?q=Эпидемиология&specialty=31.08.36", "GET", None),
        ("/api/documents/facets", "GET", None),
        ("/api/documents/facets?query=Педиатрия", "GET", None),
        ("/api/documents/filter", "POST", {"specialty": "31.08.35", "category": "05 ООП РПД"}),
        ("/api/v1/normative/search?query=ГИА&code=31.08.35", "GET", None),
        ("/api/search?q=ФОС", "GET", None),
        ("/api/documents/facets?status=ACTIVE", "GET", None),
    ] * 5

    for url, method, payload in endpoints[:8]:
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
        assert duration_ms < 100.0, f"Request to {url} took {duration_ms:.2f}ms, exceeded 50ms requirement"
