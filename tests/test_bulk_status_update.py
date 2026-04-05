"""Tests for scripts/bulk_status_update.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.bulk_status_update import bulk_status_update, parse_frontmatter


@pytest.mark.unit
class TestBulkStatusUpdate:
    """Unit-tests for bulk status updates."""

    def _create_counterparty(
        self, vault: Path, name: str, status: str = "активный", category: str = "клиент"
    ) -> Path:
        """Helper: create a minimal counterparty note."""
        note = vault / "01-КОНТРАГЕНТЫ" / f"{name}.md"
        note.write_text(
            "---\n"
            f'title: "{name}"\n'
            "type: контрагент\n"
            f'инн: "000{hash(name) % 10000000:07d}"\n'
            f"категория: {category}\n"
            f"статус: {status}\n"
            "tags:\n"
            "  - тип/контрагент\n"
            f"  - статус/{status}\n"
            "---\n\n"
            f"# {name}\n",
            encoding="utf-8",
        )
        return note

    def test_update_status_field(self, tmp_vault: Path) -> None:
        """bulk_status_update should change the status field in YAML."""
        self._create_counterparty(tmp_vault, "TestCo", status="активный")
        count = bulk_status_update(
            tmp_vault, "01-КОНТРАГЕНТЫ", "приостановлен"
        )
        assert count == 1

        updated = (tmp_vault / "01-КОНТРАГЕНТЫ" / "TestCo.md").read_text(
            encoding="utf-8"
        )
        fm = parse_frontmatter(updated)
        assert fm["статус"] == "приостановлен"

    def test_move_to_archive_on_completed(self, tmp_vault: Path) -> None:
        """When new status is 'завершён', the file should be moved to
        99-АРХИВ/."""
        self._create_counterparty(tmp_vault, "ArchiveMe", status="активный")
        count = bulk_status_update(
            tmp_vault, "01-КОНТРАГЕНТЫ", "завершён"
        )
        assert count == 1

        # The file should no longer be in the original folder
        original = tmp_vault / "01-КОНТРАГЕНТЫ" / "ArchiveMe.md"
        assert not original.exists()

        # It should be in the archive
        archive_dir = tmp_vault / "99-АРХИВ" / "01-КОНТРАГЕНТЫ"
        archived = archive_dir / "ArchiveMe.md"
        assert archived.exists()

        fm = parse_frontmatter(archived.read_text(encoding="utf-8"))
        assert fm["статус"] == "завершён"

    def test_filter_works(self, tmp_vault: Path) -> None:
        """Only notes matching the filter expression should be updated."""
        self._create_counterparty(
            tmp_vault, "ClientCo", status="активный", category="клиент"
        )
        self._create_counterparty(
            tmp_vault, "PartnerCo", status="активный", category="партнёр"
        )

        count = bulk_status_update(
            tmp_vault,
            "01-КОНТРАГЕНТЫ",
            "приостановлен",
            filter_expr="категория:клиент",
        )
        assert count == 1

        # ClientCo should be updated
        client_text = (tmp_vault / "01-КОНТРАГЕНТЫ" / "ClientCo.md").read_text(
            encoding="utf-8"
        )
        assert "приостановлен" in client_text

        # PartnerCo should remain unchanged
        partner_text = (tmp_vault / "01-КОНТРАГЕНТЫ" / "PartnerCo.md").read_text(
            encoding="utf-8"
        )
        assert "активный" in partner_text
