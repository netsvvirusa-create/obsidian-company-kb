# Testing

Test strategy, execution instructions, and fixture descriptions for obsidian-company-kb.

## Current status

- **Tests passed:** 598
- **Code coverage:** 79%
- **Test files:** 23
- **Scripts covered:** 19

## Test strategy

Testing is organized into three layers:

### Unit tests (`@pytest.mark.unit`)

Test individual functions in isolation:

- `parse_frontmatter()` -- YAML parsing with valid, invalid, and edge-case inputs
- `format_date_russian()` -- date formatting for different dates and invalid inputs
- `build_contract_variables()` -- variable dictionary assembly from frontmatter data
- `replace_vars_in_paragraph()` -- variable substitution in Word paragraph runs
- `resolve_nested_vars()` -- recursive nested variable resolution
- `is_genitive()` -- morphological case detection
- `map_columns()` -- CSV column auto-detection
- `_safe_filename()` -- filename sanitization
- `_mirror_description()` -- relationship mirror lookup
- `matches_filter()` -- filter expression evaluation

### Integration tests (`@pytest.mark.integration`)

Test script functions operating on temporary vault structures:

- `validate_vault()` with populated vault -- checks error/warning detection
- `import_csv()` with sample CSV -- verifies note generation and duplicate handling
- `import_vcard()` with sample VCF -- verifies contact creation and counterparty linking
- `audit_links()` with broken references -- verifies detection and stub creation
- `relationship_sync()` with asymmetric links -- verifies fix behavior
- `bulk_status_update()` with filter -- verifies status change and archival

### Functional tests (`@pytest.mark.functional`)

End-to-end tests that exercise complete workflows:

- Full contract generation from vault data through .docx output
- Specification generation with dynamic service tables
- Vault initialization via `init_vault.sh`
- Complete import-validate-report cycle

## Running tests

### All tests

```bash
make test
```

Equivalent to:
```bash
python -m pytest tests/ -v --tb=short
```

### By category

```bash
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-functional    # Functional tests only
```

Equivalent to:
```bash
python -m pytest tests/ -v -m unit
python -m pytest tests/ -v -m integration
python -m pytest tests/ -v -m functional
```

### Code coverage

```bash
make coverage
```

Equivalent to:
```bash
python -m pytest tests/ --cov=scripts --cov-report=term-missing --cov-report=html:docs/coverage_html
```

Coverage report is generated in two formats:
- Terminal output with missing line numbers
- HTML report in `docs/coverage_html/`

### Coverage target

**Minimum coverage: 80%** (enforced in `pyproject.toml`):

```toml
[tool.coverage.report]
fail_under = 80
```

### Linting

```bash
make lint
```

Runs ruff check and format verification on `scripts/` (19 scripts) and `tests/` (23 test files).

### Security audit

```bash
make audit
```

Runs:
- `ruff check --select S` (bandit security rules)
- `vulture` (dead code detection)
- `mypy` (type checking)

### Full pipeline

```bash
make all
```

Runs lint, test, coverage, and audit in sequence.

## Test files

| File | Description |
|------|-------------|
| `tests/conftest.py` | Shared pytest fixtures (vault, notes, template paths) |
| `tests/test_skill_frontmatter.py` | SKILL.md frontmatter validation |
| `tests/test_templates.py` | Note template structure and field checks |
| `tests/test_bases.py` | .base dashboard YAML validation |
| `tests/test_canvas.py` | .canvas JSON structure validation |
| `tests/test_validate_vault.py` | Vault validation logic |
| `tests/test_init_vault.py` | Vault initialization script |
| `tests/test_import_csv.py` | CSV import functionality |
| `tests/test_financial.py` | Financial module (payments, invoices, budgets) |
| `tests/test_import_meeting.py` | Meeting import functionality |
| `tests/test_quick_capture.py` | Quick capture functionality |
| `tests/test_daily_operations.py` | Daily operations (briefings, overdue checks) |
| `tests/test_periodic_synthesis.py` | Periodic synthesis (weekly/monthly retrospectives) |
| `tests/test_sync_moc.py` | MOC index synchronization |
| `tests/test_generate_canvas.py` | Canvas generation from vault data |
| `tests/test_archive_manager.py` | Archive management (scan, archive, reports) |

## Fixture descriptions

### Shared fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `tmp_vault` | Temporary vault with all 20 directories created in `tmp_path` |
| `sample_company_note` | Company note (`type: наша_компания`) with full requisites |
| `sample_counterparty_note` | Counterparty note (`type: контрагент`) with INN, bank details |
| `sample_contract_note` | Contract note (`type: договор`) with specifications, signatory data |
| `sample_employee_note` | Employee note (`type: сотрудник`) with relationship links and table |
| `sample_employee_note_2` | Second employee for bidirectional relationship testing |
| `sample_contact_note` | Contact note (`type: контакт`) linked to counterparty |
| `contract_template_path` | Path to `.docx` contract template fixture |
| `specification_template_path` | Path to `.docx` specification template fixture |

### File fixtures (tests/fixtures/)

| File | Description |
|------|-------------|
| `contract_template.docx` | Word contract template with `{{VAR\|...\|...}}` placeholders |
| `specification_services.docx` | Word specification template with service table |
| `sample.csv` | CSV file with counterparty data for import testing |
| `sample.vcf` | vCard file with contact data for import testing |
| `sample_notes/` | Pre-built .md notes for integration tests |
| `sample_vault/` | Complete sample vault structure for functional tests |

## Configuration

Test configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "functional: functional tests",
]
```

Strict markers mode prevents typos in marker names from silently creating new markers.
