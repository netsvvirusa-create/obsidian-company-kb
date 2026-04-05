#!/usr/bin/env python3
"""Массовое обновление статуса заметок в Obsidian vault.

Находит заметки в указанной папке, обновляет поле ``статус`` в YAML
frontmatter, при необходимости перемещает в ``99-АРХИВ/``, записывает
изменения в секцию «История изменений».
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ARCHIVE_STATUSES = {"завершён", "отменён"}


# ---------------------------------------------------------------------------
# Парсинг frontmatter
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict[str, Any]:
    """Извлекает YAML-свойства из frontmatter, разделённого ``---``.

    Args:
        text: Полный текст .md-файла.

    Returns:
        Словарь ключ-значение из frontmatter.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


# ---------------------------------------------------------------------------
# Обновление статуса в frontmatter
# ---------------------------------------------------------------------------

def update_status_in_text(text: str, new_status: str) -> str:
    """Обновляет поле ``статус`` в frontmatter текста .md.

    Args:
        text: Полный текст файла.
        new_status: Новое значение статуса.

    Returns:
        Обновлённый текст.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text

    fm_lines = parts[1].splitlines()
    updated_lines: list[str] = []
    status_found = False

    for line in fm_lines:
        if line.strip().startswith("статус:"):
            updated_lines.append(f"статус: {new_status}")
            status_found = True
        elif line.strip().startswith("- статус/"):
            updated_lines.append(f"  - статус/{new_status}")
        else:
            updated_lines.append(line)

    if not status_found:
        # Добавляем статус перед tags если его нет
        updated_lines.append(f"статус: {new_status}")

    return f"---{''.join(chr(10) + l for l in updated_lines)}\n---{parts[2]}"


def add_history_entry(text: str, entry: str) -> str:
    """Добавляет запись в секцию «История изменений» если она существует.

    Args:
        text: Полный текст файла.
        entry: Строка для добавления (без ``- ``).

    Returns:
        Обновлённый текст.
    """
    # Ищем секцию "## История изменений"
    marker = "## История изменений"
    if marker not in text:
        return text

    idx = text.index(marker)
    after_marker = text[idx + len(marker):]

    # Находим конец секции (следующий ## или конец файла)
    next_section = re.search(r"\n## ", after_marker)
    if next_section:
        insert_pos = idx + len(marker) + next_section.start()
    else:
        insert_pos = len(text)

    # Добавляем запись перед концом секции
    new_entry = f"\n- {entry}"
    return text[:insert_pos] + new_entry + text[insert_pos:]


# ---------------------------------------------------------------------------
# Фильтрация заметок
# ---------------------------------------------------------------------------

def matches_filter(fm: dict[str, Any], filter_expr: str) -> bool:
    """Проверяет, соответствует ли frontmatter фильтру ``key:value``.

    Args:
        fm: Словарь frontmatter.
        filter_expr: Выражение вида ``ключ:значение``.

    Returns:
        ``True`` если совпадает.
    """
    if ":" not in filter_expr:
        logger.warning("Некорректный фильтр: '%s'. Ожидается формат 'ключ:значение'.", filter_expr)
        return False
    key, _, value = filter_expr.partition(":")
    key = key.strip()
    value = value.strip().lower()
    fm_value = str(fm.get(key, "")).lower()
    return value in fm_value


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def bulk_status_update(
    vault: Path,
    folder: str,
    new_status: str,
    filter_expr: str = "",
) -> int:
    """Массово обновляет статус заметок в указанной папке.

    Args:
        vault: Путь к vault.
        folder: Относительный путь папки в vault.
        new_status: Новый статус.
        filter_expr: Фильтр ``ключ:значение`` (необязательный).

    Returns:
        Количество обновлённых файлов.
    """
    today = date.today().isoformat()
    target_dir = vault / folder

    if not target_dir.is_dir():
        logger.error("Папка не найдена: %s", target_dir)
        return 0

    # Определяем, нужна ли архивация
    need_archive = new_status in _ARCHIVE_STATUSES
    # Проверяем, не в архиве ли уже
    folder_parts = Path(folder).parts
    in_archive = any(p.startswith("99-АРХИВ") for p in folder_parts)

    updated = 0

    for md in sorted(target_dir.glob("*.md")):
        if md.name.startswith("_"):
            continue  # Пропускаем MOC и служебные

        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)

        # Применяем фильтр
        if filter_expr and not matches_filter(fm, filter_expr):
            continue

        old_status = fm.get("статус", "")
        if old_status == new_status:
            logger.debug("Пропуск '%s': статус уже '%s'.", md.name, new_status)
            continue

        # Обновляем статус
        new_text = update_status_in_text(text, new_status)

        # Добавляем запись в историю
        history_note = f"{today} — Статус изменён: {old_status} → {new_status}"
        new_text = add_history_entry(new_text, history_note)

        # Определяем конечный путь
        if need_archive and not in_archive:
            # Имя оригинальной папки (без номера-префикса для вложенности)
            original_folder_name = Path(folder).name
            archive_dir = vault / "99-АРХИВ" / original_folder_name
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / md.name
        else:
            dest = md

        # Записываем
        if dest != md:
            dest.write_text(new_text, encoding="utf-8")
            md.unlink()
            logger.info(
                "Обновлён и перемещён: %s → %s",
                md.relative_to(vault),
                dest.relative_to(vault),
            )
        else:
            md.write_text(new_text, encoding="utf-8")
            logger.info("Обновлён: %s", md.relative_to(vault))

        updated += 1

    return updated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки.

    Args:
        argv: Список аргументов.

    Returns:
        Пространство имён с разобранными аргументами.
    """
    parser = argparse.ArgumentParser(
        description="Массовое обновление статуса заметок в Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--folder", required=True,
        help="Относительный путь папки в vault (например, 02-ДОГОВОРЫ).",
    )
    parser.add_argument(
        "--status", required=True,
        help="Новый статус (например, завершён, отменён, активный, приостановлен).",
    )
    parser.add_argument(
        "--filter", dest="filter_expr", default="",
        help='Фильтр "ключ:значение" для выбора заметок (например, "категория:клиент").',
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
    )

    if not args.vault.is_dir():
        logger.error("Vault не найден: %s", args.vault)
        sys.exit(1)

    count = bulk_status_update(
        args.vault,
        args.folder,
        args.status,
        args.filter_expr,
    )
    logger.info("Итого обновлено файлов: %d", count)


if __name__ == "__main__":
    main()
