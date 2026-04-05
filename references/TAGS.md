# Tag Taxonomy

Hierarchical tags for the corporate knowledge base. Tags may contain letters,
digits (not as first character), underscores, hyphens, and `/` for hierarchy.

## Statuses

```
#статус/активный
#статус/завершён
#статус/приостановлен
#статус/отменён
#статус/черновик
#статус/на-согласовании
#статус/оплачен
#статус/просрочен
#статус/выставлен
```

## Types

```
#тип/контрагент
#тип/договор
#тип/проект
#тип/переговоры
#тип/событие
#тип/идея
#тип/цель
#тип/задача
#тип/сотрудник
#тип/контакт
#тип/компания
#тип/календарь
#тип/платёж
#тип/счёт
#тип/бюджет
#тип/ретроспектива
#тип/moc
```

## Priorities

```
#приоритет/критический
#приоритет/высокий
#приоритет/средний
#приоритет/низкий
```

## Departments / Directions

```
#направление/продажи
#направление/производство
#направление/маркетинг
#направление/hr
#направление/финансы
#направление/it
#направление/юридическое
```

## Relationship types (between people)

```
#связь/руководство
#связь/семья
#связь/деловая
#связь/дружба
#связь/учёба
#связь/прочее
```

## Counterparty categories

```
клиент
поставщик
партнёр
подрядчик
государственный
```

## Usage rules

1. Every note MUST have at least one `#тип/*` tag
2. Every note MUST have a `#статус/*` tag
3. Tags are placed in YAML `tags` array, without `#` prefix
4. Hierarchical tags use `/` separator: `тип/договор`
5. Tags in body text use `#` prefix: `#статус/активный`
