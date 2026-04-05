#!/usr/bin/env python3
"""Импорт данных из CSV-файла в Obsidian vault.

Читает CSV с автоопределением колонок, проверяет дубликаты (по ИНН для
контрагентов), генерирует .md-файлы по шаблонам корпоративной базы знаний.
Поддерживает типы: контрагент, контакт, сотрудник.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Маппинг распространённых имён колонок CSV → полей шаблонов
# ---------------------------------------------------------------------------

_COUNTERPARTY_COL_MAP: dict[str, str] = {
    "инн": "инн",
    "inn": "инн",
    "огрн": "огрн",
    "ogrn": "огрн",
    "название": "title",
    "наименование": "title",
    "name": "title",
    "организация": "title",
    "опф": "опф_краткая",
    "опф_полная": "опф_полная",
    "опф_краткая": "опф_краткая",
    "полное_название": "название_полное",
    "название_полное": "название_полное",
    "название_краткое": "название_краткое",
    "краткое_название": "название_краткое",
    "юридический_адрес": "юридический_адрес",
    "юр_адрес": "юридический_адрес",
    "адрес": "юридический_адрес",
    "address": "юридический_адрес",
    "фактический_адрес": "фактический_адрес",
    "факт_адрес": "фактический_адрес",
    "сайт": "сайт",
    "website": "сайт",
    "site": "сайт",
    "кпп": "кпп",
    "расчётный_счёт": "расчётный_счёт",
    "р_с": "расчётный_счёт",
    "банк": "банк",
    "бик": "бик",
    "корр_счёт": "корр_счёт",
    "к_с": "корр_счёт",
    "категория": "категория",
    "category": "категория",
    "статус": "статус",
    "status": "статус",
}

_CONTACT_COL_MAP: dict[str, str] = {
    "фио": "title",
    "имя": "title",
    "name": "title",
    "фамилия_имя": "title",
    "контрагент": "контрагент",
    "организация": "контрагент",
    "org": "контрагент",
    "роль": "роль",
    "должность": "роль",
    "role": "роль",
    "title": "роль",
    "телефон": "телефон",
    "phone": "телефон",
    "tel": "телефон",
    "email": "email",
    "почта": "email",
    "статус": "статус",
}

_EMPLOYEE_COL_MAP: dict[str, str] = {
    "фио": "title",
    "имя": "title",
    "name": "title",
    "фамилия_имя": "title",
    "должность": "должность",
    "position": "должность",
    "отдел": "отдел",
    "department": "отдел",
    "дата_найма": "дата_найма",
    "hire_date": "дата_найма",
    "руководитель": "руководитель",
    "manager": "руководитель",
    "телефон": "телефон",
    "phone": "телефон",
    "email": "email",
    "почта": "email",
    "статус": "статус",
}

TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "контрагент": {
        "col_map": _COUNTERPARTY_COL_MAP,
        "folder": "01-КОНТРАГЕНТЫ",
        "duplicate_key": "инн",
        "type_tag": "тип/контрагент",
    },
    "контакт": {
        "col_map": _CONTACT_COL_MAP,
        "folder": "05-КОНТАКТЫ",
        "duplicate_key": None,
        "type_tag": "тип/контакт",
    },
    "сотрудник": {
        "col_map": _EMPLOYEE_COL_MAP,
        "folder": "04-СОТРУДНИКИ",
        "duplicate_key": None,
        "type_tag": "тип/сотрудник",
    },
}


# ---------------------------------------------------------------------------
# Чтение frontmatter
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict[str, Any]:
    """Извлекает YAML-свойства из frontmatter, разделённого ``---``.

    Args:
        text: Полный текст .md-файла.

    Returns:
        Словарь ключ-значение из frontmatter (простые строки).
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
# Сборка существующих ИНН / имён для проверки дубликатов
# ---------------------------------------------------------------------------

def collect_existing_keys(vault: Path, folder: str, key_field: str | None) -> set[str]:
    """Собирает множество значений ``key_field`` из существующих .md-файлов.

    Args:
        vault: Путь к vault.
        folder: Подпапка vault (например, ``01-КОНТРАГЕНТЫ``).
        key_field: Имя поля frontmatter для проверки дубликатов.

    Returns:
        Множество найденных значений.
    """
    keys: set[str] = set()
    if key_field is None:
        return keys
    target = vault / folder
    if not target.exists():
        return keys
    for md in target.glob("*.md"):
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        val = fm.get(key_field, "")
        if val:
            keys.add(str(val))
    return keys


# ---------------------------------------------------------------------------
# Маппинг колонок CSV → полей шаблонов
# ---------------------------------------------------------------------------

