---
name: obsidian-company-kb
description: >-
  Manage a corporate knowledge base in Obsidian: counterparties, contracts,
  employees, contacts, negotiations, projects, operations, strategy.
  Generate .docx contracts and specifications with grammar checking.
  Use when working with company data, CRM, contracts, specifications,
  or corporate vault in Obsidian. Depends on obsidian-markdown, obsidian-bases,
  json-canvas, obsidian-cli.
license: MIT
compatibility: >-
  Requires Python 3.10+, bash. Packages: pyyaml, python-docx, pymorphy3,
  pymorphy3-dicts-ru, vobject. Works with Claude Code, Codex CLI, OpenCode.
metadata:
  author: cifratronika
  version: "1.0.0"
  lang: ru
---

# Obsidian Company KB Skill

Corporate knowledge base management for Obsidian vaults — counterparties,
contracts, employees, contacts, negotiations, projects, operations, strategy,
and automated .docx document generation.

## Workflow

### 1. Initialize vault

```bash
bash scripts/init_vault.sh /path/to/vault
```

Creates 15 folders, .base dashboards, .canvas maps, and MOC index notes.
See [VAULT_STRUCTURE.md](references/VAULT_STRUCTURE.md).

### 2. Daily operations

Determine the note type from user's description and generate using the
appropriate template. Every note MUST have YAML frontmatter with `type` field.

**Note types and folders:**

| Type | Folder | Template |
|------|--------|----------|
| контрагент | 01-КОНТРАГЕНТЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#контрагент |
| контакт | 05-КОНТАКТЫ/ | [TEMPLATES_CONTACTS.md](references/TEMPLATES_CONTACTS.md)#контакт |
| сотрудник | 04-СОТРУДНИКИ/ | [TEMPLATES_CONTACTS.md](references/TEMPLATES_CONTACTS.md)#сотрудник |
| договор | 02-ДОГОВОРЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#договор |
| проект | 03-ПРОЕКТЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#проект |
| переговоры | 06-ПЕРЕГОВОРЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#переговоры |
| событие | 07-ОПЕРАЦИИ/ | [TEMPLATES.md](references/TEMPLATES.md)#событие |
| дневная_запись | 08-КАЛЕНДАРЬ/ | [TEMPLATES.md](references/TEMPLATES.md)#дневная-запись |
| цель | 09-СТРАТЕГИЯ/Цели/ | [TEMPLATES.md](references/TEMPLATES.md)#цель |
| идея | 09-СТРАТЕГИЯ/Идеи/ | [TEMPLATES.md](references/TEMPLATES.md)#идея |
| наша_компания | root | [TEMPLATES.md](references/TEMPLATES.md)#наша-компания |
| платёж | 10-ФИНАНСЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#платёж |
| счёт | 10-ФИНАНСЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#счёт |
| бюджет | 10-ФИНАНСЫ/ | [TEMPLATES.md](references/TEMPLATES.md)#бюджет |
| ретроспектива | 09-СТРАТЕГИЯ/Ретроспективы/ | [TEMPLATES.md](references/TEMPLATES.md)#ретроспектива |

### 3. Obsidian Flavored Markdown rules

- Internal links: ALWAYS use `[[wikilinks]]`, never `[text](path)`
- Embeds: `![[Note#Section]]` to inline content
- Callouts: `> [!type]` for visual blocks (important, warning, tip, info, etc.)
- Block IDs: `^id` for key decisions and agreements
- Highlights: `==key figures==`
- Confidential data: wrap in collapsible `> [!warning]-` callout
- Dates: always `YYYY-MM-DD`
- Markdown links `[text](url)` — ONLY for external URLs

### 4. File naming

| Entity | Pattern |
|--------|---------|
| Counterparty | `Название организации` |
| Employee | `Фамилия Имя` |
| Contact | `Фамилия Имя (Контрагент)` |
| Contract | `Договор №XXX` |
| Negotiation | `ГГГГ-ММ-ДД Краткое название` |
| Event | `ГГГГ-ММ-ДД Краткое название` |
| Daily | `ГГГГ-ММ-ДД` |

### 5. Tags taxonomy

See full taxonomy in [TAGS.md](references/TAGS.md).

**Statuses:** `#статус/активный`, `#статус/завершён`, `#статус/приостановлен`,
`#статус/отменён`, `#статус/черновик`, `#статус/на-согласовании`

**Types:** `#тип/контрагент`, `#тип/договор`, `#тип/проект`, `#тип/переговоры`,
`#тип/событие`, `#тип/идея`, `#тип/цель`, `#тип/задача`, `#тип/сотрудник`,
`#тип/контакт`

### 6. Bidirectional relationships

Relationships between people are ALWAYS bidirectional. When user reports A→B:

1. Create entry in BOTH cards
2. Add wikilink to `связи` property of both notes
3. Use mirrored descriptions (руководит ↔ подчиняется, etc.)

See [RELATIONSHIPS.md](references/RELATIONSHIPS.md) for full mirror table.

### 7. Contact creation behavior

When user mentions a new person from counterparty side:

1. Create contact card in `05-КОНТАКТЫ/Фамилия Имя (Контрагент).md`
2. Add `[[contact]]` to counterparty card (section + `контактные_лица` property)
3. If mentioned in contract context — add to contract properties
4. Ask user what data to fill (leave empty if unknown)

