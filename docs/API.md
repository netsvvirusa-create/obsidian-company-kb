# API Reference

CLI interface and data format specifications for obsidian-company-kb.

## CLI interface

All Python scripts accept `--vault PATH` as a required argument pointing to the Obsidian vault root directory. Output is JSON (to stdout) unless otherwise noted.

### generate_contract.py

```
python scripts/generate_contract.py --vault PATH --contract NAME
                                    [--template PATH] [--output PATH]
                                    [--dry-run] [--check-grammar]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to Obsidian vault root |
| `--contract` | yes | Name of the contract note (e.g. `"Договор №001"`) |
| `--template` | no | Path to .docx template (default: `assets/docx-templates/contract_template.docx`) |
| `--output` | no | Output path (default: `vault/14-ВЛОЖЕНИЯ/Документы/Договор {номер}.docx`) |
| `--dry-run` | no | Show variable substitution table without generating file |
| `--check-grammar` | no | Run grammar check on generated document |

**Exit codes:** 0 on success, 1 on failure

**Output JSON:**
```json
{
  "success": true,
  "output": "/path/to/Договор 001.docx",
  "replacements": 32,
  "remaining_vars": [],
  "grammar_warnings": []
}
```

### generate_specification.py

```
python scripts/generate_specification.py --vault PATH --contract NAME --spec N
                                         [--template PATH] [--output PATH]
                                         [--dry-run] [--check-grammar]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to Obsidian vault root |
| `--contract` | yes | Name of the contract note |
| `--spec` | yes | Specification number (1-based index into `спецификации` array) |
| `--template` | no | Path to .docx template (default: `assets/docx-templates/specification_services.docx`) |
| `--output` | no | Output path (default: `vault/14-ВЛОЖЕНИЯ/Документы/Спецификация №N к Договору {номер}.docx`) |
| `--dry-run` | no | Show variable table without generating |
| `--check-grammar` | no | Run grammar check |

**Output JSON:**
```json
{
  "success": true,
  "output": "/path/to/Спецификация №1 к Договору 001.docx",
  "spec_number": 1,
  "services_count": 2,
  "total": "300 000",
  "nds": "50 000",
  "replacements": 40,
  "remaining_vars": []
}
```

### validate_vault.py

```
python scripts/validate_vault.py --vault PATH
```

**Output JSON:**
```json
{
  "vault": "/path/to/vault",
  "total_notes": 42,
  "errors": [
    {"file": "01-КОНТРАГЕНТЫ/Foo.md", "type": "missing_field", "message": "..."}
  ],
  "warnings": [
    {"file": "02-ДОГОВОРЫ/Bar.md", "type": "unresolved_link", "message": "..."}
  ],
  "summary": {
    "by_type": {"контрагент": 10, "договор": 5},
    "errors_count": 2,
    "warnings_count": 3
  }
}
```

**Error types:** `invalid_yaml`, `missing_field`, `invalid_tag`, `duplicate_inn`, `duplicate_contract_number`

**Warning types:** `unresolved_link`, `expired_active_contract`, `missing_reverse_link`

### import_csv.py

```
python scripts/import_csv.py --vault PATH --type TYPE --file CSV_PATH
                              [--dry-run] [-v]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to vault |
| `--type` | yes | Note type: `контрагент`, `контакт`, `сотрудник` |
| `--file` | yes | Path to CSV file (UTF-8, auto-detected columns) |
| `--dry-run` | no | Show what would be created without writing |
| `-v` | no | Verbose output (DEBUG level) |

### import_vcard.py

```
python scripts/import_vcard.py --vault PATH --file VCF_PATH
                               [--counterparty NAME] [-v]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to vault |
| `--file` | yes | Path to .vcf file |
| `--counterparty` | no | Counterparty name for linking contacts |
| `-v` | no | Verbose output |

### generate_report.py

```
python scripts/generate_report.py --vault PATH --type REPORT_TYPE
                                  [--days N] [--counterparty NAME]
                                  [--employee NAME] [-v]
```

| Report type | Required args | Description |
|-------------|---------------|-------------|
| `expiring-contracts` | `--days` (default 30) | Contracts expiring within N days |
| `counterparty-history` | `--counterparty` | Full history for a counterparty |
| `employee-activity` | `--employee` | Projects, contracts, meetings for an employee |

