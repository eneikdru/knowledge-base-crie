"""Tests for deterministic admission_records funding-type mapping and gated feedback.jsonl updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

BUDGET_FUNDING_CLAUSE = (
    "по очной форме обучения на места в рамках контрольных цифр приема "
    "за счет бюджетных ассигнований федерального бюджета"
)
PAID_FUNDING_CLAUSE = (
    "по очной форме обучения по договорам об образовании за счет средств "
    "физических и (или) юридических лиц"
)

FUNDING_CLAUSE_MAP: dict[str, tuple[str, str]] = {
    "budget": ("BUDGET_FEDERAL", BUDGET_FUNDING_CLAUSE),
    "target_quota": ("TARGET_QUOTA_FEDERAL", BUDGET_FUNDING_CLAUSE),
    "paid_contract": ("PAID_CONTRACT", PAID_FUNDING_CLAUSE),
}


def map_admission_funding(record: dict[str, Any]) -> tuple[str, str]:
    """Map an admission_records entry to its normative funding key and clause."""
    if not isinstance(record, dict):
        raise ValueError(f"Expected admission_records dict, got {type(record).__name__}")
    raw_funding = record.get("funding_type")
    if not isinstance(raw_funding, str):
        raise ValueError(f"Corrupted or missing funding_type in admission_records: {raw_funding!r}")
    normalized = raw_funding.strip().lower()
    if normalized not in FUNDING_CLAUSE_MAP:
        raise ValueError(f"Unmapped admission_records funding_type: {raw_funding!r}")
    return FUNDING_CLAUSE_MAP[normalized]


def resolve_feedback_record(
    jsonl_path: Path,
    record_id: int,
    *,
    verification_passed: bool,
    audit_note: str,
    expected_current_status: str = "open",
    clock: Callable[[], str],
) -> dict[str, Any]:
    """Transition a feedback.jsonl record to 'resolved' only after template verification."""
    if not verification_passed:
        raise RuntimeError("Template verification must pass before resolving feedback records.")
    if not audit_note or not audit_note.strip():
        raise ValueError("An explicit audit_note is required when resolving a feedback record.")

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]

    updated_record: dict[str, Any] | None = None
    for rec in records:
        if rec.get("id") == record_id:
            current_status = rec.get("status")
            if current_status != expected_current_status:
                raise ValueError(
                    f"Conditional transition failed for id={record_id}: "
                    f"expected status {expected_current_status!r}, found {current_status!r}"
                )
            rec["status"] = "resolved"
            rec["audit_note"] = audit_note
            rec["resolved_at"] = clock()
            updated_record = dict(rec)
            break

    if updated_record is None:
        raise LookupError(f"Feedback record id={record_id} not found in {jsonl_path}")

    serialized = "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records) + "\n"
    jsonl_path.write_text(serialized, encoding="utf-8")
    return updated_record


@pytest.mark.parametrize(
    ("funding_type", "expected_key"),
    [
        ("budget", "BUDGET_FEDERAL"),
        ("target_quota", "TARGET_QUOTA_FEDERAL"),
    ],
)
def test_map_admission_funding_budget_and_target_quota(
    funding_type: str, expected_key: str
) -> None:
    """Budget and target quota records map to the federal budget normative clause."""
    key, clause = map_admission_funding({"specialty": "32.08.12", "funding_type": funding_type})
    assert key == expected_key
    assert clause == BUDGET_FUNDING_CLAUSE


def test_map_admission_funding_paid_contract() -> None:
    """Paid contract records map to the paid education contract normative clause."""
    key, clause = map_admission_funding({"specialty": "32.08.12", "funding_type": "paid_contract"})
    assert key == "PAID_CONTRACT"
    assert clause == PAID_FUNDING_CLAUSE


@pytest.mark.parametrize("bad_value", [None, "", "   ", "unknown_enum", 42])
def test_map_admission_funding_rejects_corrupted_values(bad_value: Any) -> None:
    """Corrupted or unmapped funding_type values must fail explicitly."""
    with pytest.raises(ValueError):
        map_admission_funding({"specialty": "32.08.12", "funding_type": bad_value})


def test_feedback_transition_blocked_when_template_verification_fails(tmp_path: Path) -> None:
    """Feedback id=1 must remain open when template verification has not passed."""
    feedback_file = tmp_path / "feedback.jsonl"
    initial_content = json.dumps({"id": 1, "status": "open", "summary": "Template check"}) + "\n"
    feedback_file.write_text(initial_content, encoding="utf-8")

    with pytest.raises(RuntimeError, match="Template verification must pass"):
        resolve_feedback_record(
            feedback_file,
            1,
            verification_passed=False,
            audit_note="Should not apply",
            clock=lambda: "2026-11-19T00:00:00Z",
        )

    assert feedback_file.read_text(encoding="utf-8") == initial_content


def test_feedback_id_1_transitions_to_resolved_with_audit_note_and_fixed_timestamp(
    tmp_path: Path,
) -> None:
    """Verified template check transitions id=1 to resolved with audit note and deterministic timestamp."""
    feedback_file = tmp_path / "feedback.jsonl"
    rows = [
        {"id": 1, "status": "open", "template": "TPL-APPROVED-ADMISSION-RESIDENCY"},
        {"id": 2, "status": "open", "template": "OTHER"},
    ]
    feedback_file.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    fixed_ts = "2026-11-19T00:00:00Z"
    updated = resolve_feedback_record(
        feedback_file,
        1,
        verification_passed=True,
        audit_note="Verified TPL-APPROVED-ADMISSION-RESIDENCY for 32.08.12",
        clock=lambda: fixed_ts,
    )

    assert updated["status"] == "resolved"
    assert updated["audit_note"] == "Verified TPL-APPROVED-ADMISSION-RESIDENCY for 32.08.12"
    assert updated["resolved_at"] == fixed_ts

    persisted = [json.loads(line) for line in feedback_file.read_text(encoding="utf-8").splitlines()]
    assert persisted[0]["status"] == "resolved"
    assert persisted[0]["resolved_at"] == fixed_ts
    assert persisted[1]["status"] == "open"


def test_feedback_transition_rejects_already_resolved_record(tmp_path: Path) -> None:
    """Conditional status guard prevents overwriting an already-terminal feedback record."""
    feedback_file = tmp_path / "feedback.jsonl"
    feedback_file.write_text(
        json.dumps({"id": 1, "status": "resolved", "audit_note": "Already closed"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Conditional transition failed"):
        resolve_feedback_record(
            feedback_file,
            1,
            verification_passed=True,
            audit_note="Duplicate close attempt",
            clock=lambda: "2026-11-19T00:00:00Z",
        )
