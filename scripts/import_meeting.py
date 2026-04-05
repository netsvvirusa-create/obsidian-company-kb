#!/usr/bin/env python3
"""Импорт резюме встречи из файла в заметку type:переговоры в 06-ПЕРЕГОВОРЫ/.

Поддерживает форматы: plain text, транскрипция (Whisper/Otter), .docx.
Автоматически извлекает участников, решения, задачи и темы обсуждений.
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
# Регулярные выражения для извлечения данных
# ---------------------------------------------------------------------------

# ФИО: "Иванов Иван Иванович" или "Иванов Иван"
_RE_FIO_FULL = re.compile(
    r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)"
)
# ФИО сокращённое: "Иванов И.И."
_RE_FIO_SHORT = re.compile(
    r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)"
)

# Ключевые слова решений
_RE_DECISION = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*(?:решено|договорились|согласовано|утверждено)"
    r"[:\s]+(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Ключевые слова задач
_RE_TASK = re.compile(
    r"(?:^|\n)\s*[-•*]?\s*(?:поручить|выполнить|сделать|подготовить)"
    r"[:\s]+(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Дата в тексте (ГГГГ-ММ-ДД или ДД.ММ.ГГГГ)
_RE_DATE_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")
_RE_DATE_RU = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

# Временные метки транскрипции
_RE_TIMESTAMP = re.compile(r"\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*")
_RE_SPEAKER = re.compile(r"^(?:Speaker\s*\d+|Говорящий\s*\d+)\s*:\s*", re.IGNORECASE)

# Паттерн для определения формата транскрипции
_RE_TRANSCRIPT_PATTERN = re.compile(
    r"(?:\[\d{1,2}:\d{2}(?::\d{2})?\]|Speaker\s*\d+\s*:|Говорящий\s*\d+\s*:)",
    re.IGNORECASE,
)


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
# Безопасное имя файла
# ---------------------------------------------------------------------------

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
# Определение формата файла
# ---------------------------------------------------------------------------

def detect_format(filepath: Path) -> str:
    """Определяет формат входного файла.

    Args:
        filepath: Путь к файлу.

    Returns:
        Строка формата: ``text``, ``transcript`` или ``docx``.
    """
    suffix = filepath.suffix.lower()
    if suffix == ".docx":
        return "docx"
    # Для .txt / .md — проверяем наличие временных меток
    if suffix in (".txt", ".md", ""):
        try:
            text = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = filepath.read_text(encoding="cp1251")
        matches = _RE_TRANSCRIPT_PATTERN.findall(text)
        if len(matches) >= 3:
            return "transcript"
        return "text"
    return "text"


# ---------------------------------------------------------------------------
# Извлечение участников
# ---------------------------------------------------------------------------

def extract_participants(text: str) -> list[str]:
    """Извлекает ФИО участников из текста.

    Args:
        text: Текст встречи.

    Returns:
        Список уникальных ФИО.
    """
    found: list[str] = []
    # Сначала полные ФИО
    for m in _RE_FIO_FULL.finditer(text):
        name = m.group(1).strip()
        if name not in found:
            found.append(name)
    # Затем сокращённые (И.И.)
    for m in _RE_FIO_SHORT.finditer(text):
        name = m.group(1).strip()
        if name not in found:
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Извлечение решений
# ---------------------------------------------------------------------------

def extract_decisions(text: str) -> list[str]:
    """Извлекает решения из текста.

    Args:
        text: Текст встречи.

    Returns:
        Список решений.
    """
    decisions: list[str] = []
    for m in _RE_DECISION.finditer(text):
        decision = m.group(1).strip()
        if decision and decision not in decisions:
            decisions.append(decision)
    return decisions


# ---------------------------------------------------------------------------
# Извлечение задач
# ---------------------------------------------------------------------------

def extract_tasks(text: str) -> list[str]:
    """Извлекает задачи из текста.

    Args:
        text: Текст встречи.

    Returns:
        Список задач.
    """
    tasks: list[str] = []
    for m in _RE_TASK.finditer(text):
        task = m.group(1).strip()
        if task and task not in tasks:
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Извлечение тем
# ---------------------------------------------------------------------------

def _extract_topics(text: str) -> list[str]:
    """Извлекает темы обсуждений из текста.

    Ищет заголовки, пункты повестки, нумерованные списки в начале.

    Args:
        text: Текст встречи.

    Returns:
        Список тем.
    """
    topics: list[str] = []
    # Ищем строки вида "Повестка:", "Тема:", нумерованные пункты в начале
    header_re = re.compile(
        r"(?:повестка|тема|agenda|вопрос)\s*[:\-]\s*(.+)",
        re.IGNORECASE,
    )
    for m in header_re.finditer(text):
        topic = m.group(1).strip()
        if topic and topic not in topics:
            topics.append(topic)

    # Нумерованные пункты в первой четверти текста
    first_quarter = text[: len(text) // 4]
    numbered_re = re.compile(r"^\s*\d+[.)]\s+(.+)", re.MULTILINE)
    for m in numbered_re.finditer(first_quarter):
        topic = m.group(1).strip()
        if topic and topic not in topics and len(topic) < 120:
            topics.append(topic)

    return topics


# ---------------------------------------------------------------------------
# Извлечение даты из текста
# ---------------------------------------------------------------------------

def _extract_date(text: str) -> str | None:
    """Пытается извлечь дату из текста.

    Args:
        text: Текст встречи.

    Returns:
        Дата в формате ISO или ``None``.
    """
    m = _RE_DATE_ISO.search(text)
    if m:
        return m.group(1)
    m = _RE_DATE_RU.search(text)
    if m:
        parts = m.group(1).split(".")
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return None


# ---------------------------------------------------------------------------
# Парсинг plain text
# ---------------------------------------------------------------------------

def parse_text(text: str) -> dict[str, Any]:
    """Парсит plain text (чат-лог, email, заметки).

    Args:
        text: Нормализованный текст.

    Returns:
        Словарь с ключами: participants, decisions, tasks, topics.
    """
    return {
        "participants": extract_participants(text),
        "decisions": extract_decisions(text),
        "tasks": extract_tasks(text),
        "topics": _extract_topics(text),
    }


# ---------------------------------------------------------------------------
# Парсинг транскрипции
# ---------------------------------------------------------------------------

def parse_transcript(text: str) -> dict[str, Any]:
    """Парсит транскрипцию (Whisper/Otter формат с временными метками).

    Удаляет временные метки, группирует по спикерам, извлекает решения.

    Args:
        text: Текст транскрипции.

    Returns:
        Словарь с ключами: participants, decisions, tasks, topics.
    """
    # Убираем временные метки
    cleaned = _RE_TIMESTAMP.sub("", text)
    # Убираем маркеры спикеров, оставляя текст
    cleaned = _RE_SPEAKER.sub("", cleaned)

    return {
        "participants": extract_participants(cleaned),
        "decisions": extract_decisions(cleaned),
        "tasks": extract_tasks(cleaned),
        "topics": _extract_topics(cleaned),
    }


# ---------------------------------------------------------------------------
# Парсинг .docx
# ---------------------------------------------------------------------------

def parse_docx(filepath: Path) -> str:
    """Читает .docx-файл и возвращает plain text.

    Args:
        filepath: Путь к .docx-файлу.

    Returns:
        Текстовое содержимое документа.

    Raises:
        SystemExit: Если библиотека python-docx не установлена.
    """
    try:
        import docx  # noqa: WPS433
    except ImportError:
        logger.error(
            "Библиотека python-docx не установлена. "
            "Установите: pip install python-docx"
        )
        sys.exit(1)

    doc = docx.Document(str(filepath))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Нормализация текста
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Нормализует текст: пробелы, переводы строк.

    Args:
        text: Исходный текст.

    Returns:
        Нормализованный текст.
    """
    # Нормализуем переводы строк
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Убираем множественные пробелы (но не переводы строк)
    text = re.sub(r"[^\S\n]+", " ", text)
    # Убираем множественные пустые строки
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Построение заметки переговоров
# ---------------------------------------------------------------------------

