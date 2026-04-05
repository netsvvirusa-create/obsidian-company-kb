"""Скрипт синхронизации обратных связей в базе знаний Obsidian.

Сканирует файлы сотрудников и контактов, проверяет наличие обратных
wikilink-связей в YAML-frontmatter и в таблице «Связи и отношения».
Может автоматически добавлять недостающие обратные ссылки (--fix)
или только показывать отчёт (--dry-run).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Зеркальные описания связей ──────────────────────────────────────────────

MIRROR_DESCRIPTIONS: dict[str, str] = {
    "руководит": "подчиняется",
    "подчиняется": "руководит",
    "является наставником": "является подопечным",
    "является подопечным": "является наставником",
    "является родителем": "является ребёнком",
    "является ребёнком": "является родителем",
    "является супругом/ой": "является супругом/ой",
    "является другом": "является другом",
    "является однокурсником": "является однокурсником",
    "рекомендовал": "рекомендован",
    "рекомендован": "рекомендовал",
    "инвестирует в": "получает инвестиции от",
    "получает инвестиции от": "инвестирует в",
    "является братом/сестрой": "является братом/сестрой",
}

# ── Вспомогательные функции ──────────────────────────────────────────────────


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Разделяет содержимое файла на frontmatter и тело.

    Args:
        text: Полное содержимое Markdown-файла.

    Returns:
        Кортеж (frontmatter_без_разделителей, тело_после_frontmatter).
        Если frontmatter отсутствует, первый элемент — пустая строка.
    """
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return parts[1].strip(), parts[2]


def _extract_wikilinks(value: str) -> list[str]:
    """Извлекает имена из [[wikilink]] в строке.

    Args:
        value: Строка, содержащая wikilink-ссылки.

    Returns:
        Список имён без квадратных скобок.
    """
    return re.findall(r"\[\[([^\]]+)\]\]", value)


def _parse_связи_yaml(frontmatter: str) -> list[str]:
    """Парсит список ``связи`` из YAML-frontmatter.

    Args:
        frontmatter: Текст frontmatter без разделителей ``---``.

    Returns:
        Список имён, на которые указывают wikilink-ссылки в поле ``связи``.
    """
    links: list[str] = []
    in_section = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("связи:"):
            in_section = True
            # связи: [[Кто-то]] — однострочный вариант
            inline = stripped[len("связи:"):].strip()
            if inline and inline != "[]":
                links.extend(_extract_wikilinks(inline))
            continue
        if in_section:
            if stripped.startswith("- "):
                links.extend(_extract_wikilinks(stripped))
            else:
                in_section = False
    return links


def _parse_связи_table(body: str) -> list[dict[str, str]]:
    """Парсит таблицу из раздела «## Связи и отношения» в теле файла.

    Ожидаемый формат таблицы:
        | Персона | Тип связи | Описание |
        |---------|-----------|----------|
        | [[Имя]] | тип       | ...      |

    Args:
        body: Тело Markdown-файла (после frontmatter).

    Returns:
        Список словарей с ключами ``person``, ``type``, ``description``.
    """
    rows: list[dict[str, str]] = []
    in_section = False
    header_passed = False

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Связи и отношения"):
            in_section = True
            header_passed = False
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        if not stripped.startswith("|"):
            if header_passed and stripped == "":
                continue
            if header_passed and not stripped.startswith("|"):
                break
            continue
        # Пропускаем заголовок и разделитель
        if "---" in stripped:
            header_passed = True
            continue
        if not header_passed:
            header_passed = False
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) >= 2:
            persons = _extract_wikilinks(cells[0])
            rel_type = cells[1].strip() if len(cells) > 1 else ""
            desc = cells[2].strip() if len(cells) > 2 else ""
            for person in persons:
                rows.append({"person": person, "type": rel_type, "description": desc})
    return rows


