import ast
import os
import json
from pathlib import Path


def _collect_gost_fonts(node):
    """Recursively collect all 'gost_font' values from parsed JSON data."""
    found = []
    if isinstance(node, dict):
        if "gost_font" in node:
            found.append(node["gost_font"])
        for value in node.values():
            found.extend(_collect_gost_fonts(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_gost_fonts(item))
    return found


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


def test_template_registry_gost_font_spec():
    registry_path = Path("data/templates/template_registry.json")
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        gost_fonts = _collect_gost_fonts(data)
        assert gost_fonts, "Expected at least one 'gost_font' declaration in template_registry.json"
        assert all(font == "Times New Roman 14pt" for font in gost_fonts)


def test_document_engine_defines_compile_session_to_docx():
    engine_path = Path("crie_document_engine.py")
    if engine_path.exists():
        source = engine_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        func_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert "compile_session_to_docx" in func_names


def test_synthetic_avatars_exists():
    avatars_path = Path("data/avatars/synthetic_avatars.json")
    if avatars_path.exists():
        with open(avatars_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "avatars" in data
            assert len(data["avatars"]) > 0
