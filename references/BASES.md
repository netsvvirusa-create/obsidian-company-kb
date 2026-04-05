# Obsidian Bases Dashboards

9 `.base` dashboard files for the corporate knowledge base. Each is a YAML
file with `.base` extension, stored in `11-БАЗЫ/`.

---

## Активные договоры

File: `11-БАЗЫ/Активные договоры.base`

```yaml
filters:
  and:
    - file.inFolder("02-ДОГОВОРЫ")
    - 'статус == "активный"'
formulas:
  дней_до_окончания: 'if(дата_окончания, (date(дата_окончания) - today()).days, "")'
  просрочен: 'if(дата_окончания, date(дата_окончания) < today(), false)'
properties:
  formula.дней_до_окончания:
    displayName: "Дней до окончания"
  formula.просрочен:
    displayName: "Просрочен"
views:
  - type: table
    name: "Все активные"
    order:
      - file.name
      - контрагент
      - сумма
      - дата_окончания
      - formula.дней_до_окончания
      - ответственный_наш
      - подписант_контрагента
    groupBy:
      property: ответственный_наш
      direction: ASC
    summaries:
      сумма: Sum
  - type: cards
    name: "Карточки"
    order:
      - file.name
      - контрагент
      - сумма
      - статус
      - подписант_контрагента
```

---

## Контрагенты

File: `11-БАЗЫ/Контрагенты.base`

```yaml
filters:
  and:
    - file.inFolder("01-КОНТРАГЕНТЫ")
    - 'file.ext == "md"'
formulas:
  последнее_обновление: 'file.mtime.relative()'
  кол_во_контактов: 'if(контактные_лица, контактные_лица.length, 0)'
properties:
  formula.последнее_обновление:
    displayName: "Обновлено"
  formula.кол_во_контактов:
    displayName: "Контактов"
views:
  - type: table
    name: "Все контрагенты"
    order:
      - file.name
      - категория
      - formula.кол_во_контактов
      - статус
      - formula.последнее_обновление
    groupBy:
      property: категория
      direction: ASC
  - type: list
    name: "Быстрый список"
    order:
      - file.name
      - категория
      - статус
```

---

## Контактные лица

File: `11-БАЗЫ/Контактные лица.base`

```yaml
filters:
  and:
    - file.inFolder("05-КОНТАКТЫ")
    - 'статус == "активный"'
formulas:
  обновлено: 'file.mtime.relative()'
properties:
  formula.обновлено:
    displayName: "Обновлено"
views:
  - type: table
    name: "По контрагентам"
    order:
      - file.name
      - контрагент
      - роль
      - статус
      - formula.обновлено
    groupBy:
      property: контрагент
      direction: ASC
  - type: cards
    name: "Карточки"
    order:
      - file.name
      - контрагент
      - роль
  - type: table
    name: "Все контакты"
    order:
      - file.name
      - контрагент
      - роль
      - статус
```

---

## Сотрудники

File: `11-БАЗЫ/Сотрудники.base`

```yaml
filters:
  and:
    - file.inFolder("04-СОТРУДНИКИ")
    - 'статус == "активный"'
formulas:
  стаж: 'if(дата_найма, ((now() - date(дата_найма)).days / 365).round(1).toString() + " лет", "")'
properties:
  formula.стаж:
    displayName: "Стаж"
views:
  - type: table
    name: "По отделам"
    order:
      - file.name
      - должность
      - formula.стаж
      - руководитель
    groupBy:
      property: отдел
      direction: ASC
  - type: cards
    name: "Карточки"
    order:
      - file.name
      - должность
      - отдел
```

---

## Переговоры

File: `11-БАЗЫ/Переговоры.base`

```yaml
filters:
  and:
    - file.inFolder("06-ПЕРЕГОВОРЫ")
views:
  - type: table
    name: "Все переговоры"
    order:
      - file.name
      - дата
      - контрагент
      - тема
      - формат
      - статус
    groupBy:
      property: контрагент
      direction: ASC
  - type: table
    name: "Последние 30"
    limit: 30
    order:
      - file.name
      - дата
      - контрагент
      - тема
```

---

## Стратегические цели

File: `11-БАЗЫ/Стратегические цели.base`