def build_meeting_note(
    data: dict[str, Any],
    date_str: str,
    counterparty: str,
) -> str:
    """Генерирует содержимое .md для заметки переговоров.

    Args:
        data: Словарь с извлечёнными данными (participants, decisions, tasks, topics).
        date_str: Дата в формате ISO.
        counterparty: Название контрагента (может быть пустым).

    Returns:
        Полный текст .md-файла.
    """
    participants = data.get("participants", [])
    decisions = data.get("decisions", [])
    tasks = data.get("tasks", [])
    topics = data.get("topics", [])

    first_topic = topics[0] if topics else "Встреча"
    title = f"Переговоры: {first_topic} — {date_str}"

    # Frontmatter: участники
    participants_yaml = ""
    if participants:
        items = "\n".join(f'  - "[[{p}]]"' for p in participants)
        participants_yaml = f"участники_наши:\n{items}"
    else:
        participants_yaml = "участники_наши: []"

    cp_link = f'"[[{counterparty}]]"' if counterparty else '""'

    theme = first_topic if topics else ""

    fm = f"""---
title: "{title}"
type: переговоры
дата: {date_str}
время: ""
формат: ""
{participants_yaml}
участники_контрагента: []
контрагент: {cp_link}
тема: "{theme}"
статус: завершён
tags:
  - тип/переговоры
  - статус/завершён
---"""

    # Тело: участники
    participants_section = ""
    if participants:
        lines = "\n".join(f"> - [[{p}]]" for p in participants)
        participants_section = f"""> [!info] Участники
{lines}"""
    else:
        participants_section = "> [!info] Участники\n> (не определены)"

    # Повестка
    if topics:
        agenda_items = "\n".join(f"{i}. {t}" for i, t in enumerate(topics, 1))
    else:
        agenda_items = "1. (тема не определена)"

    # Решения
    if decisions:
        decisions_lines = "\n\n".join(
            f"### Решение {i}\n\n- **Решение:** {d}"
            for i, d in enumerate(decisions, 1)
        )
    else:
        decisions_lines = "### (решения не извлечены)\n\n- **Обсуждение:**\n- **Решение:**"

    # Задачи
    if tasks:
        tasks_lines = "\n".join(f"- [ ] {t}" for t in tasks)
    else:
        tasks_lines = "- [ ] (задачи не извлечены)"

    # Связанные заметки
    related = ""
    if counterparty:
        related = f"- [[{counterparty}]]"
    else:
        related = "- [[]]"

    body = f"""

# {title}

## Участники

{participants_section}

## Повестка

{agenda_items}

## Ключевые обсуждения и решения

{decisions_lines}

## Следующие шаги

{tasks_lines}

> [!question] Открытые вопросы
> -

## Связанные заметки

{related}
"""

    return fm + body


