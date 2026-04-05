# Modules

Detailed documentation for each script in the `scripts/` directory.

---

## init_vault.sh

**Purpose:** Initialize an Obsidian vault with the full folder structure, dashboards, canvases, and MOC index notes.

**CLI:**
```bash
bash scripts/init_vault.sh /path/to/vault
```

**Dependencies:** bash, coreutils (mkdir, cp, cat)

**Key behavior:**
- Creates 15 top-level folders and subfolders (20 directories total)
- Copies `.base` dashboard files from `assets/vault-init/bases/` to `11-БАЗЫ/`
- Copies `.canvas` map files from `assets/vault-init/canvases/` to `12-КАНВАСЫ/`
- Creates `_MOC.md` index notes in 8 main folders
- Idempotent: skips existing folders, files, and MOC notes

---

## generate_contract.py

**Purpose:** Generate a .docx contract document by substituting vault data into a Word template.

**CLI:**
```bash
python scripts/generate_contract.py --vault PATH --contract "Договор №001" \
  [--template PATH] [--output PATH] [--dry-run] [--check-grammar]
```

**Dependencies:** pyyaml, python-docx, (optional) pymorphy3 for grammar check

**Key functions:**
- `parse_frontmatter(filepath)` -- extracts YAML frontmatter from .md file using `yaml.safe_load`
- `resolve_wikilink(vault, link)` -- finds a file by wikilink name (stem match)
- `find_note_by_type(vault, note_type)` -- finds a note by `type` field value
- `format_date_russian(date_str)` -- converts `YYYY-MM-DD` to Russian format
- `build_contract_variables(contract_fm, company_fm, counterparty_fm)` -- assembles 32 variable dictionary from three frontmatter sources
- `replace_vars_in_paragraph(paragraph, variables)` -- replaces `{{VAR|ID|default}}` across Word runs
- `process_document(doc, variables)` -- processes all paragraphs, tables, headers, and footers
- `check_remaining_vars(doc)` -- reports unreplaced variables
- `generate_contract(...)` -- main orchestration function, returns JSON result dict

**Output:** `.docx` file in `14-ВЛОЖЕНИЯ/Документы/` (or custom path), JSON result to stdout

---

## generate_specification.py

**Purpose:** Generate a .docx specification appendix to a contract with dynamic service tables, totals, and VAT calculation.

**CLI:**
```bash
python scripts/generate_specification.py --vault PATH --contract "Договор №001" \
  --spec 1 [--template PATH] [--output PATH] [--dry-run] [--check-grammar]
```

**Dependencies:** pyyaml, python-docx, (optional) pymorphy3

**Key functions:**
- `resolve_nested_vars(text, variables)` -- recursively resolves nested `{{VAR|...|...}}` inside-out
- `replace_vars_in_paragraph_nested(paragraph, variables)` -- nested-aware paragraph replacement
- `format_number_with_spaces(num)` -- formats numbers with space as thousands separator (e.g. `150 000`)
- `clone_row(table, row_idx)` -- deep-copies a Word table row for dynamic service rows
- `find_service_table(doc)` -- locates the service table by header text
- `process_service_table(table, services, variables)` -- fills service rows, calculates totals and VAT (20%)
- `generate_specification(...)` -- main function, reads specification data from `спецификации[N]` in contract frontmatter

**Output:** `.docx` file, JSON result to stdout

---

## validate_vault.py

**Purpose:** Validate the Obsidian vault: check frontmatter schema, tags, links, duplicates, expired contracts, and bidirectional relationships.

**CLI:**
```bash
python scripts/validate_vault.py --vault PATH
```

**Dependencies:** pyyaml (optional, has fallback parser)

**Key functions:**
- `_parse_frontmatter(text)` -- parses YAML with error reporting
- `_simple_yaml_parse(raw)` -- fallback parser when PyYAML is unavailable
- `_extract_wikilinks(text)` -- extracts `[[link]]` targets from body
- `validate_vault(vault_path)` -- main validation, checks:
  - Required fields per note type (common + type-specific)
  - Tag taxonomy compliance
  - Unresolved wikilinks
  - Duplicate INN values across counterparties
  - Duplicate contract numbers
  - Expired active contracts (end date in the past)
  - Missing reverse bidirectional links

**Output:** JSON with `total_notes`, `errors`, `warnings`, `summary`

---

## import_csv.py

**Purpose:** Import counterparties, contacts, or employees from CSV files into vault .md notes.

**CLI:**
```bash
python scripts/import_csv.py --vault PATH --type контрагент --file data.csv \
  [--dry-run] [-v]
```

**Dependencies:** csv (stdlib)

**Key functions:**
- `map_columns(headers, col_map)` -- auto-detects CSV columns by matching against known aliases (Russian and English)
- `collect_existing_keys(vault, folder, key_field)` -- builds set of existing values for duplicate checking
- `import_csv(vault, note_type, csv_path, dry_run)` -- reads CSV, maps columns, checks duplicates, generates .md files
- `_build_counterparty_md(fields, today)` -- generates counterparty note content
- `_build_contact_md(fields, today)` -- generates contact note content
- `_build_employee_md(fields, today)` -- generates employee note content
- `_safe_filename(name)` -- sanitizes strings for use as filenames

**Supported types:** `контрагент`, `контакт`, `сотрудник`

---

## import_vcard.py