```yaml
filters:
  and:
    - file.inFolder("09-СТРАТЕГИЯ/Цели")
    - 'статус == "активный"'
formulas:
  дней_до_дедлайна: 'if(дедлайн, (date(дедлайн) - today()).days, "")'
  горит: 'if(дедлайн, (date(дедлайн) - today()).days < 30 && статус == "активный", false)'
properties:
  formula.дней_до_дедлайна:
    displayName: "Дней до дедлайна"
  formula.горит:
    displayName: "Срочно"
views:
  - type: table
    name: "Активные цели"
    order:
      - file.name
      - горизонт
      - направление
      - formula.дней_до_дедлайна
      - ответственный
    groupBy:
      property: горизонт
      direction: ASC
    summaries:
      formula.дней_до_дедлайна: Min
```

---

## Операционные события

File: `11-БАЗЫ/Операционные события.base`

```yaml
filters:
  and:
    - file.inFolder("07-ОПЕРАЦИИ")
views:
  - type: table
    name: "Последние события"
    limit: 50
    order:
      - file.name
      - дата
      - категория
      - направление
      - приоритет
    groupBy:
      property: категория
      direction: ASC
  - type: table
    name: "Критические"
    filters:
      and:
        - 'приоритет == "критический"'
    order:
      - file.name
      - дата
      - направление
```

---

## Календарь

File: `11-БАЗЫ/Календарь.base`

```yaml
filters:
  and:
    - file.inFolder("08-КАЛЕНДАРЬ")
formulas:
  день_недели: 'date(file.basename).format("dddd")'
  размер: '(file.size / 5).round(0)'
properties:
  formula.день_недели:
    displayName: "День"
  formula.размер:
    displayName: "~Слов"
views:
  - type: table
    name: "Последние записи"
    limit: 30
    order:
      - file.name
      - formula.день_недели
      - formula.размер
      - file.mtime
```

---

## Связи между людьми

File: `11-БАЗЫ/Связи между людьми.base`

```yaml
filters:
  or:
    - file.inFolder("04-СОТРУДНИКИ")
    - file.inFolder("05-КОНТАКТЫ")
formulas:
  кол_во_связей: 'if(связи, связи.length, 0)'
  тип_лица: 'if(type == "сотрудник", "Сотрудник", "Контакт")'
properties:
  formula.кол_во_связей:
    displayName: "Связей"
  formula.тип_лица:
    displayName: "Тип"
views:
  - type: table
    name: "Все люди со связями"
    filters:
      and:
        - 'if(связи, связи.length > 0, false)'
    order:
      - file.name
      - formula.тип_лица
      - связи
      - formula.кол_во_связей
    groupBy:
      property: formula.тип_лица
      direction: ASC
    summaries:
      formula.кол_во_связей: Sum
  - type: table
    name: "Сотрудники"
    filters:
      and:
        - file.inFolder("04-СОТРУДНИКИ")
    order:
      - file.name
      - должность
      - отдел
      - связи
      - formula.кол_во_связей
    groupBy:
      property: отдел
      direction: ASC
  - type: table
    name: "Контакты контрагентов"
    filters:
      and:
        - file.inFolder("05-КОНТАКТЫ")
    order:
      - file.name
      - контрагент
      - роль
      - связи
      - formula.кол_во_связей
    groupBy:
      property: контрагент
      direction: ASC
  - type: cards
    name: "Карточки"
    order:
      - file.name
      - formula.тип_лица
      - связи
```

---

## Финансы

File: `11-БАЗЫ/Финансы.base`

```yaml
filters:
  and:
    - file.inFolder("10-ФИНАНСЫ")
formulas:
  просрочен: 'if(дата_оплаты_план, date(дата_оплаты_план) < today() && статус != "оплачен", false)'
  дней_просрочки: 'if(дата_оплаты_план, if(date(дата_оплаты_план) < today() && статус != "оплачен", (today() - date(дата_оплаты_план)).days, ""), "")'
properties:
  formula.просрочен:
    displayName: "Просрочен"
  formula.дней_просрочки:
    displayName: "Дней просрочки"
views:
  - type: table
    name: "Все операции"
    order:
      - file.name
      - type
      - контрагент
      - договор
      - сумма
      - направление
      - статус
      - formula.просрочен
    groupBy:
      property: type
      direction: ASC
    summaries:
      сумма: Sum
  - type: table
    name: "Ожидают оплаты"
    filters:
      and:
        - 'статус == "ожидается" || статус == "выставлен"'
    order:
      - file.name
      - контрагент
      - сумма
      - дата_оплаты_план
      - formula.дней_просрочки
    summaries:
      сумма: Sum
  - type: table
    name: "По контрагентам"
    order:
      - file.name
      - сумма
      - направление
      - статус
    groupBy:
      property: контрагент
      direction: ASC
    summaries:
      сумма: Sum
```