def _build_file_index(vault: Path) -> dict[str, Path]:
    """Строит индекс имя_файла→путь для всех .md в целевых папках.

    Args:
        vault: Корневой путь хранилища Obsidian.

    Returns:
        Словарь, где ключ — имя файла без расширения, значение — Path.
    """
    index: dict[str, Path] = {}
    for folder in ("04-СОТРУДНИКИ", "05-КОНТАКТЫ"):
        target = vault / folder
        if not target.exists():
            logger.warning("Папка %s не найдена, пропускаем.", target)
            continue
        for md_file in target.rglob("*.md"):
            index[md_file.stem] = md_file
    return index


def _mirror_description(description: str) -> str:
    """Возвращает зеркальное описание связи.

    Args:
        description: Описание связи от A к B.

    Returns:
        Описание связи от B к A. Если зеркало не найдено, возвращается
        исходное описание.
    """
    normalized = description.strip().lower()
    for key, value in MIRROR_DESCRIPTIONS.items():
        if normalized == key.lower():
            return value
    return description


# ── Добавление обратных связей ───────────────────────────────────────────────


def _add_yaml_link(frontmatter: str, target_name: str) -> str:
    """Добавляет wikilink в список ``связи`` в frontmatter.

    Args:
        frontmatter: Текст frontmatter без разделителей ``---``.
        target_name: Имя персоны для добавления.

    Returns:
        Обновлённый frontmatter.
    """
    link_entry = f"  - \"[[{target_name}]]\""
    lines = frontmatter.splitlines()
    insert_idx: Optional[int] = None
    in_section = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("связи:"):
            in_section = True
            # Если связи: [] — заменяем на список
            if stripped == "связи: []" or stripped == "связи:":
                lines[i] = "связи:"
            continue
        if in_section:
            if stripped.startswith("- "):
                insert_idx = i + 1
            else:
                if insert_idx is None:
                    insert_idx = i
                in_section = False
                break

    if insert_idx is not None:
        lines.insert(insert_idx, link_entry)
    else:
        # Поле связи отсутствует — добавляем в конец
        lines.append("связи:")
        lines.append(link_entry)

    return "\n".join(lines)


def _add_table_row(body: str, target_name: str, rel_type: str, description: str) -> str:
    """Добавляет строку в таблицу раздела «## Связи и отношения».

    Args:
        body: Тело Markdown-файла.
        target_name: Имя персоны.
        rel_type: Тип связи.
        description: Описание связи.

    Returns:
        Обновлённое тело файла.
    """
    new_row = f"| [[{target_name}]] | {rel_type} | {description} |"
    lines = body.splitlines()
    insert_idx: Optional[int] = None
    in_section = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Связи и отношения"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            insert_idx = i
            break
        if in_section and stripped.startswith("|"):
            insert_idx = i + 1

    if insert_idx is not None:
        lines.insert(insert_idx, new_row)
    elif in_section:
        lines.append(new_row)
    else:
        # Раздел отсутствует — создаём
        lines.append("")
        lines.append("## Связи и отношения")
        lines.append("")
        lines.append("| Персона | Тип связи | Описание |")
        lines.append("|---------|-----------|----------|")
        lines.append(new_row)

    return "\n".join(lines)


def _fix_file(
    file_path: Path,
    target_name: str,
    rel_type: str,
    description: str,
) -> None:
    """Добавляет обратную связь в файл (frontmatter + таблица).

    Args:
        file_path: Путь к файлу, в который нужно добавить связь.
        target_name: Имя персоны, на которую указывает обратная связь.
        rel_type: Тип связи.
        description: Описание обратной связи.
    """
    text = file_path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)

    frontmatter = _add_yaml_link(frontmatter, target_name)
    body = _add_table_row(body, target_name, rel_type, description)

    new_text = f"---\n{frontmatter}\n---{body}"
    file_path.write_text(new_text, encoding="utf-8")
    logger.info("Обновлён файл: %s (добавлена связь → %s)", file_path.name, target_name)


# ── Основная логика ──────────────────────────────────────────────────────────


