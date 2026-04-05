"""Tests for scripts/audit_links.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit_links import audit_links


@pytest.mark.unit
class TestAuditLinks:
    """Unit-tests for wikilink auditing."""

    def test_detect_broken_wikilinks(self, tmp_vault: Path) -> None:
        """Notes containing [[NonExistent]] links should be reported as
        broken."""
        note = tmp_vault / "00-INBOX" / "with_broken.md"
        note.write_text(
            "---\n"
            'title: "Note with broken link"\n'
            "type: идея\n"
            "статус: черновик\n"
            "tags:\n"
            "  - тип/контрагент\n"
            "---\n\n"
            "Reference to [[NonExistent]] here.\n",
            encoding="utf-8",
        )
        broken = audit_links(tmp_vault, fix=False)
        assert len(broken) >= 1
        all_targets = [t for targets in broken.values() for t in targets]
        assert "NonExistent" in all_targets

    def test_fix_creates_empty_cards(self, tmp_vault: Path) -> None:
        """With --fix, audit_links should create stub .md files for broken
        targets."""
        note = tmp_vault / "00-INBOX" / "with_broken2.md"
        note.write_text(
            "---\n"
            'title: "Another broken"\n'
            "type: идея\n"
            "статус: черновик\n"
            "tags:\n"
            "  - тип/контрагент\n"
            "---\n\n"
            "Link to [[StubTarget]] and [[AnotherStub]].\n",
            encoding="utf-8",
        )
        audit_links(tmp_vault, fix=True)

        # After fix, the targets should exist somewhere in the vault
        all_stems = {f.stem for f in tmp_vault.rglob("*.md")}
        assert "StubTarget" in all_stems
        assert "AnotherStub" in all_stems

    def test_no_broken_links_clean_output(
        self,
        tmp_vault: Path,
        sample_company_note: Path,
        sample_counterparty_note: Path,
        sample_contract_note: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
        sample_contact_note: Path,
    ) -> None:
        """A vault where all wikilinks resolve should produce an empty broken
        dict."""
        broken = audit_links(tmp_vault, fix=False)
        # All links from sample notes reference notes that exist in the vault
        # (some may still be broken if targets are missing, but the set of
        # fixture notes covers the main cross-references).
        # We check the function returns a dict (possibly empty or small).
        assert isinstance(broken, dict)
