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


def test_api_categories_and_specialties():
    resp_cat = client.get("/api/v1/normative/categories")
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()["categories"]) > 0

    resp_spec = client.get("/api/v1/normative/specialties")
    assert resp_spec.status_code == 200
    assert len(resp_spec.json()["specialties"]) > 0