# ---------------------------------------------------------------------------
# Создание контактных карточек
# ---------------------------------------------------------------------------

def _create_contact_cards(
    vault: Path,
    participants: list[str],
    counterparty: str,
    dry_run: bool,
) -> list[str]:
    """Создаёт карточки контактов для новых участников.

    Args:
        vault: Путь к vault.
        participants: Список ФИО участников.
        counterparty: Название контрагента.
        dry_run: Если ``True``, только показывает, что будет создано.

    Returns:
        Список путей к созданным файлам.
    """
    contacts_dir = vault / "05-КОНТАКТЫ"
    today = date.today().isoformat()
    created: list[str] = []

    for name in participants:
        if counterparty:
            filename = f"{_safe_filename(name)} ({_safe_filename(counterparty)}).md"
        else:
            filename = f"{_safe_filename(name)}.md"

        filepath = contacts_dir / filename
        if filepath.exists():
            logger.debug("Контакт '%s' уже существует — пропущен.", filename)
            continue

        cp_link = f"[[{counterparty}]]" if counterparty else ""
        first_name = name.split()[0] if name.split() else name

        content = f"""---
title: "{name}"
type: контакт
контрагент: "{cp_link}"
роль: ""
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

# {name}

## Быстрая справка

- **Контрагент:** {cp_link}
- **Роль / Должность:**
- **Рабочий телефон:**
- **Email рабочий:**

^быстрая-справка

## Контактные данные

> [!info]- Телефоны
> - **Рабочий:**

> [!info]- Электронная почта
> - **Рабочий email:**

## История взаимодействия

| Дата | Событие | Заметки |
|------|---------|---------|
| {today} | Участие во встрече | |

## Заметки и особенности

-
"""
        if dry_run:
            logger.info("[DRY-RUN] Будет создан контакт: %s", filepath)
        else:
            contacts_dir.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            logger.info("Создан контакт: %s", filepath)
        created.append(str(filepath))

    return created


