"""Tests for scripts/import_vcard.py."""

from __future__ import annotations

from pathlib import Path

import pytest

vobject = pytest.importorskip("vobject", reason="vobject is required for vCard tests")

from scripts.import_vcard import extract_contact, import_vcard  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.unit
class TestImportVcard:
    """Unit-tests for vCard import into Obsidian vault."""

    def test_parse_produces_correct_contacts(self) -> None:
        """Parsing the sample .vcf should yield two contact entries."""
        vcf_path = FIXTURES_DIR / "sample.vcf"
        text = vcf_path.read_text(encoding="utf-8")
        cards = list(vobject.readComponents(text))
        assert len(cards) == 2

    def test_maps_fn_tel_email_title(self) -> None:
        """FN, TEL, EMAIL, and TITLE fields should be mapped correctly."""
        vcf_path = FIXTURES_DIR / "sample.vcf"
        text = vcf_path.read_text(encoding="utf-8")
        cards = list(vobject.readComponents(text))

        first = extract_contact(cards[0])
        assert first["title"] == "Сидоров Алексей Петрович"
        assert "+7 (495) 123-45-67" in first.get("phone", "")
        assert first.get("email", "") == "sidorov@example.com"
        assert first.get("role", "") == "Технический директор"

        second = extract_contact(cards[1])
        assert second["title"] == "Козлова Мария Ивановна"
        assert "+7 (495) 987-65-43" in second.get("phone", "")
        assert second.get("email", "") == "kozlova@example.com"
        assert second.get("role", "") == "Финансовый директор"

    def test_import_creates_md_files(self, tmp_vault: Path) -> None:
        """import_vcard should create .md contact files in the vault."""
        vcf_path = FIXTURES_DIR / "sample.vcf"
        count = import_vcard(tmp_vault, vcf_path)
        assert count == 2

        contacts_dir = tmp_vault / "05-КОНТАКТЫ"
        created = list(contacts_dir.glob("*.md"))
        assert len(created) == 2

    def test_import_with_counterparty(self, tmp_vault: Path, sample_counterparty_note: Path) -> None:
        """Import with counterparty should link contacts."""
        vcf_path = FIXTURES_DIR / "sample.vcf"
        count = import_vcard(tmp_vault, vcf_path, counterparty="ООО Пример")
        assert count == 2
        contacts_dir = tmp_vault / "05-КОНТАКТЫ"
        created = list(contacts_dir.glob("*.md"))
        assert len(created) >= 2

    def test_build_contact_md(self) -> None:
        """build_contact_md should generate valid markdown."""
        from scripts.import_vcard import build_contact_md
        fields = {
            "title": "Иванов Иван Иванович",
            "role": "Директор",
            "phone": "+7 (495) 123-45-67",
            "email": "ivanov@test.com",
        }
        md = build_contact_md(fields, "ООО Тест", "2026-04-05")
        assert "Иванов Иван Иванович" in md
        assert "[[ООО Тест]]" in md
        assert "Директор" in md
        assert "type: контакт" in md

    def test_build_contact_md_no_counterparty(self) -> None:
        from scripts.import_vcard import build_contact_md
        fields = {"title": "Тест Тестович", "organization": "ООО Авто"}
        md = build_contact_md(fields, "", "2026-04-05")
        assert "[[ООО Авто]]" in md

    def test_safe_filename(self) -> None:
        from scripts.import_vcard import _safe_filename
        assert _safe_filename('Test<>:"/\\|?*Name') == "TestName"
        assert _safe_filename("Normal Name") == "Normal Name"

    def test_extract_contact_minimal(self) -> None:
        """Extract from vCard with only FN."""
        card = vobject.vCard()
        card.add("fn").value = "Минимальный Контакт"
        result = extract_contact(card)
        assert result["title"] == "Минимальный Контакт"

    def test_extract_contact_with_org(self) -> None:
        """Extract organization from vCard."""
        card = vobject.vCard()
        card.add("fn").value = "Тест"
        card.add("org").value = ["ООО Тест"]
        result = extract_contact(card)
        assert "ООО Тест" in result.get("organization", "")

    def test_import_empty_vcf(self, tmp_vault: Path, tmp_path: Path) -> None:
        """Importing an empty vCard file should create 0 contacts."""
        empty_vcf = tmp_path / "empty.vcf"
        empty_vcf.write_text("", encoding="utf-8")
        count = import_vcard(tmp_vault, empty_vcf)
        assert count == 0

    def test_parse_frontmatter(self) -> None:
        from scripts.import_vcard import parse_frontmatter
        text = '---\ntitle: "Test"\ntype: контакт\n---\n\nBody'
        fm = parse_frontmatter(text)
        assert fm["title"] == "Test"
        assert fm["type"] == "контакт"

    def test_parse_frontmatter_no_fm(self) -> None:
        from scripts.import_vcard import parse_frontmatter
        assert parse_frontmatter("No frontmatter") == {}


