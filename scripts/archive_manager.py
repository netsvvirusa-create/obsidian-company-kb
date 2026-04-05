#!/usr/bin/env python3
"""Управление архивом Obsidian vault.

Подкоманды:
- scan: поиск кандидатов на архивацию.
- archive: перемещение заметок в архив с обновлением frontmatter.
- report: отчёт по содержимому архива.

Архив размещается в папке 99-АРХИВ/ с подпапками по исходным директориям.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

ARCHIVE_DIR = "99-АРХИВ"

ARCHIVABLE_CONTRACT_STATUSES = ("завершён", "отменён")
ARCHIVABLE_PROJECT_STATUSES = ("завершён", "отменён")
EVENT_AGE_DAYS = 90

FOLDER_TYPE_MAP: dict[str, str] = {
    "02-ДОГОВОРЫ": "договор",
    "03-ПРОЕКТЫ": "проект",
    "08-ЦЕЛИ": "цель",
    "07-СОБЫТИЯ": "событие",
}


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
    stripped = text.lstrip("\ufeff").lstrip()
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            result[key] = val
    return result


def _update_frontmatter_field(text: str, key: str, value: str) -> str:
    """Добавляет или обновляет поле в frontmatter.

    Args:
        text: Полный текст .md-файла.
        key: Ключ поля.
        value: Новое значение.

    Returns:
        Обновлённый текст файла.
    """
    stripped = text.lstrip("\ufeff").lstrip()
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return text

    fm_lines = parts[1].strip().splitlines()
    found = False
    new_lines: list[str] = []

    for line in fm_lines:
        if ":" in line:
            k, _, _ = line.partition(":")
            if k.strip() == key:
                new_lines.append(f"{key}: {value}")
                found = True
                continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{key}: {value}")

    return f"---\n" + "\n".join(new_lines) + "\n---" + parts[2]


def _append_history(text: str, entry: str) -> str:
    """Добавляет запись в секцию '## История изменений', если она существует.

    Args:
        text: Полный текст .md-файла.
        entry: Текст записи для добавления.

    Returns:
        Обновлённый текст файла.
    """
    marker = "## История изменений"
    if marker not in text:
        return text

    lines = text.splitlines()
    result: list[str] = []
    inserted = False

    for i, line in enumerate(lines):
        result.append(line)
        if not inserted and line.strip() == marker:
            # Вставляем после заголовка (с пустой строкой)
            if i + 1 < len(lines) and lines[i + 1].strip() == "":
                result.append("")
                result.append(f"- {entry}")
                inserted = True
            else:
                result.append(f"- {entry}")
                inserted = True

    if not inserted:
        # Если заголовок последний — просто добавляем
        result.append(f"- {entry}")

    return "\n".join(result)


def _parse_date(val: str) -> date | None:
    """Пытается разобрать дату из строки ISO.

    Args:
        val: Строковое представление даты.

    Returns:
        Объект ``date`` или ``None``.
    """
    try:
        return date.fromisoformat(val.strip())
    except (ValueError, AttributeError):
        return None


def _parse_filter(expr: str) -> tuple[str, str]:
    """Разбирает выражение фильтра вида ``ключ:значение``.

    Args:
        expr: Строка фильтра.

    Returns:
        Кортеж (ключ, значение).

    Raises:
        ValueError: Если формат некорректен.
    """
    if ":" not in expr:
        raise ValueError(f"Некорректный формат фильтра: '{expr}'. Ожидается 'ключ:значение'.")
    key, _, val = expr.partition(":")
    return key.strip(), val.strip()


def _read_notes(vault: Path, folder: str) -> list[tuple[Path, str, dict[str, Any]]]:
    """Читает все .md-файлы из подпапки vault.

    Args:
        vault: Путь к vault.
        folder: Имя подпапки.

    Returns:
        Список кортежей (путь, текст, frontmatter).
    """
    target = vault / folder
    if not target.exists():
        return []
    notes: list[tuple[Path, str, dict[str, Any]]] = []
    for md in sorted(target.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        notes.append((md, text, fm))
    return notes


# ---------------------------------------------------------------------------
# scan: поиск кандидатов
# ---------------------------------------------------------------------------


def scan_candidates(vault: Path) -> list[dict[str, Any]]:
    """Сканирует vault и возвращает список кандидатов на архивацию.

    Правила:
    - Договоры: статус in (завершён, отменён).
    - Проекты: статус in (завершён, отменён).
    - Цели: статус == завершён AND дедлайн < сегодня.
    - События: старше 90 дней.

    Args:
        vault: Путь к vault.

    Returns:
        Список словарей-кандидатов.
    """
    today = date.today()
    candidates: list[dict[str, Any]] = []

    # Договоры
    for path, text, fm in _read_notes(vault, "02-ДОГОВОРЫ"):
        status = fm.get("статус", "")
        if status.lower() in ARCHIVABLE_CONTRACT_STATUSES:
            candidates.append({
                "file": str(path.relative_to(vault)),
                "type": "договор",
                "reason": f"Статус: {status}",
                "status": status,
                "date": fm.get("дата_окончания", fm.get("дата_подписания", "")),
            })

    # Проекты
    for path, text, fm in _read_notes(vault, "03-ПРОЕКТЫ"):
        status = fm.get("статус", "")
        if status.lower() in ARCHIVABLE_PROJECT_STATUSES:
            candidates.append({
                "file": str(path.relative_to(vault)),
                "type": "проект",
                "reason": f"Статус: {status}",
                "status": status,
                "date": fm.get("дата_окончания", fm.get("дата_начала", "")),
            })

    # Цели
    for path, text, fm in _read_notes(vault, "08-ЦЕЛИ"):
        status = fm.get("статус", "")
        deadline_str = fm.get("дедлайн", "")
        deadline = _parse_date(deadline_str)
        if status.lower() == "завершён" and deadline is not None and deadline < today:
            candidates.append({
                "file": str(path.relative_to(vault)),
                "type": "цель",
                "reason": f"Завершена, дедлайн {deadline_str} истёк",
                "status": status,
                "date": deadline_str,
            })

    # События
    for path, text, fm in _read_notes(vault, "07-СОБЫТИЯ"):
        event_date_str = fm.get("дата", "")
        event_date = _parse_date(event_date_str)
        if event_date is not None and (today - event_date).days > EVENT_AGE_DAYS:
            age = (today - event_date).days
            candidates.append({
                "file": str(path.relative_to(vault)),
                "type": "событие",
                "reason": f"Старше {EVENT_AGE_DAYS} дней ({age} дн.)",
                "status": fm.get("статус", ""),
                "date": event_date_str,
            })

    logger.info("Найдено кандидатов на архивацию: %d", len(candidates))
    return candidates


# ---------------------------------------------------------------------------
# archive: перемещение в архив
# ---------------------------------------------------------------------------


def _move_to_archive(vault: Path, note_path: Path, reason: str) -> Path:
    """Перемещает заметку в архив и обновляет frontmatter.

    Args:
        vault: Путь к vault.
        note_path: Путь к исходной заметке.
        reason: Причина архивации.

    Returns:
        Путь к перемещённому файлу.
    """
    today_str = date.today().isoformat()

    # Определяем исходную папку
    try:
        rel = note_path.relative_to(vault)
        original_folder = rel.parts[0] if len(rel.parts) > 1 else "Разное"
    except ValueError:
        original_folder = "Разное"

    # Целевая директория
    dest_dir = vault / ARCHIVE_DIR / original_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / note_path.name

    # Обработка конфликта имён
    if dest_path.exists():
        stem = note_path.stem
        suffix = note_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    # Читаем и обновляем содержимое
    text = note_path.read_text(encoding="utf-8")
    text = _update_frontmatter_field(text, "архивирован", today_str)
    text = _append_history(text, f"{today_str} — Архивировано. Причина: {reason}")

    # Записываем в новое место
    dest_path.write_text(text, encoding="utf-8")

    # Удаляем оригинал
    note_path.unlink()

    logger.info("Перемещено: %s -> %s", note_path, dest_path)
    return dest_path


def archive_notes(
    vault: Path,
    folder: str | None = None,
    filter_expr: str | None = None,
    days_old: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Архивирует заметки, соответствующие критериям.

    Args:
        vault: Путь к vault.
        folder: Конкретная папка для сканирования (опционально).
        filter_expr: Фильтр вида ``ключ:значение`` (опционально).
        days_old: Минимальный возраст файла в днях (опционально).
        dry_run: Если ``True``, только отчёт без перемещения.

    Returns:
        Словарь с результатами: ``{"moved": [...], "skipped": [...], "errors": [...]}``.
    """
    candidates = scan_candidates(vault)
    today = date.today()

    # Фильтрация по папке
    if folder:
        candidates = [c for c in candidates if c["file"].startswith(folder)]

    # Фильтрация по выражению
    if filter_expr:
        fkey, fval = _parse_filter(filter_expr)
        candidates = [c for c in candidates if c.get(fkey, "").lower() == fval.lower()]

    result: dict[str, Any] = {"moved": [], "skipped": [], "errors": []}

    for candidate in candidates:
        note_path = vault / candidate["file"]

        if not note_path.exists():
            result["errors"].append({"file": candidate["file"], "error": "Файл не найден"})
            continue

        # Фильтрация по возрасту файла
        if days_old is not None:
            mtime = datetime.fromtimestamp(note_path.stat().st_mtime).date()
            age = (today - mtime).days
            if age < days_old:
                result["skipped"].append({
                    "file": candidate["file"],
                    "reason": f"Возраст {age} дн. < {days_old} дн.",
                })
                continue

        if dry_run:
            result["moved"].append({
                "file": candidate["file"],
                "reason": candidate["reason"],
                "dry_run": True,
            })
            logger.info("[DRY-RUN] Будет перемещено: %s (%s)", candidate["file"], candidate["reason"])
        else:
            try:
                dest = _move_to_archive(vault, note_path, candidate["reason"])
                result["moved"].append({
                    "file": candidate["file"],
                    "destination": str(dest.relative_to(vault)),
                    "reason": candidate["reason"],
                })
            except Exception as exc:
                result["errors"].append({
                    "file": candidate["file"],
                    "error": str(exc),
                })
                logger.error("Ошибка при архивации %s: %s", candidate["file"], exc)

    logger.info(
        "Итого: перемещено %d, пропущено %d, ошибок %d",
        len(result["moved"]),
        len(result["skipped"]),
        len(result["errors"]),
    )
    return result


