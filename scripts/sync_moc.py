"""Синхронизация MOC (Map of Content) индексных заметок.

Сканирует папки vault, сравнивает содержимое _MOC.md с реальными
заметками и обновляет при необходимости.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Извлекает YAML-свойства из frontmatter, разделённого ``---``.

    Args:
        text: Полный текст .md-файла.

    Returns:
        Словарь ключ-значение из frontmatter.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: Dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            result[key] = val
    return result


def _extract_existing_links(moc_text: str) -> Set[str]:
    """Извлекает все wikilinks из секции ``## Содержимое`` MOC-файла.

    Args:
        moc_text: Полный текст _MOC.md.

    Returns:
        Множество имён ссылок (без ``[[`` / ``]]``).
    """
    links: Set[str] = set()
    # Ищем секцию ## Содержимое
    match = re.search(r"^##\s+Содержимое\s*$", moc_text, re.MULTILINE)
    if not match:
        # Собираем ссылки из всего файла
        for m in re.finditer(r"\[\[([^\]|#]+?)(?:\|[^\]]*?)?\]\]", moc_text):
            links.add(m.group(1))
        return links
    section_start = match.end()
    # Ограничиваем до следующего заголовка первого/второго уровня
    next_h = re.search(r"^#{1,2}\s+", moc_text[section_start:], re.MULTILINE)
    section = moc_text[section_start : section_start + next_h.start()] if next_h else moc_text[section_start:]
    for m in re.finditer(r"\[\[([^\]|#]+?)(?:\|[^\]]*?)?\]\]", section):
        links.add(m.group(1))
    return links


def _scan_folder_notes(folder: Path) -> List[Tuple[str, str, str]]:
    """Сканирует все .md-файлы в папке (исключая _MOC.md).

    Args:
        folder: Путь к папке.

    Returns:
        Список кортежей (имя_файла_без_расширения, title, статус).
    """
    notes: List[Tuple[str, str, str]] = []
    for md in sorted(folder.glob("*.md")):
        if md.name == "_MOC.md":
            continue
        if md.name.startswith("_"):
            continue
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        stem = md.stem
        title = fm.get("title", stem)
        status = fm.get("статус", "")
        notes.append((stem, title, status))
    return notes


def _group_by_status(
    notes: List[Tuple[str, str, str]],
) -> Dict[str, List[Tuple[str, str]]]:
    """Группирует заметки по статусу.

    Args:
        notes: Список кортежей (stem, title, статус).

    Returns:
        Словарь {группа: [(stem, title), ...]}.
    """
    groups: Dict[str, List[Tuple[str, str]]] = {}

    status_to_group = {
        "активный": "Активные",
        "активная": "Активные",
        "в работе": "Активные",
        "запланирован": "Активные",
        "запланирована": "Активные",
        "черновик": "Активные",
        "на паузе": "Активные",
        "завершён": "Завершённые",
        "завершена": "Завершённые",
        "закрыт": "Завершённые",
        "закрыта": "Завершённые",
        "отменён": "Завершённые",
        "отменена": "Завершённые",
        "архив": "Завершённые",
    }

    for stem, title, status in notes:
        group_name = status_to_group.get(status.lower(), "Активные") if status else "Активные"
        groups.setdefault(group_name, []).append((stem, title))

    # Сортировка внутри групп по алфавиту
    for group in groups:
        groups[group].sort(key=lambda x: x[1].lower())

    return groups


def _build_moc_content(folder_name: str, notes: List[Tuple[str, str, str]]) -> str:
    """Строит содержимое _MOC.md файла.

    Args:
        folder_name: Название папки для заголовка.
        notes: Список кортежей (stem, title, статус).

    Returns:
        Полный текст _MOC.md.
    """
    today_str = date.today().isoformat()
    groups = _group_by_status(notes)

    # Определяем порядок групп: сначала Активные, потом Завершённые, потом остальные
    group_order = ["Активные", "Завершённые"]
    all_groups = list(groups.keys())
    ordered = [g for g in group_order if g in all_groups]
    ordered += [g for g in sorted(all_groups) if g not in ordered]

    lines: List[str] = [
        "---",
        f'title: "MOC: {folder_name}"',
        "type: moc",
        "tags:",
        "  - тип/moc",
        "---",
        "",
        f"# {folder_name}",
        "",
        "> [!info] Карта содержимого",
        f"> Автоматически обновлено: {today_str}",
        "",
        "## Содержимое",
        "",
    ]

    for group_name in ordered:
        items = groups[group_name]
        lines.append(f"### {group_name}")
        for stem, title in items:
            lines.append(f"- [[{stem}]]")
        lines.append("")

    return "\n".join(lines)


def _update_moc_section(existing_text: str, folder_name: str, notes: List[Tuple[str, str, str]]) -> str:
    """Обновляет только секцию ``## Содержимое`` в существующем MOC.

    Args:
        existing_text: Текущий текст _MOC.md.
        folder_name: Название папки.
        notes: Список заметок.

    Returns:
        Обновлённый текст _MOC.md.
    """
    today_str = date.today().isoformat()
    groups = _group_by_status(notes)

    group_order = ["Активные", "Завершённые"]
    all_groups = list(groups.keys())
    ordered = [g for g in group_order if g in all_groups]
    ordered += [g for g in sorted(all_groups) if g not in ordered]

    # Строим новую секцию
    new_section_lines: List[str] = ["## Содержимое", ""]
    for group_name in ordered:
        items = groups[group_name]
        new_section_lines.append(f"### {group_name}")
        for stem, title in items:
            new_section_lines.append(f"- [[{stem}]]")
        new_section_lines.append("")
    new_section = "\n".join(new_section_lines)

    # Ищем существующую секцию ## Содержимое
    match = re.search(r"^##\s+Содержимое\s*$", existing_text, re.MULTILINE)
    if not match:
        # Если секции нет, добавляем в конец
        return existing_text.rstrip() + "\n\n" + new_section

    section_start = match.start()
    # Ищем следующий заголовок ## (не ###)
    rest = existing_text[match.end():]
    next_h = re.search(r"^##\s+(?!#)", rest, re.MULTILINE)
    if next_h:
        section_end = match.end() + next_h.start()
        return existing_text[:section_start] + new_section + existing_text[section_end:]

    # Секция идёт до конца файла
    # Обновляем также дату в info-блоке
    updated = existing_text[:section_start] + new_section
    updated = re.sub(
        r"(>\s*Автоматически обновлено:\s*)\d{4}-\d{2}-\d{2}",
        rf"\g<1>{today_str}",
        updated,
    )
    return updated


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------


def sync_moc(
    vault: Path,
    folder_filter: Optional[str] = None,
    dry_run: bool = False,
    fix: bool = False,
) -> Dict[str, Any]:
    """Синхронизирует MOC-файлы с содержимым папок vault.

    Args:
        vault: Путь к vault.
        folder_filter: Если указано, обрабатывать только эту папку.
        dry_run: Только отчёт без изменений.
        fix: Применить исправления.

    Returns:
        Словарь с результатами синхронизации.
    """
    stats: Dict[str, Any] = {
        "folders_checked": 0,
        "notes_indexed": 0,
        "updates_needed": 0,
        "updates_applied": 0,
    }

    # Находим все папки с _MOC.md
    folders_to_check: List[Path] = []
    if folder_filter:
        target = vault / folder_filter
        if target.is_dir() and (target / "_MOC.md").exists():
            folders_to_check.append(target)
        elif target.is_dir():
            # Папка существует, но без MOC -- если --fix, создадим
            if fix:
                folders_to_check.append(target)
            else:
                logger.warning("В папке %s нет _MOC.md", folder_filter)
    else:
        for item in sorted(vault.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                moc_file = item / "_MOC.md"
                if moc_file.exists():
                    folders_to_check.append(item)
                # Также проверяем подпапки (например, 09-СТРАТЕГИЯ/Цели)
                for sub in sorted(item.iterdir()):
                    if sub.is_dir():
                        sub_moc = sub / "_MOC.md"
                        if sub_moc.exists():
                            folders_to_check.append(sub)

    for folder in folders_to_check:
        stats["folders_checked"] += 1
        moc_file = folder / "_MOC.md"
        folder_name = folder.name

        notes = _scan_folder_notes(folder)
        stats["notes_indexed"] += len(notes)

        note_stems: Set[str] = {stem for stem, _, _ in notes}

        if moc_file.exists():
            moc_text = moc_file.read_text(encoding="utf-8")
            existing_links = _extract_existing_links(moc_text)
        else:
            moc_text = ""
            existing_links = set()

        # Сравниваем
        new_notes = note_stems - existing_links
        removed_notes = existing_links - note_stems

        if new_notes or removed_notes:
            stats["updates_needed"] += 1

            if new_notes:
                logger.info(
                    "[%s] Новые заметки не в MOC (%d): %s",
                    folder_name, len(new_notes), ", ".join(sorted(new_notes)),
                )
            if removed_notes:
                logger.info(
                    "[%s] Удалённые заметки ещё в MOC (%d): %s",
                    folder_name, len(removed_notes), ", ".join(sorted(removed_notes)),
                )

            if fix and not dry_run:
                if moc_file.exists():
                    updated = _update_moc_section(moc_text, folder_name, notes)
                else:
                    updated = _build_moc_content(folder_name, notes)
                moc_file.write_text(updated, encoding="utf-8")
                stats["updates_applied"] += 1
                logger.info("[%s] MOC обновлён: %s", folder_name, moc_file)
        else:
            logger.debug("[%s] MOC актуален.", folder_name)

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки.

    Args:
        argv: Список аргументов (по умолчанию sys.argv).

    Returns:
        Пространство имён с разобранными аргументами.
    """
    parser = argparse.ArgumentParser(
        description="Синхронизация MOC (Map of Content) индексных заметок.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--folder", type=str, default=None,
        help="Обработать только указанную папку.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Только отчёт без изменений.",
    )
    parser.add_argument(
        "--fix", action="store_true", default=False,
        help="Применить исправления к _MOC.md.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        help="Подробный вывод (DEBUG).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Точка входа CLI."""
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    if not args.vault.is_dir():
        logger.error("Vault не найден: %s", args.vault)
        sys.exit(1)

    stats = sync_moc(
        vault=args.vault,
        folder_filter=args.folder,
        dry_run=args.dry_run,
        fix=args.fix,
    )

    sys.stdout.write(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