**Output:** Markdown to stdout (logs to stderr)

### audit_links.py

```
python scripts/audit_links.py --vault PATH [--fix] [-v]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to vault |
| `--fix` | no | Create stub notes for broken links |
| `-v` | no | Verbose output |

### bulk_status_update.py

```
python scripts/bulk_status_update.py --vault PATH --folder FOLDER --status STATUS
                                     [--filter "key:value"] [-v]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to vault |
| `--folder` | yes | Relative folder path (e.g. `02-ДОГОВОРЫ`) |
| `--status` | yes | New status value |
| `--filter` | no | Filter expression `key:value` |
| `-v` | no | Verbose output |

### relationship_sync.py

```
python scripts/relationship_sync.py --vault PATH [--fix] [--dry-run]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--vault` | yes | Path to vault |
| `--fix` | no | Automatically add missing reverse links |
| `--dry-run` | no | Show what would be fixed without writing |

### grammar_check.py

```
python scripts/grammar_check.py --file PATH [--verbose]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--file` | yes | Path to .docx file |
| `--verbose` | no | Show detailed per-warning output |

### init_vault.sh

```
bash scripts/init_vault.sh /path/to/vault
```

Single positional argument: the vault directory path.

### daily_operations.py

```
python scripts/daily_operations.py --vault PATH [-v] COMMAND [OPTIONS]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Subcommands:**

**`create-daily`** -- Create a daily record from template.

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--date` | no | `str` (default: today) | Date in YYYY-MM-DD format |

**`morning-briefing`** -- Generate morning briefing (Markdown to stdout).

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--days` | no | `int` (default `7`) | Horizon in days for expiring contracts |

**`check-overdue`** -- Check overdue tasks, contracts, and payments (JSON to stdout). No additional arguments.

**Output:** `create-daily` writes a file; `morning-briefing` outputs Markdown to stdout; `check-overdue` outputs JSON to stdout with keys `overdue_tasks`, `expiring_contracts`, `overdue_payments`.

### periodic_synthesis.py

```
python scripts/periodic_synthesis.py --vault PATH --type TYPE
                                     [--date DATE] [--dry-run] [-v]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `--type` | yes | `str` choices: `weekly`, `monthly` | Retrospective type |
| `--date` | no | `str` (default: today) | Date within target period (YYYY-MM-DD) |
| `--dry-run` | no | `bool` (default `false`) | Print content without creating file |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Output:** Creates a retrospective file in `09-СТРАТЕГИЯ/Ретроспективы/`. With `--dry-run`, prints Markdown to stdout.

### sync_moc.py

```
python scripts/sync_moc.py --vault PATH [--folder FOLDER]
                            [--dry-run] [--fix] [-v]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `--folder` | no | `str` (default: all folders) | Process only the specified folder |
| `--dry-run` | no | `bool` (default `false`) | Report only, no changes |
| `--fix` | no | `bool` (default `false`) | Apply fixes to `_MOC.md` files |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Output JSON:**
```json
{
  "folders_checked": 10,
  "notes_indexed": 42,
  "updates_needed": 3,
  "updates_applied": 3
}
```

### generate_canvas.py

```
python scripts/generate_canvas.py --vault PATH --type TYPE
                                  [--target NAME] [--output PATH] [-v]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `--type` | yes | `str` choices: `contract-participants`, `person-relationships`, `project-roadmap`, `counterparty-map` | Canvas type |
| `--target` | conditional | `str` (default `""`) | Target object name (required for all types except `counterparty-map`) |
| `--output` | no | `Path` (default: `12-КАНВАСЫ/`) | Output path for `.canvas` file |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Output:** Creates a `.canvas` JSON file in `12-КАНВАСЫ/` (or custom path).

### archive_manager.py

```
python scripts/archive_manager.py --vault PATH [-v] COMMAND [OPTIONS]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Subcommands:**

**`scan`** -- Find archive candidates. No additional arguments. Outputs JSON array.

**`archive`** -- Move notes to archive.

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--folder` | no | `str` (default: all) | Folder to scan (e.g. `02-ДОГОВОРЫ`) |
| `--filter` | no | `str` | Filter expression `key:value` (e.g. `status:завершён`) |
| `--days-old` | no | `int` | Minimum file age in days for archiving |
| `--dry-run` | no | `bool` (default `false`) | Report only, no actual move |

