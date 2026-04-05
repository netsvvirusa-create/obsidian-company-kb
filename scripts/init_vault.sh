#!/usr/bin/env bash
# init_vault.sh — Инициализация структуры Obsidian vault для корпоративной базы знаний.
# Создаёт 15 папок, копирует .base дашборды, .canvas карты и MOC-заметки.
#
# Использование: bash scripts/init_vault.sh /path/to/vault

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Ошибка: укажите путь к vault"
    echo "Использование: bash $0 /path/to/vault"
    exit 1
fi

VAULT_PATH="$1"

echo "=== Инициализация vault: $VAULT_PATH ==="

# --- Создание папок ---
FOLDERS=(
    "00-INBOX"
    "01-КОНТРАГЕНТЫ"
    "02-ДОГОВОРЫ"
    "03-ПРОЕКТЫ"
    "04-СОТРУДНИКИ"
    "05-КОНТАКТЫ"
    "06-ПЕРЕГОВОРЫ"
    "07-ОПЕРАЦИИ"
    "08-КАЛЕНДАРЬ"
    "09-СТРАТЕГИЯ/Цели"
    "09-СТРАТЕГИЯ/Идеи"
    "09-СТРАТЕГИЯ/Ретроспективы"
    "10-ФИНАНСЫ"
    "11-БАЗЫ"
    "12-КАНВАСЫ"
    "13-ШАБЛОНЫ"
    "14-ВЛОЖЕНИЯ/Фото сотрудников"
    "14-ВЛОЖЕНИЯ/Фото контактов"
    "14-ВЛОЖЕНИЯ/Документы"
    "99-АРХИВ"
)

for folder in "${FOLDERS[@]}"; do
    dir="$VAULT_PATH/$folder"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        echo "  Создана папка: $folder"
    else
        echo "  Папка уже существует: $folder"
    fi
done

# --- Копирование .base файлов ---
BASE_SRC="$SKILL_ROOT/assets/vault-init/bases"
BASE_DST="$VAULT_PATH/11-БАЗЫ"

if [[ -d "$BASE_SRC" ]]; then
    for base_file in "$BASE_SRC"/*.base; do
        [[ -f "$base_file" ]] || continue
        filename="$(basename "$base_file")"
        if [[ ! -f "$BASE_DST/$filename" ]]; then
            cp "$base_file" "$BASE_DST/$filename"
            echo "  Скопирован дашборд: $filename"
        else
            echo "  Дашборд уже существует: $filename"
        fi
    done
fi

# --- Копирование .canvas файлов ---
CANVAS_SRC="$SKILL_ROOT/assets/vault-init/canvases"
CANVAS_DST="$VAULT_PATH/12-КАНВАСЫ"

if [[ -d "$CANVAS_SRC" ]]; then
    for canvas_file in "$CANVAS_SRC"/*.canvas; do
        [[ -f "$canvas_file" ]] || continue
        filename="$(basename "$canvas_file")"
        if [[ ! -f "$CANVAS_DST/$filename" ]]; then
            cp "$canvas_file" "$CANVAS_DST/$filename"
            echo "  Скопирован канвас: $filename"
        else
            echo "  Канвас уже существует: $filename"
        fi
    done
fi

# --- Создание MOC-заметок ---
MOC_FOLDERS=(
    "01-КОНТРАГЕНТЫ"
    "02-ДОГОВОРЫ"
    "03-ПРОЕКТЫ"
    "04-СОТРУДНИКИ"
    "05-КОНТАКТЫ"
    "06-ПЕРЕГОВОРЫ"
    "07-ОПЕРАЦИИ"
    "09-СТРАТЕГИЯ"
)

for folder in "${MOC_FOLDERS[@]}"; do
    moc_path="$VAULT_PATH/$folder/_MOC.md"
    if [[ ! -f "$moc_path" ]]; then
        folder_name="${folder#*-}"
        cat > "$moc_path" << MOCEOF
---
title: "MOC: $folder_name"
type: moc
tags:
  - тип/moc
---

# $folder_name

> [!info] Карта содержимого
> Индексная заметка для папки \`$folder\`.

## Содержимое

-

MOCEOF
        echo "  Создан MOC: $folder/_MOC.md"
    else
        echo "  MOC уже существует: $folder/_MOC.md"
    fi
done

echo ""
echo "=== Инициализация завершена ==="
echo "Vault: $VAULT_PATH"
echo "Папок создано/проверено: ${#FOLDERS[@]}"
echo ""
echo "Следующие шаги:"
echo "  1. Откройте vault в Obsidian"
echo "  2. Создайте заметку type:наша_компания с реквизитами компании"
echo "  3. Начинайте добавлять контрагентов, договоры и контакты"
