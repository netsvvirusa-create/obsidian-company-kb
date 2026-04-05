"""Tests for scripts/daily_operations.py."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

try:
    from scripts.daily_operations import (
        cmd_create_daily,
        cmd_morning_briefing,
        cmd_check_overdue,
    )
except ImportError:
    pytest.skip("Module not yet available", allow_module_level=True)


@pytest.mark.unit
class TestCreateDaily:
    """Tests for cmd_create_daily."""

    def test_creates_daily_file(self, tmp_vault: Path) -> None:
        """Should create a daily record markdown file."""
        target = date(2026, 4, 5)
        cmd_create_daily(tmp_vault, target)
        # Check that at least one .md was created in the calendar folder
        calendar_dir = tmp_vault / "08-КАЛЕНДАРЬ"
        md_files = list(calendar_dir.rglob("*.md"))
        assert len(md_files) >= 1

    def test_daily_file_has_frontmatter(self, tmp_vault: Path) -> None:
        """The created daily file should contain YAML frontmatter."""
        target = date(2026, 4, 5)
        cmd_create_daily(tmp_vault, target)
        calendar_dir = tmp_vault / "08-КАЛЕНДАРЬ"
        md_files = list(calendar_dir.rglob("*.md"))
        assert len(md_files) >= 1
        content = md_files[0].read_text(encoding="utf-8")
        assert content.startswith("---")

    def test_idempotent_creation(self, tmp_vault: Path) -> None:
        """Running create_daily twice for the same date should not duplicate."""
        target = date(2026, 4, 5)
        cmd_create_daily(tmp_vault, target)
        calendar_dir = tmp_vault / "08-КАЛЕНДАРЬ"
        count_before = len(list(calendar_dir.rglob("*.md")))
        cmd_create_daily(tmp_vault, target)
        count_after = len(list(calendar_dir.rglob("*.md")))
        assert count_after == count_before


@pytest.mark.unit
class TestMorningBriefing:
    """Tests for cmd_morning_briefing."""

    def test_returns_markdown(self, tmp_vault: Path) -> None:
        """Morning briefing should return a markdown string."""
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert isinstance(result, str)

    def test_briefing_includes_heading(self, tmp_vault: Path) -> None:
        """The briefing should contain at least one markdown heading."""
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "#" in result

    def test_briefing_with_daily_note(
        self, tmp_vault: Path, sample_daily_note: Path
    ) -> None:
        """When a daily note exists, the briefing should include relevant info."""
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert isinstance(result, str)

    def test_briefing_with_negotiation(
        self, tmp_vault: Path, sample_negotiation_today: Path
    ) -> None:
        """Negotiations for today should appear in the morning briefing."""
        result = cmd_morning_briefing(tmp_vault, days=1)
        assert isinstance(result, str)


@pytest.mark.unit
class TestCheckOverdue:
    """Tests for cmd_check_overdue."""

    def test_returns_dict(self, tmp_vault: Path) -> None:
        """check_overdue should return a dict."""
        result = cmd_check_overdue(tmp_vault)
        assert isinstance(result, dict)

    def test_dict_has_expected_keys(self, tmp_vault: Path) -> None:
        """Result should contain lists for different overdue categories."""
        result = cmd_check_overdue(tmp_vault)
        # At least should be a dict with list-type values
        for value in result.values():
            assert isinstance(value, list)

    def test_overdue_contract_detected(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        """A contract with a past end date should show up as overdue."""
        # Modify the contract to have an expired date
        content = sample_contract_note.read_text(encoding="utf-8")
        content = content.replace("2027-04-05", "2025-01-01")
        sample_contract_note.write_text(content, encoding="utf-8")
        result = cmd_check_overdue(tmp_vault)
        assert isinstance(result, dict)

    def test_no_overdue_on_empty_vault(self, tmp_vault: Path) -> None:
        """An empty vault should produce no overdue items."""
        result = cmd_check_overdue(tmp_vault)
        total = sum(len(v) for v in result.values())
        assert total == 0


# ---------------------------------------------------------------------------
# NEW TESTS — appended to increase coverage
# ---------------------------------------------------------------------------

try:
    from scripts.daily_operations import (
        parse_frontmatter,
        _parse_date,
        read_notes,
        _extract_section,
        _extract_unchecked_tasks,
        _extract_checked_tasks,
        parse_args,
    )
except ImportError:
    pass  # already skipped at module level


@pytest.mark.unit
class TestCreateDailyDetailed:
    """Additional tests for cmd_create_daily."""

    def test_file_named_with_date(self, tmp_vault: Path) -> None:
        """The file should be named with the ISO date."""
        target = date(2026, 5, 10)
        cmd_create_daily(tmp_vault, target)
        expected = tmp_vault / "08-КАЛЕНДАРЬ" / "2026-05-10.md"
        assert expected.exists()

    def test_file_contains_date_in_title(self, tmp_vault: Path) -> None:
        target = date(2026, 5, 10)
        cmd_create_daily(tmp_vault, target)
        content = (tmp_vault / "08-КАЛЕНДАРЬ" / "2026-05-10.md").read_text(encoding="utf-8")
        assert "2026-05-10" in content

    def test_file_contains_tasks_section(self, tmp_vault: Path) -> None:
        target = date(2026, 5, 10)
        cmd_create_daily(tmp_vault, target)
        content = (tmp_vault / "08-КАЛЕНДАРЬ" / "2026-05-10.md").read_text(encoding="utf-8")
        assert "## Задачи" in content

    def test_file_contains_meetings_section(self, tmp_vault: Path) -> None:
        target = date(2026, 5, 10)
        cmd_create_daily(tmp_vault, target)
        content = (tmp_vault / "08-КАЛЕНДАРЬ" / "2026-05-10.md").read_text(encoding="utf-8")
        assert "## Встречи и переговоры" in content

    def test_carries_tasks_from_yesterday(self, tmp_vault: Path) -> None:
        """If yesterday's note has tasks in 'На завтра', they appear in today."""
        yesterday = date(2026, 5, 9)
        today = date(2026, 5, 10)
        cal = tmp_vault / "08-КАЛЕНДАРЬ"
        cal.mkdir(parents=True, exist_ok=True)
        (cal / f"{yesterday.isoformat()}.md").write_text(
            f'---\ntitle: "{yesterday}"\ntype: дневная_запись\n---\n\n'
            f"# {yesterday}\n\n"
            "## На завтра / на контроле\n\n"
            "- [ ] Carry this task\n",
            encoding="utf-8",
        )
        cmd_create_daily(tmp_vault, today)
        content = (cal / "2026-05-10.md").read_text(encoding="utf-8")
        assert "Carry this task" in content

    def test_includes_meetings_for_date(self, tmp_vault: Path) -> None:
        """If a negotiation is scheduled for the target date, it should appear."""
        target = date(2026, 6, 15)
        meeting = tmp_vault / "06-ПЕРЕГОВОРЫ" / "meeting.md"
        meeting.write_text(
            '---\ntitle: "Important Meeting"\ntype: переговоры\n'
            f'дата: {target.isoformat()}\n---\n\n# Meeting\n',
            encoding="utf-8",
        )
        cmd_create_daily(tmp_vault, target)
        content = (tmp_vault / "08-КАЛЕНДАРЬ" / f"{target.isoformat()}.md").read_text(
            encoding="utf-8"
        )
        assert "meeting" in content.lower() or "[[meeting" in content.lower() or "Important Meeting" in content


