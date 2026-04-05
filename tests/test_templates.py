"""Tests for note templates defined in references/TEMPLATES.md."""

import re
from pathlib import Path

import pytest
import yaml

TEMPLATES_PATH = Path(__file__).parent.parent / "references" / "TEMPLATES.md"

KNOWN_TYPES = {
    "контрагент",
    "договор",
    "проект",
    "переговоры",
    "событие",
    "дневная_запись",
    "цель",
    "идея",
    "наша_компания",
    "сотрудник",
    "контакт",
    "moc",
    "платёж",
    "счёт",
    "бюджет",
    "ретроспектива",
}


def _extract_template_blocks() -> list[tuple[str, str]]:
    """Extract (label, code) pairs from ```markdown code blocks in TEMPLATES.md."""
    text = TEMPLATES_PATH.read_text(encoding="utf-8")
    # Find all ```markdown ... ``` blocks
    pattern = re.compile(r"```markdown\s*\n(.*?)```", re.DOTALL)
    matches = pattern.findall(text)
    assert len(matches) > 0, "No ```markdown code blocks found in TEMPLATES.md"

    results = []
    for i, block in enumerate(matches):
        results.append((f"template_{i}", block))
    return results


def _parse_frontmatter(block: str) -> dict:
    """Parse YAML frontmatter from a template block."""
    parts = block.split("---", 2)
    assert len(parts) >= 3, "Template block must contain YAML frontmatter between --- delimiters"
    return yaml.safe_load(parts[1])


def _get_template_ids() -> list[str]:
    blocks = _extract_template_blocks()
    return [label for label, _ in blocks]


@pytest.mark.unit
class TestTemplates:
    """Validate each template in TEMPLATES.md."""

    @pytest.fixture(autouse=True)
    def _load_templates(self):
        self.templates = _extract_template_blocks()

    @pytest.mark.parametrize(
        "idx",
        range(len(_extract_template_blocks())),
        ids=_get_template_ids(),
    )
    def test_valid_yaml(self, idx):
        label, block = self.templates[idx]
        fm = _parse_frontmatter(block)
        assert isinstance(fm, dict), f"{label}: frontmatter must parse to a dict"

    @pytest.mark.parametrize(
        "idx",
        range(len(_extract_template_blocks())),
        ids=_get_template_ids(),
    )
    def test_has_required_fields(self, idx):
        label, block = self.templates[idx]
        fm = _parse_frontmatter(block)
        for field in ("title", "type", "tags"):
            assert field in fm, f"{label}: missing required field '{field}'"

    @pytest.mark.parametrize(
        "idx",
        range(len(_extract_template_blocks())),
        ids=_get_template_ids(),
    )
    def test_type_is_known(self, idx):
        label, block = self.templates[idx]
        fm = _parse_frontmatter(block)
        note_type = fm.get("type", "")
        assert note_type in KNOWN_TYPES, (
            f"{label}: unknown type '{note_type}', expected one of {KNOWN_TYPES}"
        )
