# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-04-05

### Added

- **Skill definition** (`SKILL.md`) with full workflow, note types, and agent behavior rules
- **11 note types**: counterparty, contract, project, employee, contact, negotiation, event, daily entry, goal, idea, company card
- **10 reference documents**: templates, tags, relationships, vault structure, contract variables, bases, canvases, dataview migration
- **9 `.base` dashboards**: active contracts, counterparties, contacts, employees, negotiations, strategic goals, operational events, calendar, people relationships
- **4 `.canvas` map templates**: org chart, contract participants, relationship map, strategic map
- **Vault initialization** (`init_vault.sh`): creates 15 folders, copies dashboards and canvases, generates MOC index notes
- **Contract generation** (`generate_contract.py`): .docx generation from templates with 32 variables, run-aware substitution, header/footer support
- **Specification generation** (`generate_specification.py`): .docx specification with nested variables, dynamic service tables, totals and VAT calculation
- **Grammar checking** (`grammar_check.py`): Russian genitive case and gender agreement validation for legal documents using pymorphy3
- **Vault validation** (`validate_vault.py`): frontmatter schema checks, tag taxonomy enforcement, duplicate INN/contract detection, expired contract warnings, bidirectional link verification
- **CSV import** (`import_csv.py`): auto-column detection for counterparties, contacts, and employees with duplicate checking
- **vCard import** (`import_vcard.py`): vCard 3.0/4.0 contact import with counterparty card linking
- **Report generation** (`generate_report.py`): expiring contracts, counterparty history, and employee activity reports in Markdown
- **Link audit** (`audit_links.py`): broken wikilink detection with context-aware stub creation
- **Bulk status update** (`bulk_status_update.py`): mass status changes with filter support and automatic archival
- **Relationship sync** (`relationship_sync.py`): bidirectional link consistency checking and automatic fixing
- **Test suite**: unit, integration, and functional tests with pytest; 80% coverage target
- **Linting and audit**: ruff (including bandit security rules), vulture, mypy
- **Documentation**: architecture, modules, API reference, security, testing, user guide, GOST compliance
