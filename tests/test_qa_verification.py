import ast
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_TRACKED_PREFIXES = (
    ".eneik/",
    "playwright-report/",
    "test-results/",
    "coverage/",
    "node_modules/",
    "target/",
    "dist/",
    "build/",
    "__pycache__/",
    ".pytest_cache/",
)

FORBIDDEN_TRACKED_EXTENSIONS = (
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".orig",
    ".rej",
)

FORBIDDEN_TRACKED_BASENAMES = {".DS_Store", ".env"}

PRESENT_PYTHON_MODULES = (
    "crie_assistant_api.py",
    "crie_assistant_index.py",
    "crie_autonomous_agent.py",
    "crie_document_engine.py",
    "crie_feedback_manager.py",
    "crie_normative_knowledge.py",
    "crie_smart_consultant.py",
    "crie_template_manager.py",
    "crie/workload/__init__.py",
    "crie/workload/schemas.py",
    "scripts/backup_restore.py",
    "scripts/build_standalone_ui.py",
    "scripts/ingest_materials.py",
)

MISSING_DIFF_CONCERN_MARKERS = (
    "diff",
    "not included",
    "never seen",
    "without diff",
    "lenient",
    "could not be verified",
    "uninspected",
)


def evaluate_review_verdict(context: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a PR review context under the binary knowledge-first gate."""
    reasons: list[str] = []
    diff = context.get("diff")
    diff_present = context.get("diff_present", True)

    if not diff_present or not isinstance(diff, str) or not diff.strip():
        reasons.append("Missing or empty PR diff evidence")
        return {"verdict": "block", "reasons": reasons}

    target_files = set(context.get("target_files") or [])
    inspected_files = set(context.get("inspected_files") or [])
    if target_files and not target_files.issubset(inspected_files):
        missing = sorted(target_files - inspected_files)
        reasons.append(f"Uninspected target files: {', '.join(missing)}")
        return {"verdict": "block", "reasons": reasons}

    for concern in context.get("concerns") or []:
        severity = str(concern.get("severity", "")).lower()
        message = str(concern.get("message", "")).lower()
        if any(marker in message for marker in MISSING_DIFF_CONCERN_MARKERS):
            reasons.append(f"Unverified diff evidence concern: {concern.get('message')}")
            return {"verdict": "block", "reasons": reasons}
        if severity in {"high", "critical"}:
            reasons.append(f"Blocking {severity} concern: {concern.get('message')}")

    if not context.get("acceptance_criteria_verified"):
        reasons.append("Acceptance criteria not verified")
    if not context.get("security_checks_passed"):
        reasons.append("Security checks not verified")
    if not context.get("build_artifacts_clean"):
        reasons.append("Build artifact cleanliness not verified")

    if reasons:
        return {"verdict": "reject", "reasons": reasons}

    return {"verdict": "approve", "reasons": []}


def _load_json(relative_path: str) -> Any:
    """Load and parse a required repository JSON file."""
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"Required JSON file missing: {path}"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _collect_tracked_or_repo_files() -> list[str]:
    """Return tracked repository relative paths deterministically."""
    if (REPO_ROOT / ".git").exists():
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"git ls-files failed: {proc.stderr}"
        return [line for line in proc.stdout.splitlines() if line]

    ignored_runtime_dirs = {".pytest_cache", "__pycache__"}
    discovered: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in ignored_runtime_dirs for part in Path(rel).parts):
            continue
        discovered.append(rel)
    return discovered


def _seed_catalog_to_sqlite(db_path: Path, catalog: dict[str, Any]) -> int:
    """Idempotently seed normative catalog entries into SQLite and return row count."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS normative_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                file_name TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                UNIQUE(category, relative_path)
            )
            """
        )
        rows = [
            (
                cat["category"],
                item["file_name"],
                item["relative_path"],
                int(item["size_bytes"]),
            )
            for cat in catalog["categories"]
            for item in cat["files"]
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO normative_documents (
                category, file_name, relative_path, size_bytes
            ) VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM normative_documents").fetchone()[0]
        return int(count)


def test_knowledge_first_gate_approves_complete_verified_context() -> None:
    """Complete diff and all verification gates produce an approve verdict."""
    context = {
        "diff": "diff --git a/tests/test_qa_verification.py b/tests/test_qa_verification.py\n+def ok(): pass",
        "diff_present": True,
        "target_files": ["tests/test_qa_verification.py"],
        "inspected_files": ["tests/test_qa_verification.py"],
        "acceptance_criteria_verified": True,
        "security_checks_passed": True,
        "build_artifacts_clean": True,
        "concerns": [],
    }
    result = evaluate_review_verdict(context)
    assert result["verdict"] == "approve"
    assert result["reasons"] == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"diff": None, "diff_present": False},
        {"diff": ""},
        {"diff": "   \n\t  "},
        {"diff_present": False},
        {"diff": None, "lenient": True, "pipeline_continue": True},
    ],
)
def test_knowledge_first_gate_never_approves_missing_diff(overrides: dict[str, Any]) -> None:
    """Missing or empty diff contexts strictly return reject/block and never approve."""
    context: dict[str, Any] = {
        "diff": "diff --git a/a.py b/a.py\n+x = 1",
        "diff_present": True,
        "target_files": ["a.py"],
        "inspected_files": ["a.py"],
        "acceptance_criteria_verified": True,
        "security_checks_passed": True,
        "build_artifacts_clean": True,
        "concerns": [],
    }
    context.update(overrides)

    result = evaluate_review_verdict(context)
    assert result["verdict"] in {"reject", "block"}
    assert result["verdict"] != "approve"
    assert len(result["reasons"]) > 0


def test_knowledge_first_gate_blocks_uninspected_target_files() -> None:
    """Diffs that omit declared target files must not be approved."""
    context = {
        "diff": "diff --git a/a.py b/a.py\n+x = 1",
        "diff_present": True,
        "target_files": ["a.py", "b.py"],
        "inspected_files": ["a.py"],
        "acceptance_criteria_verified": True,
        "security_checks_passed": True,
        "build_artifacts_clean": True,
        "concerns": [],
    }
    result = evaluate_review_verdict(context)
    assert result["verdict"] in {"reject", "block"}
    assert result["verdict"] != "approve"
    assert any("b.py" in reason for reason in result["reasons"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"acceptance_criteria_verified": False},
        {"security_checks_passed": False},
        {"build_artifacts_clean": False},
        {"concerns": [{"severity": "high", "message": "SQLite schema unverified"}]},
        {
            "concerns": [
                {
                    "severity": "medium",
                    "message": "Approved leniently without diff inspection",
                }
            ]
        },
    ],
)
def test_knowledge_first_gate_rejects_unverified_checks_and_blocking_concerns(
    overrides: dict[str, Any],
) -> None:
    """Failed gates or blocking concerns strictly prevent approval."""
    context: dict[str, Any] = {
        "diff": "diff --git a/a.py b/a.py\n+x = 1",
        "diff_present": True,
        "target_files": ["a.py"],
        "inspected_files": ["a.py"],
        "acceptance_criteria_verified": True,
        "security_checks_passed": True,
        "build_artifacts_clean": True,
        "concerns": [],
    }
    context.update(overrides)

    result = evaluate_review_verdict(context)
    assert result["verdict"] in {"reject", "block"}
    assert result["verdict"] != "approve"
    assert len(result["reasons"]) > 0


def test_no_unintended_build_artifacts_tracked() -> None:
    """Repository must not track build artifacts, internal state, or env files."""
    tracked_files = _collect_tracked_or_repo_files()
    assert len(tracked_files) > 0

    violations: list[str] = []
    for rel_path in tracked_files:
        normalized = rel_path.replace("\\", "/")
        if any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in FORBIDDEN_TRACKED_PREFIXES):
            violations.append(rel_path)
        elif normalized.endswith(FORBIDDEN_TRACKED_EXTENSIONS):
            violations.append(rel_path)
        elif Path(normalized).name in FORBIDDEN_TRACKED_BASENAMES:
            violations.append(rel_path)

    assert violations == [], f"Unintended build/internal artifacts found: {violations}"


def test_normative_catalog_invariants_and_sqlite_seed_idempotency(tmp_path: Path) -> None:
    """Normative catalog must be well-formed, deduplicated, and idempotent to seed."""
    catalog = _load_json("data/normative/corpus_catalog.json")
    assert isinstance(catalog, dict)
    assert catalog.get("total_normative_files", 0) > 0

    categories = catalog.get("categories", [])
    assert isinstance(categories, list) and len(categories) > 0

    seen_keys: set[tuple[str, str]] = set()
    for cat in categories:
        cat_name = cat.get("category")
        files = cat.get("files", [])
        assert cat_name
        assert len(files) >= 3
        for item in files:
            rel_path = item.get("relative_path")
            assert item.get("file_name")
            assert rel_path
            assert item.get("size_bytes", 0) > 0
            key = (cat_name, rel_path)
            assert key not in seen_keys, f"Duplicate catalog entry detected: {key}"
            seen_keys.add(key)

    db_path = tmp_path / "normative_seed.db"
    first_count = _seed_catalog_to_sqlite(db_path, catalog)
    second_count = _seed_catalog_to_sqlite(db_path, catalog)
    assert first_count == len(seen_keys)
    assert second_count == first_count


def test_template_and_avatar_registry_invariants() -> None:
    """Template registries and synthetic avatars must exist and contain valid entries."""
    registry = _load_json("data/templates/template_registry.json")
    assert isinstance(registry, dict)
    templates = registry.get("templates")
    assert isinstance(templates, (list, dict)) and len(templates) > 0

    extended_registry = _load_json("data/templates/template_registry_extended.json")
    assert isinstance(extended_registry, (dict, list)) and len(extended_registry) > 0

    avatars_payload = _load_json("data/avatars/synthetic_avatars.json")
    assert isinstance(avatars_payload, dict)
    avatars = avatars_payload.get("avatars")
    assert isinstance(avatars, (list, dict)) and len(avatars) > 0


def test_document_engine_module_invariants() -> None:
    """Document engine module must parse cleanly and expose compile_session_to_docx."""
    doc_engine_path = REPO_ROOT / "crie_document_engine.py"
    assert doc_engine_path.is_file()
    tree = ast.parse(doc_engine_path.read_text(encoding="utf-8"), filename=str(doc_engine_path))
    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "compile_session_to_docx" in function_names


def test_present_python_modules_parse_cleanly() -> None:
    """All expected Python deliverable modules must be present and syntactically valid."""
    for rel_path in PRESENT_PYTHON_MODULES:
        module_path = REPO_ROOT / rel_path
        assert module_path.is_file(), f"Expected module missing: {rel_path}"
        source = module_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(module_path))