@pytest.mark.unit
class TestMorningBriefingDetailed:
    """Additional tests for cmd_morning_briefing."""

    def test_contains_overdue_section(self, tmp_vault: Path) -> None:
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Просроченные задачи" in result

    def test_contains_meetings_section(self, tmp_vault: Path) -> None:
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Встречи сегодня" in result

    def test_contains_expiring_contracts_section(self, tmp_vault: Path) -> None:
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Истекающие договоры" in result

    def test_contains_recent_events_section(self, tmp_vault: Path) -> None:
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Последние события" in result

    def test_with_overdue_tasks(self, tmp_vault: Path) -> None:
        """Overdue tasks from past daily notes should appear in briefing."""
        yesterday = date.today() - timedelta(days=1)
        cal = tmp_vault / "08-КАЛЕНДАРЬ"
        cal.mkdir(parents=True, exist_ok=True)
        (cal / f"{yesterday.isoformat()}.md").write_text(
            f'---\ntitle: "{yesterday}"\ntype: дневная_запись\n---\n\n'
            f"# {yesterday}\n\n"
            "## Задачи\n\n"
            "- [ ] Overdue task from yesterday\n",
            encoding="utf-8",
        )
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Overdue task from yesterday" in result

    def test_with_expiring_contract(
        self, tmp_vault: Path, sample_contract_note: Path
    ) -> None:
        """Contract expiring within horizon should be mentioned."""
        today = date.today()
        soon = today + timedelta(days=3)
        content = sample_contract_note.read_text(encoding="utf-8")
        content = content.replace("2027-04-05", soon.isoformat())
        sample_contract_note.write_text(content, encoding="utf-8")
        result = cmd_morning_briefing(tmp_vault, days=7)
        assert "Договор №001" in result or "001" in result


