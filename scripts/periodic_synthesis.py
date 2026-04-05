"""Генерация периодических ретроспектив (еженедельных и ежемесячных).

Агрегирует данные из дневных записей, переговоров и операций vault,
формируя итоговый обзор за период.
"""

from __future__ import annotations

import argparse
import calendar
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
    next_heading = re.search(r"^#{1,2}\s+", text[start:], re.MULTILINE)
    if next_heading:
        return text[start : start + next_heading.start()].strip()
    return text[start:].strip()


def _extract_unchecked_tasks(text: str) -> List[str]:
    """Извлекает невыполненные задачи (``- [ ]``) из текста.

    Args:
        text: Текст для поиска.

    Returns:
        Список строк задач.
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
        Список строк задач.
    """
    tasks: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [x]"):
            task = stripped[5:].strip().strip("~")
            if task:
                tasks.append(task)
    return tasks


def _monday_of_week(d: date) -> date:
    """Возвращает понедельник недели для указанной даты.

    Args:
        d: Дата.

    Returns:
        Дата понедельника.
    """
    return d - timedelta(days=d.weekday())


def _month_range(d: date) -> Tuple[date, date]:
    """Возвращает диапазон дат для месяца указанной даты.

    Args:
        d: Дата (используется год и месяц).

    Returns:
        Кортеж (первый_день, последний_день).
    """
    first = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=last_day)
    return first, last


# ---------------------------------------------------------------------------
# Сборка данных за период
# ---------------------------------------------------------------------------


def _collect_daily_notes(
    vault: Path,
    start: date,
    end: date,
) -> List[Tuple[date, str]]:
    """Собирает дневные записи за указанный диапазон дат.

    Args:
        vault: Путь к vault.
        start: Начало периода (включительно).
        end: Конец периода (включительно).

    Returns:
        Список кортежей (дата, полный_текст).
    """
    calendar_dir = vault / "08-КАЛЕНДАРЬ"
    if not calendar_dir.exists():
        return []
    result: List[Tuple[date, str]] = []
    current = start
    while current <= end:
        md_file = calendar_dir / f"{current.isoformat()}.md"
        if md_file.exists():
            text = md_file.read_text(encoding="utf-8")
            result.append((current, text))
        current += timedelta(days=1)
    return result


def _collect_meetings(
    vault: Path,
    start: date,
    end: date,
) -> List[Tuple[str, str, str]]:
    """Собирает переговоры за указанный диапазон дат.

    Args:
        vault: Путь к vault.
        start: Начало периода.
        end: Конец периода.

    Returns:
        Список кортежей (дата_строка, название, контрагент).
    """
    meetings: List[Tuple[str, str, str]] = []
    for path, fm, _text in read_notes(vault, "06-ПЕРЕГОВОРЫ"):
        meeting_date = _parse_date(fm.get("дата", ""))
        if meeting_date and start <= meeting_date <= end:
            title = fm.get("title", path.stem)
            cp = fm.get("контрагент", "")
            meetings.append((fm.get("дата", ""), title, cp))
    return meetings


def _collect_operations(
    vault: Path,
    start: date,
    end: date,
) -> List[Tuple[str, str, str]]:
    """Собирает операционные события за указанный диапазон дат.

    Args:
        vault: Путь к vault.
        start: Начало периода.
        end: Конец периода.

    Returns:
        Список кортежей (дата_строка, название, категория).
    """
    events: List[Tuple[str, str, str]] = []
    for path, fm, _text in read_notes(vault, "07-ОПЕРАЦИИ"):
        event_date = _parse_date(fm.get("дата", ""))
        if event_date and start <= event_date <= end:
            title = fm.get("title", path.stem)
            category = fm.get("категория", "")
            events.append((fm.get("дата", ""), title, category))
    return events


def _collect_contract_activity(
    vault: Path,
    start: date,
    end: date,
) -> List[Tuple[str, str, str]]:
    """Собирает активность по договорам за период (подписанные, истекающие).

    Args:
        vault: Путь к vault.
        start: Начало периода.
        end: Конец периода.

    Returns:
        Список кортежей (событие, название, дата).
    """
    activity: List[Tuple[str, str, str]] = []
    for path, fm, _text in read_notes(vault, "02-ДОГОВОРЫ"):
        title = fm.get("title", path.stem)
        sign_date = _parse_date(fm.get("дата_подписания", ""))
        if sign_date and start <= sign_date <= end:
            activity.append(("подписан", title, sign_date.isoformat()))
        end_date = _parse_date(fm.get("дата_окончания", ""))
        if end_date and start <= end_date <= end:
            activity.append(("истекает", title, end_date.isoformat()))
    return activity


