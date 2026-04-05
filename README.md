# obsidian-company-kb

Corporate knowledge base management for Obsidian vaults. An agent skill that manages counterparties, contracts, employees, contacts, negotiations, projects, operations, and strategy. Generates .docx contracts and specifications with Russian grammar checking.

Built on the [Agent Skills specification](https://agentskills.io).

## Features

- **15 note types** (контрагент, контакт, сотрудник, договор, проект, переговоры, событие, дневная_запись, цель, идея, наша_компания, платёж, счёт, бюджет, ретроспектива)
- **13 `.base` dashboards** -- active contracts, counterparties, contacts, employees, negotiations, strategic goals, operational events, calendar, people relationships, payments, invoices, budgets, retrospectives
- **6 `.canvas` maps** -- org chart, contract participants, relationship map, strategic map, project roadmap, counterparty map
- **`.docx` generation** -- contracts and specifications from .docx templates with `{{VAR|ID|default}}` syntax and nested variable resolution
- **Grammar check** -- Russian genitive case validation for legal documents using pymorphy3
- **CSV import** -- bulk import of counterparties, contacts, and employees from CSV files with auto-column detection
- **vCard import** -- import contacts from .vcf files with automatic counterparty card linking
- **Meeting import** -- import meetings from text, transcription (Whisper/Otter), or .docx files with automatic participant, decision, and task extraction
- **Quick capture** -- rapid creation of ideas, events, and tasks from a single line of text
- **Daily operations** -- daily record creation, morning briefings, overdue task/contract/payment checks
- **Retrospectives** -- weekly and monthly retrospective synthesis from vault activity
- **MOC index sync** -- automatic population and synchronization of Map of Content index notes
- **Canvas generation** -- generate .canvas files from vault data (contract participants, person relationships, project roadmaps, counterparty maps)
- **Archive management** -- archive scanning with auto-rules, note archival with frontmatter updates, archive reporting
- **Vault validation** -- frontmatter checks, tag taxonomy enforcement, duplicate detection, broken link audit
- **Bidirectional relationships** -- automatic mirrored relationship sync between people cards
- **Bulk operations** -- mass status updates with optional archival
- **Reports** -- expiring contracts, counterparty history, employee activity, 3 new financial report types

## Installation

### Via skills marketplace

Search for `obsidian-company-kb` in the agent skills marketplace.

### Manual installation

```bash
git clone https://github.com/cifratronika/obsidian-company-kb.git
cd obsidian-company-kb
pip install -r requirements.txt
```

## Dependencies

- Python 3.10+
- [pyyaml](https://pypi.org/project/PyYAML/) >= 6.0 -- YAML frontmatter parsing
- [python-docx](https://pypi.org/project/python-docx/) >= 1.1.0 -- .docx template processing
- [pymorphy3](https://pypi.org/project/pymorphy3/) >= 2.0 -- Russian morphological analysis
- [pymorphy3-dicts-ru](https://pypi.org/project/pymorphy3-dicts-ru/) >= 2.0 -- Russian language dictionaries
- [vobject](https://pypi.org/project/vobject/) >= 0.9.7 -- vCard parsing

### Depends on (Agent Skills)

This skill depends on the following skills from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills):

- `obsidian-markdown` -- Obsidian Flavored Markdown rules (wikilinks, callouts, embeds)
- `obsidian-bases` -- `.base` dashboard YAML format
- `json-canvas` -- `.canvas` JSON format specification
- `obsidian-cli` -- Obsidian CLI operations

## Quick start

### 1. Initialize vault

```bash
bash scripts/init_vault.sh /path/to/vault
```

Creates 15 folders, 13 `.base` dashboards, 6 `.canvas` maps, and MOC index notes.

### 2. Create company note

Create a `type: наша_компания` note with your company requisites. This data is used for .docx contract generation.

### 3. Add counterparties

Create counterparty cards in `01-КОНТРАГЕНТЫ/` with INN, addresses, bank details. Link contact persons from `05-КОНТАКТЫ/`.

### 4. Generate documents

```bash
python scripts/generate_contract.py --vault /path/to/vault --contract "Договор №001"
python scripts/generate_specification.py --vault /path/to/vault --contract "Договор №001" --spec 1
```

## Scripts

| Script | Description |
|--------|-------------|
| `init_vault.sh` | Initialize vault folder structure, dashboards, canvases, and MOC notes |
| `generate_contract.py` | Generate .docx contract from template and vault data |
| `generate_specification.py` | Generate .docx specification with dynamic service tables |
| `validate_vault.py` | Validate frontmatter, tags, links, duplicates, and relationships |
| `import_csv.py` | Import counterparties, contacts, or employees from CSV |
| `import_vcard.py` | Import contacts from vCard (.vcf) files |
| `generate_report.py` | Generate reports: expiring contracts, counterparty history, employee activity |
| `audit_links.py` | Find broken wikilinks; optionally create stub notes |
| `bulk_status_update.py` | Mass-update status field with optional archival to `99-АРХИВ/` |
| `relationship_sync.py` | Check and fix bidirectional relationship links |
| `grammar_check.py` | Check Russian grammar in .docx legal documents |
| `daily_operations.py` | Daily records, morning briefings, overdue checks |
| `periodic_synthesis.py` | Weekly/monthly retrospective generation |
| `sync_moc.py` | MOC index auto-population and sync |
| `generate_canvas.py` | Canvas generation from vault data |
| `archive_manager.py` | Archive scanning, archival, reporting |
| `import_meeting.py` | Meeting import from text/transcript/.docx |
| `quick_capture.py` | Quick idea/event/task capture |

## Test coverage

598 tests, 79% coverage.

## Project structure

```
obsidian-company-kb/
  SKILL.md             # Agent skill definition (frontmatter + workflow)
  Makefile             # test, lint, coverage, audit targets
  pyproject.toml       # Project metadata and tool configuration
  requirements.txt     # Python dependencies
  LICENSE              # MIT License
  scripts/             # Python scripts and bash init script
  references/          # Skill reference documents (templates, tags, etc.)
  assets/
    docx-templates/    # .docx templates for contract/specification generation
    vault-init/        # .base and .canvas files copied during vault init
  tests/               # pytest test suite with fixtures
  docs/                # Documentation
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Modules](docs/MODULES.md)
- [API Reference](docs/API.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Changelog](docs/CHANGELOG.md)
- [User Guide (Russian)](docs/USER_GUIDE.md)
- GOST documentation: [GOST 19](docs/GOST/GOST_19.md), [GOST 34](docs/GOST/GOST_34.md), [Security Audit](docs/GOST/SECURITY_AUDIT.md)

## License

[MIT](LICENSE) -- Copyright (c) 2026 Cifratronika