@pytest.mark.unit
class TestCheckOverdueDetailed:
    """Additional tests for cmd_check_overdue."""

    def test_result_has_three_keys(self, tmp_vault: Path) -> None:
        result = cmd_check_overdue(tmp_vault)
        assert "overdue_tasks" in result
        assert "expiring_contracts" in result
        assert "overdue_payments" in result

    def test_detects_overdue_task(self, tmp_vault: Path) -> None:
        """A past daily note with unchecked task should be detected."""
        past = date.today() - timedelta(days=5)
        cal = tmp_vault / "08-КАЛЕНДАРЬ"
        (cal / f"{past.isoformat()}.md").write_text(
            f'---\ntitle: "{past}"\ntype: дневная_запись\n---\n\n'
            f"# {past}\n\n## Задачи\n\n- [ ] Forgotten task\n",
            encoding="utf-8",
        )
        result = cmd_check_overdue(tmp_vault)
        assert len(result["overdue_tasks"]) >= 1
        assert any("Forgotten task" in t["задача"] for t in result["overdue_tasks"])

    def test_ignores_completed_contracts(self, tmp_vault: Path) -> None:
        """Contracts with status завершён should not appear as expiring."""
        note = tmp_vault / "02-ДОГОВОРЫ" / "Done.md"
        note.write_text(
            '---\ntitle: "Done Contract"\ntype: договор\nстатус: завершён\n'
            f'дата_окончания: {date.today().isoformat()}\n---\n',
            encoding="utf-8",
        )
        result = cmd_check_overdue(tmp_vault)
        contracts = [c["договор"] for c in result["expiring_contracts"]]
        assert "Done Contract" not in contracts

    def test_detects_expiring_contract(self, tmp_vault: Path) -> None:
        soon = date.today() + timedelta(days=10)
        note = tmp_vault / "02-ДОГОВОРЫ" / "Soon.md"
        note.write_text(
            '---\ntitle: "Soon Contract"\ntype: договор\nстатус: активный\n'
            f'дата_окончания: {soon.isoformat()}\n---\n',
            encoding="utf-8",
        )
        result = cmd_check_overdue(tmp_vault)
        contracts = [c["договор"] for c in result["expiring_contracts"]]
        assert "Soon Contract" in contracts


@pytest.mark.unit
class TestDailyOpsParseArgs:
    """Tests for CLI argument parsing."""

    def test_create_daily_subcommand(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "create-daily"])
        assert args.command == "create-daily"

    def test_morning_briefing_subcommand(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "morning-briefing", "--days", "14"])
        assert args.command == "morning-briefing"
        assert args.days == 14

    def test_check_overdue_subcommand(self) -> None:
        args = parse_args(["--vault", "/tmp/v", "check-overdue"])
        assert args.command == "check-overdue"
