#!/usr/bin/env python3
"""Генерация отчётов по данным Obsidian vault.

Типы отчётов:
- expiring-contracts: договоры с истекающим сроком.
- counterparty-history: история взаимодействия с контрагентом.
- employee-activity: проекты и договоры по сотруднику.

Отчёт выводится в stdout в формате Markdown.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            result[key] = val
    return result


def read_notes(vault: Path, folder: str) -> list[tuple[Path, dict[str, Any]]]:
    """Читает все .md-файлы из папки vault и возвращает их с frontmatter.

    Args:
        vault: Путь к vault.
        folder: Подпапка.

    Returns:
        Список кортежей (путь, frontmatter).
    """
    target = vault / folder
    if not target.exists():
        return []
    notes: list[tuple[Path, dict[str, Any]]] = []
    for md in sorted(target.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        notes.append((md, fm))
    return notes


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


def _extract_wikilinks(text: str) -> list[str]:
    """Извлекает все ``[[ссылки]]`` из текста.

    Args:
        text: Исходный текст.

    Returns:
        Список имён ссылок (без ``[[`` / ``]]``).
    """
    import re  # noqa: WPS433
    return [m.split("|")[0] for m in re.findall(r"\[\[([^\]]+)\]\]", text)]


# ---------------------------------------------------------------------------
# Отчёт: истекающие договоры
# ---------------------------------------------------------------------------

def report_expiring_contracts(vault: Path, days: int) -> str:
    """Генерирует отчёт о договорах с истекающим сроком.

    Args:
        vault: Путь к vault.
        days: Количество дней до истечения.

    Returns:
        Markdown-текст отчёта.
    """
    today = date.today()
    deadline = today + timedelta(days=days)

    contracts = read_notes(vault, "02-ДОГОВОРЫ")
    expiring: list[tuple[str, str, str, str]] = []

    for path, fm in contracts:
        status = fm.get("статус", "")
        if status in ("завершён", "отменён"):
            continue
        end_str = fm.get("дата_окончания", "")
        end_date = _parse_date(end_str)
        if end_date is None:
            continue
        if today <= end_date <= deadline:
            title = fm.get("title", path.stem)
            cp = fm.get("контрагент", "").strip('"').strip("'")
            days_left = (end_date - today).days
            expiring.append((title, cp, end_str, str(days_left)))

    # Сортировка по дате окончания
    expiring.sort(key=lambda x: x[2])

    lines: list[str] = [
        f"# Отчёт: Истекающие договоры",
        f"",
        f"**Дата отчёта:** {today.isoformat()}",
        f"**Горизонт:** {days} дней (до {deadline.isoformat()})",
        f"**Найдено:** {len(expiring)}",
        f"",
    ]

    if not expiring:
        lines.append("> Нет договоров с истекающим сроком в указанном периоде.")
    else:
        lines.append("| Договор | Контрагент | Дата окончания | Осталось дней |")
        lines.append("|---------|------------|----------------|---------------|")
        for title, cp, end, dl in expiring:
            lines.append(f"| {title} | {cp} | {end} | {dl} |")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Отчёт: история контрагента
# ---------------------------------------------------------------------------

def report_counterparty_history(vault: Path, counterparty: str) -> str:
    """Генерирует отчёт об истории взаимодействия с контрагентом.

    Args:
        vault: Путь к vault.
        counterparty: Название контрагента.

    Returns:
        Markdown-текст отчёта.
    """
    today = date.today()
    cp_lower = counterparty.lower()

    # Собираем договоры
    contract_entries: list[tuple[str, str, str]] = []
    for path, fm in read_notes(vault, "02-ДОГОВОРЫ"):
        cp = fm.get("контрагент", "")
        if cp_lower in cp.lower():
            title = fm.get("title", path.stem)
            status = fm.get("статус", "")
            contract_entries.append((title, status, fm.get("дата_подписания", "")))

    # Собираем переговоры
    meeting_entries: list[tuple[str, str, str]] = []
    for path, fm in read_notes(vault, "06-ПЕРЕГОВОРЫ"):
        cp = fm.get("контрагент", "")
        if cp_lower in cp.lower():
            title = fm.get("title", path.stem)
            d = fm.get("дата", "")
            status = fm.get("статус", "")
            meeting_entries.append((title, status, d))

    # Собираем проекты
    project_entries: list[tuple[str, str, str]] = []
    for path, fm in read_notes(vault, "03-ПРОЕКТЫ"):
        client = fm.get("клиент", "")
        if cp_lower in client.lower():
            title = fm.get("title", path.stem)
            status = fm.get("статус", "")
            project_entries.append((title, status, fm.get("дата_начала", "")))

    # Собираем контакты
    contact_entries: list[tuple[str, str]] = []
    for path, fm in read_notes(vault, "05-КОНТАКТЫ"):
        cp = fm.get("контрагент", "")
        if cp_lower in cp.lower():
            title = fm.get("title", path.stem)
            role = fm.get("роль", "")
            contact_entries.append((title, role))

    lines: list[str] = [
        f"# Отчёт: История контрагента — {counterparty}",
        f"",
        f"**Дата отчёта:** {today.isoformat()}",
        f"",
        f"## Контактные лица ({len(contact_entries)})",
        f"",
    ]

    if contact_entries:
        lines.append("| ФИО | Роль |")
        lines.append("|-----|------|")
        for name, role in contact_entries:
            lines.append(f"| {name} | {role} |")
    else:
        lines.append("> Контакты не найдены.")

    lines += [
        f"",
        f"## Договоры ({len(contract_entries)})",
        f"",
    ]

    if contract_entries:
        lines.append("| Договор | Статус | Дата подписания |")
        lines.append("|---------|--------|-----------------|")
        for title, status, d in contract_entries:
            lines.append(f"| {title} | {status} | {d} |")
    else:
        lines.append("> Договоры не найдены.")

    lines += [
        f"",
        f"## Проекты ({len(project_entries)})",
        f"",
    ]

    if project_entries:
        lines.append("| Проект | Статус | Дата начала |")
        lines.append("|--------|--------|-------------|")
        for title, status, d in project_entries:
            lines.append(f"| {title} | {status} | {d} |")
    else:
        lines.append("> Проекты не найдены.")

    lines += [
        f"",
        f"## Переговоры ({len(meeting_entries)})",
        f"",
    ]

    if meeting_entries:
        lines.append("| Переговоры | Статус | Дата |")
        lines.append("|------------|--------|------|")
        for title, status, d in meeting_entries:
            lines.append(f"| {title} | {status} | {d} |")
    else:
        lines.append("> Переговоры не найдены.")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Отчёт: активность сотрудника
# ---------------------------------------------------------------------------

def report_employee_activity(vault: Path, employee: str) -> str:
    """Генерирует отчёт о проектах и договорах сотрудника.

    Args:
        vault: Путь к vault.
        employee: ФИО сотрудника (для поиска по wikilinks).

    Returns:
        Markdown-текст отчёта.
    """
    today = date.today()
    emp_lower = employee.lower()

    # Проекты, где сотрудник — руководитель или в команде
    project_entries: list[tuple[str, str, str]] = []
    for path, fm in read_notes(vault, "03-ПРОЕКТЫ"):
        text = path.read_text(encoding="utf-8")
        links = [lnk.lower() for lnk in _extract_wikilinks(text)]
        if any(emp_lower in lnk for lnk in links):
            title = fm.get("title", path.stem)
            status = fm.get("статус", "")
            role_parts: list[str] = []
            mgr = fm.get("руководитель", "")
            if emp_lower in mgr.lower():
                role_parts.append("руководитель")
            else:
                role_parts.append("участник")
            project_entries.append((title, status, ", ".join(role_parts)))

    # Договоры, где сотрудник — ответственный
    contract_entries: list[tuple[str, str, str]] = []
    for path, fm in read_notes(vault, "02-ДОГОВОРЫ"):
        resp = fm.get("ответственный_наш", "")
        text = path.read_text(encoding="utf-8")
        links = [lnk.lower() for lnk in _extract_wikilinks(text)]
        if emp_lower in resp.lower() or any(emp_lower in lnk for lnk in links):
            title = fm.get("title", path.stem)
            status = fm.get("статус", "")
            contract_entries.append((title, status, fm.get("дата_окончания", "")))

    # Переговоры
    meeting_entries: list[tuple[str, str]] = []
    for path, fm in read_notes(vault, "06-ПЕРЕГОВОРЫ"):
        text = path.read_text(encoding="utf-8")
        links = [lnk.lower() for lnk in _extract_wikilinks(text)]
        if any(emp_lower in lnk for lnk in links):
            title = fm.get("title", path.stem)
            d = fm.get("дата", "")
            meeting_entries.append((title, d))

    lines: list[str] = [
        f"# Отчёт: Активность сотрудника — {employee}",
        f"",
        f"**Дата отчёта:** {today.isoformat()}",
        f"",
        f"## Проекты ({len(project_entries)})",
        f"",
    ]

    if project_entries:
        lines.append("| Проект | Статус | Роль |")
        lines.append("|--------|--------|------|")
        for title, status, role in project_entries:
            lines.append(f"| {title} | {status} | {role} |")
    else:
        lines.append("> Проекты не найдены.")

    lines += [
        f"",
        f"## Договоры ({len(contract_entries)})",
        f"",
    ]

    if contract_entries:
        lines.append("| Договор | Статус | Дата окончания |")
        lines.append("|---------|--------|----------------|")
        for title, status, end in contract_entries:
            lines.append(f"| {title} | {status} | {end} |")
    else:
        lines.append("> Договоры не найдены.")

    lines += [
        f"",
        f"## Переговоры ({len(meeting_entries)})",
        f"",
    ]

    if meeting_entries:
        lines.append("| Переговоры | Дата |")
        lines.append("|------------|------|")
        for title, d in meeting_entries:
            lines.append(f"| {title} | {d} |")
    else:
        lines.append("> Переговоры не найдены.")

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
        description="Генерация отчётов по данным Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--type", dest="report_type", required=True,
        choices=["expiring-contracts", "counterparty-history", "employee-activity"],
        help="Тип отчёта.",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Горизонт в днях для expiring-contracts (по умолчанию 30).",
    )
    parser.add_argument(
        "--counterparty", default="",
        help="Название контрагента (для counterparty-history).",
    )
    parser.add_argument(
        "--employee", default="",
        help="ФИО сотрудника (для employee-activity).",
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

    if args.report_type == "expiring-contracts":
        report = report_expiring_contracts(args.vault, args.days)

    elif args.report_type == "counterparty-history":
        if not args.counterparty:
            logger.error("Для отчёта counterparty-history укажите --counterparty.")
            sys.exit(1)
        report = report_counterparty_history(args.vault, args.counterparty)

    elif args.report_type == "employee-activity":
        if not args.employee:
            logger.error("Для отчёта employee-activity укажите --employee.")
            sys.exit(1)
        report = report_employee_activity(args.vault, args.employee)

    else:
        logger.error("Неизвестный тип отчёта: %s", args.report_type)
        sys.exit(1)

    sys.stdout.write(report)


if __name__ == "__main__":
    main()