**Purpose:** Import contacts from vCard 3.0/4.0 (.vcf) files into vault contact notes.

**CLI:**
```bash
python scripts/import_vcard.py --vault PATH --file contacts.vcf \
  [--counterparty "ООО Пример"] [-v]
```

**Dependencies:** vobject

**Key functions:**
- `extract_contact(card)` -- extracts title, phones, emails, organization, role from vCard object
- `build_contact_md(fields, counterparty, today)` -- generates contact .md content
- `update_counterparty_card(vault, counterparty, contact_names)` -- adds `[[contact]]` wikilinks to counterparty frontmatter
- `import_vcard(vault, vcf_path, counterparty)` -- main import function

**Behavior:** Creates contacts in `05-КОНТАКТЫ/` with filename `Фамилия Имя (Контрагент).md`. Optionally updates the counterparty card with new contact links.

---

## generate_report.py

**Purpose:** Generate Markdown reports from vault data.

**CLI:**
```bash
python scripts/generate_report.py --vault PATH --type expiring-contracts --days 30
python scripts/generate_report.py --vault PATH --type counterparty-history --counterparty "ООО Пример"
python scripts/generate_report.py --vault PATH --type employee-activity --employee "Иванов Иван"
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `report_expiring_contracts(vault, days)` -- finds active contracts expiring within N days
- `report_counterparty_history(vault, counterparty)` -- aggregates contacts, contracts, projects, negotiations for a counterparty
- `report_employee_activity(vault, employee)` -- lists projects, contracts, and negotiations involving an employee

**Output:** Markdown text to stdout (logs to stderr)

---

## audit_links.py

**Purpose:** Audit wikilinks in the vault, find broken references, optionally create stub notes.

**CLI:**
```bash
python scripts/audit_links.py --vault PATH [--fix] [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `build_file_index(vault)` -- builds `{stem_lower: path}` index of all .md files
- `extract_wikilinks(text)` -- extracts link targets, excluding media embeds
- `guess_type_from_context(link_target, source_fm, source_text)` -- infers note type from link name and source context
- `create_stub(vault, link_target, note_type)` -- creates minimal .md stub with frontmatter
- `audit_links(vault, fix)` -- scans vault, reports broken links, optionally creates stubs

**Fix behavior:** Stubs are created in the type-appropriate folder (e.g. `01-КОНТРАГЕНТЫ/` for contracts) or `00-INBOX/` if type cannot be determined.

---

## bulk_status_update.py

**Purpose:** Mass-update the `статус` field in notes within a folder. Optionally archives completed/cancelled notes.

**CLI:**
```bash
python scripts/bulk_status_update.py --vault PATH --folder 02-ДОГОВОРЫ --status завершён \
  [--filter "категория:клиент"] [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `update_status_in_text(text, new_status)` -- updates `статус:` and `статус/*` tag in frontmatter
- `add_history_entry(text, entry)` -- appends to `## История изменений` section
- `matches_filter(fm, filter_expr)` -- evaluates `key:value` filter against frontmatter
- `bulk_status_update(vault, folder, new_status, filter_expr)` -- processes all notes in folder

**Archive behavior:** Notes set to `завершён` or `отменён` are moved to `99-АРХИВ/{folder_name}/`.

---

## relationship_sync.py

**Purpose:** Check and fix bidirectional relationship links between employee and contact notes.

**CLI:**
```bash
python scripts/relationship_sync.py --vault PATH [--fix] [--dry-run]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `_parse_связи_yaml(frontmatter)` -- extracts wikilinks from `связи:` YAML list
- `_parse_связи_table(body)` -- parses `## Связи и отношения` Markdown table
- `_mirror_description(description)` -- returns mirrored relationship description (e.g. `руководит` -> `подчиняется`)
- `_add_yaml_link(frontmatter, target_name)` -- adds wikilink to `связи:` list
- `_add_table_row(body, target_name, rel_type, description)` -- adds row to relationship table
- `sync_relationships(vault, fix, dry_run)` -- main function, scans `04-СОТРУДНИКИ/` and `05-КОНТАКТЫ/`

**Output:** JSON with `checked`, `missing_reverse`, `issues`, and optionally `fixed` count

---

## grammar_check.py

**Purpose:** Check Russian grammar in .docx legal documents. Validates genitive case and gender agreement in standard legal phrases.

**CLI:**
```bash
python scripts/grammar_check.py --file PATH [--verbose]
```

**Dependencies:** python-docx, pymorphy3 (optional, degrades gracefully)

**Key functions:**
- `is_genitive(word)` -- checks if a word is in genitive case using pymorphy3
- `check_v_litse(text, para_num)` -- validates genitive after "в лице"
- `check_na_osnovanii(text, para_num)` -- validates genitive after "на основании"
- `check_imenuemoe(text, para_num)` -- validates gender agreement of "именуемое/ый/ая" with OPF type
- `check_deystvuyushego(text, para_num)` -- validates gender agreement of "действующего/ей" with signatory gender
- `check_document(filepath, verbose)` -- scans all paragraphs and table cells

**Checked patterns:**
1. "в лице [position] [name]" -- genitive case required
2. "на основании [document]" -- genitive case required
3. "именуемое/ый/ая" -- must agree with legal entity type (ООО = neuter, ИП = masculine)
4. "действующего/ей" -- must agree with signatory gender (detected by patronymic ending)
