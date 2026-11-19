---
staging_table: MT Particulars History
etl_script: InsertMtParticularsHistory.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (EntNameChanges.EntCode)
exact_sources: [EntNameChanges]
lookup_sources: []
---
# MT Particulars History

## Overview
Migrates the confirmed name-change history (old formal name -> new formal name, date of change) of in-scope Client Master Files.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtParticularsHistory.sql` into staging table `[MT Particulars History]`.

## Scope filter
Only in-scope Clients: `EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per confirmed name change of an in-scope client. No join, no DISTINCT.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| EntNameChanges | Name changes that are confirmed: change status 'P' and a confirmation date. | `FROM EntNameChanges WHERE ChangeStatus = 'P' AND DateConfirmed IS NOT NULL AND EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the name change history of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- [Type] = 2 and [Change Type] = 0 (constants); [Change No_] = ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY SeqNr)
- OldName -> [Old Formal Name]; NewName -> [New Formal Name]; DateConfirmed -> [Date Of Change]

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtParticularsHistory'
GO

INSERT INTO [MT Particulars History]
(
    [Type]
    , [No_]
    , [Change No_]
    , [Change Type]
    , [Date Of Change]
    , [Address Type]
    , [Time of Change]
    , [Which Name]
    , [Old Surname]
    , [Old Forename]
    , [New Surname]
    , [New Forename]
    , [User ID]
    , [Old Value]
    , [New Value]
    , [System Date]
    , [Old Formal Name]
    , [New Formal Name]
    , [Old Address]
    , [New Address]
    , [Old Address 2]
    , [New Address 2]
    , [Old City]
    , [New City]
    , [Old Post Code]
    , [New Post Code]
    , [Old County]
    , [New County]
    , [Old Country Code]
    , [New Country Code]
    , [Old Address 3]
    , [New Address 3]
    , [Old Entity Address Type]
    , [Entity Address Type]
    , [Address Code]
    , [NAV_Entry No]
)
SELECT
    2 AS [Type]
    , EntCode AS [No_]
    , ROW_NUMBER() OVER(PARTITION BY EntCode ORDER BY SeqNr) AS [Change No_]
    , 0 AS [Change Type]
    , DateConfirmed AS [Date Of Change]
    , 0 AS [Address Type]
    , NULL AS [Time of Change]
    , NULL AS [Which Name]
    , NULL AS [Old Surname]
    , NULL AS [Old Forename]
    , NULL AS [New Surname]
    , NULL AS [New Forename]
    , NULL AS [User ID]
    , NULL AS [Old Value]
    , NULL AS [New Value]
    , NULL AS [System Date]
    , OldName AS [Old Formal Name]
    , [NewName] AS [New Formal Name]
    , NULL AS [Old Address]
    , NULL AS [New Address]
    , NULL AS [Old Address 2]
    , NULL AS [New Address 2]
    , NULL AS [Old City]
    , NULL AS [New City]
    , NULL AS [Old Post Code]
    , NULL AS [New Post Code]
    , NULL AS [Old County]
    , NULL AS [New County]
    , NULL AS [Old Country Code]
    , NULL AS [New Country Code]
    , NULL AS [Old Address 3]
    , NULL AS [New Address 3]
    , NULL AS [Old Entity Address Type]
    , NULL AS [Entity Address Type]
    , NULL AS [Address Code]
    , ROW_NUMBER() OVER(ORDER BY EntCode) AS [NAV_Entry No]
FROM EntNameChanges
WHERE
    ChangeStatus = 'P' AND DateConfirmed IS NOT NULL
    AND EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
