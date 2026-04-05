"""Скрипт валидации хранилища (vault) Obsidian для корпоративной базы знаний.

Проверяет структуру заметок, YAML-фронтматтер, теги, ссылки,
дубликаты и двусторонние связи. Результат выводится в формате JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

REQUIRED_FIELDS_COMMON: List[str] = ["title", "type", "tags"]

REQUIRED_FIELDS_BY_TYPE: Dict[str, List[str]] = {
    "контрагент": ["инн", "категория", "статус"],
    "договор": ["номер", "контрагент", "дата_подписания", "статус"],
    "сотрудник": ["должность", "статус"],
    "контакт": ["контрагент", "роль", "статус"],
    "проект": ["клиент", "руководитель", "статус"],
    "переговоры": ["дата", "контрагент", "статус"],
    "событие": ["дата", "категория", "статус"],
    "цель": ["горизонт", "статус", "дедлайн"],
    "идея": ["статус"],
    "наша_компания": ["опф_полная", "инн"],
    "платёж": ["дата", "контрагент", "сумма", "статус"],
    "счёт": ["номер", "дата_выставления", "контрагент", "сумма", "статус"],
    "бюджет": ["период", "статус"],
    "ретроспектива": ["период", "статус"],
    "moc": [],
}

ALLOWED_TAG_PREFIXES: Tuple[str, ...] = (
    "тип/",
    "статус/",
    "приоритет/",
    "направление/",
    "связь/",
)

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]*?)?\]\]")

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Извлекает и разбирает YAML-фронтматтер из текста заметки.

    Args:
        text: Полный текст файла заметки.

    Returns:
        Кортеж (словарь_фронтматтера, сообщение_об_ошибке).
        Если фронтматтер отсутствует или невалиден, первый элемент -- None.
    """
    stripped = text.lstrip("\ufeff").lstrip()
    if not stripped.startswith("---"):
        return None, "Фронтматтер не найден (файл не начинается с ---)"

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return None, "Фронтматтер не закрыт (отсутствует завершающий ---)"

    raw_yaml = parts[1]

    if yaml is not None:
        try:
            data = yaml.safe_load(raw_yaml)
        except yaml.YAMLError as exc:
            return None, f"Ошибка разбора YAML: {exc}"
    else:
        # Простой fallback-парсер без PyYAML
        data = _simple_yaml_parse(raw_yaml)
        if data is None:
            return None, "Ошибка разбора YAML (PyYAML не установлен, fallback не справился)"

    if not isinstance(data, dict):
        return None, "Фронтматтер не является словарём YAML"

    return data, None


