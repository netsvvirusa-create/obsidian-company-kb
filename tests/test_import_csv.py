"""Tests for scripts/import_csv.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.import_csv import import_csv

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.unit
class TestImportCsv:
    """Unit-tests for CSV import into Obsidian vault."""

    def test_import_creates_md_files(self, tmp_vault: Path) -> None:
        """Importing a valid CSV should create .md files in the vault."""
        csv_path = FIXTURES_DIR / "sample.csv"
        count = import_csv(tmp_vault, "контрагент", csv_path)
        assert count == 3

        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 3

    def test_empty_csv_no_files(self, tmp_vault: Path) -> None:
        """An empty CSV (header only, no rows) should create no files."""
        empty_csv = tmp_vault / "empty.csv"
        empty_csv.write_text(
            "Название,ИНН,Категория,Статус\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", empty_csv)
        assert count == 0

        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 0

    def test_duplicate_inn_warning(self, tmp_vault: Path) -> None:
        """Rows with duplicate INN values should be skipped after the first."""
        dup_csv = tmp_vault / "dup.csv"
        dup_csv.write_text(
            "Название,ИНН,Категория,Статус\n"
            "Компания А,1234567890,клиент,активный\n"
            "Компания Б,1234567890,клиент,активный\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", dup_csv)
        # Only one file should be created; the duplicate is skipped
        assert count == 1

    def test_dry_run_no_files_created(self, tmp_vault: Path) -> None:
        """Dry-run mode should report files but not actually create them."""
        csv_path = FIXTURES_DIR / "sample.csv"
        count = import_csv(tmp_vault, "контрагент", csv_path, dry_run=True)
        assert count == 3

        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 0


# -----------------------------------------------------------------------
# NEW TESTS: more edge cases and function coverage
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestImportCsvEdgeCases:
    def test_import_contact_type(self, tmp_vault: Path) -> None:
        """Importing as type 'контакт' should create files in 05-КОНТАКТЫ."""
        csv_path = tmp_vault / "contacts.csv"
        csv_path.write_text(
            "ФИО,Контрагент,Роль,Телефон,Email\n"
            "Иванов Иван,ООО Тест,Директор,+7900123,ivan@test.ru\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контакт", csv_path)
        assert count == 1
        target_dir = tmp_vault / "05-КОНТАКТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 1

    def test_import_employee_type(self, tmp_vault: Path) -> None:
        """Importing as type 'сотрудник' should create files in 04-СОТРУДНИКИ."""
        csv_path = tmp_vault / "employees.csv"
        csv_path.write_text(
            "ФИО,Должность,Отдел,Телефон,Email\n"
            "Петров Пётр,Разработчик,IT,+7900456,petrov@test.ru\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "сотрудник", csv_path)
        assert count == 1
        target_dir = tmp_vault / "04-СОТРУДНИКИ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 1

    def test_missing_title_row_skipped(self, tmp_vault: Path) -> None:
        """Rows without a title/name should be skipped."""
        csv_path = tmp_vault / "no_title.csv"
        csv_path.write_text(
            "Название,ИНН,Категория,Статус\n"
            ",1234567890,клиент,активный\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", csv_path)
        assert count == 0

    def test_existing_file_skipped(self, tmp_vault: Path) -> None:
        """If a file already exists, the row should be skipped."""
        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        target_dir.mkdir(parents=True, exist_ok=True)
        existing = target_dir / "ООО ТестКомпания.md"
        existing.write_text("---\ntitle: existing\n---\n", encoding="utf-8")

        csv_path = FIXTURES_DIR / "sample.csv"
        count = import_csv(tmp_vault, "контрагент", csv_path)
        # Only 2 should be created; ООО ТестКомпания already exists
        assert count == 2

    def test_unrecognized_columns_ignored(self, tmp_vault: Path) -> None:
        """Columns not in the mapping should be silently ignored."""
        csv_path = tmp_vault / "extra_cols.csv"
        csv_path.write_text(
            "Название,ИНН,НеизвестнаяКолонка,Статус\n"
            "ООО Тест,1111111111,значение,активный\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", csv_path)
        assert count == 1

    def test_no_mappable_columns(self, tmp_vault: Path) -> None:
        """If no columns can be mapped, import should return 0."""
        csv_path = tmp_vault / "bad_headers.csv"
        csv_path.write_text(
            "Foo,Bar,Baz\n"
            "a,b,c\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", csv_path)
        assert count == 0

    def test_existing_inn_in_vault_skipped(self, tmp_vault: Path) -> None:
        """If an INN already exists in vault .md files, the row is skipped."""
        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        target_dir.mkdir(parents=True, exist_ok=True)
        existing = target_dir / "Existing.md"
        existing.write_text(
            "---\ntitle: \"Existing\"\nинн: \"9999999999\"\n---\n",
            encoding="utf-8",
        )

        csv_path = tmp_vault / "dup_inn_vault.csv"
        csv_path.write_text(
            "Название,ИНН,Категория\n"
            "Новая Компания,9999999999,клиент\n",
            encoding="utf-8",
        )
        count = import_csv(tmp_vault, "контрагент", csv_path)
        assert count == 0


# -----------------------------------------------------------------------
# NEW TESTS: map_columns, parse_frontmatter, _safe_filename, _build_*
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestMapColumns:
    def test_maps_known_columns(self):
        from scripts.import_csv import map_columns, _COUNTERPARTY_COL_MAP
        headers = ["Название", "ИНН", "Статус"]
        result = map_columns(headers, _COUNTERPARTY_COL_MAP)
        assert result["Название"] == "title"
        assert result["ИНН"] == "инн"
        assert result["Статус"] == "статус"

    def test_unknown_columns_not_mapped(self):
        from scripts.import_csv import map_columns, _COUNTERPARTY_COL_MAP
        headers = ["FooBar", "BazQux"]
        result = map_columns(headers, _COUNTERPARTY_COL_MAP)
        assert len(result) == 0

    def test_case_insensitive_matching(self):
        from scripts.import_csv import map_columns, _CONTACT_COL_MAP
        headers = ["ФИО", "Email", "Телефон"]
        result = map_columns(headers, _CONTACT_COL_MAP)
        assert len(result) == 3


@pytest.mark.unit
class TestParseFrontmatterCsv:
    def test_valid_frontmatter(self):
        from scripts.import_csv import parse_frontmatter
        text = '---\ntitle: "Test"\nинн: "123"\n---\nBody'
        fm = parse_frontmatter(text)
        assert fm["title"] == "Test"
        assert fm["инн"] == "123"

    def test_no_frontmatter(self):
        from scripts.import_csv import parse_frontmatter
        text = "No frontmatter here"
        fm = parse_frontmatter(text)
        assert fm == {}


@pytest.mark.unit
class TestSafeFilename:
    def test_removes_special_chars(self):
        from scripts.import_csv import _safe_filename
        assert _safe_filename('ООО "Тест"') == "ООО Тест"
        assert _safe_filename("Test<>:file") == "Testfile"


@pytest.mark.unit
class TestCollectExistingKeys:
    def test_collects_inn_from_notes(self, tmp_vault: Path):
        from scripts.import_csv import collect_existing_keys
        target = tmp_vault / "01-КОНТРАГЕНТЫ"
        target.mkdir(parents=True, exist_ok=True)
        note = target / "Test.md"
        note.write_text('---\nинн: "123456"\n---\n', encoding="utf-8")

        keys = collect_existing_keys(tmp_vault, "01-КОНТРАГЕНТЫ", "инн")
        assert "123456" in keys

    def test_none_key_returns_empty(self, tmp_vault: Path):
        from scripts.import_csv import collect_existing_keys
        keys = collect_existing_keys(tmp_vault, "01-КОНТРАГЕНТЫ", None)
        assert keys == set()

    def test_missing_folder_returns_empty(self, tmp_vault: Path):
        from scripts.import_csv import collect_existing_keys
        keys = collect_existing_keys(tmp_vault, "NONEXISTENT", "инн")
        assert keys == set()


# -----------------------------------------------------------------------
# NEW TESTS: main() and parse_args()
# -----------------------------------------------------------------------

@pytest.mark.unit
class TestImportCsvMain:
    def test_main_runs_import(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        csv_path = FIXTURES_DIR / "sample.csv"
        with patch.object(sys, "argv", [
            "import_csv",
            "--vault", str(tmp_vault),
            "--type", "контрагент",
            "--file", str(csv_path),
        ]):
            from scripts.import_csv import main
            main()  # Should not raise

        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 3

    def test_main_dry_run(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        csv_path = FIXTURES_DIR / "sample.csv"
        with patch.object(sys, "argv", [
            "import_csv",
            "--vault", str(tmp_vault),
            "--type", "контрагент",
            "--file", str(csv_path),
            "--dry-run",
        ]):
            from scripts.import_csv import main
            main()

        target_dir = tmp_vault / "01-КОНТРАГЕНТЫ"
        created = list(target_dir.glob("*.md"))
        assert len(created) == 0

    def test_main_vault_not_found(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "import_csv",
            "--vault", str(tmp_path / "nonexistent"),
            "--type", "контрагент",
            "--file", str(FIXTURES_DIR / "sample.csv"),
        ]):
            from scripts.import_csv import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_file_not_found(self, tmp_vault: Path) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [
            "import_csv",
            "--vault", str(tmp_vault),
            "--type", "контрагент",
            "--file", str(tmp_vault / "nonexistent.csv"),
        ]):
            from scripts.import_csv import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_parse_args_verbose(self) -> None:
        from scripts.import_csv import parse_args
        args = parse_args([
            "--vault", "/tmp/v",
            "--type", "контрагент",
            "--file", "/tmp/f.csv",
            "--verbose",
        ])
        assert args.verbose is True
        assert args.note_type == "контрагент"