When user reports new data about existing contact:
1. Report which fields to update
2. Suggest updating related notes if role/counterparty changed

### 8. Generate .docx documents

#### Contract generation

```bash
python scripts/generate_contract.py --vault PATH --contract "Договор №001" \
  [--template PATH] [--output PATH] [--dry-run] [--check-grammar]
```

#### Specification generation

```bash
python scripts/generate_specification.py --vault PATH --contract "Договор №001" \
  --spec 1 [--template PATH] [--output PATH] [--dry-run] [--check-grammar]
```

See [CONTRACT_VARS.md](references/CONTRACT_VARS.md) for variable registry and
[DOCX_GENERATION.md](references/DOCX_GENERATION.md) for generation workflow.

### 9. Dashboards (.base)

13 dashboards in `11-БАЗЫ/`. See [BASES.md](references/BASES.md):
- Активные договоры, Контрагенты, Контактные лица, Сотрудники
- Переговоры, Стратегические цели, Операционные события
- Календарь, Связи между людьми
- Финансы, Проекты, Ретроспективы, Архив

### 10. Visual maps (.canvas)

See [CANVAS.md](references/CANVAS.md) for templates:
- Оргструктура, Участники договора, Карта связей, Стратегическая карта
- Дорожная карта проекта, Карта контрагентов

Generate canvases from vault data:
```bash
python scripts/generate_canvas.py --vault PATH --type contract-participants --target "Договор №001"
python scripts/generate_canvas.py --vault PATH --type person-relationships --target "Иванов Иван"
python scripts/generate_canvas.py --vault PATH --type project-roadmap --target "Проект"
python scripts/generate_canvas.py --vault PATH --type counterparty-map
```

### 11. Utility scripts

```bash
python scripts/validate_vault.py --vault PATH
python scripts/import_csv.py --vault PATH --type контрагент --file data.csv
python scripts/import_vcard.py --vault PATH --counterparty "ООО Пример" --file contacts.vcf
python scripts/import_meeting.py --vault PATH --file meeting.txt [--counterparty NAME] [--format auto]
python scripts/quick_capture.py --vault PATH --type идея --text "Описание идеи"
python scripts/generate_report.py --vault PATH --type expiring-contracts --days 30
python scripts/generate_report.py --vault PATH --type overdue-payments
python scripts/generate_report.py --vault PATH --type financial-summary --period 2026-04
python scripts/audit_links.py --vault PATH [--fix]
python scripts/bulk_status_update.py --vault PATH --folder 02-ДОГОВОРЫ --status завершён
python scripts/relationship_sync.py --vault PATH [--fix] [--dry-run]
python scripts/grammar_check.py --file PATH [--verbose]
python scripts/daily_operations.py --vault PATH create-daily [--date YYYY-MM-DD]
python scripts/daily_operations.py --vault PATH morning-briefing [--days 7]
python scripts/daily_operations.py --vault PATH check-overdue
python scripts/periodic_synthesis.py --vault PATH --type weekly [--date YYYY-MM-DD]
python scripts/sync_moc.py --vault PATH [--fix] [--dry-run]
python scripts/archive_manager.py --vault PATH scan
python scripts/archive_manager.py --vault PATH archive [--folder FOLDER] [--dry-run]
```

### 12. Agent behavior

1. Determine note type from description → generate using template
2. Create ALL needed notes if description implies multiple entities
3. Ensure mutual `[[wikilinks]]` between related notes
4. Proactively ask for critical data
5. After response suggest: more notes/contacts, .base updates, .canvas, tasks
6. Extract data from unstructured text (protocols, emails, business cards)
7. On first use suggest creating full set of .base files and org chart .canvas
8. Import meeting notes from text, audio transcription, or .docx files
9. Quick capture ideas from single-line descriptions
10. Generate morning briefings and periodic retrospectives
11. Auto-sync MOC index notes when vault content changes
12. Manage archive: scan candidates, move completed items, generate reports

### 13. Dataview migration

If vault contains Dataview queries, see
[DATAVIEW_MIGRATION.md](references/DATAVIEW_MIGRATION.md) for migration to
native Obsidian Bases.

## References

- [TEMPLATES.md](references/TEMPLATES.md) — Note templates
- [TEMPLATES_CONTACTS.md](references/TEMPLATES_CONTACTS.md) — Employee and contact dossiers
- [BASES.md](references/BASES.md) — Dashboard definitions
- [CANVAS.md](references/CANVAS.md) — Canvas templates
- [TAGS.md](references/TAGS.md) — Tag taxonomy
- [RELATIONSHIPS.md](references/RELATIONSHIPS.md) — Relationship types and mirrors
- [VAULT_STRUCTURE.md](references/VAULT_STRUCTURE.md) — Folder structure
- [CONTRACT_VARS.md](references/CONTRACT_VARS.md) — Variable registry for .docx
- [DOCX_GENERATION.md](references/DOCX_GENERATION.md) — Document generation workflow
- [DATAVIEW_MIGRATION.md](references/DATAVIEW_MIGRATION.md) — Dataview → Bases migration
