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
