from __future__ import annotations

import ast
import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_TRACKED_ARTIFACT_PATTERNS = (
    re.compile(r"(^|/)__pycache__(/|$)"),
    re.compile(r"\.py[cod]$"),
    re.compile(r"(^|/)node_modules(/|$)"),
    re.compile(r"(^|/)target(/|$)"),
    re.compile(r"(^|/)dist(/|$)"),
    re.compile(r"(^|/)build(/|$)"),
    re.compile(r"(^|/)playwright-report(/|$)"),
    re.compile(r"(^|/)test-results(/|$)"),
    re.compile(r"(^|/)\.pytest_cache(/|$)"),
    re.compile(r"(^|/)htmlcov(/|$)"),
    re.compile(r"(^|/)\.coverage$"),
    re.compile(r"(^|/)\.eneik(/|$)"),
    re.compile(r"\.(db|sqlite|sqlite3)$"),
)

MISSING_EVIDENCE_MARKERS = (
    "not included",
    "never seen",
    "without diff",
    "diff was absent",
    "missing diff",
    "could not be verified",
    "could not be inspected",
)

BLOCKING_SEVERITIES = {"high", "critical", "blocker"}


@dataclass(frozen=True)
class ReviewContext:
    """Structured review evidence context evaluated by the knowledge-first gate."""

    pr_number: int
    diff_present: bool
    diff_content: str | None = None
    target_files: tuple[str, ...] = ()
    inspected_files: tuple[str, ...] = ()
    acceptance_criteria_verified: bool = False
    security_checked: bool = False
    build_artifacts_clean: bool = False
    concerns: tuple[dict[str, str] | str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VerificationVerdict:
    """Binary outcome returned by the knowledge-first verification helper."""

    verdict: str
    approved: bool
    reasons: tuple[str, ...]


def _normalize_path(path_value: str) -> str:
    return path_value.strip().replace("\\", "/").lstrip("./")


def _coerce_context(context: ReviewContext | dict[str, Any]) -> ReviewContext:
    if isinstance(context, ReviewContext):
        return context
    return ReviewContext(
        pr_number=int(context.get("pr_number", 0)),
        diff_present=bool(context.get("diff_present", False)),
        diff_content=context.get("diff_content"),
        target_files=tuple(context.get("target_files", ()) or ()),
        inspected_files=tuple(context.get("inspected_files", ()) or ()),
        acceptance_criteria_verified=bool(context.get("acceptance_criteria_verified", False)),
        security_checked=bool(context.get("security_checked", False)),
        build_artifacts_clean=bool(context.get("build_artifacts_clean", False)),
        concerns=tuple(context.get("concerns", ()) or ()),
    )


def evaluate_review_evidence(context: ReviewContext | dict[str, Any]) -> VerificationVerdict:
    """Enforce knowledge-first PR review gating: never approve without diff and verification evidence."""
    ctx = _coerce_context(context)
    block_reasons: list[str] = []
    reject_reasons: list[str] = []

    if not ctx.diff_present or not isinstance(ctx.diff_content, str) or not ctx.diff_content.strip():
        block_reasons.append("Missing inspectable diff evidence in review context")

    if ctx.target_files:
        inspected_set = {_normalize_path(p) for p in ctx.inspected_files}
        missing_targets = [
            t for t in ctx.target_files if _normalize_path(t) not in inspected_set
        ]
        if missing_targets:
            block_reasons.append(
                f"Target files not inspected in diff: {', '.join(missing_targets)}"
            )

    if not ctx.acceptance_criteria_verified:
        reject_reasons.append("Acceptance criteria verification is incomplete")
    if not ctx.security_checked:
        reject_reasons.append("Security inspection was not completed")
    if not ctx.build_artifacts_clean:
        reject_reasons.append("Build-artifact cleanliness check failed")

    for concern in ctx.concerns:
        if isinstance(concern, dict):
            severity = str(concern.get("severity", "")).strip().lower()
            message = str(concern.get("message") or concern.get("description") or "").strip()
        else:
            severity = ""
            message = str(concern).strip()
        message_lower = message.lower()
        if severity in BLOCKING_SEVERITIES:
            reject_reasons.append(f"Blocking {severity} concern: {message or 'unspecified'}")
        elif any(marker in message_lower for marker in MISSING_EVIDENCE_MARKERS):
            block_reasons.append(f"Unverified evidence concern: {message}")

    if block_reasons:
        return VerificationVerdict(
            verdict="block",
            approved=False,
            reasons=tuple(block_reasons + reject_reasons),
        )
    if reject_reasons:
        return VerificationVerdict(
            verdict="reject",
            approved=False,
            reasons=tuple(reject_reasons),
        )
    return VerificationVerdict(verdict="approve", approved=True, reasons=())


def test_knowledge_first_approves_complete_review_context() -> None:
    context = ReviewContext(
        pr_number=500,
        diff_present=True,
        diff_content="--- a/tests/test_qa_verification.py\n+++ b/tests/test_qa_verification.py\n+def ok(): pass\n",
        target_files=("tests/test_qa_verification.py",),
        inspected_files=("tests/test_qa_verification.py",),
        acceptance_criteria_verified=True,
        security_checked=True,
        build_artifacts_clean=True,
        concerns=(),
    )
    result = evaluate_review_evidence(context)
    assert result.verdict == "approve"
    assert result.approved is True
    assert result.reasons == ()


@pytest.mark.parametrize(
    "diff_present,diff_content",
    [
        (False, None),
        (False, ""),
        (True, None),
        (True, ""),
        (True, "   \n\t  "),
    ],
)
def test_knowledge_first_blocks_missing_diff_contexts(
    diff_present: bool, diff_content: str | None
) -> None:
    context = {
        "pr_number": 419,
        "diff_present": diff_present,
        "diff_content": diff_content,
        "target_files": ["crie_normative_knowledge.py"],
        "inspected_files": ["crie_normative_knowledge.py"],
        "acceptance_criteria_verified": True,
        "security_checked": True,
        "build_artifacts_clean": True,
    }
    result = evaluate_review_evidence(context)
    assert result.verdict == "block"
    assert result.approved is False
    assert result.verdict != "approve"
    assert len(result.reasons) >= 1


def test_knowledge_first_blocks_uninspected_target_files() -> None:
    context = ReviewContext(
        pr_number=419,
        diff_present=True,
        diff_content="diff --git a/crie_normative_knowledge.py b/crie_normative_knowledge.py\n+x = 1\n",
        target_files=("crie_normative_knowledge.py", "crie_persistent_memory.py"),
        inspected_files=("crie_normative_knowledge.py",),
        acceptance_criteria_verified=True,
        security_checked=True,
        build_artifacts_clean=True,
    )
    result = evaluate_review_evidence(context)
    assert result.verdict in {"block", "reject"}
    assert result.approved is False
    assert any("crie_persistent_memory.py" in reason for reason in result.reasons)


def test_knowledge_first_rejects_lenient_approval_with_missing_evidence_concerns() -> None:
    context = ReviewContext(
        pr_number=415,
        diff_present=True,
        diff_content="diff --git a/a.py b/a.py\n+pass\n",
        target_files=("a.py",),
        inspected_files=("a.py",),
        acceptance_criteria_verified=True,
        security_checked=True,
        build_artifacts_clean=True,
        concerns=(
            {"severity": "high", "message": "Target diff was not included and could not be verified"},
        ),
    )
    result = evaluate_review_evidence(context)
    assert result.verdict in {"block", "reject"}
    assert result.approved is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"acceptance_criteria_verified": False},
        {"security_checked": False},
        {"build_artifacts_clean": False},
    ],
)
def test_knowledge_first_rejects_incomplete_verification_gates(
    overrides: dict[str, bool],
) -> None:
    payload: dict[str, Any] = {
        "pr_number": 417,
        "diff_present": True,
        "diff_content": "diff --git a/app.py b/app.py\n+pass\n",
        "target_files": ["app.py"],
        "inspected_files": ["app.py"],
        "acceptance_criteria_verified": True,
        "security_checked": True,
        "build_artifacts_clean": True,
    }
    payload.update(overrides)
    result = evaluate_review_evidence(payload)
    assert result.verdict == "reject"
    assert result.approved is False