def map_columns(headers: list[str], col_map: dict[str, str]) -> dict[str, str]:
    """Сопоставляет заголовки CSV с полями шаблона.

    Args:
        headers: Заголовки из CSV-файла.
        col_map: Словарь допустимых маппингов.

    Returns:
        Словарь ``{заголовок_csv: поле_шаблона}``.
    """
    mapping: dict[str, str] = {}
    for h in headers:
        norm = h.strip().lower().replace(" ", "_")
        if norm in col_map:
            mapping[h] = col_map[norm]
        else:
            logger.debug("Колонка '%s' не распознана — пропущена.", h)
    return mapping


# ---------------------------------------------------------------------------
# Генерация .md
# ---------------------------------------------------------------------------

def _build_counterparty_md(fields: dict[str, str], today: str) -> str:
    """Генерирует содержимое .md для контрагента.

    Args:
        fields: Словарь маппированных полей.
        today: Текущая дата в формате ISO.

    Returns:
        Полный текст .md-файла.
    """
    title = fields.get("title", "Без названия")
    inn = fields.get("инн", "")
    ogrn = fields.get("огрн", "")
    status = fields.get("статус", "активный")
    category = fields.get("категория", "клиент")

    return f"""---
title: "{title}"
type: контрагент
инн: "{inn}"
огрн: "{ogrn}"
опф_полная: "{fields.get('опф_полная', '')}"
опф_краткая: "{fields.get('опф_краткая', '')}"
название_полное: "{fields.get('название_полное', '')}"
название_краткое: "{fields.get('название_краткое', '')}"
юридический_адрес: "{fields.get('юридический_адрес', '')}"
фактический_адрес: "{fields.get('фактический_адрес', '')}"
сайт: "{fields.get('сайт', '')}"
кпп: "{fields.get('кпп', '')}"
расчётный_счёт: "{fields.get('расчётный_счёт', '')}"
банк: "{fields.get('банк', '')}"
бик: "{fields.get('бик', '')}"
корр_счёт: "{fields.get('корр_счёт', '')}"
категория: {category}
статус: {status}
дата_создания: {today}
контактные_лица: []
tags:
  - тип/контрагент
  - статус/{status}
aliases:
  - {title}
---

# {title}

## Общая информация

- **ИНН / ОГРН:** {inn} / {ogrn}
- **Юридический адрес:** {fields.get('юридический_адрес', '')}
- **Фактический адрес:** {fields.get('фактический_адрес', '')}
- **Сайт:** {fields.get('сайт', '')}

## Контактные лица

| Роль | Контакт | Телефон | Email |
|------|---------|---------|-------|
| | | | |

## История взаимодействия

| Дата | Событие | Участники | Ссылка |
|------|---------|-----------|--------|
| {today} | Импорт из CSV | | |

## Связанные договоры

-

## Заметки

-
"""


def _build_contact_md(fields: dict[str, str], today: str) -> str:
    """Генерирует содержимое .md для контакта.

    Args:
        fields: Словарь маппированных полей.
        today: Текущая дата в формате ISO.

    Returns:
        Полный текст .md-файла.
    """
    title = fields.get("title", "Без имени")
    counterparty = fields.get("контрагент", "")
    role = fields.get("роль", "")
    phone = fields.get("телефон", "")
    email = fields.get("email", "")
    status = fields.get("статус", "активный")

    cp_link = f"[[{counterparty}]]" if counterparty else ""

    return f"""---
title: "{title}"
type: контакт
контрагент: "{cp_link}"
роль: "{role}"
статус: {status}
дата_создания: {today}
фото: ""
связи: []
tags:
  - тип/контакт
  - статус/{status}
aliases:
  - {title.split()[0] if title.split() else title}
---

# {title}

## Быстрая справка

- **Контрагент:** {cp_link}
- **Роль / Должность:** {role}
- **Рабочий телефон:** {phone}
- **Email рабочий:** {email}

^быстрая-справка

## Контактные данные

> [!info]- Телефоны
> - **Рабочий:** {phone}

> [!info]- Электронная почта
> - **Рабочий email:** {email}

## История взаимодействия

| Дата | Событие | Заметки |
|------|---------|---------|
| {today} | Импорт из CSV | |

## Заметки и особенности

-
"""


