import json
from pathlib import Path
import pytest
from crie_assistant_index import NormativeIndex
from crie_assistant_api import create_app


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "normative" / "corpus_catalog.json"


@pytest.fixture(scope="module")
def corpus_catalog():
    assert CATALOG_PATH.exists(), f"Corpus catalog file not found at {CATALOG_PATH}"
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def normative_index():
    return NormativeIndex(catalog_path=CATALOG_PATH)


@pytest.fixture(scope="module")
def test_client():
    app = create_app(catalog_path=CATALOG_PATH)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_corpus_categories_have_at_least_three_items(corpus_catalog):
    """
    AC 1:
    Given a fresh installation seeded with the CRIE corpus,
    When automated acceptance tests query each category,
    Then every category returns at least 3 genuine items.
    """
    categories = corpus_catalog.get("categories", [])
    assert len(categories) > 0, "Expected at least one category in the seeded corpus"

    for entry in categories:
        category_name = entry.get("category")
        file_count = entry.get("file_count", 0)
        files = entry.get("files", [])

        assert category_name, "Category name must not be empty"
        assert file_count >= 3, f"Category '{category_name}' has file_count={file_count}, expected >= 3"
        assert len(files) >= 3, f"Category '{category_name}' has {len(files)} items listed, expected >= 3"

        for item in files:
            assert item.get("file_name"), f"Item in {category_name} missing file_name"
            assert item.get("relative_path"), f"Item in {category_name} missing relative_path"
            assert item.get("size_bytes", 0) > 0, f"Item in {category_name} has invalid size_bytes"


def test_api_categories_endpoint_walkability(test_client):
    """
    AC 1 (API walkability):
    Verify that querying categories through the HTTP API returns complete walkability
    and every category contains at least 3 genuine items.
    """
    response = test_client.get("/api/normative/categories")
    assert response.status_code == 200, f"API error: {response.status_code}"
    data = response.get_json()
    assert "categories" in data

    categories = data["categories"]
    assert len(categories) > 0
    for category_meta in categories:
        cat_name = category_meta.get("name") or category_meta.get("category")
        assert cat_name
        count = category_meta.get("file_count", 0)
        assert count >= 3, f"Category '{cat_name}' API reports count {count} < 3"

        # Query files under this category
        cat_files_resp = test_client.get(f"/api/normative/files?category={cat_name}")
        assert cat_files_resp.status_code == 200
        cat_files = cat_files_resp.get_json().get("files", [])
        assert len(cat_files) >= 3, f"Querying files for '{cat_name}' returned {len(cat_files)} < 3"


@pytest.mark.parametrize("query_keyword", ["Педиатрия", "Эпидемиология"])
def test_search_retrieves_accredited_syllabi_and_reviews(normative_index, query_keyword):
    """
    AC 2:
    Given a specific search for 'Педиатрия' or 'Эпидемиология',
    When the query runs against seeded data,
    Then corresponding accredited syllabi and reviews are retrieved.
    """
    results = normative_index.search(query_keyword)
    assert len(results) > 0, f"No search results found for keyword '{query_keyword}'"

    # Syllabi typically include РПД or ООП, reviews include Рецензия
    has_syllabus = any(
        ("рпд" in res.get("file_name", "").lower() or "ооп" in res.get("file_name", "").lower() or "рабочая программа" in res.get("file_name", "").lower())
        and query_keyword.lower() in (res.get("file_name", "") + " " + res.get("relative_path", "")).lower()
        for res in results
    )
    has_review = any(
        "рецензия" in res.get("file_name", "").lower()
        and query_keyword.lower() in (res.get("file_name", "") + " " + res.get("relative_path", "")).lower()
        for res in results
    )

    assert has_syllabus, f"Search for '{query_keyword}' did not retrieve accredited syllabi (РПД/ООП)"
    assert has_review, f"Search for '{query_keyword}' did not retrieve accredited reviews (Рецензии)"


@pytest.mark.parametrize("query_keyword", ["Педиатрия", "Эпидемиология"])
def test_api_search_retrieves_syllabi_and_reviews(test_client, query_keyword):
    """
    AC 2 (API search flow):
    Verify that HTTP API search for 'Педиатрия' or 'Эпидемиология' returns both syllabi and reviews.
    """
    response = test_client.get(f"/api/normative/search?q={query_keyword}")
    assert response.status_code == 200
    data = response.get_json()
    results = data.get("results", [])
    assert len(results) > 0

    file_names = [item.get("file_name", "").lower() for item in results]
    has_syllabus = any(
        "рпд" in name or "ооп" in name or "рабочая программа" in name
        for name in file_names
    )
    has_review = any("рецензия" in name for name in file_names)

    assert has_syllabus, f"API search for '{query_keyword}' missing accredited syllabi"
    assert has_review, f"API search for '{query_keyword}' missing accredited reviews"