def test_repository_build_artifact_cleanliness() -> None:
    gitignore_path = REPO_ROOT / ".gitignore"
    assert gitignore_path.is_file(), "Root .gitignore must exist"
    assert gitignore_path.read_text(encoding="utf-8").strip(), "Root .gitignore must not be empty"

    assert (REPO_ROOT / ".git").exists(), "Repository must have git metadata for tracked-file inspection"
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    assert len(tracked_files) > 0, "git ls-files returned no tracked files"

    offending = [
        rel_path
        for rel_path in tracked_files
        if any(pattern.search(rel_path) for pattern in FORBIDDEN_TRACKED_ARTIFACT_PATTERNS)
    ]
    assert offending == [], f"Forbidden build or internal artifacts tracked in git: {offending}"


def test_repository_deliverables_and_target_modules_present_and_valid() -> None:
    expected_deliverables = (
        "data/normative/corpus_catalog.json",
        "data/templates/template_registry.json",
        "data/avatars/synthetic_avatars.json",
        "crie_document_engine.py",
        "crie_normative_knowledge.py",
        "crie_template_manager.py",
        "crie_assistant_api.py",
        "crie_assistant_index.py",
        "crie_feedback_manager.py",
        "crie_smart_consultant.py",
        "crie_autonomous_agent.py",
        "crie/workload/schemas.py",
        "scripts/ingest_materials.py",
        "scripts/backup_restore.py",
    )
    for rel_path in expected_deliverables:
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"Expected deliverable missing: {rel_path}"
        assert full_path.stat().st_size > 0, f"Deliverable is empty: {rel_path}"

    ignored_roots = {".git", ".venv", "venv", "node_modules", "target", "__pycache__"}
    python_files = [
        path
        for path in REPO_ROOT.rglob("*.py")
        if not any(part in ignored_roots for part in path.relative_to(REPO_ROOT).parts)
    ]
    assert len(python_files) > 0, "No Python modules found in repository"

    for py_path in python_files:
        source = py_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(py_path))


