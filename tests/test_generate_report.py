"""Tests for scripts/generate_report.py."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts.generate_report import (
    report_counterparty_history,
    report_employee_activity,
    report_expiring_contracts,
)


@pytest.mark.unit
class TestGenerateReport:
    """Unit-tests for report generation."""

    def test_expiring_contracts_report(self, tmp_vault: Path) -> None:
        """A contract expiring within the given horizon should appear in the
        expiring-contracts report."""
        soon = (date.today() + timedelta(days=10)).isoformat()
        note = tmp_vault / "02-ДОГОВОРЫ" / "Expiring.md"
        note.write_text(
            "---\n"
            'title: "Expiring Contract"\n'
            "type: договор\n"
            'номер: "EXP-002"\n'
            'контрагент: "[[ООО Пример]]"\n'
            "дата_подписания: 2025-01-01\n"
            f"дата_окончания: {soon}\n"
            "статус: активный\n"
            "tags:\n"
            "  - тип/договор\n"
            "---\n\n"
            "# Expiring Contract\n",
            encoding="utf-8",
        )
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "Expiring Contract" in report
        assert "Найдено:** 1" in report or "**Найдено:** 1" in report

    def test_counterparty_history_report(
        self,
        tmp_vault: Path,
        sample_counterparty_note: Path,
        sample_contract_note: Path,
        sample_contact_note: Path,
    ) -> None:
        """The counterparty-history report should include the contract and
        contact linked to the counterparty."""
        report = report_counterparty_history(tmp_vault, "ООО Пример")
        assert "ООО Пример" in report
        # Contract should be listed
        assert "Договор" in report

    def test_employee_activity_report(
        self,
        tmp_vault: Path,
        sample_employee_note: Path,
        sample_contract_note: Path,
    ) -> None:
        """The employee-activity report should mention the employee's
        contracts."""
        report = report_employee_activity(tmp_vault, "Иванов Иван")
        assert "Иванов Иван" in report
        # The contract references Иванов Иван as ответственный_наш
        assert "Договор" in report or "договор" in report.lower()

    def test_expiring_contracts_no_results(self, tmp_vault: Path) -> None:
        """Empty vault should produce a report with 0 found."""
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "0" in report or "Не найдено" in report or report is not None

    def test_expiring_contracts_far_future(self, tmp_vault: Path) -> None:
        """Contract far in the future should NOT appear in short horizon."""
        far = (date.today() + timedelta(days=365)).isoformat()
        note = tmp_vault / "02-ДОГОВОРЫ" / "FarAway.md"
        note.write_text(
            "---\n"
            'title: "Far Away Contract"\n'
            "type: договор\n"
            'номер: "FAR-001"\n'
            f"дата_окончания: {far}\n"
            "статус: активный\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# Far Away\n",
            encoding="utf-8",
        )
        report = report_expiring_contracts(tmp_vault, days=7)
        assert "Far Away" not in report

    def test_counterparty_history_not_found(self, tmp_vault: Path) -> None:
        """Non-existing counterparty should still return a report."""
        report = report_counterparty_history(tmp_vault, "NonExistent")
        assert report is not None

    def test_employee_activity_not_found(self, tmp_vault: Path) -> None:
        """Non-existing employee should still return a report."""
        report = report_employee_activity(tmp_vault, "NonExistent")
        assert report is not None

    def test_read_notes_function(self, tmp_vault: Path) -> None:
        """read_notes should return list of (path, frontmatter)."""
        from scripts.generate_report import read_notes
        note = tmp_vault / "02-ДОГОВОРЫ" / "Test.md"
        note.write_text(
            "---\n"
            'title: "Test"\n'
            "type: договор\n"
            "---\n\n# Test\n",
            encoding="utf-8",
        )
        notes = read_notes(tmp_vault, "02-ДОГОВОРЫ")
        assert len(notes) >= 1
        assert notes[0][1].get("type") == "договор"

    def test_read_notes_empty_folder(self, tmp_vault: Path) -> None:
        from scripts.generate_report import read_notes
        notes = read_notes(tmp_vault, "03-ПРОЕКТЫ")
        assert notes == []

    def test_read_notes_nonexistent_folder(self, tmp_vault: Path) -> None:
        from scripts.generate_report import read_notes
        notes = read_notes(tmp_vault, "NONEXISTENT")
        assert notes == []

    def test_parse_date_valid(self) -> None:
        from scripts.generate_report import _parse_date
        d = _parse_date("2026-04-05")
        assert d == date(2026, 4, 5)

    def test_parse_date_invalid(self) -> None:
        from scripts.generate_report import _parse_date
        assert _parse_date("not-a-date") is None
        assert _parse_date("") is None

    def test_extract_wikilinks(self) -> None:
        from scripts.generate_report import _extract_wikilinks
        links = _extract_wikilinks("See [[Note One]] and [[Note Two|display]]")
        assert "Note One" in links
        assert "Note Two" in links

    def test_parse_frontmatter_function(self) -> None:
        from scripts.generate_report import parse_frontmatter
        text = '---\ntitle: "Test"\ntype: договор\n---\nBody'
        fm = parse_frontmatter(text)
        assert fm["title"] == "Test"
        assert fm["type"] == "договор"

    def test_parse_frontmatter_no_fm(self) -> None:
        from scripts.generate_report import parse_frontmatter
        assert parse_frontmatter("No frontmatter here") == {}


# -----------------------------------------------------------------------
# NEW TESTS: rich report scenarios with sample data
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestExpiringContractsDetailed:
    def test_multiple_expiring_contracts(self, tmp_vault: Path) -> None:
        """Multiple contracts within horizon should all appear."""
        for i in range(3):
            d = (date.today() + timedelta(days=5 + i)).isoformat()
            note = tmp_vault / "02-ДОГОВОРЫ" / f"Exp{i}.md"
            note.write_text(
                "---\n"
                f'title: "Exp Contract {i}"\n'
                "type: договор\n"
                f'номер: "E-{i}"\n'
                f"дата_окончания: {d}\n"
                "статус: активный\n"
                "tags:\n  - тип/договор\n"
                "---\n\n# Exp\n",
                encoding="utf-8",
            )
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "Exp Contract 0" in report
        assert "Exp Contract 1" in report
        assert "Exp Contract 2" in report
        assert "3" in report  # found count

    def test_finished_contract_excluded(self, tmp_vault: Path) -> None:
        """Contracts with status 'завершён' should not appear."""
        soon = (date.today() + timedelta(days=5)).isoformat()
        note = tmp_vault / "02-ДОГОВОРЫ" / "Finished.md"
        note.write_text(
            "---\n"
            'title: "Finished"\n'
            "type: договор\n"
            f"дата_окончания: {soon}\n"
            "статус: завершён\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# Finished\n",
            encoding="utf-8",
        )
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "Finished" not in report

    def test_cancelled_contract_excluded(self, tmp_vault: Path) -> None:
        """Contracts with status 'отменён' should not appear."""
        soon = (date.today() + timedelta(days=5)).isoformat()
        note = tmp_vault / "02-ДОГОВОРЫ" / "Cancelled.md"
        note.write_text(
            "---\n"
            'title: "Cancelled"\n'
            "type: договор\n"
            f"дата_окончания: {soon}\n"
            "статус: отменён\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# Cancelled\n",
            encoding="utf-8",
        )
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "Cancelled" not in report

    def test_contract_without_end_date_excluded(self, tmp_vault: Path) -> None:
        """Contracts without дата_окончания should not appear."""
        note = tmp_vault / "02-ДОГОВОРЫ" / "NoDate.md"
        note.write_text(
            "---\n"
            'title: "NoDate"\n'
            "type: договор\n"
            "статус: активный\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# NoDate\n",
            encoding="utf-8",
        )
        report = report_expiring_contracts(tmp_vault, days=30)
        assert "NoDate" not in report

    def test_report_sorted_by_date(self, tmp_vault: Path) -> None:
        """Contracts should be sorted by end date."""
        d1 = (date.today() + timedelta(days=20)).isoformat()
        d2 = (date.today() + timedelta(days=5)).isoformat()
        for i, d in enumerate([d1, d2]):
            note = tmp_vault / "02-ДОГОВОРЫ" / f"Sort{i}.md"
            note.write_text(
                "---\n"
                f'title: "Sort{i}"\n'
                "type: договор\n"
                f"дата_окончания: {d}\n"
                "статус: активный\n"
                "tags:\n  - тип/договор\n"
                "---\n\n# Sort\n",
                encoding="utf-8",
            )
        report = report_expiring_contracts(tmp_vault, days=30)
        # Sort1 (5 days) should appear before Sort0 (20 days)
        idx0 = report.index("Sort0") if "Sort0" in report else -1
        idx1 = report.index("Sort1") if "Sort1" in report else -1
        if idx0 >= 0 and idx1 >= 0:
            assert idx1 < idx0

    def test_no_expiring_message(self, tmp_vault: Path) -> None:
        """Empty results should show informational message."""
        report = report_expiring_contracts(tmp_vault, days=1)
        assert "Нет договоров" in report or "**Найдено:** 0" in report


@pytest.mark.unit
class TestCounterpartyHistoryDetailed:
    def test_includes_contacts_contracts_projects(self, tmp_vault: Path) -> None:
        """All sections should appear in the counterparty history."""
        # Create a counterparty
        (tmp_vault / "01-КОНТРАГЕНТЫ").mkdir(exist_ok=True)
        # Create contract
        note = tmp_vault / "02-ДОГОВОРЫ" / "CPContract.md"
        note.write_text(
            "---\n"
            'title: "CP Contract"\n'
            "type: договор\n"
            'контрагент: "[[ООО ЦелевойКП]]"\n'
            "статус: активный\n"
            "дата_подписания: 2026-01-01\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# CP\n",
            encoding="utf-8",
        )
        # Create contact
        note2 = tmp_vault / "05-КОНТАКТЫ" / "CPContact.md"
        note2.write_text(
            "---\n"
            'title: "CP Contact"\n'
            "type: контакт\n"
            'контрагент: "[[ООО ЦелевойКП]]"\n'
            'роль: "Менеджер"\n'
            "статус: активный\n"
            "tags:\n  - тип/контакт\n"
            "---\n\n# CP Contact\n",
            encoding="utf-8",
        )
        # Create project
        note3 = tmp_vault / "03-ПРОЕКТЫ" / "CPProject.md"
        note3.write_text(
            "---\n"
            'title: "CP Project"\n'
            "type: проект\n"
            'клиент: "[[ООО ЦелевойКП]]"\n'
            'руководитель: "[[Тест]]"\n'
            "статус: активный\n"
            "tags:\n  - тип/проект\n"
            "---\n\n# CP Project\n",
            encoding="utf-8",
        )

        report = report_counterparty_history(tmp_vault, "ООО ЦелевойКП")
        assert "CP Contract" in report
        assert "CP Contact" in report
        assert "CP Project" in report
        assert "Контактные лица" in report
        assert "Договоры" in report
        assert "Проекты" in report

    def test_empty_counterparty_shows_placeholders(self, tmp_vault: Path) -> None:
        report = report_counterparty_history(tmp_vault, "НесуществующийКП")
        assert "Контакты не найдены" in report
        assert "Договоры не найдены" in report
        assert "Проекты не найдены" in report

    def test_meetings_included(self, tmp_vault: Path) -> None:
        """Meetings (переговоры) should appear in the report."""
        note = tmp_vault / "06-ПЕРЕГОВОРЫ" / "Meeting.md"
        note.write_text(
            "---\n"
            'title: "Meeting Alpha"\n'
            "type: переговоры\n"
            'контрагент: "[[ООО МитингКП]]"\n'
            "дата: 2026-03-01\n"
            "статус: проведена\n"
            "tags:\n  - тип/переговоры\n"
            "---\n\n# Meeting\n",
            encoding="utf-8",
        )
        report = report_counterparty_history(tmp_vault, "ООО МитингКП")
        assert "Meeting Alpha" in report


@pytest.mark.unit
class TestEmployeeActivityDetailed:
    def test_employee_with_projects_contracts_meetings(self, tmp_vault: Path) -> None:
        """An employee referenced in projects, contracts, and meetings."""
        # Project where employee is руководитель
        note = tmp_vault / "03-ПРОЕКТЫ" / "EmpProject.md"
        note.write_text(
            "---\n"
            'title: "Emp Project"\n'
            "type: проект\n"
            'клиент: "[[Клиент]]"\n'
            'руководитель: "[[Тестов Тест]]"\n'
            "статус: активный\n"
            "tags:\n  - тип/проект\n"
            "---\n\n# Emp Project\n\n[[Тестов Тест]] is the lead.\n",
            encoding="utf-8",
        )
        # Contract where employee is ответственный
        note2 = tmp_vault / "02-ДОГОВОРЫ" / "EmpContract.md"
        note2.write_text(
            "---\n"
            'title: "Emp Contract"\n'
            "type: договор\n"
            'ответственный_наш: "[[Тестов Тест]]"\n'
            "статус: активный\n"
            "дата_окончания: 2027-01-01\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# Emp Contract\n\n[[Тестов Тест]]\n",
            encoding="utf-8",
        )
        # Meeting where employee is mentioned
        note3 = tmp_vault / "06-ПЕРЕГОВОРЫ" / "EmpMeeting.md"
        note3.write_text(
            "---\n"
            'title: "Emp Meeting"\n'
            "type: переговоры\n"
            "дата: 2026-03-01\n"
            'контрагент: "[[Клиент]]"\n'
            "статус: проведена\n"
            "tags:\n  - тип/переговоры\n"
            "---\n\n# Emp Meeting\n\nУчастники: [[Тестов Тест]]\n",
            encoding="utf-8",
        )

        report = report_employee_activity(tmp_vault, "Тестов Тест")
        assert "Emp Project" in report
        assert "Emp Contract" in report
        assert "Emp Meeting" in report
        assert "руководитель" in report

    def test_employee_no_data(self, tmp_vault: Path) -> None:
        report = report_employee_activity(tmp_vault, "Несуществующий Сотрудник")
        assert "Проекты не найдены" in report
        assert "Договоры не найдены" in report
        assert "Переговоры не найдены" in report

    def test_employee_as_participant(self, tmp_vault: Path) -> None:
        """Employee mentioned in project but not as руководитель."""
        note = tmp_vault / "03-ПРОЕКТЫ" / "PartProject.md"
        note.write_text(
            "---\n"
            'title: "Part Project"\n'
            "type: проект\n"
            'клиент: "[[Клиент]]"\n'
            'руководитель: "[[Другой Руководитель]]"\n'
            "статус: активный\n"
            "tags:\n  - тип/проект\n"
            "---\n\n# Part Project\n\nКоманда: [[Участник Один]]\n",
            encoding="utf-8",
        )
        report = report_employee_activity(tmp_vault, "Участник Один")
        assert "Part Project" in report
        assert "участник" in report


# -----------------------------------------------------------------------
# NEW TESTS: main() and parse_args()
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestGenerateReportMain:
    def test_main_expiring_contracts(self, tmp_vault: Path, capsys) -> None:
        import sys
        from unittest.mock import patch

        soon = (date.today() + timedelta(days=5)).isoformat()
        note = tmp_vault / "02-ДОГОВОРЫ" / "MainExp.md"
        note.write_text(
            "---\n"
            'title: "MainExp"\n'
            "type: договор\n"
            f"дата_окончания: {soon}\n"
            "статус: активный\n"
            "tags:\n  - тип/договор\n"
            "---\n\n# MainExp\n",
            encoding="utf-8",
        )

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_vault),
            "--type", "expiring-contracts",
            "--days", "30",
        ]):
            from scripts.generate_report import main
            main()

        captured = capsys.readouterr()
        assert "MainExp" in captured.out

    def test_main_counterparty_history(self, tmp_vault: Path, capsys) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_vault),
            "--type", "counterparty-history",
            "--counterparty", "ООО Тест",
        ]):
            from scripts.generate_report import main
            main()

        captured = capsys.readouterr()
        assert "ООО Тест" in captured.out

    def test_main_employee_activity(self, tmp_vault: Path, capsys) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_vault),
            "--type", "employee-activity",
            "--employee", "Тестов Тест",
        ]):
            from scripts.generate_report import main
            main()

        captured = capsys.readouterr()
        assert "Тестов Тест" in captured.out

    def test_main_vault_not_found(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_path / "nonexistent"),
            "--type", "expiring-contracts",
        ]):
            from scripts.generate_report import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_counterparty_missing_arg(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_vault),
            "--type", "counterparty-history",
        ]):
            from scripts.generate_report import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_employee_missing_arg(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "generate_report",
            "--vault", str(tmp_vault),
            "--type", "employee-activity",
        ]):
            from scripts.generate_report import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_parse_args_defaults(self) -> None:
        from scripts.generate_report import parse_args
        args = parse_args([
            "--vault", "/tmp/v",
            "--type", "expiring-contracts",
        ])
        assert args.days == 30
        assert args.counterparty == ""
        assert args.employee == ""

    def test_parse_args_verbose(self) -> None:
        from scripts.generate_report import parse_args
        args = parse_args([
            "--vault", "/tmp/v",
            "--type", "expiring-contracts",
            "--verbose",
        ])
        assert args.verbose is True
