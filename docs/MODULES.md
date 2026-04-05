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

---

## daily_operations.py

**Purpose:** Daily vault operations: create daily records from template, generate morning briefings, check overdue tasks/contracts/payments.

**CLI:**
```bash
python scripts/daily_operations.py --vault PATH [-v] create-daily [--date YYYY-MM-DD]
python scripts/daily_operations.py --vault PATH [-v] morning-briefing [--days 7]
python scripts/daily_operations.py --vault PATH [-v] check-overdue
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `parse_frontmatter(text)` -- extracts YAML frontmatter from .md file
- `read_notes(vault, folder)` -- reads all .md files from a vault folder, returns (path, frontmatter, text) tuples
- `cmd_create_daily(vault, target_date)` -- creates a daily record from template in `08-КАЛЕНДАРЬ/`, pulls meetings from `06-ПЕРЕГОВОРЫ/` and carry-over tasks from yesterday
- `cmd_morning_briefing(vault, days)` -- generates Markdown morning briefing with overdue tasks, today's meetings, expiring contracts, and recent events
- `cmd_check_overdue(vault)` -- checks overdue tasks, expiring/overdue contracts, and overdue payments; returns JSON with `overdue_tasks`, `expiring_contracts`, `overdue_payments`

**Output:** `create-daily` writes file to `08-КАЛЕНДАРЬ/`; `morning-briefing` outputs Markdown to stdout; `check-overdue` outputs JSON to stdout

---

## periodic_synthesis.py

**Purpose:** Generate weekly and monthly retrospectives by aggregating data from daily records, negotiations, operations, projects, and contracts.

**CLI:**
```bash
python scripts/periodic_synthesis.py --vault PATH --type weekly [--date YYYY-MM-DD] [--dry-run] [-v]
python scripts/periodic_synthesis.py --vault PATH --type monthly [--date YYYY-MM-DD] [--dry-run] [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `generate_weekly(vault, ref_date)` -- generates weekly retrospective (completed tasks, meetings, operations, open questions) for the week containing `ref_date`
- `generate_monthly(vault, ref_date)` -- generates monthly retrospective with additional project and contract activity sections
- `_collect_daily_notes(vault, start, end)` -- collects daily records for a date range
- `_collect_meetings(vault, start, end)` -- collects negotiations for a date range
- `_collect_operations(vault, start, end)` -- collects operational events for a date range
- `_collect_contract_activity(vault, start, end)` -- collects signed/expiring contracts for a date range

**Output:** Retrospective .md file in `09-СТРАТЕГИЯ/Ретроспективы/` (or stdout with `--dry-run`)

---

## sync_moc.py

**Purpose:** Synchronize MOC (Map of Content) index notes with actual folder contents, detecting new and removed notes.

**CLI:**
```bash
python scripts/sync_moc.py --vault PATH [--folder FOLDER] [--fix] [--dry-run] [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `sync_moc(vault, folder_filter, dry_run, fix)` -- main function: scans folders with `_MOC.md`, compares existing links to actual notes, optionally updates
- `_extract_existing_links(moc_text)` -- extracts wikilinks from the `## Содержимое` section of a MOC file
- `_scan_folder_notes(folder)` -- scans .md files in a folder, returns (stem, title, status) tuples
- `_group_by_status(notes)` -- groups notes into "Активные" and "Завершённые" categories
- `_build_moc_content(folder_name, notes)` -- builds full _MOC.md content from scratch
- `_update_moc_section(existing_text, folder_name, notes)` -- updates only the `## Содержимое` section in an existing MOC

**Output:** JSON with `folders_checked`, `notes_indexed`, `updates_needed`, `updates_applied` to stdout

---

## generate_canvas.py

**Purpose:** Generate `.canvas` files from vault data with automatic node layout (radial, tree, timeline).

**CLI:**
```bash
python scripts/generate_canvas.py --vault PATH --type contract-participants --target "Договор №001" [--output PATH] [-v]
python scripts/generate_canvas.py --vault PATH --type person-relationships --target "Иванов Иван" [--output PATH] [-v]
python scripts/generate_canvas.py --vault PATH --type project-roadmap --target "Проект Альфа" [--output PATH] [-v]
python scripts/generate_canvas.py --vault PATH --type counterparty-map [--output PATH] [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `generate_contract_participants(vault, target, output)` -- generates canvas with our side and counterparty side groups, linked to a central contract node
- `generate_person_relationships(vault, target, output)` -- generates radial canvas of a person's relationships from frontmatter and wikilinks
- `generate_project_roadmap(vault, target, output)` -- generates timeline canvas of project milestones and stages
- `generate_counterparty_map(vault, output)` -- generates map of all counterparties with contract connections
- `layout_radial(cx, cy, radius, count)` -- computes positions on a circle
- `layout_tree(x, y, children_count, spacing)` -- computes top-down tree positions
- `layout_timeline(x_start, y, count, spacing)` -- computes left-to-right timeline positions
- `build_canvas(nodes, edges)` -- assembles canvas structure from nodes and edges
- `save_canvas(canvas, output_path)` -- saves canvas JSON to file

**Output:** `.canvas` file in `12-КАНВАСЫ/` (or custom path)

---

## archive_manager.py

**Purpose:** Archive management: scan for archival candidates, move notes to `99-АРХИВ/` with frontmatter updates, generate archive reports.

**CLI:**
```bash
python scripts/archive_manager.py --vault PATH [-v] scan
python scripts/archive_manager.py --vault PATH [-v] archive [--folder FOLDER] [--filter "key:value"] [--days-old N] [--dry-run]
python scripts/archive_manager.py --vault PATH [-v] report
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `scan_candidates(vault)` -- scans vault for archival candidates: completed/cancelled contracts and projects, completed goals past deadline, events older than 90 days
- `archive_notes(vault, folder, filter_expr, days_old, dry_run)` -- archives notes matching criteria with optional folder, filter, and age constraints
- `archive_report(vault)` -- generates Markdown report of archive contents by subfolder with recent archival dates
- `_move_to_archive(vault, note_path, reason)` -- moves a note to `99-АРХИВ/{original_folder}/`, updates frontmatter with `архивирован` date and history entry
- `_update_frontmatter_field(text, key, value)` -- adds or updates a field in frontmatter
- `_append_history(text, entry)` -- appends entry to `## История изменений` section

**Output:** `scan` and `archive` output JSON to stdout; `report` outputs Markdown to stdout

---

## import_meeting.py

**Purpose:** Import meeting summaries from text, transcription (Whisper/Otter format), or .docx files into `06-ПЕРЕГОВОРЫ/` notes with automatic extraction of participants, decisions, tasks, and discussion topics.

**CLI:**
```bash
python scripts/import_meeting.py --vault PATH --file PATH \
  [--counterparty "ООО Пример"] [--date YYYY-MM-DD] \
  [--format auto|text|transcript|docx] [--dry-run] [-v]
```

**Dependencies:** python-docx (for .docx format only)

**Key functions:**
- `import_meeting(vault, filepath, counterparty, date_str, fmt, dry_run)` -- main import function: detects format, parses content, builds meeting note, optionally creates contact cards
- `detect_format(filepath)` -- auto-detects file format (text, transcript, docx) by extension and content analysis
- `extract_participants(text)` -- extracts participant names (full and abbreviated Russian FIO patterns)
- `extract_decisions(text)` -- extracts decisions by keyword patterns (решено, договорились, согласовано, утверждено)
- `extract_tasks(text)` -- extracts tasks by keyword patterns (поручить, выполнить, сделать, подготовить)
- `parse_text(text)` -- parses plain text format
- `parse_transcript(text)` -- parses transcription format (strips timestamps and speaker markers)
- `parse_docx(filepath)` -- reads .docx file to plain text
- `build_meeting_note(data, date_str, counterparty)` -- generates full .md content for a negotiation note

**Output:** Meeting note in `06-ПЕРЕГОВОРЫ/`, optional contact cards in `05-КОНТАКТЫ/`, JSON result to stdout

---

## quick_capture.py

**Purpose:** Rapid creation of notes from a single line of text. Supports ideas (to `09-СТРАТЕГИЯ/Идеи/`), events (to `07-ОПЕРАЦИИ/`), and tasks (appended to today's daily record in `08-КАЛЕНДАРЬ/`).

**CLI:**
```bash
python scripts/quick_capture.py --vault PATH --type идея --text "Текст идеи" \
  [--direction DIR] [--priority PRI] [--link "Цель"] [--author "Имя"] [-v]
python scripts/quick_capture.py --vault PATH --type событие --text "Описание события" \
  [--direction DIR] [--priority PRI] [-v]
python scripts/quick_capture.py --vault PATH --type задача --text "Текст задачи" [-v]
```

**Dependencies:** none (stdlib only)

**Key functions:**
- `capture_idea(vault, text, direction, priority, link, author)` -- creates an idea note in `09-СТРАТЕГИЯ/Идеи/` with full template (problem, expected result, resources, validation steps)
- `capture_event(vault, text, direction, priority)` -- creates an event note in `07-ОПЕРАЦИИ/` with description, measures, and result sections
- `capture_task(vault, text)` -- adds a task to today's daily record in `08-КАЛЕНДАРЬ/`; creates the daily record from template if it does not exist

**Supported types:** `идея`, `событие`, `задача`
