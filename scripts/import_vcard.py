#!/usr/bin/env python3
"""Импорт контактов из vCard (.vcf) в Obsidian vault.

Парсит vCard 3.0/4.0 через библиотеку vobject, создаёт карточки контактов
в 05-КОНТАКТЫ/. При указании ``--counterparty`` добавляет ссылки на контакты
в карточку контрагента.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
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
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


# ---------------------------------------------------------------------------
# Извлечение полей из vCard
# ---------------------------------------------------------------------------

def extract_contact(card: Any) -> dict[str, str]:
    """Извлекает основные поля из одного vCard-объекта.

    Args:
        card: Объект vobject.vCard.

    Returns:
        Словарь полей контакта.
    """
    fields: dict[str, str] = {}

    if hasattr(card, "fn"):
        fields["title"] = card.fn.value.strip()

    if hasattr(card, "tel"):
        phones: list[str] = []
        if isinstance(card.contents.get("tel"), list):
            for t in card.contents["tel"]:
                phones.append(t.value.strip())
        else:
            phones.append(card.tel.value.strip())
        fields["phone"] = phones[0] if phones else ""
        if len(phones) > 1:
            fields["phone_extra"] = "; ".join(phones[1:])

    if hasattr(card, "email"):
        emails: list[str] = []
        if isinstance(card.contents.get("email"), list):
            for e in card.contents["email"]:
                emails.append(e.value.strip())
        else:
            emails.append(card.email.value.strip())
        fields["email"] = emails[0] if emails else ""
        if len(emails) > 1:
            fields["email_extra"] = "; ".join(emails[1:])

    if hasattr(card, "org"):
        org_val = card.org.value
        if isinstance(org_val, list):
            fields["organization"] = " ".join(str(o) for o in org_val if o).strip()
        else:
            fields["organization"] = str(org_val).strip()

    if hasattr(card, "title"):
        fields["role"] = card.title.value.strip()

    return fields


# ---------------------------------------------------------------------------
# Генерация .md контакта
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Создаёт безопасное имя файла.

    Args:
        name: Исходная строка.

    Returns:
        Строка, пригодная для имени файла.
    """
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()


def build_contact_md(
    fields: dict[str, str],
    counterparty: str,
    today: str,
) -> str:
    """Генерирует содержимое .md для контакта.

    Args:
        fields: Словарь полей контакта.
        counterparty: Название контрагента (может быть пустым).
        today: Текущая дата в формате ISO.

    Returns:
        Полный текст .md-файла.
    """
    title = fields.get("title", "Без имени")
    role = fields.get("role", "")
    phone = fields.get("phone", "")
    phone_extra = fields.get("phone_extra", "")
    email = fields.get("email", "")
    email_extra = fields.get("email_extra", "")
    organization = fields.get("organization", "")

    cp_link = f"[[{counterparty}]]" if counterparty else ""
    if not cp_link and organization:
        cp_link = f"[[{organization}]]"

    first_name = title.split()[0] if title.split() else title

    return f"""---
title: "{title}"
type: контакт
контрагент: "{cp_link}"
роль: "{role}"
статус: активный
дата_создания: {today}
фото: ""
связи: []
tags:
  - тип/контакт
  - статус/активный
aliases:
  - {first_name}
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
> - **Дополнительный:** {phone_extra}

> [!info]- Электронная почта
> - **Рабочий email:** {email}
> - **Дополнительный email:** {email_extra}

> [!info]- Мессенджеры и соцсети
> - **Telegram:**
> - **WhatsApp:**

## История взаимодействия

| Дата | Событие | Заметки |
|------|---------|---------|
| {today} | Импорт из vCard | |

## Заметки и особенности

-
"""


# ---------------------------------------------------------------------------
# Обновление карточки контрагента
# ---------------------------------------------------------------------------