# ---------------------------------------------------------------------------
# report: отчёт по архиву
# ---------------------------------------------------------------------------


def archive_report(vault: Path) -> str:
    """Генерирует Markdown-отчёт о содержимом архива.

    Args:
        vault: Путь к vault.

    Returns:
        Markdown-текст отчёта.
    """
    archive_path = vault / ARCHIVE_DIR
    today = date.today()

    if not archive_path.exists():
        return f"# Отчёт: Архив\n\n**Дата:** {today.isoformat()}\n\n> Папка архива не найдена.\n"

    # Подсчёт по подпапкам
    folder_counts: dict[str, int] = {}
    total = 0
    recent_dates: list[tuple[str, str]] = []  # (файл, дата_архивации)

    for subfolder in sorted(archive_path.iterdir()):
        if not subfolder.is_dir():
            continue
        folder_name = subfolder.name
        md_files = list(subfolder.glob("*.md"))
        count = len(md_files)
        folder_counts[folder_name] = count
        total += count

        # Ищем даты архивации
        for md in md_files:
            try:
                text = md.read_text(encoding="utf-8")
                fm = parse_frontmatter(text)
                arch_date = fm.get("архивирован", "")
                if arch_date:
                    rel = md.relative_to(vault)
                    recent_dates.append((str(rel), arch_date))
            except Exception:
                pass

    # Сортируем по дате (последние первыми)
    recent_dates.sort(key=lambda x: x[1], reverse=True)

    lines: list[str] = [
        f"# Отчёт: Архив",
        f"",
        f"**Дата отчёта:** {today.isoformat()}",
        f"**Всего архивных заметок:** {total}",
        f"",
        f"## Содержимое по папкам",
        f"",
    ]

    if folder_counts:
        lines.append("| Папка | Количество файлов |")
        lines.append("|-------|-------------------|")
        for folder_name, count in folder_counts.items():
            lines.append(f"| {folder_name} | {count} |")
    else:
        lines.append("> Архив пуст.")

    lines += [
        f"",
        f"## Последние архивации",
        f"",
    ]

    top_recent = recent_dates[:10]
    if top_recent:
        lines.append("| Файл | Дата архивации |")
        lines.append("|------|----------------|")
        for filepath, arch_date in top_recent:
            lines.append(f"| {filepath} | {arch_date} |")
    else:
        lines.append("> Нет данных о датах архивации.")

    return "\n".join(lines) + "\n"


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
        description="Управление архивом Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        help="Подробный вывод (DEBUG).",
    )

    subparsers = parser.add_subparsers(dest="command", help="Подкоманда.")

    # scan
    subparsers.add_parser("scan", help="Поиск кандидатов на архивацию.")

    # archive
    archive_parser = subparsers.add_parser("archive", help="Архивация заметок.")
    archive_parser.add_argument(
        "--folder", default=None,
        help="Папка для сканирования (например, 02-ДОГОВОРЫ).",
    )
    archive_parser.add_argument(
        "--filter", dest="filter_expr", default=None,
        help="Фильтр вида 'ключ:значение' (например, 'status:завершён').",
    )
    archive_parser.add_argument(
        "--days-old", type=int, default=None,
        help="Минимальный возраст файла в днях для архивации.",
    )
    archive_parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Только отчёт, без реального перемещения.",
    )

    # report
    subparsers.add_parser("report", help="Отчёт по содержимому архива.")

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

    if not args.command:
        logger.error("Укажите подкоманду: scan, archive или report.")
        sys.exit(1)

    if args.command == "scan":
        candidates = scan_candidates(args.vault)
        output = json.dumps(candidates, indent=2, ensure_ascii=False)
        sys.stdout.write(output + "\n")

    elif args.command == "archive":
        result = archive_notes(
            vault=args.vault,
            folder=args.folder,
            filter_expr=args.filter_expr,
            days_old=args.days_old,
            dry_run=args.dry_run,
        )
        output = json.dumps(result, indent=2, ensure_ascii=False)
        sys.stdout.write(output + "\n")

    elif args.command == "report":
        report = archive_report(args.vault)
        sys.stdout.write(report)

    else:
        logger.error("Неизвестная подкоманда: %s", args.command)
        sys.exit(1)


if __name__ == "__main__":
    main()