# ---------------------------------------------------------------------------
# Основная логика импорта
# ---------------------------------------------------------------------------

def import_meeting(
    vault: Path,
    filepath: Path,
    counterparty: str = "",
    date_str: str = "",
    fmt: str = "auto",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Импортирует резюме встречи и создаёт заметку переговоров.

    Args:
        vault: Путь к Obsidian vault.
        filepath: Путь к файлу встречи.
        counterparty: Название контрагента.
        date_str: Дата встречи (ГГГГ-ММ-ДД). Если пусто — извлекается из текста.
        fmt: Формат файла (auto / text / transcript / docx).
        dry_run: Если ``True``, только показывает, что будет создано.

    Returns:
        Словарь с результатами: note_path, contacts_created, data.
    """
    # Определяем формат
    if fmt == "auto":
        fmt = detect_format(filepath)
        logger.info("Определён формат файла: %s", fmt)

    # Читаем и парсим файл
    if fmt == "docx":
        raw_text = parse_docx(filepath)
    else:
        try:
            raw_text = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw_text = filepath.read_text(encoding="cp1251")

    text = _normalize_text(raw_text)

    if not text:
        logger.error("Файл пуст: %s", filepath)
        return {"note_path": None, "contacts_created": [], "data": {}}

    # Парсим в зависимости от формата
    if fmt == "transcript":
        data = parse_transcript(text)
    else:
        data = parse_text(text)

    # Определяем дату
    if not date_str:
        extracted_date = _extract_date(text)
        if extracted_date:
            date_str = extracted_date
            logger.info("Дата извлечена из текста: %s", date_str)
        else:
            date_str = date.today().isoformat()
            logger.info("Дата не найдена, используется сегодняшняя: %s", date_str)

    # Генерируем заметку
    note_content = build_meeting_note(data, date_str, counterparty)

    # Формируем имя файла
    topics = data.get("topics", [])
    if counterparty:
        name_part = counterparty
    elif topics:
        name_part = topics[0][:50]
    else:
        name_part = "Встреча"

    filename = f"{date_str} {_safe_filename(name_part)}.md"
    target_dir = vault / "06-ПЕРЕГОВОРЫ"
    note_path = target_dir / filename

    if dry_run:
        logger.info("[DRY-RUN] Будет создана заметка: %s", note_path)
        logger.info("[DRY-RUN] Участники: %s", ", ".join(data.get("participants", [])))
        logger.info("[DRY-RUN] Решения: %d", len(data.get("decisions", [])))
        logger.info("[DRY-RUN] Задачи: %d", len(data.get("tasks", [])))
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        note_path.write_text(note_content, encoding="utf-8")
        logger.info("Создана заметка переговоров: %s", note_path)

    # Создаём контактные карточки
    contacts_created: list[str] = []
    if counterparty and data.get("participants"):
        contacts_created = _create_contact_cards(
            vault, data["participants"], counterparty, dry_run,
        )

    return {
        "note_path": str(note_path),
        "contacts_created": contacts_created,
        "data": data,
    }


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
        description="Импорт резюме встречи из файла в Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--file", type=Path, required=True,
        help="Путь к файлу встречи (.txt, .md, .docx).",
    )
    parser.add_argument(
        "--counterparty", default="",
        help="Название контрагента для привязки.",
    )
    parser.add_argument(
        "--date", dest="date_str", default="",
        help="Дата встречи в формате ГГГГ-ММ-ДД.",
    )
    parser.add_argument(
        "--format", dest="fmt", default="auto",
        choices=["auto", "text", "transcript", "docx"],
        help="Формат входного файла (по умолчанию: auto).",
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
        logger.error("Файл не найден: %s", args.file)
        sys.exit(1)

    result = import_meeting(
        vault=args.vault,
        filepath=args.file,
        counterparty=args.counterparty,
        date_str=args.date_str,
        fmt=args.fmt,
        dry_run=args.dry_run,
    )

    if result["note_path"]:
        action = "будет создана" if args.dry_run else "создана"
        logger.info("Заметка %s: %s", action, result["note_path"])
        if result["contacts_created"]:
            logger.info(
                "Контактов %s: %d",
                "будет создано" if args.dry_run else "создано",
                len(result["contacts_created"]),
            )
    else:
        logger.error("Не удалось создать заметку.")
        sys.exit(1)


if __name__ == "__main__":
    main()
