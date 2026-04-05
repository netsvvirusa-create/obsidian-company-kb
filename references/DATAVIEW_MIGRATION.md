# Dataview → Obsidian Bases Migration

If your vault contains Dataview plugin queries, migrate them to native
Obsidian Bases (`.base` files). Bases are built into Obsidian and do not
require plugins.

## Migration steps

1. Identify all Dataview queries in vault (search for ` ```dataview`)
2. For each query, create equivalent `.base` file in `11-БАЗЫ/`
3. Replace inline Dataview queries with `![[11-БАЗЫ/Dashboard.base]]` embeds
4. Remove Dataview plugin after full migration

## Common conversions

### TABLE query → .base table view

Dataview:
```dataview
TABLE контрагент, сумма, дата_окончания
FROM "02-ДОГОВОРЫ"
WHERE статус = "активный"
SORT дата_окончания ASC
```

Bases equivalent:
```yaml
filters:
  and:
    - file.inFolder("02-ДОГОВОРЫ")
    - 'статус == "активный"'
views:
  - type: table
    order:
      - file.name
      - контрагент
      - сумма
      - дата_окончания
```

### LIST query → .base list view

Dataview:
```dataview
LIST
FROM "01-КОНТРАГЕНТЫ"
WHERE категория = "клиент"
```

Bases equivalent:
```yaml
filters:
  and:
    - file.inFolder("01-КОНТРАГЕНТЫ")
    - 'категория == "клиент"'
views:
  - type: list
    order:
      - file.name
```

### Computed fields → formulas

Dataview:
```dataview
TABLE (date(дата_окончания) - date(today)) AS "Дней осталось"
```

Bases equivalent:
```yaml
formulas:
  дней_осталось: 'if(дата_окончания, (date(дата_окончания) - today()).days, "")'
properties:
  formula.дней_осталось:
    displayName: "Дней осталось"
```

### GROUP BY → groupBy

Dataview:
```dataview
TABLE WITHOUT ID ...
GROUP BY ответственный_наш
```

Bases equivalent:
```yaml
views:
  - type: table
    groupBy:
      property: ответственный_наш
      direction: ASC
```

## Key differences

| Feature | Dataview | Bases |
|---------|----------|-------|
| Plugin required | Yes | No (built-in) |
| Query language | DQL | YAML filters |
| Inline queries | `= this.field` | Not supported |
| Computed fields | DQL expressions | Formula expressions |
| Views | TABLE, LIST, TASK | table, list, cards, map |
| Grouping | GROUP BY | groupBy property |
| Performance | JS evaluation | Native |
