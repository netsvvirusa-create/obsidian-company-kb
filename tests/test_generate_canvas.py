"""Tests for canvas generation functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from scripts.generate_canvas import (
        generate_contract_participants,
        generate_person_relationships,
        generate_project_roadmap,
        generate_counterparty_map,
        layout_radial,
        layout_tree,
        layout_timeline,
    )
except ImportError:
    pytest.skip("Module not yet available", allow_module_level=True)

# Aliases for backward-compatible test names
generate_contract_canvas = generate_contract_participants
generate_connections_canvas = generate_person_relationships
generate_roadmap_canvas = generate_project_roadmap
generate_counterparty_canvas = generate_counterparty_map


@pytest.mark.unit
class TestGenerateContractCanvas:
    """Tests for contract participant canvas generation."""

    def test_returns_valid_json(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        """Generated canvas should be valid JSON with nodes and edges."""
        result = generate_contract_canvas(tmp_vault, "Договор №001")
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert "nodes" in data
        assert "edges" in data

    def test_has_contract_node(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        """The canvas should have at least one node referencing the contract."""
        result = generate_contract_canvas(tmp_vault, "Договор №001")
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert len(data["nodes"]) >= 1


@pytest.mark.unit
class TestGenerateConnectionsCanvas:
    """Tests for connections map canvas generation."""

    def test_returns_valid_json(
        self, tmp_vault: Path, sample_employee_note: Path
    ) -> None:
        """Generated canvas should be valid JSON."""
        result = generate_connections_canvas(tmp_vault, "Иванов Иван Иванович")
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert "nodes" in data
        assert "edges" in data

    def test_center_node_present(
        self, tmp_vault: Path, sample_employee_note: Path
    ) -> None:
        """There should be a central node for the person."""
        result = generate_connections_canvas(tmp_vault, "Иванов Иван Иванович")
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert len(data["nodes"]) >= 1


@pytest.mark.unit
class TestGenerateRoadmapCanvas:
    """Tests for project roadmap canvas generation."""

    def test_returns_valid_json(self, tmp_vault: Path) -> None:
        """Roadmap canvas should be valid JSON."""
        project = tmp_vault / "03-ПРОЕКТЫ" / "Проект Альфа.md"
        project.write_text(
            "---\n"
            'title: "Проект Альфа"\n'
            "type: проект\n"
            "статус: активный\n"
            "tags:\n"
            "  - тип/проект\n"
            "---\n\n"
            "# Проект Альфа\n\n"
            "## Фазы\n\n"
            "1. Анализ\n"
            "2. Разработка\n"
            "3. Тестирование\n",
            encoding="utf-8",
        )
        result = generate_roadmap_canvas(tmp_vault, "Проект Альфа")
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert "nodes" in data
        assert len(data["nodes"]) >= 1


@pytest.mark.unit
class TestGenerateCounterpartyCanvas:
    """Tests for counterparty map canvas generation."""

    def test_returns_valid_json(
        self, tmp_vault: Path, sample_counterparty_note: Path
    ) -> None:
        """Counterparty canvas should be valid JSON."""
        result = generate_counterparty_canvas(tmp_vault)
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, Path):
            data = json.loads(result.read_text(encoding="utf-8"))
        else:
            data = result
        assert "nodes" in data
        assert "edges" in data


@pytest.mark.unit
class TestLayoutHelpers:
    """Tests for layout helper functions (radial, tree, timeline)."""

    def test_radial_returns_correct_count(self) -> None:
        """layout_radial should return coordinates for N items."""
        coords = layout_radial(0, 0, 200, 6)
        assert len(coords) == 6
        for x, y in coords:
            assert isinstance(x, (int, float))
            assert isinstance(y, (int, float))

    def test_radial_single_item(self) -> None:
        """layout_radial with 1 item should return 1 coordinate."""
        coords = layout_radial(0, 0, 100, 1)
        assert len(coords) == 1

    def test_tree_returns_correct_count(self) -> None:
        """layout_tree should return coordinates for all nodes."""
        coords = layout_tree(0, 0, 4, 100)
        assert len(coords) == 4
        for x, y in coords:
            assert isinstance(x, (int, float))
            assert isinstance(y, (int, float))

    def test_timeline_returns_correct_count(self) -> None:
        """layout_timeline should return coordinates for N phases."""
        coords = layout_timeline(0, 0, 5, 200)
        assert len(coords) == 5
        # Timeline should be horizontally ordered
        xs = [c[0] for c in coords]
        assert xs == sorted(xs)

    def test_timeline_zero_items(self) -> None:
        """layout_timeline with 0 items should return empty list."""
        coords = layout_timeline(0, 0, 0, 200)
        assert len(coords) == 0


# ---------------------------------------------------------------------------
# NEW TESTS — appended to increase coverage
# ---------------------------------------------------------------------------

try:
    from scripts.generate_canvas import (
        _gen_id,
        _make_node,
        _make_edge,
        build_canvas,
        parse_frontmatter_text,
        _extract_wikilinks,
        resolve_wikilink,
        save_canvas,
        generate_contract_participants,
        generate_person_relationships,
        generate_counterparty_map,
        generate_project_roadmap,
    )
except ImportError:
    pass  # already skipped at module level


@pytest.mark.unit
class TestGenId:
    """Tests for _gen_id helper."""

    def test_returns_16_char_hex(self) -> None:
        """_gen_id should return a 16-character hexadecimal string."""
        result = _gen_id()
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_unique_ids(self) -> None:
        """Two consecutive calls should produce different IDs."""
        id1 = _gen_id()
        id2 = _gen_id()
        assert id1 != id2

    def test_return_type_is_str(self) -> None:
        """_gen_id should return a str."""
        assert isinstance(_gen_id(), str)


@pytest.mark.unit
class TestMakeNode:
    """Tests for _make_node helper."""

    def test_required_fields_present(self) -> None:
        """_make_node should return a dict with all required canvas fields."""
        node = _make_node("abc123", "text", 10, 20, 100, 50)
        assert node["id"] == "abc123"
        assert node["type"] == "text"
        assert node["x"] == 10
        assert node["y"] == 20
        assert node["width"] == 100
        assert node["height"] == 50

    def test_extra_kwargs_included(self) -> None:
        """Extra keyword arguments should be merged into the dict."""
        node = _make_node("n1", "file", 0, 0, 200, 60, file="path/to/file.md", color="4")
        assert node["file"] == "path/to/file.md"
        assert node["color"] == "4"

    def test_text_node(self) -> None:
        """A text-type node should accept a text kwarg."""
        node = _make_node("n2", "text", 0, 0, 100, 50, text="Hello")
        assert node["text"] == "Hello"
        assert node["type"] == "text"


@pytest.mark.unit
class TestMakeEdge:
    """Tests for _make_edge helper."""

    def test_required_fields_present(self) -> None:
        """_make_edge should return a dict with id, fromNode, toNode."""
        edge = _make_edge("e1", "nodeA", "nodeB")
        assert edge["id"] == "e1"
        assert edge["fromNode"] == "nodeA"
        assert edge["toNode"] == "nodeB"

    def test_extra_kwargs_included(self) -> None:
        """Extra keyword arguments like label should be included."""
        edge = _make_edge("e2", "n1", "n2", label="relates to", fromSide="right")
        assert edge["label"] == "relates to"
        assert edge["fromSide"] == "right"


@pytest.mark.unit
class TestLayoutRadialDetailed:
    """Detailed tests for layout_radial with actual API signature."""

    def test_returns_correct_count(self) -> None:
        """layout_radial should return exactly count positions."""
        positions = layout_radial(0, 0, 200, 5)
        assert len(positions) == 5

    def test_zero_count_returns_empty(self) -> None:
        """layout_radial with count=0 should return empty list."""
        assert layout_radial(0, 0, 100, 0) == []

    def test_single_item_at_top(self) -> None:
        """With count=1, the point should be at the top of the circle (angle -pi/2)."""
        positions = layout_radial(0, 0, 100, 1)
        assert len(positions) == 1
        x, y = positions[0]
        # At angle -pi/2, x ~ 0, y ~ -100
        assert abs(x) < 2
        assert y < 0

    def test_coordinates_are_ints(self) -> None:
        """All coordinates should be integers."""
        for x, y in layout_radial(100, 200, 300, 8):
            assert isinstance(x, int)
            assert isinstance(y, int)


@pytest.mark.unit
class TestLayoutTreeDetailed:
    """Detailed tests for layout_tree with actual API signature."""

    def test_returns_correct_count(self) -> None:
        positions = layout_tree(0, 100, 4, spacing=200)
        assert len(positions) == 4

    def test_zero_children(self) -> None:
        assert layout_tree(0, 100, 0) == []

    def test_single_child_centered(self) -> None:
        """A single child should be centered on root x."""
        positions = layout_tree(500, 200, 1, spacing=200)
        assert len(positions) == 1
        assert positions[0] == (500, 200)

    def test_children_horizontally_symmetric(self) -> None:
        """Children should be symmetrically distributed around x."""
        positions = layout_tree(0, 100, 3, spacing=100)
        xs = [p[0] for p in positions]
        assert xs[0] == -xs[-1]

    def test_all_same_y(self) -> None:
        """All children share the same y coordinate."""
        positions = layout_tree(0, 300, 5, spacing=150)
        ys = [p[1] for p in positions]
        assert all(y == 300 for y in ys)


@pytest.mark.unit
class TestLayoutTimelineDetailed:
    """Detailed tests for layout_timeline with actual API signature."""

    def test_returns_correct_count(self) -> None:
        positions = layout_timeline(0, 50, 3, spacing=350)
        assert len(positions) == 3

    def test_zero_items(self) -> None:
        assert layout_timeline(0, 0, 0) == []

    def test_positions_are_monotonic(self) -> None:
        """X coordinates should increase monotonically."""
        positions = layout_timeline(100, 0, 5, spacing=200)
        xs = [p[0] for p in positions]
        for i in range(1, len(xs)):
            assert xs[i] > xs[i - 1]

    def test_all_same_y(self) -> None:
        """All items share the same Y coordinate."""
        positions = layout_timeline(0, 77, 4, spacing=100)
        assert all(p[1] == 77 for p in positions)

    def test_first_position_at_x_start(self) -> None:
        """First position should be at x_start."""
        positions = layout_timeline(42, 0, 3)
        assert positions[0][0] == 42


@pytest.mark.unit
class TestBuildCanvas:
    """Tests for build_canvas."""

    def test_returns_nodes_and_edges(self) -> None:
        """build_canvas should return dict with nodes and edges keys."""
        nodes = [_make_node("n1", "text", 0, 0, 100, 50, text="A")]
        edges = [_make_edge("e1", "n1", "n2")]
        canvas = build_canvas(nodes, edges)
        assert "nodes" in canvas
        assert "edges" in canvas
        assert canvas["nodes"] == nodes
        assert canvas["edges"] == edges

    def test_empty_canvas(self) -> None:
        """build_canvas with empty lists should return empty nodes and edges."""
        canvas = build_canvas([], [])
        assert canvas == {"nodes": [], "edges": []}


@pytest.mark.unit
class TestParseFrontmatterText:
    """Tests for parse_frontmatter_text."""

    def test_parses_simple_frontmatter(self) -> None:
        text = '---\ntitle: "Test"\ntype: note\n---\n\n# Test\n'
        fm = parse_frontmatter_text(text)
        assert fm["title"] == "Test"
        assert fm["type"] == "note"

    def test_no_frontmatter(self) -> None:
        fm = parse_frontmatter_text("# Just a heading\n\nSome text.")
        assert fm == {}

    def test_list_value(self) -> None:
        text = '---\ntags: [a, b, c]\n---\n\n'
        fm = parse_frontmatter_text(text)
        assert fm["tags"] == ["a", "b", "c"]


@pytest.mark.unit
class TestExtractWikilinks:
    """Tests for _extract_wikilinks."""

    def test_extracts_links(self) -> None:
        text = "See [[Foo]] and [[Bar|Display Name]]."
        links = _extract_wikilinks(text)
        assert "Foo" in links
        assert "Bar" in links

    def test_no_links(self) -> None:
        assert _extract_wikilinks("No links here.") == []


@pytest.mark.unit
class TestResolveWikilink:
    """Tests for resolve_wikilink."""

    def test_resolves_existing_file(self, tmp_vault: Path) -> None:
        note = tmp_vault / "04-СОТРУДНИКИ" / "Test Person.md"
        note.write_text("---\ntitle: Test\n---\n", encoding="utf-8")
        result = resolve_wikilink(tmp_vault, "Test Person")
        assert result is not None
        assert result.name == "Test Person.md"

    def test_returns_none_for_missing(self, tmp_vault: Path) -> None:
        result = resolve_wikilink(tmp_vault, "Nonexistent Note")
        assert result is None


@pytest.mark.unit
class TestSaveCanvas:
    """Tests for save_canvas."""

    def test_creates_file(self, tmp_path: Path) -> None:
        canvas = build_canvas([], [])
        out = tmp_path / "sub" / "test.canvas"
        save_canvas(canvas, out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data == {"nodes": [], "edges": []}


@pytest.mark.unit
class TestGenerateContractParticipants:
    """Tests for generate_contract_participants with real API."""

    def test_creates_canvas_file(
        self, tmp_vault: Path, sample_contract_note: Path, sample_employee_note: Path
    ) -> None:
        """Should create a .canvas file in the vault."""
        result = generate_contract_participants(tmp_vault, "Договор №001")
        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".canvas"

    def test_canvas_has_contract_node(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        """Canvas should contain at least one node for the contract."""
        result = generate_contract_participants(tmp_vault, "Договор №001")
        data = json.loads(result.read_text(encoding="utf-8"))
        assert len(data["nodes"]) >= 1

    def test_canvas_structure(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        result = generate_contract_participants(tmp_vault, "Договор №001")
        data = json.loads(result.read_text(encoding="utf-8"))
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)


@pytest.mark.unit
class TestGeneratePersonRelationships:
    """Tests for generate_person_relationships with real API."""

    def test_creates_canvas_file(
        self, tmp_vault: Path, sample_employee_note: Path, sample_employee_note_2: Path
    ) -> None:
        result = generate_person_relationships(tmp_vault, "Иванов Иван Иванович")
        assert isinstance(result, Path)
        assert result.exists()

    def test_center_node_is_person(
        self, tmp_vault: Path, sample_employee_note: Path, sample_employee_note_2: Path
    ) -> None:
        result = generate_person_relationships(tmp_vault, "Иванов Иван Иванович")
        data = json.loads(result.read_text(encoding="utf-8"))
        # At least the center node
        assert len(data["nodes"]) >= 1
        # Should have edges to relationships
        file_nodes = [n for n in data["nodes"] if n["type"] == "file"]
        assert len(file_nodes) >= 1


@pytest.mark.unit
class TestGenerateCounterpartyMap:
    """Tests for generate_counterparty_map with real API."""

    def test_creates_canvas_file(
        self, tmp_vault: Path, sample_counterparty_note: Path
    ) -> None:
        result = generate_counterparty_map(tmp_vault)
        assert isinstance(result, Path)
        assert result.exists()

    def test_canvas_has_counterparty_nodes(
        self, tmp_vault: Path, sample_counterparty_note: Path
    ) -> None:
        result = generate_counterparty_map(tmp_vault)
        data = json.loads(result.read_text(encoding="utf-8"))
        assert len(data["nodes"]) >= 1

    def test_empty_vault_still_works(self, tmp_vault: Path) -> None:
        """Even with no counterparties, the canvas should be generated."""
        result = generate_counterparty_map(tmp_vault)
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert "nodes" in data


@pytest.mark.unit
class TestGenerateProjectRoadmap:
    """Tests for generate_project_roadmap with real API."""

    def test_creates_canvas_file(self, tmp_vault: Path) -> None:
        project = tmp_vault / "03-ПРОЕКТЫ" / "Проект Бета.md"
        project.write_text(
            "---\n"
            'title: "Проект Бета"\n'
            "type: проект\n"
            "статус: активный\n"
            "---\n\n"
            "# Проект Бета\n\n"
            "## Этапы / Милестоуны\n\n"
            "| Этап | Дедлайн | Статус |\n"
            "|------|---------|--------|\n"
            "| Анализ | 2026-05-01 | завершён |\n"
            "| Разработка | 2026-06-01 | в работе |\n"
            "| Тестирование | 2026-07-01 | не начат |\n",
            encoding="utf-8",
        )
        result = generate_project_roadmap(tmp_vault, "Проект Бета")
        assert isinstance(result, Path)
        assert result.exists()

    def test_roadmap_has_milestone_nodes(self, tmp_vault: Path) -> None:
        project = tmp_vault / "03-ПРОЕКТЫ" / "Проект Гамма.md"
        project.write_text(
            "---\n"
            'title: "Проект Гамма"\n'
            "type: проект\n"
            "---\n\n"
            "# Проект Гамма\n\n"
            "## Этапы\n\n"
            "| Этап | Срок |\n"
            "|------|------|\n"
            "| Фаза 1 | 2026-05 |\n"
            "| Фаза 2 | 2026-06 |\n",
            encoding="utf-8",
        )
        result = generate_project_roadmap(tmp_vault, "Проект Гамма")
        data = json.loads(result.read_text(encoding="utf-8"))
        # Title node + 2 milestone nodes
        assert len(data["nodes"]) >= 3
