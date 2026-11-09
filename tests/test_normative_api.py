from fastapi.testclient import TestClient
from crie_assistant_api import app

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
    # Empty search with facet filters via GET
    resp_get = client.get("/api/documents/filter?specialty=31.08.19&category=05 ООП РПД")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["total_hits"] > 0
    assert len(data_get["results"]) > 0
    assert "facets" in data_get

    # Empty search with facet filters via POST
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
