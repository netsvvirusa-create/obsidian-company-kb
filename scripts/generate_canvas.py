#!/usr/bin/env python3
"""Генерация .canvas файлов из данных Obsidian vault.

Типы канвасов:
- contract-participants: участники договора (наша сторона и контрагент).
- person-relationships: связи персоны (сотрудника или контакта).
- project-roadmap: дорожная карта проекта (этапы / милестоуны).
- counterparty-map: карта контрагентов компании.

Результат сохраняется в папку 12-КАНВАСЫ/ внутри vault.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

CANVAS_DIR = "12-КАНВАСЫ"

NODE_W = 260
NODE_H = 60
GROUP_PADDING = 40

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]*?)?\]\]")


# ---------------------------------------------------------------------------
# Вспомогательные функции: идентификаторы и структуры
# ---------------------------------------------------------------------------


def _gen_id() -> str:
    """Генерирует 16-символьный шестнадцатеричный идентификатор.

    Returns:
        Случайная строка из 16 hex-символов.
    """
    return os.urandom(8).hex()


def _make_node(
    node_id: str,
    node_type: str,
    x: int,
    y: int,
    w: int,
    h: int,
    **kwargs: Any,
) -> dict[str, Any]:
    """Создаёт словарь узла канваса.

    Args:
        node_id: Уникальный идентификатор узла.
        node_type: Тип узла (``text`` или ``file``).
        x: Координата X (левый верхний угол).
        y: Координата Y (левый верхний угол).
        w: Ширина.
        h: Высота.
        **kwargs: Дополнительные поля (``text``, ``file``, ``label``, ``color``).

    Returns:
        Словарь с описанием узла.
    """
    node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
    node.update(kwargs)
    return node


def _make_edge(
    edge_id: str,
    from_node: str,
    to_node: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Создаёт словарь ребра канваса.

    Args:
        edge_id: Уникальный идентификатор ребра.
        from_node: ID узла-источника.
        to_node: ID узла-приёмника.
        **kwargs: Дополнительные поля (``label``, ``fromSide``, ``toSide``).

    Returns:
        Словарь с описанием ребра.
    """
    edge: dict[str, Any] = {
        "id": edge_id,
        "fromNode": from_node,
        "toNode": to_node,
    }
    edge.update(kwargs)
    return edge


# ---------------------------------------------------------------------------
# Вспомогательные функции: расположение (layout)
# ---------------------------------------------------------------------------


def layout_radial(
    cx: int,
    cy: int,
    radius: int,
    count: int,
) -> list[tuple[int, int]]:
    """Вычисляет координаты точек по окружности.

    Args:
        cx: Центр X.
        cy: Центр Y.
        radius: Радиус.
        count: Количество точек.

    Returns:
        Список кортежей (x, y).
    """
    if count == 0:
        return []
    positions: list[tuple[int, int]] = []
    for i in range(count):
        angle = 2 * math.pi * i / count - math.pi / 2
        x = int(cx + radius * math.cos(angle))
        y = int(cy + radius * math.sin(angle))
        positions.append((x, y))
    return positions


def layout_tree(
    x: int,
    y: int,
    children_count: int,
    spacing: int = 200,
) -> list[tuple[int, int]]:
    """Вычисляет координаты для дерева «сверху-вниз».

    Args:
        x: X-координата корня.
        y: Y-координата первого ряда дочерних элементов.
        children_count: Количество дочерних элементов.
        spacing: Расстояние между элементами по горизонтали.

    Returns:
        Список кортежей (x, y) для дочерних элементов.
    """
    if children_count == 0:
        return []
    total_w = (children_count - 1) * spacing
    start_x = x - total_w // 2
    return [(start_x + i * spacing, y) for i in range(children_count)]


def layout_timeline(
    x_start: int,
    y: int,
    count: int,
    spacing: int = 350,
) -> list[tuple[int, int]]:
    """Вычисляет координаты для линейной шкалы (слева направо).

    Args:
        x_start: Начальная X-координата.
        y: Y-координата (одинаковая для всех).
        count: Количество элементов.
        spacing: Расстояние между элементами.

    Returns:
        Список кортежей (x, y).
    """
    return [(x_start + i * spacing, y) for i in range(count)]


