# Security

Security considerations and protections implemented in obsidian-company-kb.

## Path traversal protection

All file paths are resolved within the vault directory boundary. Scripts accept `--vault PATH` as the root and construct all file paths relative to it:

- `resolve_wikilink()` searches only within the vault using `vault.rglob("*.md")`
- `find_note_by_type()` scans only within the vault directory
- Output files default to `vault/14-ВЛОЖЕНИЯ/Документы/`
- `init_vault.sh` creates folders only under the provided vault path
- `_safe_filename()` strips characters that could enable path traversal: `< > : " / \ | ? *`

No script follows symbolic links outside the vault or accepts absolute paths for note references.

## YAML injection mitigation

All YAML parsing uses `yaml.safe_load()` exclusively:

- `generate_contract.py` -- `parse_frontmatter()` uses `yaml.safe_load()`
- `validate_vault.py` -- `_parse_frontmatter()` uses `yaml.safe_load()` with error handling
- When PyYAML is unavailable, `validate_vault.py` falls back to a minimal key-value parser (`_simple_yaml_parse()`) that does not evaluate arbitrary YAML constructs

The `yaml.safe_load()` function prevents deserialization of arbitrary Python objects, blocking code execution through crafted YAML payloads.

## Shell injection prevention

No script uses `subprocess` with `shell=True`:

- `init_vault.sh` is a self-contained bash script that does not invoke Python or other interpreters with user-controlled strings
- All Python scripts operate through the `pathlib` module and standard library file I/O
- No `os.system()`, `subprocess.call()`, or `subprocess.Popen()` calls exist in the codebase
- File operations use `Path.read_text()`, `Path.write_text()`, and `Path.mkdir()` exclusively

## Confidential data handling

The skill handles corporate data including:

- **INN/OGRN** -- Tax identification numbers
- **Bank details** -- Account numbers, BIK, correspondent accounts
- **Personal data** -- Employee and contact information (names, phones, emails)
- **Contract terms** -- Amounts, dates, obligations

### Protection measures

1. **PII in collapsible callouts** -- Contact details are stored in collapsible `> [!info]-` and `> [!warning]-` Obsidian callouts, collapsed by default
2. **Confidential data callout** -- Sensitive information uses `> [!warning]-` callouts with the collapse flag
3. **No network access** -- Scripts operate entirely locally; no data is sent over the network
4. **No logging of sensitive values** -- Log output includes file paths and operation counts but not actual PII values
5. **No credential storage** -- The skill does not manage passwords, API keys, or authentication tokens

## File access restrictions

All file operations are restricted to the vault directory:

| Operation | Scope | Scripts |
|-----------|-------|---------|
| Read .md files | `vault/**/*.md` | All scripts |
| Write .md files | `vault/{folder}/*.md` | import_csv, import_vcard, audit_links, bulk_status_update, relationship_sync |
| Read .docx templates | `assets/docx-templates/` or user-specified path | generate_contract, generate_specification |
| Write .docx files | `vault/14-ВЛОЖЕНИЯ/Документы/` or user-specified path | generate_contract, generate_specification |
| Read CSV/VCF | User-specified path (read-only) | import_csv, import_vcard |
| Create directories | Within vault only | init_vault.sh, import scripts |
| Delete/move files | `vault/{folder}/ -> vault/99-АРХИВ/` | bulk_status_update, archive_manager |
| Read meeting files | User-specified path (read-only) | import_meeting |
| Write .canvas files | `vault/**/*.canvas` | generate_canvas |
| Create notes (quick) | `vault/{folder}/*.md` | quick_capture |
| Read/write daily notes | `vault/08-КАЛЕНДАРЬ/*.md` | daily_operations |
| Read/write synthesis notes | `vault/09-СТРАТЕГИЯ/**/*.md` | periodic_synthesis |
| Read/write MOC notes | `vault/**/*MOC*.md` | sync_moc |

## Security notes for new scripts

### import_meeting.py

- File reading only -- reads meeting text/docx files, no network access
- Path validation ensures input files exist and are readable
- Output notes are created within the vault directory only
- Uses `yaml.safe_load()` for any YAML parsing

### generate_canvas.py

- Generates JSON Canvas (.canvas) files within the vault only
- No external file access or network communication
- Output paths are validated to remain within vault boundaries

### archive_manager.py

- Moves files within the vault only (from working folders to `99-АРХИВ/`)
- Path traversal protection -- all source and destination paths are resolved within vault
- Does not delete files, only relocates them
- Supports `--dry-run` for previewing changes

### daily_operations.py, periodic_synthesis.py, sync_moc.py

- Vault-local operations only -- read and write .md files within the vault
- No network access, no external file I/O
- All paths are resolved relative to the vault root
- Use `yaml.safe_load()` for frontmatter parsing

### quick_capture.py

- Creates files within the vault only
- Filename sanitization via `_safe_filename()` -- strips characters that could enable path traversal
- Input text is treated as plain data, not evaluated or executed
- Note type is validated against the allowed type list

## Input validation

- **Frontmatter validation** -- `validate_vault.py` checks required fields, tag taxonomy, and data types
- **Duplicate detection** -- Import scripts check for existing INN values and file names before creating notes
- **Date validation** -- Date fields are parsed with `date.fromisoformat()` and validated
- **Tag taxonomy enforcement** -- Only tags with allowed prefixes (`тип/`, `статус/`, `приоритет/`, `направление/`, `связь/`) pass validation

## Dependency security

Development dependencies include security-oriented tools:

- **ruff** with `S` (bandit) rules enabled -- static security analysis
- **vulture** -- dead code detection to reduce attack surface
- **mypy** -- type checking to catch type confusion bugs

The `make audit` target runs all three tools:
```bash
python -m ruff check scripts/ --select S
python -m vulture scripts/ --min-confidence 80
python -m mypy scripts/ --ignore-missing-imports
```
