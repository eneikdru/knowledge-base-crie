import json
from pathlib import Path
import pytest

CORPUS_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "normative" / "corpus_catalog.json"


@pytest.fixture(scope="module")
def corpus_catalog():
    """Load the seeded CRIE normative corpus catalog."""
    assert CORPUS_CATALOG_PATH.is_file(), f"Corpus catalog missing at {CORPUS_CATALOG_PATH}"
    with open(CORPUS_CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_corpus_catalog_walkability_all_categories(corpus_catalog):
    """
    Given a fresh installation seeded with the CRIE corpus,
    When automated acceptance tests query each category,
    Then every category returns at least 3 genuine items.
    """
    categories = corpus_catalog.get("categories", [])
    assert len(categories) > 0, "Corpus must define categories"

    for cat in categories:
        cat_name = cat.get("category")
        files = cat.get("files", [])
        file_count = cat.get("file_count", len(files))

        assert cat_name, "Category name must not be empty"
        assert file_count >= 3, f"Category '{cat_name}' has file_count={file_count}, expected >= 3"
        assert len(files) >= 3, f"Category '{cat_name}' has {len(files)} files listed, expected >= 3"

        # Verify items are genuine documents with valid names, paths and positive size
        for item in files:
            assert item.get("file_name"), f"File missing file_name in {cat_name}"
            assert item.get("relative_path"), f"File missing relative_path in {cat_name}"
            assert item.get("size_bytes", 0) > 0, f"File {item.get('file_name')} has non-positive size"


@pytest.mark.parametrize(
    "search_query,expected_syllabi_substr,expected_review_substr",
    [
        ("Педиатрия", "педиатрия", "рецензия"),
        ("Эпидемиология", "эпидемиология", "рецензия"),
    ],
)
def test_normative_search_retrieves_syllabi_and_reviews(
    corpus_catalog, search_query, expected_syllabi_substr, expected_review_substr
):
    """
    Given a specific search for 'Педиатрия' or 'Эпидемиология',
    When the query runs against seeded data,
    Then corresponding accredited syllabi (РПД/ООП) and reviews (Рецензия) are retrieved.
    """
    query_lower = search_query.lower()
    matching_files = []

    for cat in corpus_catalog.get("categories", []):
        for file_entry in cat.get("files", []):
            name = file_entry.get("file_name", "")
            rel_path = file_entry.get("relative_path", "")
            if query_lower in name.lower() or query_lower in rel_path.lower():
                matching_files.append(file_entry)

    assert len(matching_files) > 0, f"No seeded files matched query '{search_query}'"

    syllabi_matches = [
        f for f in matching_files
        if any(token in f["file_name"].lower() or token in f["relative_path"].lower() for token in ["рпд", "ооп", "рабочая программа"])
        and expected_syllabi_substr in (f["file_name"].lower() + " " + f["relative_path"].lower())
    ]

    reviews_matches = [
        f for f in matching_files
        if expected_review_substr in f["file_name"].lower() or expected_review_substr in f["relative_path"].lower()
    ]

    assert len(syllabi_matches) >= 1, f"Expected accredited syllabi for '{search_query}', found 0"
    assert len(reviews_matches) >= 1, f"Expected accredited reviews for '{search_query}', found 0"
