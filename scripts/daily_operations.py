"""Ежедневные операции с vault: создание дневных записей, утренний брифинг, проверка просроченных.

Подкоманды:
- create-daily: создание дневной записи из шаблона.
- morning-briefing: утренний брифинг в формате Markdown.
- check-overdue: проверка просроченных задач, договоров, платежей (JSON).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def _parse_date(val: str) -> Optional[date]:
    """Пытается разобрать дату из строки ISO.

    Args:
        val: Строковое представление даты (ГГГГ-ММ-ДД).

    Returns:
        Объект ``date`` или ``None``.
    """
    try:
        return date.fromisoformat(val.strip())
    except (ValueError, AttributeError):
        return None


def read_notes(vault: Path, folder: str) -> List[Tuple[Path, Dict[str, Any], str]]:
    """Читает все .md-файлы из папки vault и возвращает их с frontmatter и телом.

    Args:
        vault: Путь к vault.
        folder: Подпапка внутри vault.

    Returns:
        Список кортежей (путь, frontmatter, полный_текст).
    """
    target = vault / folder
    if not target.exists():
        logger.debug("Папка не найдена: %s", target)
        return []
    notes: List[Tuple[Path, Dict[str, Any], str]] = []
    for md in sorted(target.glob("*.md")):
        if md.name.startswith("_"):
            continue
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        notes.append((md, fm, text))
    return notes


def _extract_section(text: str, heading: str) -> str:
    """Извлекает содержимое секции Markdown по названию заголовка (##).

    Args:
        text: Полный текст заметки.
        heading: Название заголовка (без ``## ``).

    Returns:
        Текст секции или пустая строка.
    """
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    # Ищем следующий заголовок того же или высшего уровня
    next_heading = re.search(r"^#{1,2}\s+", text[start:], re.MULTILINE)
    if next_heading:
        return text[start : start + next_heading.start()].strip()
    return text[start:].strip()


def _extract_unchecked_tasks(text: str) -> List[str]:
    """Извлекает невыполненные задачи (``- [ ]``) из текста.

    Args:
        text: Текст для поиска.

    Returns:
        Список строк задач (без маркера ``- [ ]``).
    """
    tasks: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            task = stripped[5:].strip()
            if task:
                tasks.append(task)
    return tasks


def _extract_checked_tasks(text: str) -> List[str]:
    """Извлекает выполненные задачи (``- [x]``) из текста.

    Args:
        text: Текст для поиска.

    Returns:
        Список строк задач (без маркера ``- [x]``).
    """
    tasks: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [x]"):
            task = stripped[5:].strip().strip("~")
            if task:
                tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# create-daily
# ---------------------------------------------------------------------------


def cmd_create_daily(vault: Path, target_date: date) -> None:
    """Создаёт дневную запись из шаблона.

    Args:
        vault: Путь к vault.
        target_date: Дата записи.
    """
    folder = vault / "08-КАЛЕНДАРЬ"
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / f"{target_date.isoformat()}.md"

    if filename.exists():
        logger.info("Дневная запись уже существует: %s", filename)
        return

    # Собираем встречи на эту дату из 06-ПЕРЕГОВОРЫ
    meetings: List[str] = []
    for path, fm, _text in read_notes(vault, "06-ПЕРЕГОВОРЫ"):
        meeting_date = _parse_date(fm.get("дата", ""))
        if meeting_date == target_date:
            title = fm.get("title", path.stem)
            meetings.append(f"- [[{path.stem}|{title}]]")

    # Собираем задачи из вчерашней записи (секция "На завтра / на контроле")
    yesterday = target_date - timedelta(days=1)
    yesterday_file = folder / f"{yesterday.isoformat()}.md"
    tomorrow_tasks: List[str] = []
    if yesterday_file.exists():
        yesterday_text = yesterday_file.read_text(encoding="utf-8")
        section = _extract_section(yesterday_text, "На завтра / на контроле")
        for task in _extract_unchecked_tasks(section):
            tomorrow_tasks.append(f"- [ ] {task}")

    # Формируем содержимое файла
    date_str = target_date.isoformat()
    meetings_block = "\n".join(meetings) if meetings else "- [[]]"
    tasks_block = "\n".join(tomorrow_tasks) if tomorrow_tasks else "- [ ] "

    content = f"""---
title: "{date_str}"
type: дневная_запись
дата: {date_str}
tags:
  - тип/календарь
---

# {date_str}

## Ключевые события дня

-

## Встречи и переговоры

{meetings_block}

## Задачи

{tasks_block}

## Выполнено

- [x] ~~...~~

> [!note] Наблюдения
> Важные наблюдения и инсайты за день

## На завтра / на контроле

- [ ]
"""

    filename.write_text(content, encoding="utf-8")
    logger.info("Создана дневная запись: %s", filename)


# ---------------------------------------------------------------------------
# morning-briefing
# ---------------------------------------------------------------------------


def cmd_morning_briefing(vault: Path, days: int) -> str:
    """Генерирует утренний брифинг в формате Markdown.

    Args:
        vault: Путь к vault.
        days: Горизонт дней для истекающих договоров.

    Returns:
        Текст брифинга в формате Markdown.
    """
    today = date.today()
    lines: List[str] = [
        f"# Утренний брифинг — {today.isoformat()}",
        "",
    ]

    # 1. Просроченные задачи из 08-КАЛЕНДАРЬ за последние 7 дней
    lines.append("## Просроченные задачи")
    lines.append("")
    overdue_found = False
    for i in range(1, 8):
        past_date = today - timedelta(days=i)
        daily_file = vault / "08-КАЛЕНДАРЬ" / f"{past_date.isoformat()}.md"
        if not daily_file.exists():
            continue
        text = daily_file.read_text(encoding="utf-8")
        tasks_section = _extract_section(text, "Задачи")
        unchecked = _extract_unchecked_tasks(tasks_section)
        for task in unchecked:
            lines.append(f"- **{past_date.isoformat()}**: {task}")
            overdue_found = True
    if not overdue_found:
        lines.append("> Нет просроченных задач.")
    lines.append("")

    # 2. Встречи сегодня из 06-ПЕРЕГОВОРЫ
    lines.append("## Встречи сегодня")
    lines.append("")
    meetings_found = False
    for path, fm, _text in read_notes(vault, "06-ПЕРЕГОВОРЫ"):
        meeting_date = _parse_date(fm.get("дата", ""))
        if meeting_date == today:
            title = fm.get("title", path.stem)
            time_str = fm.get("время", "")
            cp = fm.get("контрагент", "")
            line = f"- **{time_str}** — {title}"
            if cp:
                line += f" ({cp})"
            lines.append(line)
            meetings_found = True
    if not meetings_found:
        lines.append("> Нет запланированных встреч.")
    lines.append("")

    # 3. Истекающие договоры в горизонте --days
    lines.append(f"## Истекающие договоры (в течение {days} дней)")
    lines.append("")
    deadline = today + timedelta(days=days)
    expiring_found = False
    for path, fm, _text in read_notes(vault, "02-ДОГОВОРЫ"):
        status = fm.get("статус", "")
        if status in ("завершён", "отменён"):
            continue
        end_str = fm.get("дата_окончания", "")
        end_date = _parse_date(end_str)
        if end_date and today <= end_date <= deadline:
            title = fm.get("title", path.stem)
            days_left = (end_date - today).days
            cp = fm.get("контрагент", "")
            lines.append(f"- **{title}** ({cp}) — истекает {end_str} (осталось {days_left} дн.)")
            expiring_found = True
    if not expiring_found:
        lines.append("> Нет истекающих договоров.")
    lines.append("")

    # 4. Последние события из 07-ОПЕРАЦИИ за последние 3 дня
    lines.append("## Последние события (3 дня)")
    lines.append("")
    cutoff = today - timedelta(days=3)
    events_found = False
    for path, fm, _text in read_notes(vault, "07-ОПЕРАЦИИ"):
        event_date = _parse_date(fm.get("дата", ""))
        if event_date and event_date >= cutoff:
            title = fm.get("title", path.stem)
            category = fm.get("категория", "")
            lines.append(f"- **{fm.get('дата', '')}** — {title} [{category}]")
            events_found = True
    if not events_found:
        lines.append("> Нет недавних событий.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# check-overdue
# ---------------------------------------------------------------------------


def cmd_check_overdue(vault: Path) -> Dict[str, Any]:
    """Проверяет просроченные задачи, договоры и платежи.

    Args:
        vault: Путь к vault.

    Returns:
        Словарь с ключами overdue_tasks, expiring_contracts, overdue_payments.
    """
    today = date.today()
    result: Dict[str, Any] = {
        "overdue_tasks": [],
        "expiring_contracts": [],
        "overdue_payments": [],
    }

    # 1. Просроченные задачи из 08-КАЛЕНДАРЬ (все даты до сегодня)
    calendar_dir = vault / "08-КАЛЕНДАРЬ"
    if calendar_dir.exists():
        for md in sorted(calendar_dir.glob("*.md")):
            if md.name.startswith("_"):
                continue
            file_date = _parse_date(md.stem)
            if file_date is None or file_date >= today:
                continue
            text = md.read_text(encoding="utf-8")
            tasks_section = _extract_section(text, "Задачи")
            unchecked = _extract_unchecked_tasks(tasks_section)
            for task in unchecked:
                result["overdue_tasks"].append({
                    "дата": file_date.isoformat(),
                    "задача": task,
                    "файл": md.name,
                })

    # 2. Истекающие/просроченные договоры
    for path, fm, _text in read_notes(vault, "02-ДОГОВОРЫ"):
        status = fm.get("статус", "")
        if status in ("завершён", "отменён"):
            continue
        end_str = fm.get("дата_окончания", "")
        end_date = _parse_date(end_str)
        if end_date and end_date <= today + timedelta(days=30):
            title = fm.get("title", path.stem)
            days_left = (end_date - today).days
            result["expiring_contracts"].append({
                "договор": title,
                "контрагент": fm.get("контрагент", ""),
                "дата_окончания": end_str,
                "дней_до_истечения": days_left,
            })

    # 3. Просроченные платежи из 10-ФИНАНСЫ
    for path, fm, _text in read_notes(vault, "10-ФИНАНСЫ"):
        status = fm.get("статус", "")
        if status in ("оплачен", "отменён"):
            continue
        due_str = fm.get("дата_оплаты", fm.get("срок_оплаты", ""))
        due_date = _parse_date(due_str)
        if due_date and due_date < today:
            title = fm.get("title", path.stem)
            days_overdue = (today - due_date).days
            result["overdue_payments"].append({
                "документ": title,
                "контрагент": fm.get("контрагент", ""),
                "дата_оплаты": due_str,
                "дней_просрочки": days_overdue,
            })

    return result


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
        description="Ежедневные операции с Obsidian vault.",
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

    # create-daily
    p_daily = subparsers.add_parser(
        "create-daily",
        help="Создать дневную запись.",
    )
    p_daily.add_argument(
        "--date", dest="target_date", type=str, default=None,
        help="Дата записи в формате ГГГГ-ММ-ДД (по умолчанию — сегодня).",
    )

    # morning-briefing
    p_briefing = subparsers.add_parser(
        "morning-briefing",
        help="Утренний брифинг.",
    )
    p_briefing.add_argument(
        "--days", type=int, default=7,
        help="Горизонт дней для истекающих договоров (по умолчанию 7).",
    )

    # check-overdue
    subparsers.add_parser(
        "check-overdue",
        help="Проверка просроченных задач, договоров, платежей.",
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

    if args.command is None:
        logger.error("Укажите подкоманду: create-daily, morning-briefing, check-overdue.")
        sys.exit(1)

    if args.command == "create-daily":
        if args.target_date:
            target = _parse_date(args.target_date)
            if target is None:
                logger.error("Неверный формат даты: %s", args.target_date)
                sys.exit(1)
        else:
            target = date.today()
        cmd_create_daily(args.vault, target)

    elif args.command == "morning-briefing":
        report = cmd_morning_briefing(args.vault, args.days)
        sys.stdout.write(report)

    elif args.command == "check-overdue":
        data = cmd_check_overdue(args.vault)
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
