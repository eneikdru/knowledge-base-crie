from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from crie_assistant_api import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "crie-assistant-api"}

def test_search_with_keywords_and_category_filter():
    response = client.get("/api/search?q=эпидемиология&category=SYLLABUS_RPD")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "facets" in data
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["category"] == "SYLLABUS_RPD"
    assert item["specialty_code"] == "31.08.36"
    assert "<mark>" in item["excerpt"]

def test_search_with_specialty_filter():
    response = client.get("/api/search?q=ГИА&specialty_code=31.08.36")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert "ГИА" in item["title"]
    assert item["specialty_code"] == "31.08.36"

def test_search_synonym_expansion():
    response = client.get("/api/search?q=экзамен")
    assert response.status_code == 200
    data = response.json()
    assert any("ГИА" in item["title"] for item in data["items"])

def test_search_empty_query_returns_422():
    response = client.get("/api/search?q=  ")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Unprocessable Entity"
    assert "guidance" in data
    assert data["errors"][0]["code"] == "EMPTY_QUERY"

def test_search_short_query_returns_422():
    response = client.get("/api/search?q=a")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Unprocessable Entity"
    assert data["errors"][0]["code"] == "QUERY_TOO_SHORT"

def test_get_synonyms():
    response = client.get("/api/search/synonyms")
    assert response.status_code == 200
    data = response.json()
    assert "гиа" in data
    assert "рпд" in data

def test_get_document_details_found():
    response = client.get("/api/documents/DOC-2026-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "DOC-2026-001"
    assert "РПД" in data["title"]

def test_get_document_details_not_found():
    response = client.get("/api/documents/DOC-NON-EXISTENT")
    assert response.status_code == 404
