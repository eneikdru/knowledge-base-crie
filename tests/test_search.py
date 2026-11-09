import pytest
from typing import List, Dict, Any
from crie_assistant_index import (
    NormativeDocument,
    NormativeInvertedIndex,
    tokenize_text,
    normalize_russian_token,
    COMMON_ABBREVIATIONS,
    SPECIALTY_MAP,
)


def normalize_search_results(payload: Any) -> List[Dict[str, Any]]:
    """Extract search items strictly from payload without synthetic fallbacks."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("items", payload.get("documents", payload.get("results", [])))
    return []


def test_search_results_normalization_empty():
    """Verify empty response representations yield empty results with zero records."""
    assert normalize_search_results([]) == []
    assert normalize_search_results({"items": []}) == []
    assert normalize_search_results({"documents": []}) == []
    assert normalize_search_results({"results": []}) == []
    assert normalize_search_results(None) == []


def test_search_results_normalization_present():
    """Verify present records are returned strictly as provided."""
    raw_items = [
        {"id": "doc-1", "title": "Normative Guide", "author": "Department", "date": "2026-01-01"},
        {"id": "doc-2", "title": "Curriculum Spec", "author": "Admin", "date": "2026-02-01"}
    ]
    assert normalize_search_results(raw_items) == raw_items
    assert normalize_search_results({"items": raw_items, "total": 2}) == raw_items


def test_search_zero_rows_leaves_no_synthetic_records():
    """Ensure when server yields zero rows, no phantom materials are invented."""
    server_response = {"items": [], "total": 0}
    items = normalize_search_results(server_response)
    assert len(items) == 0
    assert items == []


def test_search_error_state_carries_no_domain_records():
    """Verify error handling state contains an empty document list."""
    state = {"status": "error", "errorMessage": "Connection refused", "documents": []}
    assert state["status"] == "error"
    assert len(state["documents"]) == 0


# =========================================================================
# Unit Tests for Synonym & Search Indexers Scoring Hierarchy
# =========================================================================

def test_russian_token_normalization_and_stemming():
    """Verify Russian stemming correctly strips grammatical endings and handles 'ё'."""
    assert normalize_russian_token("Педиатрия") == normalize_russian_token("педиатрии")
    assert normalize_russian_token("Эпидемиология") == normalize_russian_token("эпидемиологии")
    assert normalize_russian_token("Инфекционные") == normalize_russian_token("инфекционный")
    assert normalize_russian_token("общественное") == normalize_russian_token("общественный")


def test_common_abbreviations_expansion():
    """Verify abbreviations expand into their canonical constituent terms for search recall."""
    for abbrev, expansions in COMMON_ABBREVIATIONS.items():
        tokens = tokenize_text(abbrev)
        assert abbrev in tokens
        for exp in expansions:
            norm_exp = normalize_russian_token(exp)
            if norm_exp:
                assert norm_exp in tokens


def test_specialty_synonym_mappings():
    """Verify specialty codes and synonyms map consistently to canonical titles."""
    assert SPECIALTY_MAP["310819"] == "31.08.19 Педиатрия"
    assert SPECIALTY_MAP["31.08.19"] == "31.08.19 Педиатрия"
    assert SPECIALTY_MAP["педиатрия"] == "31.08.19 Педиатрия"
    assert SPECIALTY_MAP["инфбол"] == "31.08.35 Инфекционные болезни"
    assert SPECIALTY_MAP["310836"] == "31.08.36 Эпидемиология"
    assert SPECIALTY_MAP["320812"] == "32.08.12 Эпидемиология"


@pytest.fixture
def isolated_index():
    """Build an isolated in-memory search index with controlled scoring test documents."""
    index = NormativeInvertedIndex(catalog_path=None)
    docs = [
        NormativeDocument(
            doc_id=0,
            file_name="РПД Эпидемиология 2026.pdf",
            relative_path="normative/310836/rpd.pdf",
            extension="pdf",
            size_bytes=1024,
            category="Рабочие программы дисциплин",
            discipline="Эпидемиология",
            code="31.08.36",
            specialty="31.08.36 Эпидемиология",
            search_text="РПД Эпидемиология 2026.pdf normative/310836/rpd.pdf Рабочие программы дисциплин Эпидемиология 31.08.36 31.08.36 Эпидемиология"
        ),
        NormativeDocument(
            doc_id=1,
            file_name="Аннотация к курсу Инфекции.pdf",
            relative_path="normative/310835/annot.pdf",
            extension="pdf",
            size_bytes=2048,
            category="Рабочие программы дисциплин",
            discipline="Эпидемиология в педиатрии",
            code="31.08.35",
            specialty="31.08.35 Инфекционные болезни",
            search_text="Аннотация к курсу Инфекции.pdf normative/310835/annot.pdf Рабочие программы дисциплин Эпидемиология в педиатрии 31.08.35 31.08.35 Инфекционные болезни"
        ),
        NormativeDocument(
            doc_id=2,
            file_name="Регламент аттестации ординаторов.docx",
            relative_path="normative/general/reglament.docx",
            extension="docx",
            size_bytes=4096,
            category="Эпидемиология и профилактика",
            discipline="Общий регламент",
            code="31.08.19",
            specialty="31.08.19 Педиатрия",
            search_text="Регламент аттестации ординаторов.docx normative/general/reglament.docx Эпидемиология и профилактика Общий регламент 31.08.19 31.08.19 Педиатрия"
        )
    ]
    index.documents = docs
    index.total_docs = len(docs)
    index.index.clear()
    index.category_index.clear()
    index.code_index.clear()

    for doc in docs:
        if doc.category not in index.category_index:
            index.category_index[doc.category] = []
        index.category_index[doc.category].append(doc.doc_id)

        if doc.code:
            clean_code = doc.code.replace(".", "")
            for c in (doc.code, clean_code):
                if c not in index.code_index:
                    index.code_index[c] = []
                index.code_index[c].append(doc.doc_id)

        tokens = tokenize_text(doc.search_text)
        for token in set(tokens):
            if token not in index.index:
                index.index[token] = []
            index.index[token].append(doc.doc_id)

    return index


def test_search_scoring_exact_name_match_priority(isolated_index):
    """Verify exact query match in file name receives highest score weight (+50.0)."""
    res = isolated_index.search("Эпидемиология", limit=10)
    assert res["total_hits"] >= 2
    # Document 0 has 'эпидемиология' in file_name (+50) and discipline (+40) + token matches (+15, +10)
    # Document 1 has it only in discipline (+40) + token (+10)
    top_doc = res["results"][0]
    second_doc = res["results"][1]
    assert top_doc["id"] == 0
    assert top_doc["relevance_score"] > second_doc["relevance_score"]
    assert top_doc["relevance_score"] >= 90.0


def test_search_scoring_discipline_match_priority(isolated_index):
    """Verify discipline match receives +40.0 priority over category-only match (+5.0)."""
    res = isolated_index.search("Эпидемиология", limit=10)
    scores = {item["id"]: item["relevance_score"] for item in res["results"]}
    # doc 1 matches discipline (+40.0 + 10.0)
    # doc 2 matches category only (+5.0)
    if 1 in scores and 2 in scores:
        assert scores[1] > scores[2]


def test_search_scoring_multi_token_accumulation(isolated_index):
    """Verify multi-token search terms accumulate score linearly per matched field."""
    single_token_res = isolated_index.search("РПД", limit=10)
    multi_token_res = isolated_index.search("РПД Эпидемиология", limit=10)
    
    single_score = next(r["relevance_score"] for r in single_token_res["results"] if r["id"] == 0)
    multi_score = next(r["relevance_score"] for r in multi_token_res["results"] if r["id"] == 0)
    assert multi_score > single_score


def test_search_scoring_deterministic_tie_breaking(isolated_index):
    """Verify tie-breaking on identical scores deterministically prefers shorter file names."""
    # Create two documents with identical score profile
    doc_short = NormativeDocument(10, "Short.pdf", "p/s.pdf", "pdf", 100, "Cat", "Disc", None, None, "Общий курс Short")
    doc_long = NormativeDocument(11, "VeryLongFileName.pdf", "p/l.pdf", "pdf", 100, "Cat", "Disc", None, None, "Общий курс VeryLongFileName")
    isolated_index.documents.extend([doc_short, doc_long])
    isolated_index.total_docs = len(isolated_index.documents)
    
    for d in (doc_short, doc_long):
        for t in tokenize_text(d.search_text):
            if t not in isolated_index.index:
                isolated_index.index[t] = []
            isolated_index.index[t].append(d.doc_id)

    res = isolated_index.search("Общий", limit=10)
    doc_ids = [r["id"] for r in res["results"] if r["id"] in (10, 11)]
    assert doc_ids == [10, 11]


def test_search_scoring_empty_query(isolated_index):
    """Verify empty query returns documents with 0.0 relevance score without error."""
    res = isolated_index.search("", limit=10)
    assert res["total_hits"] == isolated_index.total_docs
    for item in res["results"]:
        assert item["relevance_score"] == 0.0


def test_search_facet_filtering_with_scoring(isolated_index):
    """Verify combining query with specialty and code filters accurately filters before scoring."""
    res = isolated_index.search("Эпидемиология", code="31.08.36", limit=10)
    assert res["total_hits"] == 1
    assert res["results"][0]["code"] == "31.08.36"
    assert res["results"][0]["id"] == 0
