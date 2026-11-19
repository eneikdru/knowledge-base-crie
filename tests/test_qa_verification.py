import ast
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DATA_FILES = (
    "data/normative/corpus_catalog.json",
    "data/templates/template_registry.json",
    "data/templates/template_registry_extended.json",
    "data/avatars/synthetic_avatars.json",
)

CORE_PYTHON_MODULES = (
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

FORBIDDEN_TRACKED_DIR_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "target",
    "playwright-report",
    "test-results",
    "htmlcov",
    ".nyc_output",
    ".eneik",
    "dist",
    "build",
}

FORBIDDEN_TRACKED_SUFFIXES = (".pyc", ".pyo")
FORBIDDEN_TRACKED_FILENAMES = {".coverage"}

FORBIDDEN_WORKSPACE_ARTIFACT_DIRS = (
    "playwright-report",
    "test-results",
    "htmlcov",
    ".nyc_output",
)


def evaluate_review_gate(review_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate a PR review context under Goldman's knowledge-first gate.

    Approval is strictly binary: 'approve' is emitted if and only if diff
    evidence is present and inspectable, all target files were inspected,
    acceptance criteria and security checks passed, tests passed, and no
    build artifacts or blocking concerns are present.
    """
    if not isinstance(review_context, dict):
        return {
            "verdict": "block",
            "evidence_complete": False,
            "reasons": ["review_context must be a mapping"],
        }

    block_reasons: List[str] = []
    reject_reasons: List[str] = []

    diff_text = review_context.get("diff")
    if not isinstance(diff_text, str) or not diff_text.strip():
        block_reasons.append("missing or empty diff evidence")

    if review_context.get("diff_missing") or review_context.get("diff_uninspectable"):
        block_reasons.append("diff flagged as missing or uninspectable")

    target_files = review_context.get("target_files") or []
    inspected_files = set(review_context.get("inspected_files") or [])
    if not isinstance(target_files, Iterable) or isinstance(target_files, (str, bytes)):
        block_reasons.append("target_files must be a sequence of paths")
        target_list: List[str] = []
    else:
        target_list = [str(item) for item in target_files]

    if not target_list:
        block_reasons.append("target_files must be non-empty")
    else:
        uninspected = [path for path in target_list if path not in inspected_files]
        if uninspected:
            block_reasons.append(
                f"uninspected target files: {', '.join(sorted(uninspected))}"
            )

    if review_context.get("acceptance_criteria_verified") is not True:
        reject_reasons.append("acceptance criteria not verified")

    if review_context.get("security_checked") is not True:
        block_reasons.append("security checks not verified")

    if review_context.get("security_issues"):
        reject_reasons.append("security issues reported")

    if review_context.get("tests_passed") is not True:
        reject_reasons.append("required verification tests did not pass")

    committed_artifacts = list(review_context.get("committed_build_artifacts") or [])
    if review_context.get("build_artifacts_clean") is not True or committed_artifacts:
        reject_reasons.append("committed or unverified build artifacts detected")

    for concern in review_context.get("concerns") or []:
        if isinstance(concern, dict):
            severity = str(concern.get("severity", "")).lower()
            text = str(concern.get("message", concern.get("description", ""))).lower()
            if concern.get("missing_evidence") or any(
                phrase in text
                for phrase in (
                    "diff was not",
                    "diffs were not",
                    "not included",
                    "without diff",
                    "never seen",
                    "could not be verified",
                    "could not be inspected",
                )
            ):
                block_reasons.append("concern indicates missing diff or unverified evidence")
            elif severity in {"high", "critical", "blocker"}:
                reject_reasons.append(f"unresolved {severity} concern")

    if block_reasons:
        return {
            "verdict": "block",
            "evidence_complete": False,
            "reasons": block_reasons + reject_reasons,
        }

    if reject_reasons:
        return {
            "verdict": "reject",
            "evidence_complete": True,
            "reasons": reject_reasons,
        }

    return {
        "verdict": "approve",
        "evidence_complete": True,
        "reasons": [],
    }


def _complete_review_context() -> Dict[str, Any]:
    return {
        "pr_number": 999,
        "diff": "diff --git a/tests/test_qa_verification.py b/tests/test_qa_verification.py\n+assert True\n",
        "target_files": ["tests/test_qa_verification.py", "tests/test_smoke.py"],
        "inspected_files": ["tests/test_qa_verification.py", "tests/test_smoke.py"],
        "acceptance_criteria_verified": True,
        "security_checked": True,
        "security_issues": [],
        "tests_passed": True,
        "build_artifacts_clean": True,
        "committed_build_artifacts": [],
        "concerns": [],
    }


def test_knowledge_first_gate_approves_complete_evidence():
    result = evaluate_review_gate(_complete_review_context())
    assert result["verdict"] == "approve"
    assert result["evidence_complete"] is True
    assert result["reasons"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        {"diff": None},
        {"diff": ""},
        {"diff": "   \n\t  "},
        {"diff_missing": True},
        {"diff_uninspectable": True},
        {"inspected_files": ["tests/test_qa_verification.py"]},
        {"target_files": []},
        {"security_checked": False},
    ],
)
def test_knowledge_first_gate_blocks_missing_diff_or_uninspected_evidence(mutation):
    ctx = _complete_review_context()
    ctx.update(mutation)
    result = evaluate_review_gate(ctx)
    assert result["verdict"] in {"block", "reject"}
    assert result["verdict"] != "approve"
    assert result["evidence_complete"] is False
    assert len(result["reasons"]) >= 1


@pytest.mark.parametrize(
    "mutation",
    [
        {"acceptance_criteria_verified": False},
        {"tests_passed": False},
        {"build_artifacts_clean": False},
        {"committed_build_artifacts": ["playwright-report/index.html"]},
        {"security_issues": ["unsanitized SQL input"]},
        {"concerns": [{"severity": "high", "message": "Regression in schema validation"}]},
    ],
)
def test_knowledge_first_gate_rejects_failed_checks(mutation):
    ctx = _complete_review_context()
    ctx.update(mutation)
    result = evaluate_review_gate(ctx)
    assert result["verdict"] == "reject"
    assert result["verdict"] != "approve"
    assert len(result["reasons"]) >= 1


@pytest.mark.parametrize(
    "pr_label,target_files,concern_msg",
    [
        (
            "PR-419",
            ["crie_persistent_memory.py", "crie_normative_knowledge.py"],
            "The diff and target files were not included; kcp_parameters schema and idempotency could not be verified.",
        ),
        (
            "PR-415",
            ["crie_assistant_api.py"],
            "Approved leniently without diff inspection, so verify the diff against acceptance criteria before merge.",
        ),
        (
            "PR-416-417",
            ["crie_document_engine.py"],
            "Diffs were not included and could not be inspected for acceptance criteria, security issues, or committed build artifacts.",
        ),
        (
            "PR-407-408",
            ["scripts/ingest_materials.py"],
            "Neither diff was provided and SQLite tables, deduplication constraints, and tests could not be verified.",
        ),
        (
            "PR-413-418-420-421",
            ["crie_template_manager.py"],
            "Target diffs were never seen in review context.",
        ),
    ],
)
def test_knowledge_first_gate_prevents_historical_false_green_verdicts(
    pr_label, target_files, concern_msg
):
    ctx = {
        "pr_label": pr_label,
        "diff": "",
        "target_files": target_files,
        "inspected_files": [],
        "acceptance_criteria_verified": False,
        "security_checked": False,
        "tests_passed": True,
        "build_artifacts_clean": True,
        "concerns": [{"severity": "high", "message": concern_msg}],
    }
    result = evaluate_review_gate(ctx)
    assert result["verdict"] in {"block", "reject"}
    assert result["verdict"] != "approve"


def test_repository_required_deliverables_present():
    for rel_path in REQUIRED_DATA_FILES:
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Missing required deliverable: {rel_path}"
        assert path.stat().st_size > 0, f"Deliverable is empty: {rel_path}"

    for rel_path in CORE_PYTHON_MODULES:
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Missing core Python module: {rel_path}"
        assert path.stat().st_size > 0, f"Core Python module is empty: {rel_path}"


def test_no_unintended_build_artifacts_in_repository():
    for forbidden_dir in FORBIDDEN_WORKSPACE_ARTIFACT_DIRS:
        candidate = REPO_ROOT / forbidden_dir
        assert not candidate.exists(), (
            f"Unintended build/test artifact directory present: {candidate}"
        )

    git_bin = shutil.which("git")
    if (REPO_ROOT / ".git").exists() and git_bin is not None:
        proc = subprocess.run(
            [git_bin, "-C", str(REPO_ROOT), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        assert len(tracked_files) > 0, "git ls-files returned no tracked files"

        violations: List[str] = []
        for tracked in tracked_files:
            parts = set(Path(tracked).parts)
            if parts & FORBIDDEN_TRACKED_DIR_PARTS:
                violations.append(tracked)
                continue
            if tracked.endswith(FORBIDDEN_TRACKED_SUFFIXES):
                violations.append(tracked)
                continue
            if Path(tracked).name in FORBIDDEN_TRACKED_FILENAMES:
                violations.append(tracked)

        assert violations == [], f"Forbidden tracked build artifacts found: {violations}"


def test_normative_catalog_invariants():
    catalog_path = REPO_ROOT / "data" / "normative" / "corpus_catalog.json"
    assert catalog_path.is_file()
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = json.load(handle)

    assert isinstance(catalog, dict)
    categories = catalog.get("categories")
    assert isinstance(categories, list) and len(categories) > 0

    observed_files = 0
    for category in categories:
        assert isinstance(category, dict)
        assert category.get("category")
        files = category.get("files")
        assert isinstance(files, list) and len(files) >= 3
        observed_files += len(files)
        for entry in files:
            assert entry.get("file_name")
            assert entry.get("relative_path")
            assert entry.get("size_bytes", 0) > 0

    assert catalog.get("total_normative_files", 0) > 0
    assert observed_files >= len(categories) * 3


def _extract_templates(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    templates = registry.get("templates")
    if isinstance(templates, list):
        return [item for item in templates if isinstance(item, dict)]
    if isinstance(templates, dict):
        extracted: List[Dict[str, Any]] = []
        for key, value in templates.items():
            if isinstance(value, dict):
                merged = dict(value)
                merged.setdefault("id", key)
                extracted.append(merged)
        return extracted
    return []


def test_template_registries_and_document_invariants():
    for rel_path in (
        "data/templates/template_registry.json",
        "data/templates/template_registry_extended.json",
    ):
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Missing template registry: {rel_path}"
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        assert isinstance(data, dict)
        templates = _extract_templates(data)
        assert len(templates) > 0, f"No templates defined in {rel_path}"

    primary_path = REPO_ROOT / "data/templates/template_registry.json"
    raw_primary = primary_path.read_text(encoding="utf-8")
    assert "TPL-01" in raw_primary
    assert "Times New Roman 14pt" in raw_primary

    primary_data = json.loads(raw_primary)
    primary_templates = _extract_templates(primary_data)
    tpl_01 = next(
        (
            tpl
            for tpl in primary_templates
            if "TPL-01" in (str(tpl.get("id", "")), str(tpl.get("template_id", "")))
        ),
        None,
    )
    assert tpl_01 is not None, "TPL-01 template entry missing from template_registry.json"
    required_tokens = tpl_01.get("required_tokens")
    assert isinstance(required_tokens, list) and len(required_tokens) >= 7


def test_core_python_modules_ast_and_document_entrypoint():
    parsed_modules: Dict[str, ast.Module] = {}
    for rel_path in CORE_PYTHON_MODULES:
        module_path = REPO_ROOT / rel_path
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
        assert len(tree.body) > 0, f"Module has empty AST body: {rel_path}"
        parsed_modules[rel_path] = tree

    doc_tree = parsed_modules["crie_document_engine.py"]
    defined_functions = {
        node.name for node in ast.walk(doc_tree) if isinstance(node, ast.FunctionDef)
    }
    assert "compile_session_to_docx" in defined_functions


def _seed_catalog_sqlite(conn: sqlite3.Connection, catalog: Dict[str, Any]) -> int:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS normative_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            file_name TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL
        )
        """
    )
    rows_to_insert = []
    for cat in catalog.get("categories", []):
        cat_name = cat["category"]
        for entry in cat.get("files", []):
            rows_to_insert.append(
                (
                    cat_name,
                    entry["file_name"],
                    entry["relative_path"],
                    int(entry["size_bytes"]),
                )
            )

    conn.executemany(
        """
        INSERT INTO normative_documents (category, file_name, relative_path, size_bytes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(relative_path) DO UPDATE SET
            category = excluded.category,
            file_name = excluded.file_name,
            size_bytes = excluded.size_bytes
        """,
        rows_to_insert,
    )
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM normative_documents").fetchone()[0]


def test_sqlite_catalog_seed_idempotency(tmp_path):
    catalog_path = REPO_ROOT / "data" / "normative" / "corpus_catalog.json"
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = json.load(handle)

    db_path = tmp_path / "qa_seed_check.sqlite3"
    with sqlite3.connect(db_path) as conn:
        first_count = _seed_catalog_sqlite(conn, catalog)
        second_count = _seed_catalog_sqlite(conn, catalog)
        third_count = _seed_catalog_sqlite(conn, catalog)

        assert first_count > 0
        assert second_count == first_count
        assert third_count == first_count

        duplicate_paths = conn.execute(
            """
            SELECT relative_path, COUNT(*)
            FROM normative_documents
            GROUP BY relative_path
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        assert duplicate_paths == []

        sample = conn.execute(
            "SELECT category, file_name, relative_path, size_bytes FROM normative_documents LIMIT 1"
        ).fetchone()
        assert sample is not None
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO normative_documents (category, file_name, relative_path, size_bytes) VALUES (?, ?, ?, ?)",
                sample,
            )
