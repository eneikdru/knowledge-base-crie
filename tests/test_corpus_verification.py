import json
from pathlib import Path
import pytest

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "normative" / "corpus_catalog.json"


@pytest.fixture
def corpus_catalog():
    assert CATALOG_PATH.exists(), f"Corpus catalog not found at {CATALOG_PATH}"
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_corpus_categories_contain_minimum_items(corpus_catalog):
    """
    Given a fresh installation seeded with the CRIE corpus,
    When automated acceptance tests query each category,
    Then every category returns at least 3 genuine items.
    """
    categories = corpus_catalog.get("categories", [])
    assert len(categories) > 0, "Catalog should contain at least one educational category"

    for category_info in categories:
        cat_name = category_info.get("category")
        file_count = category_info.get("file_count", 0)
        files = category_info.get("files", [])

        assert file_count >= 3, f"Category '{cat_name}' has fewer than 3 files recorded ({file_count})"
        assert len(files) >= 3, f"Category '{cat_name}' has fewer than 3 file entries in catalog ({len(files)})"

        for item in files:
            assert item.get("file_name"), f"File item in category '{cat_name}' missing file_name"
            assert item.get("size_bytes", 0) > 0, f"File item '{item.get('file_name')}' has non-positive size"
            assert item.get("extension"), f"File item '{item.get('file_name')}' missing extension"


@pytest.mark.parametrize("discipline", ["Педиатрия", "Эпидемиология"])
def test_discipline_search_retrieves_syllabi_and_reviews(corpus_catalog, discipline):
    """
    Given a specific search for 'Педиатрия' or 'Эпидемиология',
    When the query runs against seeded data,
    Then corresponding accredited syllabi and reviews are retrieved.
    """
    all_files = []
    for category_info in corpus_catalog.get("categories", []):
        all_files.extend(category_info.get("files", []))

    matched_files = [
        f for f in all_files
        if discipline.lower() in f.get("file_name", "").lower()
        or discipline.lower() in f.get("relative_path", "").lower()
    ]

    assert len(matched_files) > 0, f"No files found matching query '{discipline}'"

    # Verify accredited syllabi (РПД or ООП or ОХОП or Рабочая программа)
    syllabi = [
        f for f in matched_files
        if any(term in f.get("file_name", "").lower() for term in ["рпд", "ооп", "охоп", "рабочая программа"])
    ]
    assert len(syllabi) >= 1, f"Expected accredited syllabi for '{discipline}', found none"

    # Verify reviews (Рецензия or Рецензии)
    reviews = [
        f for f in matched_files
        if "рецензия" in f.get("file_name", "").lower()
        or "рецензи" in f.get("relative_path", "").lower()
    ]
    assert len(reviews) >= 1, f"Expected accredited reviews for '{discipline}', found none"