def _build_employee_md(fields: dict[str, str], today: str) -> str:
    """Генерирует содержимое .md для сотрудника.

    Args:
        fields: Словарь маппированных полей.
        today: Текущая дата в формате ISO.

    Returns:
        Полный текст .md-файла.
    """
    title = fields.get("title", "Без имени")
    position = fields.get("должность", "")
    department = fields.get("отдел", "")
    hire_date = fields.get("дата_найма", today)
    manager = fields.get("руководитель", "")
    phone = fields.get("телефон", "")
    email = fields.get("email", "")
    status = fields.get("статус", "активный")

    mgr_link = f"[[{manager}]]" if manager else ""

    return f"""---
title: "{title}"
type: сотрудник
должность: "{position}"
отдел: "{department}"
дата_найма: {hire_date}
статус: {status}
руководитель: "{mgr_link}"
фото: ""
связи: []
tags:
  - тип/сотрудник
  - статус/{status}
aliases:
  - {title.split()[0] if title.split() else title}
---

# {title}

## Быстрая справка

- **Должность:** {position}
- **Отдел:** {department}
- **Дата найма:** {hire_date}
- **Руководитель:** {mgr_link}
- **Рабочий телефон:** {phone}
- **Email рабочий:** {email}

^быстрая-справка

## Контактные данные

> [!info]- Телефоны
> - **Рабочий:** {phone}

> [!info]- Электронная почта
> - **Рабочий email:** {email}

## Текущие проекты

-

## Текущие договоры (ответственный)

-

## История событий

| Дата | Событие | Заметки |
|------|---------|---------|
| {hire_date} | Приём на работу | Импорт из CSV |

## Заметки

-
"""


_BUILDERS: dict[str, Any] = {
    "контрагент": _build_counterparty_md,
    "контакт": _build_contact_md,
    "сотрудник": _build_employee_md,
}


def _safe_filename(name: str) -> str:
    """Создаёт безопасное имя файла из строки.

    Args:
        name: Исходная строка.

    Returns:
        Строка, пригодная для имени файла.
    """
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip()


# ---------------------------------------------------------------------------
# Основная логика импорта
# ---------------------------------------------------------------------------

def import_csv(
    vault: Path,
    note_type: str,
    csv_path: Path,
    dry_run: bool = False,
) -> int:
    """Импортирует записи из CSV и создаёт .md-файлы.

    Args:
        vault: Путь к Obsidian vault.
        note_type: Тип заметки (контрагент / контакт / сотрудник).
        csv_path: Путь к CSV-файлу.
        dry_run: Если ``True``, только показывает, что будет создано.

    Returns:
        Количество созданных (или предполагаемых) файлов.
    """
    cfg = TYPE_CONFIG[note_type]
    today = date.today().isoformat()

    # Чтение CSV
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            logger.error("CSV-файл пуст или не содержит заголовков.")
            return 0
        col_mapping = map_columns(list(reader.fieldnames), cfg["col_map"])
        if not col_mapping:
            logger.error("Не удалось сопоставить ни одну колонку CSV с полями шаблона.")
            return 0
        logger.info(
            "Сопоставление колонок: %s",
            ", ".join(f"{k} → {v}" for k, v in col_mapping.items()),
        )
        rows = list(reader)

    # Проверка дубликатов
    existing_keys = collect_existing_keys(vault, cfg["folder"], cfg["duplicate_key"])

    target_dir = vault / cfg["folder"]
    builder = _BUILDERS[note_type]
    created = 0

    for idx, row in enumerate(rows, start=1):
        # Маппинг полей
        fields: dict[str, str] = {}
        for csv_col, tmpl_field in col_mapping.items():
            val = row.get(csv_col, "").strip()
            if val:
                fields[tmpl_field] = val

        title = fields.get("title", "")
        if not title:
            logger.warning("Строка %d: отсутствует название/ФИО — пропущена.", idx)
            continue

        # Проверка дубликата
        dup_key = cfg["duplicate_key"]
        if dup_key:
            key_val = fields.get(dup_key, "")
            if key_val and key_val in existing_keys:
                logger.info("Строка %d: дубликат по %s='%s' — пропущена.", idx, dup_key, key_val)
                continue
            if key_val:
                existing_keys.add(key_val)

        filename = _safe_filename(title) + ".md"
        filepath = target_dir / filename

        if filepath.exists():
            logger.info("Строка %d: файл '%s' уже существует — пропущена.", idx, filename)
            continue

        content = builder(fields, today)

        if dry_run:
            logger.info("[DRY-RUN] Будет создан: %s", filepath)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            logger.info("Создан: %s", filepath)

        created += 1

    return created


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки.

    Args:
        argv: Список аргументов (по умолчанию ``sys.argv``).

    Returns:
        Пространство имён с разобранными аргументами.
    """
    parser = argparse.ArgumentParser(
        description="Импорт данных из CSV в Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--type", dest="note_type", required=True,
        choices=list(TYPE_CONFIG.keys()),
        help="Тип создаваемых заметок.",
    )
    parser.add_argument(
        "--file", type=Path, required=True,
        help="Путь к CSV-файлу.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Только показать, что будет создано, без записи файлов.",
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
    if not args.file.is_file():
        logger.error("CSV-файл не найден: %s", args.file)
        sys.exit(1)

    count = import_csv(args.vault, args.note_type, args.file, args.dry_run)
    action = "будет создано" if args.dry_run else "создано"
    logger.info("Итого %s файлов: %d", action, count)


if __name__ == "__main__":
    main()
