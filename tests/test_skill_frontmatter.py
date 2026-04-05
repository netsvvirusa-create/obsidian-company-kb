"""Tests for SKILL.md frontmatter validation."""

import re
from pathlib import Path

import pytest
import yaml

SKILL_PATH = Path(__file__).parent.parent / "SKILL.md"


def _parse_skill_frontmatter() -> dict:
    """Read SKILL.md and parse YAML frontmatter between --- delimiters."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    assert len(parts) >= 3, "SKILL.md must contain YAML frontmatter between --- delimiters"
    return yaml.safe_load(parts[1])


@pytest.mark.unit
class TestSkillFrontmatter:
    """Validate SKILL.md exists and its frontmatter conforms to the spec."""

    def test_skill_md_exists(self):
        assert SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"

    def test_name_length(self):
        fm = _parse_skill_frontmatter()
        name = fm.get("name", "")
        assert len(name) <= 64, f"name must be <= 64 chars, got {len(name)}"

    def test_name_lowercase_hyphens_only(self):
        fm = _parse_skill_frontmatter()
        name = fm.get("name", "")
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), (
            f"name must be lowercase letters, digits, and single hyphens: {name!r}"
        )

    def test_name_no_consecutive_hyphens(self):
        fm = _parse_skill_frontmatter()
        name = fm.get("name", "")
        assert "--" not in name, f"name must not contain consecutive hyphens: {name!r}"

    def test_name_no_leading_trailing_hyphen(self):
        fm = _parse_skill_frontmatter()
        name = fm.get("name", "")
        assert not name.startswith("-"), f"name must not start with a hyphen: {name!r}"
        assert not name.endswith("-"), f"name must not end with a hyphen: {name!r}"

    def test_description_non_empty(self):
        fm = _parse_skill_frontmatter()
        desc = fm.get("description", "")
        assert desc and len(desc.strip()) > 0, "description must be non-empty"

    def test_description_length(self):
        fm = _parse_skill_frontmatter()
        desc = fm.get("description", "")
        assert len(desc) <= 1024, f"description must be <= 1024 chars, got {len(desc)}"

    def test_name_matches_directory(self):
        fm = _parse_skill_frontmatter()
        name = fm.get("name", "")
        expected = SKILL_PATH.parent.name
        assert name == expected, (
            f"name {name!r} must match parent directory name {expected!r}"
        )
