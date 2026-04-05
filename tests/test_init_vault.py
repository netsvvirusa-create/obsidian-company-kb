"""Integration tests for init_vault.sh script."""

import subprocess
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
INIT_SCRIPT = PROJECT_ROOT / "scripts" / "init_vault.sh"

EXPECTED_FOLDERS = [
    "00-INBOX",
    "01-КОНТРАГЕНТЫ",
    "02-ДОГОВОРЫ",
    "03-ПРОЕКТЫ",
    "04-СОТРУДНИКИ",
    "05-КОНТАКТЫ",
    "06-ПЕРЕГОВОРЫ",
    "07-ОПЕРАЦИИ",
    "08-КАЛЕНДАРЬ",
    "09-СТРАТЕГИЯ/Цели",
    "09-СТРАТЕГИЯ/Идеи",
    "09-СТРАТЕГИЯ/Ретроспективы",
    "10-ФИНАНСЫ",
    "11-БАЗЫ",
    "12-КАНВАСЫ",
    "13-ШАБЛОНЫ",
    "14-ВЛОЖЕНИЯ/Фото сотрудников",
    "14-ВЛОЖЕНИЯ/Фото контактов",
    "14-ВЛОЖЕНИЯ/Документы",
    "99-АРХИВ",
]

MOC_FOLDERS = [
    "01-КОНТРАГЕНТЫ",
    "02-ДОГОВОРЫ",
    "03-ПРОЕКТЫ",
    "04-СОТРУДНИКИ",
    "05-КОНТАКТЫ",
    "06-ПЕРЕГОВОРЫ",
    "07-ОПЕРАЦИИ",
    "09-СТРАТЕГИЯ",
]


def _run_init(vault_path: Path) -> subprocess.CompletedProcess:
    """Run init_vault.sh on the given vault path."""
    return subprocess.run(
        ["bash", str(INIT_SCRIPT), str(vault_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.integration
class TestInitVault:
    """Integration tests for vault initialization script."""

    def test_folders_are_created(self, tmp_path: Path):
        vault = tmp_path / "vault"
        vault.mkdir()
        result = _run_init(vault)
        assert result.returncode == 0, f"init_vault.sh failed:\n{result.stderr}"

        for folder in EXPECTED_FOLDERS:
            assert (vault / folder).is_dir(), f"Folder not created: {folder}"

    def test_repeated_init_is_safe(self, tmp_path: Path):
        vault = tmp_path / "vault"
        vault.mkdir()

        result1 = _run_init(vault)
        assert result1.returncode == 0, f"First run failed:\n{result1.stderr}"

        result2 = _run_init(vault)
        assert result2.returncode == 0, f"Second run failed:\n{result2.stderr}"

        for folder in EXPECTED_FOLDERS:
            assert (vault / folder).is_dir(), f"Folder missing after second run: {folder}"

    def test_moc_files_created(self, tmp_path: Path):
        vault = tmp_path / "vault"
        vault.mkdir()
        result = _run_init(vault)
        assert result.returncode == 0, f"init_vault.sh failed:\n{result.stderr}"

        for folder in MOC_FOLDERS:
            moc_path = vault / folder / "_MOC.md"
            assert moc_path.exists(), f"MOC not created: {folder}/_MOC.md"

            text = moc_path.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            assert len(parts) >= 3, f"MOC {folder}/_MOC.md has no YAML frontmatter"

            fm = yaml.safe_load(parts[1])
            assert fm.get("type") == "moc", (
                f"MOC {folder}/_MOC.md: type must be 'moc', got {fm.get('type')!r}"
            )
            assert "title" in fm, f"MOC {folder}/_MOC.md: missing 'title' field"

    def test_base_files_copied(self, tmp_path: Path):
        vault = tmp_path / "vault"
        vault.mkdir()
        result = _run_init(vault)
        assert result.returncode == 0, f"init_vault.sh failed:\n{result.stderr}"

        bases_src = PROJECT_ROOT / "assets" / "vault-init" / "bases"
        bases_dst = vault / "11-БАЗЫ"

        for base_file in bases_src.glob("*.base"):
            copied = bases_dst / base_file.name
            assert copied.exists(), f".base file not copied: {base_file.name}"
            # Verify contents match
            assert copied.read_bytes() == base_file.read_bytes(), (
                f".base file content mismatch: {base_file.name}"
            )
