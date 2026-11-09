import os
import time
import pytest
from crie_assistant_index import NormativeInvertedIndex, get_normative_index, tokenize_text


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
    assert "педиатр" in tokens or "педиатри" in tokens
    assert "рпд" in tokens
    assert "310819" in tokens or "31.08.19" in tokens
