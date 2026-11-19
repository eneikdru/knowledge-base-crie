import ast
import json
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_ARTIFACT_SEGMENTS = frozenset(
    {
        ".eneik",
        ".pytest_cache",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "node_modules",
        "playwright-report",
        "target",
        "test-results",
    }
)

FORBIDDEN_ARTIFACT_EXTENSIONS = frozenset(
    {".class", ".ear", ".jar", ".orig", ".pyc", ".pyo", ".rej", ".war"}
)

EXPECTED_PYTHON_MODULES = (
    "crie/workload/__init__.py",
    "crie/workload/schemas.py",
    "crie_assistant_api.py",
    "crie_assistant_index.py",
    "crie_autonomous_agent.py",
    "crie_document_engine.py",
    "crie_feedback_manager.py",
    "crie_normative_knowledge.py",
    "crie_smart_consultant.py",
    "crie_template_manager.py",
)


@dataclass(frozen=True)
class ReviewDecision:
    """Binary-safe outcome from the knowledge-first PR verification gate."""

    verdict: str
    approved: bool
    reasons: Tuple[str, ...] = field(default_factory=tuple)


def _has_blocking_concern(concerns: Any) -> bool:
    if not isinstance(concerns, list):
        return False
    for entry in concerns:
        if isinstance(entry, dict):
            severity = str(entry.get("severity", "")).strip().lower()
            message = str(entry.get("message", entry.get("summary", ""))).lower()
            if severity in {"high", "critical", "blocker"}:
                return True
            if "without diff" in message or "diff was not included" in message:
                return True
        elif isinstance(entry, str):
            lowered = entry.lower()
            if "without diff" in lowered or "not included" in lowered:
                return True
    return False


def _is_forbidden_artifact_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if any(part in FORBIDDEN_ARTIFACT_SEGMENTS for part in parts):
        return True
    return Path(normalized).suffix.lower() in FORBIDDEN_ARTIFACT_EXTENSIONS


def evaluate_review_gate(context: Mapping[str, Any]) -> ReviewDecision:
    """
    Enforce knowledge-first PR review verification.

    Never returns 'approve' when diff evidence is absent/uninspectable, target files
    are unverified, security or acceptance checks did not pass, build artifacts are
    present, or blocking concerns exist.
    """
    block_reasons: List[str] = []
    reject_reasons: List[str] = []

    diff_text = context.get("diff")
    diff_present = context.get("diff_present", True)
    diff_inspectable = context.get("diff_inspectable", True)
    if (
        not diff_present
        or not diff_inspectable
        or not isinstance(diff_text, str)
        or not diff_text.strip()
    ):
        block_reasons.append("missing_or_uninspectable_diff")

    target_files = context.get("target_files") or []
    inspected_files = set(context.get("inspected_files") or [])
    if target_files:
        missing_targets = sorted(set(target_files) - inspected_files)
        if missing_targets:
            block_reasons.append(
                f"uninspected_target_files:{','.join(missing_targets)}"
            )
    elif not inspected_files:
        block_reasons.append("no_inspected_files")

    if context.get("security_checks_passed") is not True:
        block_reasons.append("security_checks_unverified")

    if context.get("acceptance_criteria_verified") is not True:
        block_reasons.append("acceptance_criteria_unverified")

    artifacts = [
        path
        for path in (context.get("changed_files") or [])
        if _is_forbidden_artifact_path(str(path))
    ]
    if context.get("build_artifacts"):
        artifacts.extend(str(p) for p in context["build_artifacts"])
    if artifacts:
        reject_reasons.append(f"build_artifacts_present:{','.join(sorted(set(artifacts)))}")

    if _has_blocking_concern(context.get("concerns")):
        reject_reasons.append("blocking_review_concern")

    if reject_reasons:
        return ReviewDecision(
            verdict="reject",
            approved=False,
            reasons=tuple(reject_reasons + block_reasons),
        )
    if block_reasons:
        return ReviewDecision(
            verdict="block",
            approved=False,
            reasons=tuple(block_reasons),
        )
    return ReviewDecision(verdict="approve", approved=True, reasons=())


def _complete_review_context() -> Dict[str, Any]:
    return {
        "diff": "diff --git a/crie_normative_knowledge.py b/crie_normative_knowledge.py\n+def verify(): return True\n",
        "diff_present": True,
        "diff_inspectable": True,
        "target_files": ["crie_normative_knowledge.py"],
        "inspected_files": ["crie_normative_knowledge.py"],
        "changed_files": ["crie_normative_knowledge.py"],
        "security_checks_passed": True,
        "acceptance_criteria_verified": True,
        "build_artifacts": [],
        "concerns": [],
    }


