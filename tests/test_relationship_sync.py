"""Tests for scripts/relationship_sync.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.relationship_sync import (
    MIRROR_DESCRIPTIONS,
    sync_relationships,
    _mirror_description,
    _parse_связи_yaml,
)


@pytest.mark.unit
class TestRelationshipSync:
    """Unit-tests for relationship synchronisation."""

    def test_detect_one_sided_relationships(
        self,
        tmp_vault: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
    ) -> None:
        """Иванов links to Петров, but Петров does not link back.
        This should be detected as a missing reverse link."""
        result = sync_relationships(tmp_vault, fix=False, dry_run=False)
        assert result["missing_reverse"] >= 1

        persons = {
            (issue["person_a"], issue["person_b"])
            for issue in result["issues"]
        }
        assert ("Иванов Иван", "Петров Пётр") in persons

    def test_fix_creates_reverse_entries(
        self,
        tmp_vault: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
    ) -> None:
        """With fix=True, the missing reverse link should be added."""
        result = sync_relationships(tmp_vault, fix=True, dry_run=False)
        assert result.get("fixed", 0) >= 1

        # Re-read Петров's file and check that Иванов is now in связи
        petrov = tmp_vault / "04-СОТРУДНИКИ" / "Петров Пётр.md"
        text = petrov.read_text(encoding="utf-8")
        assert "[[Иванов Иван]]" in text

    def test_dry_run_reports_but_does_not_change(
        self,
        tmp_vault: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
    ) -> None:
        """dry_run should report issues but leave files unchanged."""
        # Read original content
        petrov = tmp_vault / "04-СОТРУДНИКИ" / "Петров Пётр.md"
        original = petrov.read_text(encoding="utf-8")

        result = sync_relationships(tmp_vault, fix=True, dry_run=True)
        assert result["missing_reverse"] >= 1

        # File should remain unchanged
        after = petrov.read_text(encoding="utf-8")
        assert original == after

    def test_mirror_descriptions(self) -> None:
        """Mirror description mapping should swap 'руководит' <-> 'подчиняется'."""
        assert _mirror_description("руководит") == "подчиняется"
        assert _mirror_description("подчиняется") == "руководит"
        assert _mirror_description("является другом") == "является другом"
        # Unknown description should be returned as-is
        assert _mirror_description("unknown relation") == "unknown relation"
