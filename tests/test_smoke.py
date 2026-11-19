import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_normative_catalog_exists():
    catalog_path = REPO_ROOT / "data" / "normative" / "corpus_catalog.json"
    assert catalog_path.is_file(), f"Missing normative catalog at {catalog_path}"
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        assert "total_normative_files" in data
        assert data["total_normative_files"] > 0


def test_template_registry_exists():
    registry_path = REPO_ROOT / "data" / "templates" / "template_registry.json"
    assert registry_path.is_file(), f"Missing template registry at {registry_path}"
    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        assert "templates" in data
        assert len(data["templates"]) > 0


def test_synthetic_avatars_exists():
    avatars_path = REPO_ROOT / "data" / "avatars" / "synthetic_avatars.json"
    assert avatars_path.is_file(), f"Missing synthetic avatars at {avatars_path}"
    with open(avatars_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, dict)
        assert "avatars" in data
        assert len(data["avatars"]) > 0
