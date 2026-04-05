"""Tests for scripts/validate_vault.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_vault import validate_vault


@pytest.mark.unit
class TestValidateVault:
    """Unit-tests for vault validation."""

    def test_valid_vault_no_errors(
        self,
        tmp_vault: Path,
        sample_company_note: Path,
        sample_counterparty_note: Path,
        sample_contract_note: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
        sample_contact_note: Path,
    ) -> None:
        """A vault with properly formed notes should produce zero errors."""
        result = validate_vault(tmp_vault)
        assert result["summary"]["errors_count"] == 0

    def test_invalid_yaml_reported(self, tmp_vault: Path) -> None:
        """A note with broken YAML should produce an invalid_yaml error."""
        bad_note = tmp_vault / "00-INBOX" / "broken.md"
        bad_note.write_text(
            "---\n"
            "title: \"Broken\n"  # unclosed quote
            "type: контрагент\n"
            "---\n",
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        yaml_errors = [
            e for e in result["errors"] if e["type"] == "invalid_yaml"
        ]
        assert len(yaml_errors) >= 1

    def test_missing_required_field(self, tmp_vault: Path) -> None:
        """A note missing a required field should produce a missing_field error."""
        note = tmp_vault / "01-КОНТРАГЕНТЫ" / "NoInn.md"
        note.write_text(
            "---\n"
            "title: \"NoInn\"\n"
            "type: контрагент\n"
            "tags:\n"
            "  - тип/контрагент\n"
            "---\n\n"
            "# NoInn\n",
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        missing = [
            e for e in result["errors"]
            if e["type"] == "missing_field" and "инн" in e["message"]
        ]
        assert len(missing) >= 1

    def test_unresolved_wikilink_warning(self, tmp_vault: Path) -> None:
        """A note referencing a non-existent target via [[wikilink]] should
        produce an unresolved_link warning."""
        note = tmp_vault / "00-INBOX" / "linker.md"
        note.write_text(
            "---\n"
            "title: \"Linker\"\n"
            "type: идея\n"
            "статус: черновик\n"
            "tags:\n"
            "  - тип/контрагент\n"
            "---\n\n"
            "See [[NonExistentNote]] for details.\n",
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        unresolved = [
            w for w in result["warnings"]
            if w["type"] == "unresolved_link"
            and "NonExistentNote" in w["message"]
        ]
        assert len(unresolved) >= 1

    def test_inconsistent_relationships_detected(
        self,
        tmp_vault: Path,
        sample_employee_note: Path,
        sample_employee_note_2: Path,
    ) -> None:
        """When employee A links to B in 'связи' but B does not link back,
        a missing_reverse_link warning should appear."""
        result = validate_vault(tmp_vault)
        reverse = [
            w for w in result["warnings"]
            if w["type"] == "missing_reverse_link"
        ]
        assert len(reverse) >= 1

    def test_expired_active_contract_detected(self, tmp_vault: Path) -> None:
        """An active contract with a past end date should produce an
        expired_active_contract warning."""
        note = tmp_vault / "02-ДОГОВОРЫ" / "Expired.md"
        note.write_text(
            "---\n"
            "title: \"Expired Contract\"\n"
            "type: договор\n"
            "номер: \"EXP-001\"\n"
            "контрагент: \"[[ООО Тест]]\"\n"
            "дата_подписания: 2019-01-01\n"
            "дата_окончания: 2020-01-01\n"
            "статус: активный\n"
            "tags:\n"
            "  - тип/договор\n"
            "  - статус/активный\n"
            "---\n\n"
            "# Expired Contract\n",
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        expired = [
            w for w in result["warnings"]
            if w["type"] == "expired_active_contract"
        ]
        assert len(expired) >= 1


@pytest.mark.unit
class TestValidateVaultEdgeCases:
    def test_duplicate_inn(self, tmp_vault: Path) -> None:
        """Two counterparties with same ИНН should produce duplicate_inn error."""
        for name in ["КомпанияА", "КомпанияБ"]:
            note = tmp_vault / "01-КОНТРАГЕНТЫ" / f"{name}.md"
            note.write_text(
                f'---\ntitle: "{name}"\ntype: контрагент\n'
                f'инн: "1234567890"\nкатегория: клиент\nстатус: активный\n'
                f'tags:\n  - тип/контрагент\n  - статус/активный\n---\n\n# {name}\n',
                encoding="utf-8",
            )
        result = validate_vault(tmp_vault)
        dupes = [e for e in result["errors"] if e["type"] == "duplicate_inn"]
        assert len(dupes) >= 1

    def test_duplicate_contract_number(self, tmp_vault: Path) -> None:
        """Two contracts with same номер should produce duplicate error."""
        for name in ["Договор А", "Договор Б"]:
            note = tmp_vault / "02-ДОГОВОРЫ" / f"{name}.md"
            note.write_text(
                f'---\ntitle: "{name}"\ntype: договор\nномер: "001"\n'
                f'контрагент: "[[Тест]]"\nдата_подписания: 2026-01-01\n'
                f'статус: активный\ntags:\n  - тип/договор\n  - статус/активный\n---\n',
                encoding="utf-8",
            )
        result = validate_vault(tmp_vault)
        dupes = [e for e in result["errors"] if e["type"] == "duplicate_contract_number"]
        assert len(dupes) >= 1

    def test_empty_vault(self, tmp_vault: Path) -> None:
        """Empty vault should have 0 notes and 0 errors."""
        result = validate_vault(tmp_vault)
        assert result["total_notes"] == 0
        assert result["summary"]["errors_count"] == 0

    def test_valid_counterparty(self, tmp_vault: Path, sample_counterparty_note: Path) -> None:
        result = validate_vault(tmp_vault)
        assert result["total_notes"] >= 1
        assert result["summary"]["by_type"].get("контрагент", 0) >= 1

    def test_valid_contract(self, tmp_vault: Path, sample_contract_note: Path, sample_counterparty_note: Path) -> None:
        result = validate_vault(tmp_vault)
        assert result["summary"]["by_type"].get("договор", 0) >= 1

    def test_valid_employee(self, tmp_vault: Path, sample_employee_note: Path, sample_employee_note_2: Path) -> None:
        result = validate_vault(tmp_vault)
        assert result["summary"]["by_type"].get("сотрудник", 0) >= 1

    def test_note_without_type(self, tmp_vault: Path) -> None:
        note = tmp_vault / "00-INBOX" / "notype.md"
        note.write_text(
            '---\ntitle: "No Type"\ntags:\n  - тип/контрагент\n---\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        # Should have missing_field error for type
        missing = [e for e in result["errors"] if e["type"] == "missing_field"]
        assert len(missing) >= 1

    def test_get_body_function(self) -> None:
        from scripts.validate_vault import _get_body
        text = "---\ntitle: Test\n---\n\nBody content"
        body = _get_body(text)
        assert "Body content" in body

    def test_parse_frontmatter_with_yaml(self, tmp_vault: Path) -> None:
        from scripts.validate_vault import _parse_frontmatter
        text = '---\ntitle: "Test"\ntype: контрагент\ntags:\n  - тип/контрагент\n---\n'
        fm, err = _parse_frontmatter(text)
        assert err is None
        assert fm is not None
        assert fm["title"] == "Test"

    def test_parse_frontmatter_no_markers(self) -> None:
        from scripts.validate_vault import _parse_frontmatter
        fm, err = _parse_frontmatter("No frontmatter here")
        assert fm is None
        assert err is not None

    def test_result_json_structure(self, tmp_vault: Path) -> None:
        """Result should have correct JSON structure."""
        result = validate_vault(tmp_vault)
        assert "vault" in result
        assert "total_notes" in result
        assert "errors" in result
        assert "warnings" in result
        assert "summary" in result
        assert "by_type" in result["summary"]
        assert "errors_count" in result["summary"]
        assert "warnings_count" in result["summary"]

    def test_extract_wikilinks(self) -> None:
        from scripts.validate_vault import _extract_wikilinks
        links = _extract_wikilinks("See [[Note A]] and [[Note B|text]].")
        assert "Note A" in links
        assert "Note B" in links

    def test_check_required_fields_contract(self, tmp_vault: Path) -> None:
        """Contract missing номер should produce error."""
        note = tmp_vault / "02-ДОГОВОРЫ" / "NoNomer.md"
        note.write_text(
            '---\ntitle: "No номер"\ntype: договор\n'
            'контрагент: "[[Test]]"\nдата_подписания: 2026-01-01\n'
            'статус: активный\ntags:\n  - тип/договор\n---\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        missing = [e for e in result["errors"] if e["type"] == "missing_field" and "номер" in e.get("message", "")]
        assert len(missing) >= 1

    def test_check_required_fields_contact(self, tmp_vault: Path) -> None:
        """Contact missing контрагент should produce error."""
        note = tmp_vault / "05-КОНТАКТЫ" / "NoAgent.md"
        note.write_text(
            '---\ntitle: "No Agent"\ntype: контакт\n'
            'роль: "Менеджер"\nстатус: активный\ntags:\n  - тип/контакт\n---\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        missing = [e for e in result["errors"] if e["type"] == "missing_field" and "контрагент" in e.get("message", "")]
        assert len(missing) >= 1

    def test_multiple_note_types(
        self, tmp_vault, sample_counterparty_note, sample_contract_note,
        sample_employee_note, sample_employee_note_2, sample_contact_note,
    ) -> None:
        """Vault with multiple note types should count them."""
        result = validate_vault(tmp_vault)
        assert result["total_notes"] >= 4


# -----------------------------------------------------------------------
# NEW TESTS: additional edge cases and coverage
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestValidateVaultMoreEdgeCases:
    def test_invalid_tag_detected(self, tmp_vault: Path) -> None:
        """A tag not in ALLOWED_TAG_PREFIXES should produce an invalid_tag error."""
        note = tmp_vault / "00-INBOX" / "bad_tag.md"
        note.write_text(
            '---\ntitle: "Bad Tag"\ntype: идея\nстатус: черновик\n'
            'tags:\n  - invalid/tag\n---\n\n# Bad Tag\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        tag_errors = [e for e in result["errors"] if e["type"] == "invalid_tag"]
        assert len(tag_errors) >= 1
        assert "invalid/tag" in tag_errors[0]["message"]

    def test_note_without_frontmatter(self, tmp_vault: Path) -> None:
        """A note without frontmatter at all should produce invalid_yaml."""
        note = tmp_vault / "00-INBOX" / "no_fm.md"
        note.write_text("# Just a heading\nNo frontmatter.", encoding="utf-8")
        result = validate_vault(tmp_vault)
        yaml_errors = [e for e in result["errors"] if e["type"] == "invalid_yaml"]
        assert len(yaml_errors) >= 1

    def test_frontmatter_not_dict(self, tmp_vault: Path) -> None:
        """Frontmatter that parses to a non-dict should produce an error."""
        note = tmp_vault / "00-INBOX" / "not_dict.md"
        note.write_text("---\n- item1\n- item2\n---\n\n# List FM\n", encoding="utf-8")
        result = validate_vault(tmp_vault)
        yaml_errors = [e for e in result["errors"] if e["type"] == "invalid_yaml"]
        assert len(yaml_errors) >= 1

    def test_unclosed_frontmatter(self, tmp_vault: Path) -> None:
        """Frontmatter without closing --- should produce invalid_yaml."""
        note = tmp_vault / "00-INBOX" / "unclosed.md"
        note.write_text("---\ntitle: Test\n", encoding="utf-8")
        result = validate_vault(tmp_vault)
        yaml_errors = [e for e in result["errors"] if e["type"] == "invalid_yaml"]
        assert len(yaml_errors) >= 1

    def test_string_tags_handled(self, tmp_vault: Path) -> None:
        """Tags as a single string (not list) should be validated."""
        note = tmp_vault / "00-INBOX" / "str_tag.md"
        note.write_text(
            '---\ntitle: "Str Tag"\ntype: идея\nстатус: черновик\n'
            'tags: "тип/идея"\n---\n\n# Str Tag\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        # Single string tag with valid prefix should not produce invalid_tag
        tag_errors = [
            e for e in result["errors"]
            if e["type"] == "invalid_tag" and "str_tag" in e.get("file", "").lower()
        ]
        assert len(tag_errors) == 0

    def test_active_contract_with_future_date_no_warning(self, tmp_vault: Path) -> None:
        """Active contract with future end date should NOT produce warning."""
        note = tmp_vault / "02-ДОГОВОРЫ" / "ActiveFuture.md"
        note.write_text(
            '---\ntitle: "Active Future"\ntype: договор\nномер: "AF-001"\n'
            'контрагент: "[[Test]]"\nдата_подписания: 2026-01-01\n'
            'дата_окончания: 2030-01-01\nстатус: активный\n'
            'tags:\n  - тип/договор\n---\n\n# Active Future\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        expired = [w for w in result["warnings"] if w["type"] == "expired_active_contract"]
        # Should not find this note in expired warnings
        expired_this = [w for w in expired if "Active Future" in w.get("file", "")]
        assert len(expired_this) == 0

    def test_bidirectional_relationships_no_warning(self, tmp_vault: Path) -> None:
        """When both A and B link to each other, no warning should appear."""
        note_a = tmp_vault / "04-СОТРУДНИКИ" / "RelA.md"
        note_a.write_text(
            '---\ntitle: "RelA"\ntype: сотрудник\nдолжность: "Dev"\n'
            'статус: активный\nсвязи:\n  - "[[RelB]]"\n'
            'tags:\n  - тип/сотрудник\n  - статус/активный\n---\n\n# RelA\n',
            encoding="utf-8",
        )
        note_b = tmp_vault / "04-СОТРУДНИКИ" / "RelB.md"
        note_b.write_text(
            '---\ntitle: "RelB"\ntype: сотрудник\nдолжность: "Dev"\n'
            'статус: активный\nсвязи:\n  - "[[RelA]]"\n'
            'tags:\n  - тип/сотрудник\n  - статус/активный\n---\n\n# RelB\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        reverse = [
            w for w in result["warnings"]
            if w["type"] == "missing_reverse_link"
            and ("RelA" in w["message"] or "RelB" in w["message"])
        ]
        assert len(reverse) == 0

    def test_string_svyazi_handled(self, tmp_vault: Path) -> None:
        """When связи is a string instead of a list, it should still be processed."""
        note = tmp_vault / "04-СОТРУДНИКИ" / "StrSvyazi.md"
        note.write_text(
            '---\ntitle: "StrSvyazi"\ntype: сотрудник\nдолжность: "Dev"\n'
            'статус: активный\nсвязи: "[[StrTarget]]"\n'
            'tags:\n  - тип/сотрудник\n  - статус/активный\n---\n\n# StrSvyazi\n',
            encoding="utf-8",
        )
        result = validate_vault(tmp_vault)
        reverse = [
            w for w in result["warnings"]
            if w["type"] == "missing_reverse_link" and "StrSvyazi" in w["message"]
        ]
        assert len(reverse) >= 1


# -----------------------------------------------------------------------
# NEW TESTS: helper functions
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestHelperFunctions:
    def test_simple_yaml_parse(self) -> None:
        from scripts.validate_vault import _simple_yaml_parse
        result = _simple_yaml_parse('title: "Test"\ntype: контрагент')
        assert result is not None
        assert result["title"] == "Test"
        assert result["type"] == "контрагент"

    def test_simple_yaml_parse_list(self) -> None:
        from scripts.validate_vault import _simple_yaml_parse
        result = _simple_yaml_parse('tags: [тип/контрагент, статус/активный]')
        assert result is not None
        assert "тип/контрагент" in result["tags"]

    def test_simple_yaml_parse_empty(self) -> None:
        from scripts.validate_vault import _simple_yaml_parse
        result = _simple_yaml_parse("")
        assert result is None

    def test_parse_date_with_date_object(self) -> None:
        from datetime import date
        from scripts.validate_vault import _parse_date
        d = date(2026, 1, 1)
        assert _parse_date(d) == d

    def test_parse_date_with_none(self) -> None:
        from scripts.validate_vault import _parse_date
        assert _parse_date(None) is None

    def test_parse_date_with_int(self) -> None:
        from scripts.validate_vault import _parse_date
        assert _parse_date(12345) is None

    def test_make_error_structure(self) -> None:
        from scripts.validate_vault import _make_error
        err = _make_error("path/to/file.md", "test_type", "Test message")
        assert err["file"] == "path/to/file.md"
        assert err["type"] == "test_type"
        assert err["message"] == "Test message"

    def test_get_body_no_frontmatter(self) -> None:
        from scripts.validate_vault import _get_body
        body = _get_body("Just text, no frontmatter")
        assert body == "Just text, no frontmatter"

    def test_get_body_with_bom(self) -> None:
        from scripts.validate_vault import _get_body
        text = "\ufeff---\ntitle: Test\n---\n\nBody"
        body = _get_body(text)
        assert "Body" in body


# -----------------------------------------------------------------------
# NEW TESTS: main() function
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestValidateVaultMain:
    def test_main_success(self, tmp_vault: Path, capsys) -> None:
        import sys
        from unittest.mock import patch
        from scripts.validate_vault import main

        with patch.object(sys, "argv", ["validate_vault", "--vault", str(tmp_vault)]):
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "total_notes" in captured.out

    def test_main_with_errors(self, tmp_vault: Path, capsys) -> None:
        import sys
        from unittest.mock import patch
        from scripts.validate_vault import main

        # Create a note with invalid YAML
        bad = tmp_vault / "00-INBOX" / "bad_main.md"
        bad.write_text("---\ntitle: \"Broken\ntype: x\n---\n", encoding="utf-8")

        with patch.object(sys, "argv", ["validate_vault", "--vault", str(tmp_vault)]):
            exit_code = main()

        assert exit_code == 1

    def test_main_vault_not_found(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch
        from scripts.validate_vault import main

        with patch.object(sys, "argv", [
            "validate_vault",
            "--vault", str(tmp_path / "nonexistent"),
        ]):
            exit_code = main()
        assert exit_code == 1

    def test_build_parser(self) -> None:
        from scripts.validate_vault import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["--vault", "/tmp/test"])
        assert args.vault == Path("/tmp/test")