**`report`** -- Generate archive report (Markdown to stdout). No additional arguments.

**Output:** `scan` and `archive` output JSON to stdout; `report` outputs Markdown.

### import_meeting.py

```
python scripts/import_meeting.py --vault PATH --file FILE
                                 [--counterparty NAME] [--date DATE]
                                 [--format FORMAT] [--dry-run] [-v]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `--file` | yes | `Path` | Path to meeting file (.txt, .md, .docx) |
| `--counterparty` | no | `str` (default `""`) | Counterparty name for linking |
| `--date` | no | `str` (default: extracted from text or today) | Meeting date YYYY-MM-DD |
| `--format` | no | `str` choices: `auto`, `text`, `transcript`, `docx` (default `auto`) | Input file format |
| `--dry-run` | no | `bool` (default `false`) | Show what would be created without writing |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Behavior:** Creates a meeting note in `06-ПЕРЕГОВОРЫ/` and contact cards in `05-КОНТАКТЫ/` for new participants. Auto-extracts participants (FIO patterns), decisions (keywords: решено, договорились, согласовано, утверждено), and tasks (keywords: поручить, выполнить, сделать, подготовить).

### quick_capture.py

```
python scripts/quick_capture.py --vault PATH --type TYPE --text TEXT
                                [--direction DIR] [--priority PRI]
                                [--link LINK] [--author AUTHOR] [-v]
```

| Argument | Required | Type | Description |
|----------|----------|------|-------------|
| `--vault` | yes | `Path` | Path to Obsidian vault root |
| `--type` | yes | `str` choices: `идея`, `событие`, `задача` | Note type |
| `--text` | yes | `str` | Note text / description |
| `--direction` | no | `str` (default `""`) | Direction (for ideas and events) |
| `--priority` | no | `str` (default `""`) | Priority (for events; defaults to `средний` when empty) |
| `--link` | no | `str` (default `""`) | Related note (for ideas) |
| `--author` | no | `str` (default `""`) | Author (for ideas) |
| `-v`, `--verbose` | no | `bool` (default `false`) | Verbose output (DEBUG level) |

**Behavior:** `идея` creates a note in `09-СТРАТЕГИЯ/Идеи/`; `событие` creates a note in `07-ОПЕРАЦИИ/`; `задача` appends a task to today's daily record in `08-КАЛЕНДАРЬ/` (creates the record if it does not exist).

---

## Data formats

### YAML frontmatter

Every note starts with YAML frontmatter between `---` delimiters. Required fields for all notes:

```yaml
---
title: "Human-readable title"
type: контрагент          # one of 11 note types
tags:
  - тип/контрагент        # type tag (mandatory)
  - статус/активный       # status tag (mandatory)
---
```

Type-specific required fields are documented in `references/TEMPLATES.md`.

### .base dashboard YAML

`.base` files use Obsidian Bases format:

```yaml
filters:
  and:
    - file.inFolder("01-КОНТРАГЕНТЫ")
    - 'статус == "активный"'
formulas:
  computed_field: 'expression'
properties:
  formula.computed_field:
    displayName: "Display Name"
views:
  - type: table          # table | cards | list
    name: "View Name"
    order:
      - file.name
      - property_name
    groupBy:
      property: category
      direction: ASC
    summaries:
      numeric_field: Sum
    limit: 50
    filters:              # view-level filters
      and:
        - 'condition'
