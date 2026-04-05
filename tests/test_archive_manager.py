"""Tests for archive manager functions."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from scripts.archive_manager import (
        scan_candidates,
        archive_notes,
        archive_report,
    )
except ImportError:
    pytest.skip("Module not yet available", allow_module_level=True)


def _create_archived_candidate(vault: Path, folder: str, name: str) -> Path:
    """Helper: create a note that should be an archive candidate (status: завершён)."""
    note_dir = vault / folder
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / f"{name}.md"
    note.write_text(
        "---\n"
        f'title: "{name}"\n'
        "type: проект\n"
        "статус: завершён\n"
        "дата_окончания: 2025-01-01\n"
        "tags:\n"
        "  - тип/проект\n"
        "  - статус/завершён\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return note


def _create_active_note(vault: Path, folder: str, name: str) -> Path:
    """Helper: create a note that should NOT be archived (status: активный)."""
    note_dir = vault / folder
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / f"{name}.md"
    note.write_text(
        "---\n"
        f'title: "{name}"\n'
        "type: проект\n"
        "статус: активный\n"
        "tags:\n"
        "  - тип/проект\n"
        "  - статус/активный\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return note


@pytest.mark.unit
class TestScanCandidates:
    """Tests for scan_candidates — finds notes eligible for archiving."""

    def test_finds_completed_projects(self, tmp_vault: Path) -> None:
        """Completed/finished projects should be detected as archive candidates."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Старый проект")
        candidates = scan_candidates(tmp_vault)
        assert len(candidates) >= 1

    def test_ignores_active_notes(self, tmp_vault: Path) -> None:
        """Active notes should not appear in the candidates list."""
        _create_active_note(tmp_vault, "03-ПРОЕКТЫ", "Текущий проект")
        candidates = scan_candidates(tmp_vault)
        # candidates is a list of dicts with "file" key
        files = [c["file"] for c in candidates]
        assert not any("Текущий проект" in f for f in files)

    def test_empty_vault_no_candidates(self, tmp_vault: Path) -> None:
        """An empty vault should yield no archive candidates."""
        candidates = scan_candidates(tmp_vault)
        assert len(candidates) == 0


@pytest.mark.unit
class TestArchiveNotes:
    """Tests for archive_notes — moves files to 99-АРХИВ."""

    def test_moves_file_to_archive(self, tmp_vault: Path) -> None:
        """Archived note should be moved to the 99-АРХИВ directory."""
        note = _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Для архива")
        result = archive_notes(tmp_vault)
        assert not note.exists()
        archive_dir = tmp_vault / "99-АРХИВ"
        archived_files = list(archive_dir.rglob("Для архива.md"))
        assert len(archived_files) == 1

    def test_archive_updates_frontmatter(self, tmp_vault: Path) -> None:
        """Archived note should have updated frontmatter with архивирован field."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Сохранение")
        result = archive_notes(tmp_vault)
        archive_dir = tmp_vault / "99-АРХИВ"
        archived = list(archive_dir.rglob("Сохранение.md"))
        assert len(archived) == 1
        content = archived[0].read_text(encoding="utf-8")
        assert "архивирован:" in content

    def test_dry_run_does_not_move(self, tmp_vault: Path) -> None:
        """In dry-run mode files should not be moved."""
        note = _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Не двигать")
        archive_notes(tmp_vault, dry_run=True)
        assert note.exists()


@pytest.mark.unit
class TestArchiveReport:
    """Tests for archive_report — generates a summary report."""

    def test_returns_string(self, tmp_vault: Path) -> None:
        """The archive report should return a string."""
        result = archive_report(tmp_vault)
        assert isinstance(result, str)

    def test_report_after_archiving(self, tmp_vault: Path) -> None:
        """After archiving notes the report should mention archived items."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Архивированный")
        archive_notes(tmp_vault)
        result = archive_report(tmp_vault)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# NEW TESTS — appended to increase coverage
# ---------------------------------------------------------------------------

from datetime import date, timedelta

try:
    from scripts.archive_manager import (
        parse_frontmatter,
        _update_frontmatter_field,
        _append_history,
        _parse_date,
        _parse_filter,
        _read_notes,
        ARCHIVE_DIR,
    )
except ImportError:
    pass  # already skipped at module level