def update_counterparty_card(
    vault: Path,
    counterparty: str,
    contact_names: list[str],
) -> None:
    """Добавляет ссылки на контакты в карточку контрагента.

    Args:
        vault: Путь к vault.
        counterparty: Название контрагента.
        contact_names: Список ФИО контактов.
    """
    cp_dir = vault / "01-КОНТРАГЕНТЫ"
    cp_file = cp_dir / f"{_safe_filename(counterparty)}.md"

    if not cp_file.exists():
        logger.warning(
            "Карточка контрагента '%s' не найдена (%s). Ссылки не добавлены.",
            counterparty, cp_file,
        )
        return

    text = cp_file.read_text(encoding="utf-8")

    # Обновляем контактные_лица в frontmatter
    parts = text.split("---", 2)
    if len(parts) < 3:
        logger.warning("Не удалось разобрать frontmatter карточки контрагента.")
        return

    fm_text = parts[1]
    body = parts[2]

    # Добавляем ссылки в контактные_лица
    new_links: list[str] = []
    for name in contact_names:
        link = f'  - "[[{name}]]"'
        if link not in fm_text:
            new_links.append(link)

    if new_links:
        # Ищем контактные_лица в frontmatter
        if "контактные_лица:" in fm_text:
            insert_lines = "\n".join(new_links)
            # Если пустой список
            fm_text = fm_text.replace(
                "контактные_лица: []",
                "контактные_лица:\n" + insert_lines,
            )
            # Если уже есть элементы — добавляем в конец списка
            if "контактные_лица: []" not in parts[1]:
                # Находим последнюю строку с '  - "[[' после контактные_лица:
                lines = fm_text.splitlines()
                insert_idx = None
                in_list = False
                for i, line in enumerate(lines):
                    if line.strip().startswith("контактные_лица:"):
                        in_list = True
                        continue
                    if in_list:
                        if line.strip().startswith('- "[['):
                            insert_idx = i
                        else:
                            break
                if insert_idx is not None:
                    for j, nl in enumerate(new_links):
                        lines.insert(insert_idx + 1 + j, nl)
                    fm_text = "\n".join(lines)

        updated = f"---{fm_text}---{body}"
        cp_file.write_text(updated, encoding="utf-8")
        logger.info(
            "Обновлена карточка контрагента '%s': добавлено %d контакт(ов).",
            counterparty, len(new_links),
        )


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def import_vcard(
    vault: Path,
    vcf_path: Path,
    counterparty: str = "",
) -> int:
    """Импортирует контакты из .vcf-файла.

    Args:
        vault: Путь к Obsidian vault.
        vcf_path: Путь к .vcf-файлу.
        counterparty: Название контрагента для привязки.

    Returns:
        Количество созданных файлов.
    """
    try:
        import vobject  # noqa: WPS433
    except ImportError:
        logger.error(
            "Библиотека vobject не установлена. "
            "Установите: pip install vobject"
        )
        sys.exit(1)

    today = date.today().isoformat()
    vcf_text = vcf_path.read_text(encoding="utf-8")

    target_dir = vault / "05-КОНТАКТЫ"
    target_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    contact_names: list[str] = []

    for card in vobject.readComponents(vcf_text):
        fields = extract_contact(card)
        title = fields.get("title", "")
        if not title:
            logger.warning("vCard без FN — пропущена.")
            continue

        # Формируем имя файла с учётом контрагента
        if counterparty:
            filename_base = f"{title} ({counterparty})"
        else:
            org = fields.get("organization", "")
            filename_base = f"{title} ({org})" if org else title

        filename = _safe_filename(filename_base) + ".md"
        filepath = target_dir / filename

        if filepath.exists():
            logger.info("Файл '%s' уже существует — пропущен.", filename)
            continue

        content = build_contact_md(fields, counterparty, today)
        filepath.write_text(content, encoding="utf-8")
        logger.info("Создан: %s", filepath)
        contact_names.append(filename_base)
        created += 1

    # Обновление карточки контрагента
    if counterparty and contact_names:
        update_counterparty_card(vault, counterparty, contact_names)

    return created


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
        description="Импорт контактов из vCard (.vcf) в Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--file", type=Path, required=True,
        help="Путь к .vcf-файлу.",
    )
    parser.add_argument(
        "--counterparty", default="",
        help="Название контрагента для привязки контактов.",
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
        logger.error("VCF-файл не найден: %s", args.file)
        sys.exit(1)

    count = import_vcard(args.vault, args.file, args.counterparty)
    logger.info("Итого создано контактов: %d", count)


if __name__ == "__main__":
    main()
