---
staging_table: MT Power Of Attorney Register
etl_script: InsertMtPowerOfAttorneyRegister.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Officers.EntCode)
exact_sources: [Officers]
lookup_sources: []
---
# MT Power Of Attorney Register

## Overview
Creates the Power of Attorney register entries of in-scope Client Master Files. A register entry must exist on the client card before POA agents can be assigned, so ALL POA officers (active and resigned) produce one entry.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtPowerOfAttorneyRegister.sql` into staging table `[MT Power Of Attorney Register]`.

## Scope filter
Only POA officers of in-scope Client Master Files: `O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per POA officer of an in-scope client (active + resigned). No join, no DISTINCT.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | All POA officers regardless of resignation status. | `FROM Officers AS O WHERE O.OfficerType = 'POA' AND O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the Power of Attorney register entries for in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- [POA Entry No_] = ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY SeqNr)
- DateAppoint -> [Date Power Granted]; DateResign -> [Date Power Ends]; all other columns NULL

## Notes for reconciliation
- Count = active POA agents + resigned POA agents (MT Client POA Agent + MT Client POA Agent History).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtPowerOfAttorneyRegister'
GO

INSERT INTO [MT Power Of Attorney Register]
(
    [NAV_Entry No]
    , [Client No_]
    , [POA Entry No_]
    , [POA Reference]
    , [Status]
    , [Description]
    , [Purpose]
    , [Date Power Granted]
    , [Date Power Ends]
    , [Date Power Revoked]
    , [Law Applicable]
    , [Registered]
    , [Irrevocable]
    , [Asset Type]
    , [Asset No_]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY O.EntCode) AS [NAV_Entry No]
    , O.EntCode AS [Client No_]
    , ROW_NUMBER() OVER(PARTITION BY O.EntCode ORDER BY O.SeqNr) AS [POA Entry No_]
    , NULL AS [POA Reference]
    , NULL AS [Status]
    , NULL AS [Description]
    , NULL AS [Purpose]
    , O.DateAppoint AS [Date Power Granted]
    , O.DateResign AS [Date Power Ends]
    , NULL AS [Date Power Revoked]
    , NULL AS [Law Applicable]
    , NULL AS [Registered]
    , NULL AS [Irrevocable]
    , NULL AS [Asset Type]
    , NULL AS [Asset No_]
FROM Officers AS O
WHERE
    O.OfficerType = 'POA' AND O.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
