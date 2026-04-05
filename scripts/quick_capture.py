#!/usr/bin/env python3
"""Быстрое создание заметки из одной строки.

Поддерживает типы: идея (→ 09-СТРАТЕГИЯ/Идеи/), событие (→ 07-ОПЕРАЦИИ/),
задача (→ 08-КАЛЕНДАРЬ/ — добавление в дневную запись).
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
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _truncate(text: str, max_words: int = 5) -> str:
    """Обрезает текст до указанного количества слов.

    Args:
        text: Исходный текст.
        max_words: Максимальное количество слов.

    Returns:
        Усечённая строка.
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _safe_filename(name: str) -> str:
    """Создаёт безопасное имя файла из строки.

    Args:
        name: Исходная строка.

    Returns:
        Строка, пригодная для имени файла.
    """
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip()


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
# Создание идеи
# ---------------------------------------------------------------------------

def capture_idea(
    vault: Path,
    text: str,
    direction: str = "",
    priority: str = "",
    link: str = "",
    author: str = "",
) -> Path:
    """Создаёт заметку-идею в 09-СТРАТЕГИЯ/Идеи/.

    Args:
        vault: Путь к Obsidian vault.
        text: Текст идеи.
        direction: Направление.
        priority: Приоритет (не используется в шаблоне идеи, но принимается).
        link: Связанная цель или заметка.
        author: Автор идеи.

    Returns:
        Путь к созданному файлу.
    """
    today = date.today().isoformat()
    short_title = _truncate(text, 5)
    title_50 = text[:50]

    filename = f"Идея - {_safe_filename(short_title)}.md"
    target_dir = vault / "09-СТРАТЕГИЯ" / "Идеи"
    filepath = target_dir / filename

    author_link = f'"[[{author}]]"' if author else '""'
    link_ref = f"[[{link}]]" if link else "[[]]"

    content = f"""---
title: "Идея: {title_50}"
type: идея
направление: "{direction}"
автор: {author_link}
дата: {today}
статус: черновик
потенциал: средний
tags:
  - тип/идея
  - статус/черновик
---

# {title_50}

## Суть идеи

> [!tip] Ключевая мысль
> {text}

## Проблема, которую решает

## Предполагаемый результат

## Необходимые ресурсы

-

## Следующий шаг для проверки

- [ ] Первый шаг валидации

## Связанные цели

- {link_ref}
"""

    target_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    logger.info("Создана идея: %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# Создание события
# ---------------------------------------------------------------------------

def capture_event(
    vault: Path,
    text: str,
    direction: str = "",
    priority: str = "",
) -> Path:
    """Создаёт заметку-событие в 07-ОПЕРАЦИИ/.

    Args:
        vault: Путь к Obsidian vault.
        text: Описание события.
        direction: Направление.
        priority: Приоритет.

    Returns:
        Путь к созданному файлу.
    """
    today = date.today().isoformat()
    short_title = _truncate(text, 5)
    title_50 = text[:50]

    priority = priority or "средний"

    filename = f"{today} {_safe_filename(short_title)}.md"
    target_dir = vault / "07-ОПЕРАЦИИ"
    filepath = target_dir / filename

    content = f"""---
title: "Событие: {title_50} — {today}"
type: событие
дата: {today}
категория: заметка
направление: "{direction}"
приоритет: {priority}
статус: завершён
tags:
  - тип/событие
  - приоритет/{priority}
---

# {title_50} — {today}

## Описание

> [!note] Контекст
> {text}

## Принятые меры

1.

## Результат

"""

    target_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    logger.info("Создано событие: %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# Создание задачи (добавление в дневную запись)
# ---------------------------------------------------------------------------

def _create_daily_record(vault: Path, today: str) -> Path:
    """Создаёт дневную запись из шаблона.

    Args:
        vault: Путь к vault.
        today: Дата в формате ISO.

    Returns:
        Путь к созданному файлу.
    """
    target_dir = vault / "08-КАЛЕНДАРЬ"
    filepath = target_dir / f"{today}.md"

    content = f"""---
title: "{today}"
type: дневная_запись
дата: {today}
tags:
  - тип/календарь
---

# {today}

## Ключевые события дня

-

## Встречи и переговоры

- [[]]

## Задачи

- [ ]

## Выполнено

-

> [!note] Наблюдения
> Важные наблюдения и инсайты за день

## На завтра / на контроле

- [ ]
"""

    target_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    logger.info("Создана дневная запись: %s", filepath)
    return filepath


def capture_task(vault: Path, text: str) -> Path:
    """Добавляет задачу в дневную запись 08-КАЛЕНДАРЬ/.

    Если дневная запись не существует, создаёт её из шаблона.

    Args:
        vault: Путь к Obsidian vault.
        text: Текст задачи.

    Returns:
        Путь к дневной записи.
    """
    today = date.today().isoformat()
    target_dir = vault / "08-КАЛЕНДАРЬ"
    filepath = target_dir / f"{today}.md"

    if not filepath.exists():
        _create_daily_record(vault, today)

    content = filepath.read_text(encoding="utf-8")

    # Ищем секцию "## Задачи"
    task_line = f"- [ ] {text}"

    if "## Задачи" in content:
        # Находим позицию после "## Задачи" и вставляем задачу
        lines = content.splitlines()
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "## Задачи":
                insert_idx = i + 1
                # Пропускаем пустые строки после заголовка
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    insert_idx += 1
                break

        if insert_idx is not None:
            # Если следующая строка — пустой чекбокс "- [ ]" без текста, заменяем
            if (
                insert_idx < len(lines)
                and lines[insert_idx].strip() == "- [ ]"
            ):
                lines[insert_idx] = task_line
            else:
                lines.insert(insert_idx, task_line)
            content = "\n".join(lines)
        else:
            # Не нашли секцию — добавляем в конец
            content = content.rstrip() + f"\n\n{task_line}\n"
    else:
        # Нет секции — добавляем
        content = content.rstrip() + f"\n\n## Задачи\n\n{task_line}\n"

    filepath.write_text(content, encoding="utf-8")
    logger.info("Задача добавлена в %s: %s", filepath, text)
    return filepath


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
        description="Быстрое создание заметки из одной строки.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--type", dest="note_type", required=True,
        choices=["идея", "событие", "задача"],
        help="Тип заметки.",
    )
    parser.add_argument(
        "--text", required=True,
        help="Текст заметки / описание.",
    )
    parser.add_argument(
        "--direction", default="",
        help="Направление (для идей и событий).",
    )
    parser.add_argument(
        "--priority", default="",
        help="Приоритет (для событий).",
    )
    parser.add_argument(
        "--link", default="",
        help="Связанная заметка (для идей).",
    )
    parser.add_argument(
        "--author", default="",
        help="Автор (для идей).",
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

    if args.note_type == "идея":
        result_path = capture_idea(
            vault=args.vault,
            text=args.text,
            direction=args.direction,
            priority=args.priority,
            link=args.link,
            author=args.author,
        )
    elif args.note_type == "событие":
        result_path = capture_event(
            vault=args.vault,
            text=args.text,
            direction=args.direction,
            priority=args.priority,
        )
    elif args.note_type == "задача":
        result_path = capture_task(
            vault=args.vault,
            text=args.text,
        )
    else:
        logger.error("Неизвестный тип заметки: %s", args.note_type)
        sys.exit(1)

    logger.info("Результат: %s", result_path)


if __name__ == "__main__":
    main()