def sync_relationships(
    vault: Path,
    fix: bool = False,
    dry_run: bool = False,
) -> dict:
    """Проверяет и синхронизирует обратные связи между персонами.

    Args:
        vault: Корневой путь хранилища Obsidian.
        fix: Если True, автоматически добавляет недостающие обратные связи.
        dry_run: Если True, только показывает, что было бы исправлено.

    Returns:
        Словарь с результатами проверки в формате JSON-совместимого объекта.
    """
    file_index = _build_file_index(vault)
    if not file_index:
        logger.error("Не найдено ни одного .md файла в целевых папках.")
        return {"checked": 0, "missing_reverse": 0, "issues": []}

    issues: list[dict[str, str]] = []
    checked = 0

    for name_a, path_a in file_index.items():
        text_a = path_a.read_text(encoding="utf-8")
        fm_a, body_a = _split_frontmatter(text_a)
        links_a = _parse_связи_yaml(fm_a)
        table_a = _parse_связи_table(body_a)

        for link_b in links_a:
            checked += 1

            if link_b not in file_index:
                logger.warning(
                    "Связь %s → [[%s]]: файл «%s» не найден в индексе.",
                    name_a, link_b, link_b,
                )
                continue

            path_b = file_index[link_b]
            text_b = path_b.read_text(encoding="utf-8")
            fm_b, body_b = _split_frontmatter(text_b)
            links_b = _parse_связи_yaml(fm_b)

            if name_a in links_b:
                continue

            # Обратная связь отсутствует
            issue = {
                "person_a": name_a,
                "person_b": link_b,
                "direction": f"{name_a}→{link_b} существует, {link_b}→{name_a} отсутствует",
            }
            issues.append(issue)
            logger.info(
                "Отсутствует обратная связь: %s → %s", link_b, name_a,
            )

            # Определяем описание обратной связи из таблицы A
            rel_type = ""
            description = ""
            for row in table_a:
                if row["person"] == link_b:
                    rel_type = row["type"]
                    description = _mirror_description(row["description"])
                    break

            if dry_run:
                logger.info(
                    "[DRY-RUN] Было бы добавлено: %s ← связь → %s "
                    "(тип: %s, описание: %s)",
                    link_b, name_a, rel_type, description,
                )

            if fix and not dry_run:
                _fix_file(path_b, name_a, rel_type, description)

    # Проверка согласованности таблицы и frontmatter внутри файла
    for name, path in file_index.items():
        text = path.read_text(encoding="utf-8")
        fm, body = _split_frontmatter(text)
        yaml_links = set(_parse_связи_yaml(fm))
        table_rows = _parse_связи_table(body)
        table_persons = {row["person"] for row in table_rows}

        for person in table_persons - yaml_links:
            logger.warning(
                "Рассогласование в %s: [[%s]] есть в таблице, "
                "но отсутствует в YAML-связях.",
                name, person,
            )

        for person in yaml_links - table_persons:
            logger.warning(
                "Рассогласование в %s: [[%s]] есть в YAML-связях, "
                "но отсутствует в таблице.",
                name, person,
            )

    result: dict = {
        "checked": checked,
        "missing_reverse": len(issues),
        "issues": issues,
    }
    if fix and not dry_run:
        result["fixed"] = len(issues)

    return result


# ── CLI ──────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки.

    Returns:
        Настроенный ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Синхронизация обратных связей в базе знаний Obsidian.",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        required=True,
        help="Путь к корневой папке хранилища Obsidian.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        default=False,
        help="Автоматически добавить недостающие обратные связи.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Только показать, что было бы исправлено (без записи).",
    )
    return parser


def main() -> None:
    """Точка входа CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    vault_path: Path = args.vault.resolve()
    if not vault_path.is_dir():
        logger.error("Указанный путь не является директорией: %s", vault_path)
        sys.exit(1)

    result = sync_relationships(
        vault=vault_path,
        fix=args.fix,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
