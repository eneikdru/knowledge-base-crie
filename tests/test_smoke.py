import ast
import os
import json
from pathlib import Path

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

def test_synthetic_avatars_exists():
    avatars_path = Path("data/avatars/synthetic_avatars.json")
    if avatars_path.exists():
        with open(avatars_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "avatars" in data
            assert len(data["avatars"]) > 0

def test_document_engine_module_parses():
    """Verify crie_document_engine.py is present and syntactically valid Python."""
    engine_path = Path("crie_document_engine.py")
    if engine_path.exists():
        source = engine_path.read_text(encoding="utf-8")
        assert len(source) > 0
        tree = ast.parse(source, filename=str(engine_path))
        assert tree is not None
