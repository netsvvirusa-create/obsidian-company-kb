# Architecture

## System overview

```mermaid
graph TD
    SKILL[SKILL.md<br/>Skill definition + workflow] --> REF[references/<br/>Templates, tags, schemas]
    SKILL --> SCRIPTS[scripts/<br/>Python + bash]
    SKILL --> ASSETS[assets/<br/>docx-templates, vault-init]

    REF -->|note templates<br/>tag taxonomy<br/>variable registry| SCRIPTS
    ASSETS -->|.docx templates<br/>.base/.canvas files| SCRIPTS

    VAULT[Obsidian Vault<br/>.md notes with YAML frontmatter] <-->|read/write| SCRIPTS
    SCRIPTS -->|generate| DOCX[.docx output<br/>Contracts, specifications]

    AGENT[AI Agent<br/>Claude Code / Codex CLI] -->|reads| SKILL
    AGENT -->|executes| SCRIPTS
    AGENT -->|creates/edits| VAULT
```

## Data flow

```mermaid
flowchart LR
    subgraph Input
        MD[.md notes<br/>YAML frontmatter]
        CSV[CSV files]
        VCF[vCard .vcf files]
        TPL[.docx templates<br/>with VAR placeholders]
    end

    subgraph Processing
        PARSE[Parse frontmatter<br/>yaml.safe_load]
        RESOLVE[Resolve wikilinks<br/>find note by stem]
        BUILD[Build variable dict<br/>32+ contract vars]
        SUBST[Substitute in .docx<br/>run-aware replacement]
        GRAMMAR[Grammar check<br/>pymorphy3]
    end

    subgraph Output
        DOCX[.docx documents]
        NOTES[.md notes in vault]
        REPORTS[Markdown reports]
        JSON[JSON validation results]
    end

    MD --> PARSE --> RESOLVE --> BUILD --> SUBST --> DOCX
    SUBST --> GRAMMAR
    CSV --> NOTES
    VCF --> NOTES
    MD --> JSON
    MD --> REPORTS
```

## Layers

### Presentation layer (Obsidian)

The end-user interacts with data through Obsidian:

- **Notes** (.md) -- structured Markdown files with YAML frontmatter containing typed properties
- **Dashboards** (.base) -- YAML-defined views with filters, formulas, grouping, and summaries
- **Canvases** (.canvas) -- JSON Canvas visual maps showing relationships between notes
- **Wikilinks** -- `[[bidirectional links]]` connecting related entities across the vault

### Logic layer (Python scripts)

11 scripts handle all data processing:

- **Document generation** -- `generate_contract.py`, `generate_specification.py` read vault data and fill .docx templates
- **Grammar checking** -- `grammar_check.py` validates Russian genitive case in legal documents
- **Data import** -- `import_csv.py`, `import_vcard.py` create notes from external sources
- **Validation** -- `validate_vault.py` enforces schema, `audit_links.py` checks link integrity
- **Synchronization** -- `relationship_sync.py` maintains bidirectional links, `bulk_status_update.py` handles mass operations
- **Reporting** -- `generate_report.py` produces Markdown reports from vault data
- **Initialization** -- `init_vault.sh` sets up vault structure

### Data layer (YAML frontmatter)

All structured data lives in YAML frontmatter of .md files:

- **Type system** -- every note has a `type` field (one of 11 types)
- **Tag taxonomy** -- hierarchical tags with prefixes: `тип/`, `статус/`, `приоритет/`, `направление/`, `связь/`
- **Entity references** -- `[[wikilinks]]` in YAML properties create typed relationships
- **Contract variables** -- `_рп` suffix fields store genitive case forms for .docx generation

## Component descriptions

### SKILL.md

The skill definition file following the Agent Skills specification. Contains:
- YAML frontmatter with metadata (name, version, license, compatibility)
- Workflow instructions for the AI agent
- Note type table mapping types to folders and templates
- References to all supporting documents

### references/

10 reference documents providing schemas, templates, and specifications:
- `TEMPLATES.md`, `TEMPLATES_CONTACTS.md` -- note templates for all 11 types
- `BASES.md` -- 9 dashboard definitions in `.base` YAML format
- `CANVAS.md` -- 4 canvas templates in JSON Canvas format
- `TAGS.md` -- full tag taxonomy
- `RELATIONSHIPS.md` -- bidirectional relationship types and mirror pairs
- `VAULT_STRUCTURE.md` -- 15-folder structure specification
- `CONTRACT_VARS.md` -- 37 variable definitions for .docx generation

### scripts/

All executable logic. Python scripts use `argparse` for CLI, output JSON or Markdown, and operate on vault paths. The bash script `init_vault.sh` handles initial folder creation and file copying.

### assets/

Static resources:
- `docx-templates/` -- Word document templates with `{{VAR|ID|default}}` placeholders
- `vault-init/` -- `.base` and `.canvas` files copied during vault initialization
