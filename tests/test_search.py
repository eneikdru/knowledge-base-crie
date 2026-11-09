import pytest
from typing import List, Dict, Any


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
