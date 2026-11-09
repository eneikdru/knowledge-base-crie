import json
import os
import pytest

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "normative",
    "corpus_catalog.json",
)


@pytest.fixture(scope="session")
def corpus_catalog():
    """Load and provide the seeded normative corpus catalog."""
    assert os.path.exists(CATALOG_PATH), f"Corpus catalog file not found at {CATALOG_PATH}"
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    return catalog


def test_corpus_seeded_integrity(corpus_catalog):
    """Assert that the catalog has total normative files defined and contains categories."""
    assert "categories" in corpus_catalog
    assert len(corpus_catalog["categories"]) > 0
    assert corpus_catalog.get("total_normative_files", 0) > 0


def test_all_categories_walkable_and_have_minimum_items(corpus_catalog):
    """
    Given a fresh installation seeded with the CRIE corpus,
    When automated acceptance tests query each category,
    Then every category returns at least 3 genuine items.
    """
    categories = corpus_catalog["categories"]
    assert len(categories) > 0, "Expected at least one category in CRIE corpus catalog"

    for cat in categories:
        cat_name = cat.get("category")
        file_count = cat.get("file_count", 0)
        files = cat.get("files", [])

        assert cat_name, "Category name must not be empty"
        assert file_count >= 3, (
            f"Category '{cat_name}' has only {file_count} files, expected at least 3 items"
        )
        assert len(files) >= 3, (
            f"Category '{cat_name}' file list contains {len(files)} files, expected at least 3 items"
        )

        for item in files:
            assert item.get("file_name"), f"File name missing in category {cat_name}"
            assert item.get("relative_path"), f"Relative path missing in category {cat_name}"
            assert item.get("size_bytes", 0) > 0, f"File size must be > 0 for {item.get('file_name')}"


def test_search_pediatrics_accredited_syllabi_and_reviews(corpus_catalog):
    """
    Given a specific search for 'Педиатрия',
    When the query runs against seeded data,
    Then corresponding accredited syllabi and reviews are retrieved.
    """
    query = "педиатрия"
    matching_files = []

    for cat in corpus_catalog["categories"]:
        for item in cat.get("files", []):
            file_name = item.get("file_name", "")
            rel_path = item.get("relative_path", "")
            if query in file_name.lower() or query in rel_path.lower():
                matching_files.append(item)

    assert len(matching_files) > 0, "Search for 'Педиатрия' returned no items"

    # Check for accredited syllabi (РПД / ООП / ОХОП)
    syllabi = [
        f for f in matching_files
        if any(keyword in f["file_name"].lower() for keyword in ["рпд", "ооп", "охоп", "рабочая программа"])
    ]
    assert len(syllabi) >= 1, "Search for 'Педиатрия' must return corresponding accredited syllabi (РПД/ООП)"

    # Check for accredited reviews (Рецензия)
    reviews = [
        f for f in matching_files
        if "рецензия" in f["file_name"].lower()
    ]
    assert len(reviews) >= 1, "Search for 'Педиатрия' must return corresponding reviews (Рецензии)"


def test_search_epidemiology_accredited_syllabi_and_reviews(corpus_catalog):
    """
    Given a specific search for 'Эпидемиология',
    When the query runs against seeded data,
    Then corresponding accredited syllabi and reviews are retrieved.
    """
    query = "эпидемиология"
    matching_files = []

    for cat in corpus_catalog["categories"]:
        for item in cat.get("files", []):
            file_name = item.get("file_name", "")
            rel_path = item.get("relative_path", "")
            if query in file_name.lower() or query in rel_path.lower():
                matching_files.append(item)

    assert len(matching_files) > 0, "Search for 'Эпидемиология' returned no items"

    # Check for accredited syllabi (РПД / ООП / ОХОП / Рабочая программа)
    syllabi = [
        f for f in matching_files
        if any(keyword in f["file_name"].lower() for keyword in ["рпд", "ооп", "охоп", "рабочая программа"])
    ]
    assert len(syllabi) >= 1, "Search for 'Эпидемиология' must return corresponding accredited syllabi (РПД/ООП)"

    # Check for accredited reviews (Рецензия)
    reviews = [
        f for f in matching_files
        if "рецензия" in f["file_name"].lower()
    ]
    assert len(reviews) >= 1, "Search for 'Эпидемиология' must return corresponding reviews (Рецензии)"
