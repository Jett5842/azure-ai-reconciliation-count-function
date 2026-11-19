---
staging_table: MT Share Class RnC
etl_script: InsertMtShareClassRnC.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Share_Capital.EntCode)
exact_sources: [Share_Capital]
lookup_sources: []
---
# MT Share Class RnC

## Overview
Migrates the share class Rights and Conditions: the free-text condition note of each share class, as a VOTING right, for in-scope Client Master Files.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtShareClassRnC.sql` into staging table `[MT Share Class RnC]`.

## Scope filter
Only share classes of in-scope Client Master Files: `SC.EntCode IN (SELECT RefCode FROM fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per Share_Capital row that has a non-empty Note, excluding the special share type codes '/G' and '/L'.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Share_Capital | Share classes that have a note, excluding General Partner ('/G') and Limited Partner ('/L') share types. | `FROM Share_Capital AS SC WHERE ISNULL(SC.Note, '') <> '' AND SC.ShareTypeCode NOT IN ('/G', '/L') AND SC.EntCode IN (SELECT RefCode FROM fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the share class condition (Rights and Conditions) of active in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- EntCode -> [Client Code]; ShareClassName -> [Class of Share]; Currency -> [Currency Code]; Note -> [Detail of Condition]; [Type of Right] = constant 'VOTING'

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtShareClassRnC'
GO

INSERT INTO [MT Share Class RnC]
(
    [NAV_Entry No]
    , [Client Code]
    , [Class of Share]
    , [Currency Code]
    , [Type of Right]
    , [Detail of Condition]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY SC.EntCode ASC) AS RowNr
    , SC.EntCode AS [Client Code]
    , SC.ShareClassName AS [Class of Share]
    , SC.Currency AS [Currency Code]
    , 'VOTING' AS [Type of Right]
    , SC.Note AS [Detail of Condition]
FROM Share_Capital AS SC
WHERE
    ISNULL(SC.Note, '') <> ''
    AND SC.ShareTypeCode NOT IN('/G', '/L')
    AND SC.EntCode IN(
        SELECT RefCode FROM fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