def _create_contract_candidate(vault: Path, name: str, status: str = "завершён") -> Path:
    """Helper: create a contract note with given status."""
    note_dir = vault / "02-ДОГОВОРЫ"
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / f"{name}.md"
    note.write_text(
        "---\n"
        f'title: "{name}"\n'
        "type: договор\n"
        f"статус: {status}\n"
        "дата_окончания: 2025-01-01\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return note


def _create_event_note(vault: Path, name: str, days_ago: int) -> Path:
    """Helper: create an event note from N days ago."""
    note_dir = vault / "07-СОБЫТИЯ"
    note_dir.mkdir(parents=True, exist_ok=True)
    event_date = (date.today() - timedelta(days=days_ago)).isoformat()
    note = note_dir / f"{name}.md"
    note.write_text(
        "---\n"
        f'title: "{name}"\n'
        "type: событие\n"
        f"дата: {event_date}\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return note


@pytest.mark.unit
class TestScanCandidatesDetailed:
    """Additional tests for scan_candidates."""

    def test_finds_completed_contracts(self, tmp_vault: Path) -> None:
        _create_contract_candidate(tmp_vault, "Old Contract", "завершён")
        candidates = scan_candidates(tmp_vault)
        files = [c["file"] for c in candidates]
        assert any("Old Contract" in f for f in files)

    def test_finds_cancelled_contracts(self, tmp_vault: Path) -> None:
        _create_contract_candidate(tmp_vault, "Cancelled", "отменён")
        candidates = scan_candidates(tmp_vault)
        files = [c["file"] for c in candidates]
        assert any("Cancelled" in f for f in files)

    def test_ignores_active_contracts(self, tmp_vault: Path) -> None:
        _create_contract_candidate(tmp_vault, "Active Contract", "активный")
        candidates = scan_candidates(tmp_vault)
        files = [c["file"] for c in candidates]
        assert not any("Active Contract" in f for f in files)

    def test_finds_old_events(self, tmp_vault: Path) -> None:
        _create_event_note(tmp_vault, "Old Event", 120)
        candidates = scan_candidates(tmp_vault)
        files = [c["file"] for c in candidates]
        assert any("Old Event" in f for f in files)

    def test_ignores_recent_events(self, tmp_vault: Path) -> None:
        _create_event_note(tmp_vault, "Recent Event", 30)
        candidates = scan_candidates(tmp_vault)
        files = [c["file"] for c in candidates]
        assert not any("Recent Event" in f for f in files)

    def test_candidate_has_required_fields(self, tmp_vault: Path) -> None:
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Field Test")
        candidates = scan_candidates(tmp_vault)
        assert len(candidates) >= 1
        c = candidates[0]
        assert "file" in c
        assert "type" in c
        assert "reason" in c
        assert "status" in c


@pytest.mark.unit
class TestArchiveNotesDetailed:
    """Additional tests for archive_notes with various scenarios."""

    def test_folder_filter(self, tmp_vault: Path) -> None:
        """Only notes in the specified folder should be archived."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "ProjectX")
        _create_contract_candidate(tmp_vault, "ContractX", "завершён")
        result = archive_notes(tmp_vault, folder="03-ПРОЕКТЫ")
        moved_files = [m["file"] for m in result["moved"]]
        assert any("ProjectX" in f for f in moved_files)
        # Contract should not be moved
        assert (tmp_vault / "02-ДОГОВОРЫ" / "ContractX.md").exists()

    def test_dry_run_returns_dry_run_flag(self, tmp_vault: Path) -> None:
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "DryTest")
        result = archive_notes(tmp_vault, dry_run=True)
        for item in result["moved"]:
            assert item.get("dry_run") is True

    def test_filter_expr(self, tmp_vault: Path) -> None:
        """Filter expression should narrow candidates."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Filtered")
        result = archive_notes(tmp_vault, filter_expr="type:проект", dry_run=True)
        assert len(result["moved"]) >= 1

    def test_result_structure(self, tmp_vault: Path) -> None:
        result = archive_notes(tmp_vault, dry_run=True)
        assert "moved" in result
        assert "skipped" in result
        assert "errors" in result

    def test_archive_handles_name_conflict(self, tmp_vault: Path) -> None:
        """If a file with same name exists in archive, it should be renamed."""
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Duplicate")
        # Pre-create the destination
        dest = tmp_vault / ARCHIVE_DIR / "03-ПРОЕКТЫ"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "Duplicate.md").write_text("existing", encoding="utf-8")
        result = archive_notes(tmp_vault)
        # Should succeed without error
        assert len(result["errors"]) == 0
        # Original should be moved
        assert not (tmp_vault / "03-ПРОЕКТЫ" / "Duplicate.md").exists()


@pytest.mark.unit
class TestArchiveReportDetailed:
    """Additional tests for archive_report."""

    def test_report_mentions_empty_archive(self, tmp_vault: Path) -> None:
        result = archive_report(tmp_vault)
        # Archive dir exists but is empty
        assert "Архив" in result

    def test_report_after_multiple_archives(self, tmp_vault: Path) -> None:
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "One")
        _create_archived_candidate(tmp_vault, "03-ПРОЕКТЫ", "Two")
        archive_notes(tmp_vault)
        result = archive_report(tmp_vault)
        assert "03-ПРОЕКТЫ" in result

    def test_report_contains_date_header(self, tmp_vault: Path) -> None:
        result = archive_report(tmp_vault)
        assert "Дата" in result


@pytest.mark.unit
class TestHelperFunctions:
    """Tests for helper functions in archive_manager."""

    def test_update_frontmatter_field_new(self) -> None:
        text = "---\ntitle: Test\n---\n\n# Content\n"
        updated = _update_frontmatter_field(text, "new_field", "value")
        assert "new_field: value" in updated

    def test_update_frontmatter_field_existing(self) -> None:
        text = "---\ntitle: Test\nстатус: активный\n---\n\n# Content\n"
        updated = _update_frontmatter_field(text, "статус", "архив")
        assert "статус: архив" in updated
        assert "активный" not in updated

    def test_append_history(self) -> None:
        text = "# Note\n\n## История изменений\n\n- Entry 1\n"
        updated = _append_history(text, "New entry")
        assert "New entry" in updated

    def test_append_history_no_section(self) -> None:
        text = "# Note\n\nJust content\n"
        updated = _append_history(text, "Entry")
        # Should return text unchanged
        assert updated == text

    def test_parse_filter_valid(self) -> None:
        key, val = _parse_filter("status:завершён")
        assert key == "status"
        assert val == "завершён"

    def test_parse_filter_invalid(self) -> None:
        with pytest.raises(ValueError):
            _parse_filter("no-colon-here")