```

### .canvas JSON

`.canvas` files follow the JSON Canvas specification:

```json
{
  "nodes": [
    {
      "id": "unique-id",
      "type": "file",
      "file": "path/to/note.md",
      "x": 0, "y": 0, "width": 300, "height": 80,
      "color": "1"
    },
    {
      "id": "group-id",
      "type": "group",
      "label": "Group Name",
      "x": -400, "y": 150, "width": 350, "height": 250
    }
  ],
  "edges": [
    {
      "id": "edge-id",
      "fromNode": "source-id", "fromSide": "bottom",
      "toNode": "target-id", "toSide": "top",
      "label": "relationship"
    }
  ]
}
```

Node types: `file`, `text`, `link`, `group`

### {{VAR}} template syntax

Template variables in .docx files follow this format:

```
{{VAR|Identifier|Default value}}
```

- **Identifier** -- unique variable name matching the registry in `CONTRACT_VARS.md`
- **Default value** -- used when the variable cannot be resolved from vault data
- **Nesting** -- identifiers can contain other `{{VAR|...|...}}` references, resolved recursively inside-out:

```
{{VAR|Вариант выполняемых работ {{VAR|Номер варианта выполняемых работ|1}}|Описание}}
```

Resolution order:
1. Inner variable: `{{VAR|Номер варианта выполняемых работ|1}}` resolves to `1`
2. Outer variable: `{{VAR|Вариант выполняемых работ 1|Описание}}` resolves to service name

Word run handling: variables may span multiple Word runs due to formatting. The substitution engine concatenates all run texts, performs replacement, then writes the result back to the first run and clears subsequent runs.

### Variable sources

Variables are resolved from three frontmatter sources:

| Source | YAML fields | Variable count |
|--------|-------------|---------------|
| Contract note (`type: договор`) | `номер`, `дата_подписания`, `вид_стороны_*`, `*_рп` fields | 10 |
| Company note (`type: наша_компания`) | `опф_*`, `название_*`, `адрес`, `инн`, `кпп`, `банк`, etc. | 11 |
| Counterparty note (`type: контрагент`) | Same fields as company | 11 |
| Specification data (`спецификации[N]`) | `дата`, `услуги[i].*`, calculated totals | 5+ |

Fields ending with `_рп` store values in genitive case (Russian "родительный падеж") as required by legal document phrasing.

### Financial note frontmatter

**Платёж** (`type: платёж`):

```yaml
---
title: "2026-04-05 Платёж ООО Пример"
type: платёж
дата: 2026-04-05
контрагент: "[[ООО Пример]]"
договор: "[[Договор №001]]"
сумма: 0
валюта: RUB
направление: исходящий       # исходящий | входящий
статус: ожидается             # ожидается | оплачен | просрочен | отменён
номер_счёта: ""
назначение: ""
ответственный: "[[Иванов Иван]]"
tags:
  - тип/платёж
  - статус/ожидается
---
```

**Счёт** (`type: счёт`):

```yaml
---
title: "Счёт №001 от 2026-04-05"
type: счёт
номер: "001"
дата_выставления: 2026-04-05
дата_оплаты_план: 2026-04-20
контрагент: "[[ООО Пример]]"
договор: "[[Договор №001]]"
сумма: 0
сумма_ндс: 0
валюта: RUB
направление: исходящий
статус: выставлен              # выставлен | оплачен | просрочен | отменён
tags:
  - тип/счёт
  - статус/выставлен
---
```

**Бюджет** (`type: бюджет`):

```yaml
---
title: "Бюджет 2026-Q2"
type: бюджет
период: "2026-Q2"
дата_создания: 2026-04-05
статус: черновик               # черновик | утверждён | закрыт
доходы_план: 0
расходы_план: 0
доходы_факт: 0
расходы_факт: 0
ответственный: "[[Иванов Иван]]"
tags:
  - тип/бюджет
  - статус/черновик
---
```

### Retrospective note frontmatter

```yaml
---
title: "Ретроспектива: Неделя 2026-04-05"
type: ретроспектива
период: неделя                 # неделя | месяц
дата_начала: 2026-04-05
дата_окончания: 2026-04-11
tags:
  - тип/ретроспектива
---
```

Sections: `Выполненные задачи`, `Проведённые встречи`, `Принятые решения и события`, `Открытые вопросы`. Monthly retrospectives additionally include `Активность по проектам` and `Активность по договорам`.

### Canvas JSON format

Canvas files (`.canvas`) follow the JSON Canvas specification. See the `.canvas JSON` section above for the full node/edge schema. The `generate_canvas.py` script produces four canvas types:

| Type | Description | Root node |
|------|-------------|-----------|
| `contract-participants` | Both sides of a contract with signers and contacts | Contract note |
| `person-relationships` | All relationships for a person (employee or contact) | Person note |
| `project-roadmap` | Project milestones and timeline | Project note |
| `counterparty-map` | All counterparties grouped by category | Company note |

Node colors: `"1"` (red), `"2"` (orange), `"3"` (yellow), `"4"` (green), `"5"` (cyan), `"6"` (purple). Groups use `type: "group"` with a `label` field.
