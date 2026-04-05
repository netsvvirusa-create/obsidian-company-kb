"""Tests for .canvas files in assets/vault-init/canvases/."""

import json
from pathlib import Path

import pytest

CANVASES_DIR = Path(__file__).parent.parent / "assets" / "vault-init" / "canvases"


def _canvas_files() -> list[Path]:
    """Collect all .canvas files."""
    files = sorted(CANVASES_DIR.glob("*.canvas"))
    assert len(files) > 0, f"No .canvas files found in {CANVASES_DIR}"
    return files


def _canvas_ids() -> list[str]:
    return [f.stem for f in _canvas_files()]


@pytest.mark.unit
class TestCanvas:
    """Validate each .canvas file is well-formed JSON Canvas."""

    @pytest.mark.parametrize("canvas_file", _canvas_files(), ids=_canvas_ids())
    def test_valid_json(self, canvas_file: Path):
        text = canvas_file.read_text(encoding="utf-8")
        data = json.loads(text)
        assert isinstance(data, dict), f"{canvas_file.name}: must parse to a dict"

    @pytest.mark.parametrize("canvas_file", _canvas_files(), ids=_canvas_ids())
    def test_has_nodes_list(self, canvas_file: Path):
        data = json.loads(canvas_file.read_text(encoding="utf-8"))
        assert "nodes" in data, f"{canvas_file.name}: missing 'nodes' key"
        assert isinstance(data["nodes"], list), f"{canvas_file.name}: 'nodes' must be a list"

    @pytest.mark.parametrize("canvas_file", _canvas_files(), ids=_canvas_ids())
    def test_node_required_fields(self, canvas_file: Path):
        data = json.loads(canvas_file.read_text(encoding="utf-8"))
        required = {"id", "type", "x", "y", "width", "height"}
        for i, node in enumerate(data["nodes"]):
            missing = required - set(node.keys())
            assert not missing, (
                f"{canvas_file.name}: node[{i}] missing fields: {missing}"
            )

    @pytest.mark.parametrize("canvas_file", _canvas_files(), ids=_canvas_ids())
    def test_edge_required_fields(self, canvas_file: Path):
        data = json.loads(canvas_file.read_text(encoding="utf-8"))
        edges = data.get("edges", [])
        required = {"id", "fromNode", "toNode"}
        for i, edge in enumerate(edges):
            missing = required - set(edge.keys())
            assert not missing, (
                f"{canvas_file.name}: edge[{i}] missing fields: {missing}"
            )
