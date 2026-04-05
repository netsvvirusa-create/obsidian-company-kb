"""Tests for .base dashboard files in assets/vault-init/bases/."""

from pathlib import Path

import pytest
import yaml

BASES_DIR = Path(__file__).parent.parent / "assets" / "vault-init" / "bases"


def _base_files() -> list[Path]:
    """Collect all .base files."""
    files = sorted(BASES_DIR.glob("*.base"))
    assert len(files) > 0, f"No .base files found in {BASES_DIR}"
    return files


def _base_ids() -> list[str]:
    return [f.stem for f in _base_files()]


@pytest.mark.unit
class TestBases:
    """Validate each .base file is well-formed YAML with required structure."""

    @pytest.mark.parametrize("base_file", _base_files(), ids=_base_ids())
    def test_valid_yaml(self, base_file: Path):
        text = base_file.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        assert isinstance(data, dict), f"{base_file.name}: must parse to a dict"

    @pytest.mark.parametrize("base_file", _base_files(), ids=_base_ids())
    def test_has_filters(self, base_file: Path):
        data = yaml.safe_load(base_file.read_text(encoding="utf-8"))
        assert "filters" in data, f"{base_file.name}: missing 'filters' key"

    @pytest.mark.parametrize("base_file", _base_files(), ids=_base_ids())
    def test_has_views_with_at_least_one(self, base_file: Path):
        data = yaml.safe_load(base_file.read_text(encoding="utf-8"))
        assert "views" in data, f"{base_file.name}: missing 'views' key"
        views = data["views"]
        assert isinstance(views, list) and len(views) >= 1, (
            f"{base_file.name}: 'views' must be a list with at least one view"
        )

    @pytest.mark.parametrize("base_file", _base_files(), ids=_base_ids())
    def test_each_view_has_type(self, base_file: Path):
        data = yaml.safe_load(base_file.read_text(encoding="utf-8"))
        views = data.get("views", [])
        for i, view in enumerate(views):
            assert "type" in view, (
                f"{base_file.name}: view[{i}] missing 'type' field"
            )
