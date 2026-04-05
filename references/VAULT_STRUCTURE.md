# Vault Structure

15 folders for the corporate knowledge base.

```
📁 00-INBOX/                  ← incoming unprocessed notes
📁 01-КОНТРАГЕНТЫ/            ← counterparty cards
📁 02-ДОГОВОРЫ/               ← contracts and agreements
📁 03-ПРОЕКТЫ/                ← projects and work
📁 04-СОТРУДНИКИ/             ← OUR employee cards
📁 05-КОНТАКТЫ/               ← contact persons of counterparties
📁 06-ПЕРЕГОВОРЫ/             ← meeting and negotiation protocols
📁 07-ОПЕРАЦИИ/               ← operational events
📁 08-КАЛЕНДАРЬ/              ← daily records
📁 09-СТРАТЕГИЯ/              ← goals, plans, ideas
   ├── Цели/
   ├── Идеи/
   └── Ретроспективы/
📁 10-ФИНАНСЫ/                ← budgets, payments, invoices
📁 11-БАЗЫ/                   ← .base dashboard files
📁 12-КАНВАСЫ/                ← .canvas visual maps
📁 13-ШАБЛОНЫ/                ← note templates
📁 14-ВЛОЖЕНИЯ/               ← photos, scans, documents
   ├── Фото сотрудников/
   ├── Фото контактов/
   └── Документы/
📁 99-АРХИВ/                  ← completed/inactive records
```

## Folder descriptions

| Folder | Content | Note type |
|--------|---------|-----------|
| 00-INBOX | Unprocessed incoming notes | any |
| 01-КОНТРАГЕНТЫ | Counterparty cards with requisites | контрагент |
| 02-ДОГОВОРЫ | Contracts, agreements, amendments | договор |
| 03-ПРОЕКТЫ | Projects, work items | проект |
| 04-СОТРУДНИКИ | Our employees (with dossiers) | сотрудник |
| 05-КОНТАКТЫ | Contact persons of counterparties | контакт |
| 06-ПЕРЕГОВОРЫ | Meeting protocols, negotiations | переговоры |
| 07-ОПЕРАЦИИ | Operational events, decisions | событие |
| 08-КАЛЕНДАРЬ | Daily journal entries | дневная_запись |
| 09-СТРАТЕГИЯ | Goals, ideas, retrospectives | цель, идея |
| 10-ФИНАНСЫ | Financial records | — |
| 11-БАЗЫ | .base dashboard files | — |
| 12-КАНВАСЫ | .canvas visual maps | — |
| 13-ШАБЛОНЫ | Note templates | — |
| 14-ВЛОЖЕНИЯ | Attachments: photos, documents | — |
| 99-АРХИВ | Completed and inactive records | any |

## MOC (Map of Content) notes

Each main folder should have an index note `_MOC.md` with links to all notes
in that folder. The `init_vault.sh` script creates starter MOC notes.

## Archive rules

When a contract, project, or goal is completed or cancelled:
1. Update `статус` property
2. Move note to `99-АРХИВ/` subfolder matching the original folder name
3. Update related notes' wikilinks if needed
