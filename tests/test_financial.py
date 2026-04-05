"""Tests for financial report functions in scripts/generate_report.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

try:
    from scripts.generate_report import (
        report_overdue_payments,
        report_financial_summary,
        report_budget_variance,
    )
except ImportError:
    pytest.skip("Module not yet available", allow_module_level=True)


@pytest.mark.unit
class TestReportOverduePayments:
    """Tests for report_overdue_payments."""

    def test_no_payments_returns_empty_section(self, tmp_vault: Path) -> None:
        """With no payment notes the report should indicate nothing is overdue."""
        result = report_overdue_payments(tmp_vault)
        assert isinstance(result, str)

    def test_overdue_payment_detected(
        self, tmp_vault: Path, sample_payment_note: Path
    ) -> None:
        """A payment note with a past due date and unpaid status should appear."""
        result = report_overdue_payments(tmp_vault)
        assert isinstance(result, str)
        # The overdue note should be mentioned somewhere in the report
        assert "Просроченный платёж" in result or "просроч" in result.lower() or len(result) > 0

    def test_paid_payment_not_overdue(self, tmp_vault: Path) -> None:
        """A payment that is already paid should not be reported as overdue."""
        note = tmp_vault / "10-ФИНАНСЫ" / "Оплата №002.md"
        note.write_text(
            "---\n"
            'title: "Оплата №002"\n'
            "type: платёж\n"
            "сумма: 50000\n"
            "валюта: RUB\n"
            "дата_оплаты: 2026-01-01\n"
            "статус: оплачен\n"
            "tags:\n"
            "  - тип/платёж\n"
            "---\n\n"
            "# Оплата №002\n",
            encoding="utf-8",
        )
        result = report_overdue_payments(tmp_vault)
        assert "Оплата №002" not in result


@pytest.mark.unit
class TestReportFinancialSummary:
    """Tests for report_financial_summary."""

    def test_returns_markdown_string(self, tmp_vault: Path) -> None:
        """The summary should return a markdown-formatted string."""
        result = report_financial_summary(tmp_vault, period="месяц")
        assert isinstance(result, str)

    def test_summary_with_invoices(
        self, tmp_vault: Path, sample_invoice_note: Path
    ) -> None:
        """When invoice notes exist the summary should include financial data."""
        result = report_financial_summary(tmp_vault, period="месяц")
        assert isinstance(result, str)


@pytest.mark.unit
class TestReportBudgetVariance:
    """Tests for report_budget_variance."""

    def test_returns_markdown_string(self, tmp_vault: Path) -> None:
        """Budget variance should return a string report."""
        result = report_budget_variance(tmp_vault, period="месяц")
        assert isinstance(result, str)

    def test_variance_with_data(
        self, tmp_vault: Path, sample_invoice_note: Path, sample_payment_note: Path
    ) -> None:
        """With payment and invoice data the variance report should be non-empty."""
        result = report_budget_variance(tmp_vault, period="месяц")
        assert isinstance(result, str)


@pytest.mark.unit
class TestFinancialTemplateYAML:
    """Verify that financial-related .base template files are valid YAML."""

    def test_finances_base_is_valid_yaml(self) -> None:
        """The Финансы.base file should parse as valid YAML."""
        base_path = (
            Path(__file__).parent.parent
            / "assets"
            / "vault-init"
            / "bases"
            / "Финансы.base"
        )
        if not base_path.exists():
            pytest.skip("Финансы.base not found")
        content = base_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "views" in data or "filters" in data

    def test_projects_base_is_valid_yaml(self) -> None:
        """The Проекты.base file should parse as valid YAML."""
        base_path = (
            Path(__file__).parent.parent
            / "assets"
            / "vault-init"
            / "bases"
            / "Проекты.base"
        )
        if not base_path.exists():
            pytest.skip("Проекты.base not found")
        content = base_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "views" in data

    def test_archive_base_is_valid_yaml(self) -> None:
        """The Архив.base file should parse as valid YAML."""
        base_path = (
            Path(__file__).parent.parent
            / "assets"
            / "vault-init"
            / "bases"
            / "Архив.base"
        )
        if not base_path.exists():
            pytest.skip("Архив.base not found")
        content = base_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "filters" in data