def test_knowledge_first_gate_approves_complete_evidenced_context():
    decision = evaluate_review_gate(_complete_review_context())
    assert decision.verdict == "approve"
    assert decision.approved is True
    assert decision.reasons == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"diff": None},
        {"diff": ""},
        {"diff": "   \n\t  "},
        {"diff_present": False},
        {"diff_inspectable": False},
        {"inspected_files": []},
        {"target_files": ["crie_normative_knowledge.py", "crie_document_engine.py"], "inspected_files": ["crie_document_engine.py"]},
        {"security_checks_passed": False},
        {"security_checks_passed": None},
        {"acceptance_criteria_verified": False},
        {"acceptance_criteria_verified": None},
    ],
)
def test_knowledge_first_gate_blocks_missing_evidence_contexts(overrides):
    ctx = _complete_review_context()
    ctx.update(overrides)
    decision = evaluate_review_gate(ctx)
    assert decision.verdict == "block"
    assert decision.approved is False
    assert len(decision.reasons) >= 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"changed_files": ["crie_normative_knowledge.py", "target/crie.jar"]},
        {"changed_files": [".eneik/records/review-verdict.json"]},
        {"build_artifacts": ["__pycache__/module.pyc"]},
        {"concerns": [{"severity": "high", "message": "diff was not included"}]},
        {"concerns": ["approved leniently without diff inspection"]},
    ],
)
def test_knowledge_first_gate_rejects_artifacts_and_blocking_concerns(overrides):
    ctx = _complete_review_context()
    ctx.update(overrides)
    decision = evaluate_review_gate(ctx)
    assert decision.verdict == "reject"
    assert decision.approved is False
    assert len(decision.reasons) >= 1


def test_sqlite_seed_idempotency_and_deduplication(tmp_path: Path):
    """Verify SQLite schema constraints prevent duplicate seed rows on repeated runs."""
    db_path = tmp_path / "crie_qa_seed.db"
    seed_rows = [
        ("ORD-824", "Педиатрия", "31.08.19"),
        ("ORD-825", "Эпидемиология", "32.08.12"),
    ]

    def run_seed(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS normative_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT NOT NULL UNIQUE,
                specialty_name TEXT NOT NULL,
                specialty_code TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO normative_orders (order_code, specialty_name, specialty_code)
            VALUES (?, ?, ?)
            ON CONFLICT(order_code) DO NOTHING
            """,
            seed_rows,
        )
        conn.commit()

    with sqlite3.connect(db_path) as conn:
        run_seed(conn)
        run_seed(conn)
        rows = conn.execute(
            "SELECT order_code, specialty_name, specialty_code FROM normative_orders ORDER BY order_code"
        ).fetchall()
        assert rows == seed_rows

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO normative_orders (order_code, specialty_name, specialty_code) VALUES (?, ?, ?)",
                ("ORD-824", "Duplicate", "00.00.00"),
            )


def _list_repository_files() -> List[str]:
    if (REPO_ROOT / ".git").exists():
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    collected: List[str] = []
    for item in REPO_ROOT.rglob("*"):
        if item.is_file():
            collected.append(item.relative_to(REPO_ROOT).as_posix())
    return sorted(collected)


def test_repository_contains_no_committed_build_artifacts():
    tracked_files = _list_repository_files()
    assert len(tracked_files) > 0, "Repository file listing must not be empty"
    offenders = [path for path in tracked_files if _is_forbidden_artifact_path(path)]
    assert offenders == [], f"Unexpected build/orchestration artifacts tracked: {offenders}"


def test_pr_target_python_modules_parse_cleanly():
    for rel_path in EXPECTED_PYTHON_MODULES:
        module_path = REPO_ROOT / rel_path
        assert module_path.is_file(), f"Expected module missing: {rel_path}"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
        if rel_path == "crie_document_engine.py":
            function_names = {
                node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
            }
            assert "compile_session_to_docx" in function_names


def test_normative_template_and_avatar_invariants():
    catalog_path = REPO_ROOT / "data/normative/corpus_catalog.json"
    registry_path = REPO_ROOT / "data/templates/template_registry.json"
    extended_registry_path = REPO_ROOT / "data/templates/template_registry_extended.json"
    avatars_path = REPO_ROOT / "data/avatars/synthetic_avatars.json"

    for path in (catalog_path, registry_path, extended_registry_path, avatars_path):
        assert path.is_file(), f"Required data deliverable missing: {path}"

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert isinstance(catalog, dict)
    assert catalog.get("total_normative_files", 0) > 0
    categories = catalog.get("categories", [])
    assert isinstance(categories, list) and len(categories) > 0
    for category in categories:
        assert category.get("category")
        files = category.get("files", [])
        assert len(files) >= 3
        assert category.get("file_count", 0) >= 3

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert isinstance(registry, dict)
    templates = registry.get("templates")
    assert isinstance(templates, (list, dict)) and len(templates) > 0

    extended_registry = json.loads(extended_registry_path.read_text(encoding="utf-8"))
    assert isinstance(extended_registry, (list, dict)) and len(extended_registry) > 0

    avatars = json.loads(avatars_path.read_text(encoding="utf-8"))
    assert isinstance(avatars, dict)
    avatar_list = avatars.get("avatars")
    assert isinstance(avatar_list, (list, dict)) and len(avatar_list) > 0