# ---------------------------------------------------------------------------
# Парсинг
# ---------------------------------------------------------------------------


def parse_frontmatter(filepath: Path) -> dict[str, Any]:
    """Извлекает YAML-свойства из frontmatter файла, разделённого ``---``.

    Args:
        filepath: Путь к .md-файлу.

    Returns:
        Словарь ключ-значение из frontmatter.
    """
    text = filepath.read_text(encoding="utf-8")
    return parse_frontmatter_text(text)


def parse_frontmatter_text(text: str) -> dict[str, Any]:
    """Извлекает YAML-свойства из текста frontmatter.

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
            # Обработка списков вида "[a, b, c]"
            if val.startswith("[") and val.endswith("]"):
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                result[key] = [v for v in items if v]
            else:
                result[key] = val
    return result


def _extract_wikilinks(text: str) -> list[str]:
    """Извлекает все ``[[ссылки]]`` из текста.

    Args:
        text: Исходный текст.

    Returns:
        Список имён ссылок.
    """
    return WIKILINK_RE.findall(text)


def resolve_wikilink(vault: Path, link: str) -> Path | None:
    """Находит .md-файл по имени wiki-ссылки в vault.

    Args:
        vault: Путь к vault.
        link: Имя ссылки (без ``[[``/``]]``).

    Returns:
        Путь к файлу или ``None``, если файл не найден.
    """
    # Прямое совпадение: link может содержать путь
    direct = vault / f"{link}.md"
    if direct.exists():
        return direct
    # Поиск по имени файла во всём vault
    name = link.rsplit("/", 1)[-1]
    for md in vault.rglob(f"{name}.md"):
        return md
    return None


def _parse_markdown_table(text: str, section: str) -> list[dict[str, str]]:
    """Извлекает строки Markdown-таблицы из указанной секции.

    Args:
        text: Полный текст заметки.
        section: Заголовок секции (без ``##``).

    Returns:
        Список словарей {заголовок_столбца: значение}.
    """
    lines = text.splitlines()
    in_section = False
    table_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") and section.lower() in stripped.lower():
            in_section = True
            continue
        if in_section and stripped.startswith("##"):
            break
        if in_section and "|" in stripped:
            table_lines.append(stripped)

    if len(table_lines) < 2:
        return []

    headers = [h.strip() for h in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []

    for tl in table_lines[2:]:  # пропускаем разделитель
        cells = [c.strip() for c in tl.strip("|").split("|")]
        row: dict[str, str] = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)

    return rows


def _read_notes(vault: Path, folder: str) -> list[tuple[Path, dict[str, Any]]]:
    """Читает все .md-файлы из подпапки vault.

    Args:
        vault: Путь к vault.
        folder: Имя подпапки.

    Returns:
        Список кортежей (путь, frontmatter).
    """
    target = vault / folder
    if not target.exists():
        return []
    notes: list[tuple[Path, dict[str, Any]]] = []
    for md in sorted(target.glob("*.md")):
        fm = parse_frontmatter(md)
        notes.append((md, fm))
    return notes


# ---------------------------------------------------------------------------
# Сборка и сохранение канваса
# ---------------------------------------------------------------------------


def build_canvas(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """Собирает структуру канваса из узлов и рёбер.

    Args:
        nodes: Список узлов.
        edges: Список рёбер.

    Returns:
        Словарь ``{"nodes": [...], "edges": [...]}``.
    """
    return {"nodes": nodes, "edges": edges}


def save_canvas(canvas: dict[str, Any], output_path: Path) -> None:
    """Сохраняет канвас в JSON-файл.

    Args:
        canvas: Структура канваса.
        output_path: Путь для сохранения.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(canvas, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Канвас сохранён: %s", output_path)


# ---------------------------------------------------------------------------
# Генерация: contract-participants
# ---------------------------------------------------------------------------


def _resolve_person_link(vault: Path, link_raw: str) -> tuple[str, Path | None]:
    """Разрешает ссылку на персону, возвращая имя и путь.

    Args:
        vault: Путь к vault.
        link_raw: Сырая строка (может быть ``[[Имя]]`` или просто ``Имя``).

    Returns:
        Кортеж (отображаемое_имя, путь_или_None).
    """
    match = WIKILINK_RE.search(link_raw)
    if match:
        name = match.group(1).strip()
    else:
        name = link_raw.strip()
    path = resolve_wikilink(vault, name)
    return name, path


def generate_contract_participants(
    vault: Path,
    target: str,
    output: Path | None = None,
) -> Path:
    """Генерирует канвас участников договора.

    Args:
        vault: Путь к vault.
        target: Название договора (например, ``Договор №001``).
        output: Путь для сохранения (опционально).

    Returns:
        Путь к сохранённому файлу.
    """
    # Найти заметку договора
    contract_path = resolve_wikilink(vault, target)
    if contract_path is None:
        # Попробуем поискать в 02-ДОГОВОРЫ
        for md_path, fm in _read_notes(vault, "02-ДОГОВОРЫ"):
            title = fm.get("title", md_path.stem)
            if title == target or md_path.stem == target:
                contract_path = md_path
                break

    if contract_path is None:
        logger.error("Договор не найден: %s", target)
        sys.exit(1)

    fm = parse_frontmatter(contract_path)
    logger.info("Обрабатывается договор: %s", fm.get("title", contract_path.stem))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Центральный узел — файл договора
    contract_id = _gen_id()
    rel_path = contract_path.relative_to(vault).as_posix()
    nodes.append(_make_node(
        contract_id, "file", 0, 0, NODE_W + 40, NODE_H + 20,
        file=rel_path,
    ))

    # --- Наша сторона (слева) ---
    our_people: list[tuple[str, str]] = []  # (имя, роль)
    resp = fm.get("ответственный_наш", "")
    if resp:
        our_people.append((resp, "ответственный"))

    # Исполнители наши (если есть)
    executors = fm.get("исполнители", [])
    if isinstance(executors, str):
        executors = [e.strip() for e in executors.split(",") if e.strip()]
    for ex in executors:
        our_people.append((ex, "исполнитель"))

    our_group_id = _gen_id()
    our_x = -500
    our_positions = layout_tree(our_x, -100, len(our_people), spacing=150)

    if our_people:
        # Группа
        min_x = min(p[0] for p in our_positions) - NODE_W // 2 - GROUP_PADDING
        max_x = max(p[0] for p in our_positions) + NODE_W // 2 + GROUP_PADDING
        min_y = -100 - GROUP_PADDING
        max_y = -100 + NODE_H + GROUP_PADDING
        nodes.append(_make_node(
            our_group_id, "group", min_x, min_y - 40,
            max_x - min_x, max_y - min_y + 40,
            label="Наша сторона", color="4",
        ))

        for i, (person_name, role) in enumerate(our_people):
            clean_name = WIKILINK_RE.sub(r"\1", person_name).strip()
            pid = _gen_id()
            px, py = our_positions[i]
            person_path = resolve_wikilink(vault, clean_name)
            if person_path:
                rel = person_path.relative_to(vault).as_posix()
                nodes.append(_make_node(pid, "file", px - NODE_W // 2, py, NODE_W, NODE_H, file=rel))
            else:
                nodes.append(_make_node(pid, "text", px - NODE_W // 2, py, NODE_W, NODE_H, text=clean_name))
            edges.append(_make_edge(_gen_id(), contract_id, pid, label=role))

    # --- Сторона контрагента (справа) ---
    cp_people: list[tuple[str, str]] = []

    signer = fm.get("подписант_контрагента", "")
    if signer:
        cp_people.append((signer, "подписант"))

    cp_executors = fm.get("исполнители_контрагента", [])
    if isinstance(cp_executors, str):
        cp_executors = [e.strip() for e in cp_executors.split(",") if e.strip()]
    for ex in cp_executors:
        cp_people.append((ex, "исполнитель"))

    contacts = fm.get("контактные_лица", [])
    if isinstance(contacts, str):
        contacts = [c.strip() for c in contacts.split(",") if c.strip()]
    for c in contacts:
        cp_people.append((c, "контактное лицо"))

    cp_group_id = _gen_id()
    cp_x = 500
    cp_positions = layout_tree(cp_x, -100, len(cp_people), spacing=150)

    if cp_people:
        min_x = min(p[0] for p in cp_positions) - NODE_W // 2 - GROUP_PADDING
        max_x = max(p[0] for p in cp_positions) + NODE_W // 2 + GROUP_PADDING
        min_y = -100 - GROUP_PADDING
        max_y = -100 + NODE_H + GROUP_PADDING
        nodes.append(_make_node(
            cp_group_id, "group", min_x, min_y - 40,
            max_x - min_x, max_y - min_y + 40,
            label="Сторона контрагента", color="1",
        ))

        for i, (person_name, role) in enumerate(cp_people):
            clean_name = WIKILINK_RE.sub(r"\1", person_name).strip()
            pid = _gen_id()
            px, py = cp_positions[i]
            person_path = resolve_wikilink(vault, clean_name)
            if person_path:
                rel = person_path.relative_to(vault).as_posix()
                nodes.append(_make_node(pid, "file", px - NODE_W // 2, py, NODE_W, NODE_H, file=rel))
            else:
                nodes.append(_make_node(pid, "text", px - NODE_W // 2, py, NODE_W, NODE_H, text=clean_name))
            edges.append(_make_edge(_gen_id(), contract_id, pid, label=role))

    canvas = build_canvas(nodes, edges)
    contract_name = fm.get("title", contract_path.stem)
    if output is None:
        output = vault / CANVAS_DIR / f"Участники {contract_name}.canvas"
    save_canvas(canvas, output)
    return output


# ---------------------------------------------------------------------------
# Генерация: person-relationships
# ---------------------------------------------------------------------------


def generate_person_relationships(
    vault: Path,
    target: str,
    output: Path | None = None,
) -> Path:
    """Генерирует канвас связей персоны.

    Args:
        vault: Путь к vault.
        target: ФИО персоны.
        output: Путь для сохранения (опционально).

    Returns:
        Путь к сохранённому файлу.
    """
    # Поиск заметки персоны
    person_path: Path | None = None
    for folder in ("04-СОТРУДНИКИ", "05-КОНТАКТЫ"):
        for md_path, fm in _read_notes(vault, folder):
            title = fm.get("title", md_path.stem)
            if title == target or md_path.stem == target:
                person_path = md_path
                break
        if person_path:
            break

    if person_path is None:
        person_path = resolve_wikilink(vault, target)

    if person_path is None:
        logger.error("Персона не найдена: %s", target)
        sys.exit(1)

    fm = parse_frontmatter(person_path)
    text = person_path.read_text(encoding="utf-8")
    person_name = fm.get("title", person_path.stem)
    logger.info("Обрабатывается персона: %s", person_name)

    # Извлечение связей из frontmatter
    links_raw = fm.get("связи", [])
    if isinstance(links_raw, str):
        links_raw = [l.strip() for l in links_raw.split(",") if l.strip()]

    # Дополнительно — все wikilinks из текста
    wikilinks = _extract_wikilinks(text)

    # Собираем уникальные связи
    linked: list[tuple[str, str]] = []  # (имя, тип_связи)
    seen: set[str] = set()

    for link in links_raw:
        clean = WIKILINK_RE.sub(r"\1", link).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            linked.append((clean, "связь"))

    for wl in wikilinks:
        wl_clean = wl.strip()
        if wl_clean.lower() not in seen and wl_clean.lower() != person_name.lower():
            # Проверяем что это персона
            resolved = resolve_wikilink(vault, wl_clean)
            if resolved:
                rfm = parse_frontmatter(resolved)
                rtype = rfm.get("type", "")
                if rtype in ("сотрудник", "контакт"):
                    seen.add(wl_clean.lower())
                    role = rfm.get("роль", rfm.get("должность", ""))
                    linked.append((wl_clean, role if role else rtype))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Центральный узел
    center_id = _gen_id()
    rel_path = person_path.relative_to(vault).as_posix()
    nodes.append(_make_node(
        center_id, "file", -NODE_W // 2, -NODE_H // 2,
        NODE_W, NODE_H, file=rel_path,
    ))

    # Размещение связей по кругу
    radius = 350
    positions = layout_radial(0, 0, radius, len(linked))

    # Группировка по типу связи
    type_groups: dict[str, list[int]] = {}
    for i, (_, rel_type) in enumerate(linked):
        type_groups.setdefault(rel_type, []).append(i)

    # Создание групп (если есть несколько типов)
    if len(type_groups) > 1:
        color_idx = 0
        colors = ["1", "2", "3", "4", "5", "6"]
        for rel_type, indices in type_groups.items():
            if not indices:
                continue
            group_positions = [positions[i] for i in indices]
            gx_min = min(p[0] for p in group_positions) - NODE_W // 2 - GROUP_PADDING
            gx_max = max(p[0] for p in group_positions) + NODE_W // 2 + GROUP_PADDING
            gy_min = min(p[1] for p in group_positions) - NODE_H // 2 - GROUP_PADDING
            gy_max = max(p[1] for p in group_positions) + NODE_H // 2 + GROUP_PADDING
            nodes.append(_make_node(
                _gen_id(), "group", gx_min, gy_min - 30,
                gx_max - gx_min, gy_max - gy_min + 30,
                label=rel_type, color=colors[color_idx % len(colors)],
            ))
            color_idx += 1

    for i, (name, rel_type) in enumerate(linked):
        pid = _gen_id()
        px, py = positions[i]
        resolved = resolve_wikilink(vault, name)
        if resolved:
            rel = resolved.relative_to(vault).as_posix()
            nodes.append(_make_node(pid, "file", px - NODE_W // 2, py - NODE_H // 2, NODE_W, NODE_H, file=rel))
        else:
            nodes.append(_make_node(pid, "text", px - NODE_W // 2, py - NODE_H // 2, NODE_W, NODE_H, text=name))
        edges.append(_make_edge(_gen_id(), center_id, pid, label=rel_type))

    canvas = build_canvas(nodes, edges)
    if output is None:
        output = vault / CANVAS_DIR / f"Связи {person_name}.canvas"
    save_canvas(canvas, output)
    return output


# ---------------------------------------------------------------------------
# Генерация: project-roadmap
# ---------------------------------------------------------------------------


def generate_project_roadmap(
    vault: Path,
    target: str,
    output: Path | None = None,
) -> Path:
    """Генерирует канвас дорожной карты проекта.

    Args:
        vault: Путь к vault.
        target: Название проекта.
        output: Путь для сохранения (опционально).

    Returns:
        Путь к сохранённому файлу.
    """
    # Поиск заметки проекта
    project_path: Path | None = None
    for md_path, fm in _read_notes(vault, "03-ПРОЕКТЫ"):
        title = fm.get("title", md_path.stem)
        if title == target or md_path.stem == target:
            project_path = md_path
            break

    if project_path is None:
        project_path = resolve_wikilink(vault, target)

    if project_path is None:
        logger.error("Проект не найден: %s", target)
        sys.exit(1)

    fm = parse_frontmatter(project_path)
    text = project_path.read_text(encoding="utf-8")
    project_name = fm.get("title", project_path.stem)
    logger.info("Обрабатывается проект: %s", project_name)

    # Парсим таблицу этапов
    milestones = _parse_markdown_table(text, "Этапы / Милестоуны")
    if not milestones:
        # Пробуем альтернативные названия секций
        milestones = _parse_markdown_table(text, "Этапы")
    if not milestones:
        milestones = _parse_markdown_table(text, "Милестоуны")

    if not milestones:
        logger.warning("Таблица этапов не найдена в заметке проекта: %s", project_name)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Заголовок проекта
    title_id = _gen_id()
    nodes.append(_make_node(
        title_id, "text", 0, -120, NODE_W + 80, NODE_H,
        text=f"**{project_name}**\nДорожная карта",
    ))

    # Размещение этапов слева направо
    positions = layout_timeline(0, 0, len(milestones), spacing=350)
    prev_id: str | None = None

    # Определяем цвета по статусу
    status_colors: dict[str, str] = {
        "завершён": "4",   # зелёный
        "в работе": "5",   # жёлтый
        "ожидает": "1",    # красный
        "не начат": "0",   # серый
    }

    for i, milestone in enumerate(milestones):
        mid = _gen_id()
        px, py = positions[i]

        # Формируем текст узла
        name = milestone.get("Этап", milestone.get("Название", f"Этап {i + 1}"))
        deadline = milestone.get("Дедлайн", milestone.get("Срок", ""))
        status = milestone.get("Статус", "")
        desc = milestone.get("Описание", "")

        text_lines = [f"**{name}**"]
        if deadline:
            text_lines.append(f"Срок: {deadline}")
        if status:
            text_lines.append(f"Статус: {status}")
        if desc:
            text_lines.append(desc)

        color = status_colors.get(status.lower(), "")
        node_kwargs: dict[str, Any] = {"text": "\n".join(text_lines)}
        if color:
            node_kwargs["color"] = color

        nodes.append(_make_node(mid, "text", px, py, NODE_W + 40, NODE_H + 40, **node_kwargs))

        if prev_id is not None:
            edges.append(_make_edge(_gen_id(), prev_id, mid))
        prev_id = mid

    canvas = build_canvas(nodes, edges)
    if output is None:
        output = vault / CANVAS_DIR / f"Дорожная карта {project_name}.canvas"
    save_canvas(canvas, output)
    return output


# ---------------------------------------------------------------------------
# Генерация: counterparty-map
# ---------------------------------------------------------------------------


def generate_counterparty_map(
    vault: Path,
    output: Path | None = None,
) -> Path:
    """Генерирует канвас карты контрагентов.

    Args:
        vault: Путь к vault.
        output: Путь для сохранения (опционально).

    Returns:
        Путь к сохранённому файлу.
    """
    # Наша компания
    our_company: tuple[Path, dict[str, Any]] | None = None
    for md_path, fm in _read_notes(vault, "00-КОМПАНИЯ"):
        if fm.get("type", "") == "наша_компания":
            our_company = (md_path, fm)
            break

    # Если 00-КОМПАНИЯ нет — ищем среди 01-КОНТРАГЕНТЫ
    if our_company is None:
        for md_path, fm in _read_notes(vault, "01-КОНТРАГЕНТЫ"):
            if fm.get("type", "") == "наша_компания":
                our_company = (md_path, fm)
                break

    # Контрагенты
    counterparties = _read_notes(vault, "01-КОНТРАГЕНТЫ")
    # Фильтруем — исключаем нашу компанию
    cp_list: list[tuple[Path, dict[str, Any]]] = []
    for cp_path, cp_fm in counterparties:
        if cp_fm.get("type", "") != "наша_компания":
            cp_list.append((cp_path, cp_fm))

    # Подсчёт активных договоров для каждого контрагента
    contracts = _read_notes(vault, "02-ДОГОВОРЫ")
    contract_count: dict[str, int] = {}
    for _, cfm in contracts:
        status = cfm.get("статус", "")
        if status not in ("завершён", "отменён"):
            cp_name = cfm.get("контрагент", "").strip().strip('"').strip("'")
            cp_link = WIKILINK_RE.sub(r"\1", cp_name).strip()
            if cp_link:
                contract_count[cp_link.lower()] = contract_count.get(cp_link.lower(), 0) + 1

    # Группировка по категории
    categories: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for cp_path, cp_fm in cp_list:
        cat = cp_fm.get("категория", "Без категории")
        categories.setdefault(cat, []).append((cp_path, cp_fm))

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # Центральный узел — наша компания
    center_id = _gen_id()
    if our_company:
        rel_path = our_company[0].relative_to(vault).as_posix()
        nodes.append(_make_node(
            center_id, "file", -NODE_W // 2, -NODE_H // 2,
            NODE_W + 40, NODE_H + 20, file=rel_path,
        ))
    else:
        nodes.append(_make_node(
            center_id, "text", -NODE_W // 2, -NODE_H // 2,
            NODE_W + 40, NODE_H + 20, text="**Наша компания**",
        ))

    # Размещаем категории группами по кругу
    total_cp = len(cp_list)
    radius = max(500, total_cp * 40)
    all_positions = layout_radial(0, 0, radius, total_cp)

    idx = 0
    color_idx = 0
    colors = ["1", "2", "3", "4", "5", "6"]

    for cat, items in categories.items():
        cat_positions = all_positions[idx: idx + len(items)]
        idx += len(items)

        # Группа категории
        if cat_positions:
            gx_min = min(p[0] for p in cat_positions) - NODE_W // 2 - GROUP_PADDING
            gx_max = max(p[0] for p in cat_positions) + NODE_W // 2 + GROUP_PADDING
            gy_min = min(p[1] for p in cat_positions) - NODE_H // 2 - GROUP_PADDING
            gy_max = max(p[1] for p in cat_positions) + NODE_H // 2 + GROUP_PADDING
            nodes.append(_make_node(
                _gen_id(), "group", gx_min, gy_min - 30,
                gx_max - gx_min, gy_max - gy_min + 30,
                label=cat, color=colors[color_idx % len(colors)],
            ))
            color_idx += 1

        for j, (cp_path, cp_fm) in enumerate(items):
            cp_id = _gen_id()
            if j < len(cat_positions):
                px, py = cat_positions[j]
            else:
                px, py = 0, 0
            rel_path = cp_path.relative_to(vault).as_posix()
            nodes.append(_make_node(
                cp_id, "file", px - NODE_W // 2, py - NODE_H // 2,
                NODE_W, NODE_H, file=rel_path,
            ))

            cp_title = cp_fm.get("title", cp_path.stem)
            count = contract_count.get(cp_title.lower(), 0)
            label = f"Договоров: {count}" if count > 0 else ""
            edges.append(_make_edge(_gen_id(), center_id, cp_id, label=label))

    canvas = build_canvas(nodes, edges)
    if output is None:
        output = vault / CANVAS_DIR / "Карта контрагентов.canvas"
    save_canvas(canvas, output)
    return output


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
        description="Генерация .canvas файлов из данных Obsidian vault.",
    )
    parser.add_argument(
        "--vault", type=Path, required=True,
        help="Путь к Obsidian vault.",
    )
    parser.add_argument(
        "--type", dest="canvas_type", required=True,
        choices=[
            "contract-participants",
            "person-relationships",
            "project-roadmap",
            "counterparty-map",
        ],
        help="Тип канваса.",
    )
    parser.add_argument(
        "--target", default="",
        help="Название целевого объекта (договор, персона, проект).",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Путь для сохранения .canvas файла (по умолчанию — 12-КАНВАСЫ/).",
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

    if args.canvas_type == "contract-participants":
        if not args.target:
            logger.error("Для типа contract-participants укажите --target (название договора).")
            sys.exit(1)
        result = generate_contract_participants(args.vault, args.target, args.output)

    elif args.canvas_type == "person-relationships":
        if not args.target:
            logger.error("Для типа person-relationships укажите --target (ФИО персоны).")
            sys.exit(1)
        result = generate_person_relationships(args.vault, args.target, args.output)

    elif args.canvas_type == "project-roadmap":
        if not args.target:
            logger.error("Для типа project-roadmap укажите --target (название проекта).")
            sys.exit(1)
        result = generate_project_roadmap(args.vault, args.target, args.output)

    elif args.canvas_type == "counterparty-map":
        result = generate_counterparty_map(args.vault, args.output)

    else:
        logger.error("Неизвестный тип канваса: %s", args.canvas_type)
        sys.exit(1)

    logger.info("Готово: %s", result)


if __name__ == "__main__":
    main()