def _simple_yaml_parse(raw: str) -> Optional[Dict[str, Any]]:
    """Минимальный парсер YAML-подобных пар ключ: значение.

    Args:
        raw: Содержимое между маркерами ---.

    Returns:
        Словарь или None при ошибке.
    """
    result: Dict[str, Any] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Попытка разобрать список в формате [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
            result[key] = [i for i in items if i]
        else:
            result[key] = value if value else None
    return result if result else None


def _get_body(text: str) -> str:
    """Возвращает тело заметки (всё после фронтматтера).

    Args:
        text: Полный текст файла заметки.

    Returns:
        Строка с телом заметки.
    """
    stripped = text.lstrip("\ufeff").lstrip()
    if not stripped.startswith("---"):
        return text
    parts = stripped.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def _extract_wikilinks(text: str) -> List[str]:
    """Извлекает имена целей wiki-ссылок [[Имя]] из текста.

    Args:
        text: Тело заметки.

    Returns:
        Список имён ссылок.
    """
    return WIKILINK_RE.findall(text)


def _parse_date(value: Any) -> Optional[date]:
    """Пытается разобрать дату из строки или объекта date.

    Args:
        value: Значение поля даты.

    Returns:
        Объект date или None.
    """
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Основная валидация
# ---------------------------------------------------------------------------


def _make_error(file_path: str, error_type: str, message: str) -> Dict[str, str]:
    """Создаёт словарь ошибки/предупреждения.

    Args:
        file_path: Путь к файлу относительно хранилища.
        error_type: Тип ошибки (например, invalid_yaml).
        message: Описание проблемы.

    Returns:
        Словарь с полями file, type, message.
    """
    return {"file": file_path, "type": error_type, "message": message}


def validate_vault(vault_path: Path) -> Dict[str, Any]:
    """Выполняет валидацию хранилища Obsidian.

    Args:
        vault_path: Путь к корню хранилища.

    Returns:
        Словарь с результатами валидации (total_notes, errors, warnings, summary).
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    by_type: Dict[str, int] = {}

    # Имена всех .md файлов (stem) для проверки ссылок
    all_stems: Set[str] = set()
    md_files: List[Path] = sorted(vault_path.rglob("*.md"))
    for f in md_files:
        all_stems.add(f.stem)

    # Хранилища для проверки дубликатов
    inn_map: Dict[str, List[str]] = {}  # инн -> [файлы]
    contract_number_map: Dict[str, List[str]] = {}  # номер -> [файлы]

    # Данные для проверки двусторонних связей
    # файл -> набор целей ссылок из поля "связи"
    relations_map: Dict[str, Set[str]] = {}

    # Сбор данных по каждой заметке
    parsed_notes: List[Tuple[Path, str, Dict[str, Any], str]] = []

    for md_file in md_files:
        rel_path = str(md_file.relative_to(vault_path))
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Не удалось прочитать файл %s: %s", rel_path, exc)
            errors.append(_make_error(rel_path, "invalid_yaml", f"Не удалось прочитать файл: {exc}"))
            continue

        fm, err_msg = _parse_frontmatter(text)
        if fm is None:
            errors.append(_make_error(rel_path, "invalid_yaml", err_msg or "Нет фронтматтера"))
            continue

        parsed_notes.append((md_file, rel_path, fm, text))

        # --- Общие обязательные поля ---
        for field in REQUIRED_FIELDS_COMMON:
            if field not in fm or fm[field] is None:
                errors.append(
                    _make_error(rel_path, "missing_field", f"Отсутствует обязательное поле: {field}")
                )

        note_type: Optional[str] = fm.get("type")
        if note_type:
            by_type[note_type] = by_type.get(note_type, 0) + 1

            # --- Обязательные поля по типу ---
            type_fields = REQUIRED_FIELDS_BY_TYPE.get(note_type, [])
            for field in type_fields:
                if field not in fm or fm[field] is None:
                    errors.append(
                        _make_error(
                            rel_path,
                            "missing_field",
                            f"Для типа '{note_type}' отсутствует обязательное поле: {field}",
                        )
                    )

        # --- Проверка тегов ---
        tags = fm.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [tags]
            if isinstance(tags, list):
                for tag in tags:
                    tag_str = str(tag)
                    if not any(tag_str.startswith(prefix) for prefix in ALLOWED_TAG_PREFIXES):
                        errors.append(
                            _make_error(
                                rel_path,
                                "invalid_tag",
                                f"Тег '{tag_str}' не входит в допустимую таксономию "
                                f"({', '.join(ALLOWED_TAG_PREFIXES)})",
                            )
                        )

        # --- Неразрешённые wiki-ссылки ---
        body = _get_body(text)
        links = _extract_wikilinks(body)
        for link_target in links:
            target_name = link_target.strip()
            if target_name and target_name not in all_stems:
                warnings.append(
                    _make_error(
                        rel_path,
                        "unresolved_link",
                        f"Неразрешённая ссылка: [[{target_name}]]",
                    )
                )

        # --- Дубликаты ИНН ---
        if note_type == "контрагент":
            inn_value = fm.get("инн")
            if inn_value is not None:
                inn_str = str(inn_value)
                inn_map.setdefault(inn_str, []).append(rel_path)

        # --- Дубликаты номеров договоров ---
        if note_type == "договор":
            contract_num = fm.get("номер")
            if contract_num is not None:
                num_str = str(contract_num)
                contract_number_map.setdefault(num_str, []).append(rel_path)

        # --- Истёкшие активные договоры ---
        if note_type == "договор":
            status = fm.get("статус")
            end_date_raw = fm.get("дата_окончания")
            if status and str(status) == "активный" and end_date_raw:
                end_date = _parse_date(end_date_raw)
                if end_date and end_date < date.today():
                    warnings.append(
                        _make_error(
                            rel_path,
                            "expired_active_contract",
                            f"Договор имеет статус 'активный', но дата окончания "
                            f"({end_date.isoformat()}) уже прошла",
                        )
                    )

        # --- Сбор связей для двусторонней проверки ---
        связи = fm.get("связи")
        if связи:
            targets: Set[str] = set()
            if isinstance(связи, list):
                for item in связи:
                    raw = str(item)
                    inner_links = WIKILINK_RE.findall(raw)
                    if inner_links:
                        targets.update(inner_links)
                    else:
                        targets.add(raw.strip())
            elif isinstance(связи, str):
                inner_links = WIKILINK_RE.findall(связи)
                if inner_links:
                    targets.update(inner_links)
                else:
                    targets.add(связи.strip())
            if targets:
                relations_map[md_file.stem] = targets

    # --- Проверка дубликатов ИНН ---
    for inn_val, files in inn_map.items():
        if len(files) > 1:
            for f in files:
                errors.append(
                    _make_error(
                        f,
                        "duplicate_inn",
                        f"Дублирующийся ИНН '{inn_val}' встречается в файлах: {', '.join(files)}",
                    )
                )

    # --- Проверка дубликатов номеров договоров ---
    for num_val, files in contract_number_map.items():
        if len(files) > 1:
            for f in files:
                errors.append(
                    _make_error(
                        f,
                        "duplicate_contract_number",
                        f"Дублирующийся номер договора '{num_val}' встречается в файлах: {', '.join(files)}",
                    )
                )

    # --- Проверка двусторонних связей ---
    for source, targets in relations_map.items():
        for target in targets:
            target_relations = relations_map.get(target, set())
            if source not in target_relations:
                # Найти rel_path для source
                source_rel = None
                for md_file, rel_path, fm, text in parsed_notes:
                    if md_file.stem == source:
                        source_rel = rel_path
                        break
                if source_rel is None:
                    source_rel = source
                warnings.append(
                    _make_error(
                        source_rel,
                        "missing_reverse_link",
                        f"'{source}' ссылается на '{target}' в поле 'связи', "
                        f"но '{target}' не ссылается обратно на '{source}'",
                    )
                )

    total_notes = len(md_files)

    result: Dict[str, Any] = {
        "vault": str(vault_path),
        "total_notes": total_notes,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "by_type": by_type,
            "errors_count": len(errors),
            "warnings_count": len(warnings),
        },
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки.

    Returns:
        Настроенный ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Валидация хранилища Obsidian для корпоративной базы знаний",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        required=True,
        help="Путь к корневой директории хранилища Obsidian",
    )
    return parser


def main() -> int:
    """Точка входа CLI.

    Returns:
        Код возврата: 0 если ошибок нет, 1 если найдены ошибки.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    vault_path: Path = args.vault.resolve()

    if not vault_path.is_dir():
        logger.error("Указанный путь не является директорией: %s", vault_path)
        return 1

    result = validate_vault(vault_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["summary"]["errors_count"] > 0:
        logger.info(
            "Найдено ошибок: %d, предупреждений: %d",
            result["summary"]["errors_count"],
            result["summary"]["warnings_count"],
        )
        return 1

    logger.info(
        "Валидация завершена успешно. Заметок: %d, предупреждений: %d",
        result["total_notes"],
        result["summary"]["warnings_count"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