# ---------------------------------------------------------------------------
# Генерация ретроспективы
# ---------------------------------------------------------------------------


def generate_weekly(vault: Path, ref_date: date) -> Tuple[str, Path]:
    """Генерирует еженедельную ретроспективу.

    Args:
        vault: Путь к vault.
        ref_date: Дата внутри целевой недели.

    Returns:
        Кортеж (содержимое файла, путь для записи).
    """
    monday = _monday_of_week(ref_date)
    sunday = monday + timedelta(days=6)

    daily_notes = _collect_daily_notes(vault, monday, sunday)
    meetings = _collect_meetings(vault, monday, sunday)
    operations = _collect_operations(vault, monday, sunday)

    # Собираем задачи
    completed_tasks: List[str] = []
    open_tasks: List[str] = []
    for d, text in daily_notes:
        tasks_section = _extract_section(text, "Задачи")
        done_section = _extract_section(text, "Выполнено")
        completed_tasks.extend(
            f"{d.isoformat()}: {t}" for t in _extract_checked_tasks(tasks_section + "\n" + done_section)
        )
        open_tasks.extend(
            f"{d.isoformat()}: {t}" for t in _extract_unchecked_tasks(tasks_section)
        )

    # Формируем содержимое
    lines: List[str] = [
        "---",
        f'title: "Ретроспектива: Неделя {monday.isoformat()}"',
        "type: ретроспектива",
        "период: неделя",
        f"дата_начала: {monday.isoformat()}",
        f"дата_окончания: {sunday.isoformat()}",
        "tags:",
        "  - тип/ретроспектива",
        "---",
        "",
        f"# Ретроспектива: Неделя {monday.isoformat()} -- {sunday.isoformat()}",
        "",
        f"> [!info] Автоматически сгенерировано",
        f"> Период: {monday.isoformat()} -- {sunday.isoformat()}",
        f"> Дневных записей: {len(daily_notes)}",
        "",
    ]

    # Выполненные задачи
    lines.append("## Выполненные задачи")
    lines.append("")
    if completed_tasks:
        for task in completed_tasks:
            lines.append(f"- [x] {task}")
    else:
        lines.append("> Нет выполненных задач.")
    lines.append("")

    # Проведённые встречи
    lines.append("## Проведённые встречи")
    lines.append("")
    if meetings:
        for d_str, title, cp in meetings:
            line = f"- **{d_str}** — {title}"
            if cp:
                line += f" ({cp})"
            lines.append(line)
    else:
        lines.append("> Нет встреч за период.")
    lines.append("")

    # Принятые решения (из операций)
    lines.append("## Принятые решения и события")
    lines.append("")
    if operations:
        for d_str, title, category in operations:
            line = f"- **{d_str}** — {title}"
            if category:
                line += f" [{category}]"
            lines.append(line)
    else:
        lines.append("> Нет зафиксированных решений.")
    lines.append("")

    # Открытые вопросы
    lines.append("## Открытые вопросы")
    lines.append("")
    if open_tasks:
        for task in open_tasks:
            lines.append(f"- [ ] {task}")
    else:
        lines.append("> Нет открытых вопросов.")
    lines.append("")

    output_dir = vault / "09-СТРАТЕГИЯ" / "Ретроспективы"
    output_path = output_dir / f"Неделя {monday.isoformat()}.md"

    return "\n".join(lines), output_path


