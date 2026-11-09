import os
import time
import pytest
from crie_assistant_index import (
    NormativeInvertedIndex,
    get_normative_index,
    tokenize_text,
    normalize_russian_token,
    RUSSIAN_STOP_WORDS,
    COMMON_ABBREVIATIONS,
    SPECIALTY_MAP,
)


@pytest.fixture(scope="module")
def index():
    catalog_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "normative", "corpus_catalog.json"
    )
    return NormativeInvertedIndex(catalog_path=catalog_path)


def test_catalog_loaded_documents(index):
    assert index.total_docs == 1697
    assert len(index.category_index) > 0
    assert len(index.index) > 100


def test_discipline_search_latency_sub_10ms(index):
    queries = [
        "Педиатрия",
        "Инфекционные болезни",
        "Эпидемиология",
        "Вирусология",
        "Паразитология",
        "Фтизиатрия"
    ]
    for q in queries:
        res = index.search(q, limit=20)
        assert res["elapsed_ms"] < 10.0, f"Query '{q}' took {res['elapsed_ms']}ms, expected < 10ms"
        assert res["total_hits"] > 0
        assert len(res["results"]) > 0
        assert "snippet" in res["results"][0]


def test_abbreviations_expansion(index):
    abbrev_queries = ["РПД", "ГИА", "ГЭК", "ФОС", "РУП"]
    for abbrev in abbrev_queries:
        res = index.search(abbrev, limit=10)
        assert res["elapsed_ms"] < 10.0
        assert res["total_hits"] > 0


def test_specialty_code_filter(index):
    res_ped = index.search("", code="31.08.19", limit=50)
    assert res_ped["total_hits"] > 0
    for item in res_ped["results"]:
        assert item["code"] == "31.08.19" or "310819" in item["relative_path"]

    res_inf = index.search("", code="31.08.35", limit=50)
    assert res_inf["total_hits"] > 0
    for item in res_inf["results"]:
        assert item["code"] == "31.08.35" or "310835" in item["relative_path"]


def test_category_filter(index):
    categories = index.get_categories()
    assert len(categories) > 0
    first_cat = categories[0]["category"]
    res = index.search("", category=first_cat, limit=100)
    assert res["total_hits"] == categories[0]["count"]


def test_tokenization_and_snippet():
    tokens = tokenize_text("РПД по Педиатрии и Инфекционным болезням 31.08.19")
    assert any("педиатр" in t for t in tokens)
    assert "рпд" in tokens
    assert any("310819" in t or "31.08.19" in t for t in tokens)


def test_russian_stemming_and_normalization():
    """Verify stemming of various grammatical endings in normative texts."""
    cases = [
        ("регламенты", "регламент"),
        ("положения", "положен"),
        ("инструкциями", "инструкц"),
        ("аттестацией", "аттестац"),
        ("эпидемиологический", "эпидемиологическ"),
        ("педиатрические", "педиатрическ"),
        ("инфекционную", "инфекционн"),
    ]
    for raw_word, expected_stem in cases:
        stemmed = normalize_russian_token(raw_word)
        assert expected_stem in stemmed, f"Stemming failed for {raw_word}: got {stemmed}, expected substr {expected_stem}"


def test_stop_words_filtering():
    """Verify Russian stop words are discarded from token stream."""
    text = "что и как в во не на о по при для все"
    tokens = tokenize_text(text)
    assert len(tokens) == 0, f"Expected all stop words to be removed, got {tokens}"


def test_facet_combinations_exhaustive(index):
    """Verify multi-facet filtering (query + category + code + specialty) produces accurate intersections."""
    # Query with specialty and category
    categories = [c["category"] for c in index.get_categories()]
    assert len(categories) > 0

    # Combo 1: query + code
    res_combo1 = index.search(query="дисциплины", code="31.08.35", limit=20)
    for doc in res_combo1["results"]:
        assert doc["code"] == "31.08.35" or "310835" in doc["relative_path"]

    # Combo 2: query + specialty string
    res_combo2 = index.search(query="программа", specialty="Инфекционные болезни", limit=20)
    for doc in res_combo2["results"]:
        assert doc["specialty"] is not None
        assert "инфекционные болезни" in doc["specialty"].lower()

    # Combo 3: specialty code + category intersection
    target_cat = categories[0]
    res_combo3 = index.search(query="", category=target_cat, code="31.08.19", limit=30)
    for doc in res_combo3["results"]:
        assert target_cat.lower() in doc["category"].lower()
        assert doc["code"] == "31.08.19" or "310819" in doc["relative_path"]

    # Combo 4: non-matching combination returns 0 hits safely
    res_empty = index.search(query="несуществующийтерминxyz999", code="31.08.19")
    assert res_empty["total_hits"] == 0
    assert len(res_empty["results"]) == 0
