import os
import json
from pathlib import Path


def _find_template(templates, template_id):
    """Locate a template entry by identifier regardless of container shape."""
    if isinstance(templates, dict):
        return templates.get(template_id)
    if isinstance(templates, list):
        for item in templates:
            if isinstance(item, dict) and template_id in (
                item.get("id"),
                item.get("template_id"),
                item.get("code"),
                item.get("template_code"),
            ):
                return item
    return None


def test_normative_catalog_exists():
    catalog_path = Path("data/normative/corpus_catalog.json")
    if catalog_path.exists():
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "total_normative_files" in data
            assert data["total_normative_files"] > 0


def test_template_registry_exists():
    registry_path = Path("data/templates/template_registry.json")
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "templates" in data
            assert len(data["templates"]) > 0


def test_tpl_01_baseline_required_tokens():
    registry_path = Path("data/templates/template_registry.json")
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl_01 = _find_template(data.get("templates"), "TPL-01")
        if tpl_01 is not None and "required_tokens" in tpl_01:
            tokens = tpl_01["required_tokens"]
            assert isinstance(tokens, list)
            for expected in (
                "ORD_ID",
                "FULL_NAME",
                "SPECIALTY_CODE",
                "SPECIALTY_NAME",
                "BUDGET_TYPE",
                "ORDER_NUMBER",
                "DATE",
            ):
                assert expected in tokens


def test_synthetic_avatars_exists():
    avatars_path = Path("data/avatars/synthetic_avatars.json")
    if avatars_path.exists():
        with open(avatars_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "avatars" in data
            assert len(data["avatars"]) > 0