def generate_monthly(vault: Path, ref_date: date) -> Tuple[str, Path]:
    """Генерирует ежемесячную ретроспективу.

    Args:
        vault: Путь к vault.
        ref_date: Дата внутри целевого месяца.

    Returns:
        Кортеж (содержимое файла, путь для записи).
    """
    first, last = _month_range(ref_date)
    month_label = ref_date.strftime("%Y-%m")

    daily_notes = _collect_daily_notes(vault, first, last)
    meetings = _collect_meetings(vault, first, last)
    operations = _collect_operations(vault, first, last)
    contract_activity = _collect_contract_activity(vault, first, last)

    # Собираем задачи
    completed_tasks: List[str] = []
    open_tasks: List[str] = []
    for d, text in daily_notes:
        tasks_section = _extract_section(text, "Задачи")
        done_section = _extract_section(text, "Выполнено")
        completed_tasks.extend(
            f"{d.isoformat()}: {t}" for t in _extract_checked_tasks(tasks_section + "\n" + done_section)
        )
        open_tasks.extend(
            f"{d.isoformat()}: {t}" for t in _extract_unchecked_tasks(tasks_section)
        )

    # Изменения статусов проектов
    project_changes: List[str] = []
    for path, fm, text in read_notes(vault, "03-ПРОЕКТЫ"):
        title = fm.get("title", path.stem)
        status = fm.get("статус", "")
        start_str = fm.get("дата_начала", "")
        start_d = _parse_date(start_str)
        if start_d and first <= start_d <= last:
            project_changes.append(f"Начат: **{title}** (статус: {status})")
        end_str = fm.get("дата_окончания_план", "")
        end_d = _parse_date(end_str)
        if end_d and first <= end_d <= last:
            project_changes.append(f"Плановое завершение: **{title}** (статус: {status})")

    # Формируем содержимое
    lines: List[str] = [
        "---",
        f'title: "Ретроспектива: Месяц {month_label}"',
        "type: ретроспектива",
        "период: месяц",
        f"дата_начала: {first.isoformat()}",
        f"дата_окончания: {last.isoformat()}",
        "tags:",
        "  - тип/ретроспектива",
        "---",
        "",
        f"# Ретроспектива: {month_label}",
        "",
        f"> [!info] Автоматически сгенерировано",
        f"> Период: {first.isoformat()} -- {last.isoformat()}",
        f"> Дневных записей: {len(daily_notes)}",
        "",
    ]

    # Выполненные задачи
    lines.append("## Выполненные задачи")
    lines.append("")
    if completed_tasks:
        for task in completed_tasks:
            lines.append(f"- [x] {task}")
    else:
        lines.append("> Нет выполненных задач.")
    lines.append("")

    # Проведённые встречи
    lines.append("## Проведённые встречи")
    lines.append("")
    if meetings:
        for d_str, title, cp in meetings:
            line = f"- **{d_str}** — {title}"
            if cp:
                line += f" ({cp})"
            lines.append(line)
    else:
        lines.append("> Нет встреч за период.")
    lines.append("")

    # Принятые решения
    lines.append("## Принятые решения и события")
    lines.append("")
    if operations:
        for d_str, title, category in operations:
            line = f"- **{d_str}** — {title}"
            if category:
                line += f" [{category}]"
            lines.append(line)
    else:
        lines.append("> Нет зафиксированных решений.")
    lines.append("")

    # Активность по проектам
    lines.append("## Активность по проектам")
    lines.append("")
    if project_changes:
        for change in project_changes:
            lines.append(f"- {change}")
    else:
        lines.append("> Нет изменений по проектам.")
    lines.append("")

    # Активность по договорам
    lines.append("## Активность по договорам")
    lines.append("")
    if contract_activity:
        for event, title, d_str in contract_activity:
            lines.append(f"- **{event}**: {title} ({d_str})")
    else:
        lines.append("> Нет активности по договорам.")
    lines.append("")

    # Открытые вопросы
    lines.append("## Открытые вопросы")
    lines.append("")
    if open_tasks:
        for task in open_tasks:
            lines.append(f"- [ ] {task}")
    else:
        lines.append("> Нет открытых вопросов.")
    lines.append("")

    output_dir = vault / "09-СТРАТЕГИЯ" / "Ретроспективы"
    output_path = output_dir / f"Месяц {month_label}.md"

    return "\n".join(lines), output_path


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
        description="Генерация периодических ретроспектив для Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--type", dest="period_type", required=True,
        choices=["weekly", "monthly"],
        help="Тип ретроспективы: weekly (неделя) или monthly (месяц).",
    )
    parser.add_argument(
        "--date", dest="target_date", type=str, default=None,
        help="Дата внутри целевого периода (ГГГГ-ММ-ДД). По умолчанию — сегодня.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Вывести содержимое без создания файла.",
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

    if args.target_date:
        ref = _parse_date(args.target_date)
        if ref is None:
            logger.error("Неверный формат даты: %s", args.target_date)
            sys.exit(1)
    else:
        ref = date.today()

    if args.period_type == "weekly":
        content, output_path = generate_weekly(args.vault, ref)
    else:
        content, output_path = generate_monthly(args.vault, ref)

    if args.dry_run:
        logger.info("[dry-run] Файл не создан. Содержимое:")
        sys.stdout.write(content)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Ретроспектива сохранена: %s", output_path)


if __name__ == "__main__":
    main()