# -----------------------------------------------------------------------
# NEW TESTS: edge cases and function coverage
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestImportVcardAdditionalEdgeCases:
    def test_vcard_without_fn_skipped(self, tmp_vault: Path) -> None:
        """A vCard entry without FN should be skipped."""
        vcf_path = tmp_vault / "no_fn.vcf"
        vcf_path.write_text(
            "BEGIN:VCARD\n"
            "VERSION:3.0\n"
            "TEL:+7123456789\n"
            "END:VCARD\n",
            encoding="utf-8",
        )
        count = import_vcard(tmp_vault, vcf_path)
        assert count == 0

    def test_import_skips_existing_file(self, tmp_vault: Path) -> None:
        """If a contact file already exists, it should be skipped."""
        contacts_dir = tmp_vault / "05-КОНТАКТЫ"
        contacts_dir.mkdir(parents=True, exist_ok=True)

        existing = contacts_dir / "Сидоров Алексей Петрович (ООО ТестКомпания).md"
        existing.write_text("---\ntitle: existing\n---\n", encoding="utf-8")

        vcf_path = FIXTURES_DIR / "sample.vcf"
        count = import_vcard(tmp_vault, vcf_path)
        assert count == 1

    def test_multiple_phones_in_extract(self) -> None:
        vcf_text = (
            "BEGIN:VCARD\n"
            "VERSION:3.0\n"
            "FN:Тест Тестович\n"
            "TEL;TYPE=WORK:+71111111111\n"
            "TEL;TYPE=CELL:+72222222222\n"
            "END:VCARD\n"
        )
        cards = list(vobject.readComponents(vcf_text))
        fields = extract_contact(cards[0])
        assert fields["phone"] == "+71111111111"
        assert "+72222222222" in fields.get("phone_extra", "")

    def test_multiple_emails_in_extract(self) -> None:
        vcf_text = (
            "BEGIN:VCARD\n"
            "VERSION:3.0\n"
            "FN:Тест\n"
            "EMAIL;TYPE=WORK:a@test.ru\n"
            "EMAIL;TYPE=HOME:b@test.ru\n"
            "END:VCARD\n"
        )
        cards = list(vobject.readComponents(vcf_text))
        fields = extract_contact(cards[0])
        assert fields["email"] == "a@test.ru"
        assert "b@test.ru" in fields.get("email_extra", "")


@pytest.mark.unit
class TestUpdateCounterpartyCard:
    def test_updates_counterparty_contacts(self, tmp_vault: Path) -> None:
        from scripts.import_vcard import update_counterparty_card

        cp_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        cp_dir.mkdir(parents=True, exist_ok=True)
        cp_file = cp_dir / "ООО Тестовая.md"
        cp_file.write_text(
            '---\ntitle: "ООО Тестовая"\nконтактные_лица: []\n---\n# ООО Тестовая\n',
            encoding="utf-8",
        )

        update_counterparty_card(tmp_vault, "ООО Тестовая", ["Иванов Иван"])

        text = cp_file.read_text(encoding="utf-8")
        assert "Иванов Иван" in text

    def test_counterparty_not_found_no_error(self, tmp_vault: Path) -> None:
        from scripts.import_vcard import update_counterparty_card
        # Should not raise, just log a warning
        update_counterparty_card(tmp_vault, "Nonexistent Corp", ["Test"])

    def test_updates_existing_contact_list(self, tmp_vault: Path) -> None:
        from scripts.import_vcard import update_counterparty_card

        cp_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        cp_dir.mkdir(parents=True, exist_ok=True)
        cp_file = cp_dir / "ООО WithContacts.md"
        cp_file.write_text(
            '---\ntitle: "ООО WithContacts"\nконтактные_лица:\n'
            '  - "[[Старый Контакт]]"\n---\n# ООО WithContacts\n',
            encoding="utf-8",
        )

        update_counterparty_card(tmp_vault, "ООО WithContacts", ["Новый Контакт"])

        text = cp_file.read_text(encoding="utf-8")
        assert "Новый Контакт" in text
        assert "Старый Контакт" in text


# -----------------------------------------------------------------------
# NEW TESTS: main() and parse_args()
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestImportVcardMain:
    def test_main_runs_import(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        vcf_path = FIXTURES_DIR / "sample.vcf"
        with patch.object(sys, "argv", [
            "import_vcard",
            "--vault", str(tmp_vault),
            "--file", str(vcf_path),
        ]):
            from scripts.import_vcard import main
            main()

        contacts_dir = tmp_vault / "05-КОНТАКТЫ"
        created = list(contacts_dir.glob("*.md"))
        assert len(created) == 2

    def test_main_with_counterparty_flag(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        vcf_path = FIXTURES_DIR / "sample.vcf"
        with patch.object(sys, "argv", [
            "import_vcard",
            "--vault", str(tmp_vault),
            "--file", str(vcf_path),
            "--counterparty", "ООО Main",
        ]):
            from scripts.import_vcard import main
            main()

        contacts_dir = tmp_vault / "05-КОНТАКТЫ"
        created = list(contacts_dir.glob("*.md"))
        assert len(created) == 2

    def test_main_vault_not_found(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "import_vcard",
            "--vault", str(tmp_path / "nonexistent"),
            "--file", str(FIXTURES_DIR / "sample.vcf"),
        ]):
            from scripts.import_vcard import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_file_not_found(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "import_vcard",
            "--vault", str(tmp_vault),
            "--file", str(tmp_vault / "nonexistent.vcf"),
        ]):
            from scripts.import_vcard import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_parse_args_verbose(self) -> None:
        from scripts.import_vcard import parse_args
        args = parse_args([
            "--vault", "/tmp/v",
            "--file", "/tmp/f.vcf",
            "--verbose",
        ])
        assert args.verbose is True
        assert args.counterparty == ""