def test_normative_template_and_document_invariants() -> None:
    catalog_path = REPO_ROOT / "data" / "normative" / "corpus_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert isinstance(catalog, dict)
    assert isinstance(catalog.get("total_normative_files"), int)
    assert catalog["total_normative_files"] > 0
    categories = catalog.get("categories")
    assert isinstance(categories, list) and len(categories) > 0
    for cat in categories:
        assert isinstance(cat, dict)
        assert isinstance(cat.get("category"), str) and cat["category"].strip()
        files = cat.get("files")
        assert isinstance(files, list) and len(files) > 0
        for entry in files:
            assert isinstance(entry.get("file_name"), str) and entry["file_name"].strip()
            rel = entry.get("relative_path")
            assert isinstance(rel, str) and rel.strip()
            assert not Path(rel).is_absolute(), f"Absolute path in corpus catalog: {rel}"
            assert ".." not in Path(rel).parts, f"Path traversal in corpus catalog: {rel}"
            assert isinstance(entry.get("size_bytes"), int) and entry["size_bytes"] > 0

    registry_path = REPO_ROOT / "data" / "templates" / "template_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert isinstance(registry, dict)
    templates = registry.get("templates")
    assert isinstance(templates, list) and len(templates) > 0
    assert all(isinstance(tpl, dict) and len(tpl) > 0 for tpl in templates)

    avatars_path = REPO_ROOT / "data" / "avatars" / "synthetic_avatars.json"
    avatars = json.loads(avatars_path.read_text(encoding="utf-8"))
    assert isinstance(avatars, dict)
    assert isinstance(avatars.get("avatars"), list) and len(avatars["avatars"]) > 0

    doc_engine_path = REPO_ROOT / "crie_document_engine.py"
    tree = ast.parse(doc_engine_path.read_text(encoding="utf-8"), filename=str(doc_engine_path))
    defined_funcs = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "compile_session_to_docx" in defined_funcs


def test_sqlite_seed_idempotency_and_deterministic_loads(tmp_path: Path) -> None:
    catalog_path = REPO_ROOT / "data" / "normative" / "corpus_catalog.json"
    first_load = json.loads(catalog_path.read_text(encoding="utf-8"))
    second_load = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert first_load == second_load

    seed_rows = [
        (cat["category"], entry["file_name"], entry["relative_path"], entry["size_bytes"])
        for cat in first_load["categories"]
        for entry in cat["files"]
    ]
    assert len(seed_rows) > 0

    db_path = tmp_path / "qa_seed_verify.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS normative_corpus_seed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                file_name TEXT NOT NULL,
                relative_path TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL
            )
            """
        )
        insert_sql = """
            INSERT OR IGNORE INTO normative_corpus_seed
                (category, file_name, relative_path, size_bytes)
            VALUES (?, ?, ?, ?)
        """
        conn.executemany(insert_sql, seed_rows)
        conn.commit()
        first_count = conn.execute("SELECT COUNT(*) FROM normative_corpus_seed").fetchone()[0]

        conn.executemany(insert_sql, seed_rows)
        conn.commit()
        second_count = conn.execute("SELECT COUNT(*) FROM normative_corpus_seed").fetchone()[0]
    finally:
        conn.close()

    assert first_count > 0
    assert first_count == second_count
    assert first_count == len({row[2] for row in seed_rows})
