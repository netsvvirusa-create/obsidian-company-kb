#!/usr/bin/env python3
"""Аудит внутренних ссылок (wikilinks) в Obsidian vault.

Сканирует все .md-файлы, проверяет существование целей ``[[ссылок]]``,
группирует битые ссылки по файлу-источнику. Флаг ``--fix`` создаёт
пустые карточки с минимальным frontmatter для несуществующих целей.
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

# Паттерн для wikilinks: [[target]] или [[target|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+?)(?:\|[^\]]*?)?\]\]")

# Паттерн для embed: ![[file]] — исключаем из проверки вложения
_EMBED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".webp",
    ".pdf", ".mp3", ".mp4", ".wav", ".webm",
}

# Папки, в которых создаём заглушки по типу
_TYPE_FOLDER_MAP: dict[str, str] = {
    "контрагент": "01-КОНТРАГЕНТЫ",
    "контакт": "05-КОНТАКТЫ",
    "сотрудник": "04-СОТРУДНИКИ",
    "договор": "02-ДОГОВОРЫ",
    "проект": "03-ПРОЕКТЫ",
}


# ---------------------------------------------------------------------------
# Построение индекса файлов vault
# ---------------------------------------------------------------------------

def build_file_index(vault: Path) -> dict[str, Path]:
    """Строит индекс ``{stem_lower: path}`` для всех .md-файлов в vault.

    Args:
        vault: Путь к vault.

    Returns:
        Словарь имя_без_расширения (нижний регистр) -> путь к файлу.
    """
    index: dict[str, Path] = {}
    for md in vault.rglob("*.md"):
        key = md.stem.lower()
        index[key] = md
    return index


# ---------------------------------------------------------------------------
# Извлечение wikilinks
# ---------------------------------------------------------------------------

def extract_wikilinks(text: str) -> list[str]:
    """Извлекает цели wikilinks из текста.

    Исключает ссылки на вложения (по расширению).

    Args:
        text: Текст .md-файла.

    Returns:
        Список имён целей (без ``[[`` и ``]]``).
    """
    targets: list[str] = []
    for match in _WIKILINK_RE.findall(text):
        target = match.strip()
        if not target:
            continue
        # Пропускаем вложения
        suffix = Path(target).suffix.lower()
        if suffix in _EMBED_EXTENSIONS:
            continue
        targets.append(target)
    return targets


# ---------------------------------------------------------------------------
# Определение типа для заглушки по контексту ссылки
# ---------------------------------------------------------------------------

def guess_type_from_context(
    link_target: str,
    source_fm: dict[str, Any],
    source_text: str,
) -> str | None:
    """Пытается угадать тип заметки по контексту ссылки.

    Args:
        link_target: Имя цели wikilink.
        source_fm: Frontmatter файла-источника.
        source_text: Полный текст файла-источника.

    Returns:
        Предполагаемый тип или ``None``.
    """
    target_lower = link_target.lower()

    # По шаблонам в имени
    if target_lower.startswith("договор"):
        return "договор"

    # Если в имени есть скобки — скорее всего контакт: "Фамилия Имя (Контрагент)"
    if "(" in link_target and ")" in link_target:
        return "контакт"

    # По полям frontmatter источника
    src_type = source_fm.get("type", "")
    if src_type == "контрагент":
        # ссылки из карточки контрагента — вероятно контакты
        return "контакт"

    return None


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Извлекает YAML-свойства из frontmatter.

    Args:
        text: Полный текст .md-файла.

    Returns:
        Словарь ключ-значение.
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
# Создание заглушки
# ---------------------------------------------------------------------------

def create_stub(vault: Path, link_target: str, note_type: str | None) -> Path | None:
    """Создаёт пустую карточку с минимальным frontmatter.

    Args:
        vault: Путь к vault.
        link_target: Имя целевой заметки.
        note_type: Тип заметки (если определён).

    Returns:
        Путь к созданному файлу или ``None``.
    """
    today = date.today().isoformat()
    safe_name = re.sub(r'[<>:"/\\|?*]', "", link_target).strip()

    if note_type and note_type in _TYPE_FOLDER_MAP:
        folder = vault / _TYPE_FOLDER_MAP[note_type]
    else:
        folder = vault / "00-INBOX"
        note_type = note_type or "заглушка"

    folder.mkdir(parents=True, exist_ok=True)
    filepath = folder / f"{safe_name}.md"

    if filepath.exists():
        return None

    content = f"""---
title: "{link_target}"
type: {note_type}
статус: черновик
дата_создания: {today}
tags:
  - статус/черновик
---

# {link_target}

> [!warning] Автоматически созданная заглушка
> Эта заметка создана скриптом audit_links.py, так как на неё ссылаются
> другие заметки vault. Заполните содержимое вручную.
"""

    filepath.write_text(content, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Основная логика аудита
# ---------------------------------------------------------------------------

def audit_links(vault: Path, fix: bool = False) -> dict[str, list[str]]:
    """Сканирует vault и находит битые wikilinks.

    Args:
        vault: Путь к vault.
        fix: Если ``True``, создаёт заглушки для битых ссылок.

    Returns:
        Словарь ``{файл-источник: [список битых ссылок]}``.
    """
    file_index = build_file_index(vault)
    broken: dict[str, list[str]] = {}
    all_broken_targets: set[str] = set()
    # Храним контексты для fix
    target_contexts: dict[str, tuple[dict[str, Any], str]] = {}

    for md in sorted(vault.rglob("*.md")):
        # Пропускаем .obsidian и скрытые папки
        parts = md.relative_to(vault).parts
        if any(p.startswith(".") for p in parts):
            continue

        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        links = extract_wikilinks(text)

        file_broken: list[str] = []
        for target in links:
            target_key = target.lower()
            if target_key not in file_index:
                file_broken.append(target)
                all_broken_targets.add(target)
                if target not in target_contexts:
                    target_contexts[target] = (fm, text)

        if file_broken:
            rel = str(md.relative_to(vault))
            # Убираем дубликаты, сохраняя порядок
            seen: set[str] = set()
            unique: list[str] = []
            for t in file_broken:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            broken[rel] = unique

    # Создание заглушек
    if fix and all_broken_targets:
        created = 0
        for target in sorted(all_broken_targets):
            ctx_fm, ctx_text = target_contexts.get(target, ({}, ""))
            note_type = guess_type_from_context(target, ctx_fm, ctx_text)
            result = create_stub(vault, target, note_type)
            if result:
                logger.info("Создана заглушка: %s", result.relative_to(vault))
                created += 1
        logger.info("Всего создано заглушек: %d", created)

    return broken


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
        description="Аудит внутренних ссылок (wikilinks) в Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--fix", action="store_true", default=False,
        help="Создать пустые карточки для битых ссылок.",
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

    broken = audit_links(args.vault, fix=args.fix)

    if not broken:
        logger.info("Битых ссылок не найдено.")
        return

    total = sum(len(v) for v in broken.values())
    unique_targets = len({t for targets in broken.values() for t in targets})

    print(f"\n=== Битые ссылки ===\n")
    print(f"Файлов с битыми ссылками: {len(broken)}")
    print(f"Всего битых ссылок: {total}")
    print(f"Уникальных целей: {unique_targets}")
    print()

    for source, targets in sorted(broken.items()):
        print(f"  {source}:")
        for t in targets:
            print(f"    -> [[{t}]]")
        print()


if __name__ == "__main__":
    main()
