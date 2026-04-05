# Canvas Templates

JSON Canvas (`.canvas`) templates for visual maps. Save to `12-КАНВАСЫ/`.

Canvas node types:
- `"type": "file"` — vault file reference (`"file": "path/file.md"`)
- `"type": "text"` — Markdown text block (`"text": "content"`)
- `"type": "link"` — external URL (`"url": "https://..."`)
- `"type": "group"` — grouping container (`"label": "Group Name"`)

Edges: `"label"`, `"color"`, `"fromEnd": "arrow"`, `"toEnd": "arrow"`.

---

## Оргструктура

File: `12-КАНВАСЫ/Оргструктура.canvas`

```json
{
  "nodes": [
    {
      "id": "ceo",
      "type": "text",
      "text": "# Генеральный директор\n[[Маса Ольга]]",
      "x": 0, "y": 0, "width": 300, "height": 80, "color": "6"
    },
    {
      "id": "group-tech",
      "type": "group",
      "label": "Техническое направление",
      "x": -400, "y": 150, "width": 350, "height": 250
    },
    {
      "id": "group-sales",
      "type": "group",
      "label": "Продажи",
      "x": 200, "y": 150, "width": 350, "height": 250
    }
  ],
  "edges": [
    {
      "id": "e-ceo-tech",
      "fromNode": "ceo", "fromSide": "bottom",
      "toNode": "group-tech", "toSide": "top",
      "label": "руководит"
    },
    {
      "id": "e-ceo-sales",
      "fromNode": "ceo", "fromSide": "bottom",
      "toNode": "group-sales", "toSide": "top",
      "label": "руководит"
    }
  ]
}
```

---

## Участники договора

File: `12-КАНВАСЫ/Участники Договор №XXX.canvas`

```json
{
  "nodes": [
    {
      "id": "contract",
      "type": "file",
      "file": "02-ДОГОВОРЫ/Договор №001.md",
      "x": 0, "y": 0, "width": 300, "height": 80, "color": "3"
    },
    {
      "id": "group-our",
      "type": "group",
      "label": "Наша сторона",
      "x": -400, "y": 150, "width": 350, "height": 200
    },
    {
      "id": "our-resp",
      "type": "file",
      "file": "04-СОТРУДНИКИ/Иванов Иван.md",
      "x": -375, "y": 180, "width": 300, "height": 60
    },
    {
      "id": "group-their",
      "type": "group",
      "label": "Сторона контрагента",
      "x": 200, "y": 150, "width": 350, "height": 300
    },
    {
      "id": "their-signer",
      "type": "file",
      "file": "05-КОНТАКТЫ/Петров Алексей (ООО Пример).md",
      "x": 225, "y": 180, "width": 300, "height": 60
    },
    {
      "id": "their-exec",
      "type": "file",
      "file": "05-КОНТАКТЫ/Сидорова Мария (ООО Пример).md",
      "x": 225, "y": 270, "width": 300, "height": 60
    }
  ],
  "edges": [
    {
      "id": "e1",
      "fromNode": "contract", "fromSide": "left",
      "toNode": "our-resp", "toSide": "top",
      "label": "Ответственный"
    },
    {
      "id": "e2",
      "fromNode": "contract", "fromSide": "right",
      "toNode": "their-signer", "toSide": "top",
      "label": "Подписант"
    },
    {
      "id": "e3",
      "fromNode": "contract", "fromSide": "right",
      "toNode": "their-exec", "toSide": "top",
      "label": "Исполнитель"
    }
  ]
}
```

---

## Карта связей лица

File: `12-КАНВАСЫ/Связи {ФИО}.canvas`

Central node = person. Surrounding nodes = related people grouped by
relationship type. Create when a person has 3+ relationships.

```json
{
  "nodes": [
    {
      "id": "center",
      "type": "file",
      "file": "04-СОТРУДНИКИ/Иванов Иван.md",
      "x": 0, "y": 0, "width": 300, "height": 80, "color": "1"
    },
    {
      "id": "group-work",
      "type": "group",
      "label": "Рабочие связи",
      "x": -400, "y": -150, "width": 350, "height": 200
    },
    {
      "id": "group-personal",
      "type": "group",
      "label": "Личные связи",
      "x": 300, "y": -150, "width": 350, "height": 200
    }
  ],
  "edges": []
}
```

---

## Стратегическая карта

File: `12-КАНВАСЫ/Стратегическая карта.canvas`

Goals tree: company vision at top, strategic goals below, projects at bottom.

```json
{
  "nodes": [
    {
      "id": "vision",
      "type": "text",
      "text": "# Видение компании\nОписание стратегического видения",
      "x": 0, "y": 0, "width": 400, "height": 100, "color": "6"
    },
    {
      "id": "group-goals",
      "type": "group",
      "label": "Стратегические цели",
      "x": -300, "y": 150, "width": 800, "height": 200
    },
    {
      "id": "group-projects",
      "type": "group",
      "label": "Проекты",
      "x": -300, "y": 400, "width": 800, "height": 200
    }
  ],
  "edges": [
    {
      "id": "e-v-g",
      "fromNode": "vision", "fromSide": "bottom",
      "toNode": "group-goals", "toSide": "top"
    }
  ]
}
```

---

## Дорожная карта проекта

File: `12-КАНВАСЫ/Дорожная карта {Проект}.canvas`

Timeline layout: project at top, phases left-to-right.
Generate with `scripts/generate_canvas.py --type project-roadmap`.

---

## Карта контрагентов

File: `12-КАНВАСЫ/Карта контрагентов.canvas`

Our company at center, counterparties grouped by category.
Generate with `scripts/generate_canvas.py --type counterparty-map`.

---

## Canvas generation

```bash
python scripts/generate_canvas.py --vault PATH --type contract-participants --target "Договор №001"
python scripts/generate_canvas.py --vault PATH --type person-relationships --target "Иванов Иван"
python scripts/generate_canvas.py --vault PATH --type project-roadmap --target "Проект"
python scripts/generate_canvas.py --vault PATH --type counterparty-map
```
