---
staging_table: MT Warning Register
etl_script: InsertMtWarningRegister.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: No client/entity scope filter (any active alert); Owner branch uses IsOwner = 1
exact_sources: [RefAlerts (any active alert), RefAlerts (Owner)]
lookup_sources: []
---
# MT Warning Register

## Overview
Migrates the active alert codes (warnings) with their effective date for Client, Entity and Owner master files into the Warning Register. The alert note text itself is migrated by MT Comments / MT Rel_ Mgt_ Comment Line.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtWarningRegister.sql` into staging table `[MT Warning Register]`.

## Scope filter
No in-scope restriction on the first branch (all active alerts; the Client / Entity type is only derived from fnGetInScopeClients()). The second branch keeps alerts of Owners: `GISC.IsOwner = 1`.

## Row count behaviour
Two branches combined with UNION (identical rows removed), so staging count = distinct rows of both branches.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefAlerts (any active alert) | All active alerts. Rec_ Type 2 when the master file is a Client, 5 when it is an Entity, NULL otherwise. | `FROM RefAlerts AS RA LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode WHERE AlertActive = 1` | Bring over active alerts of Client and Entity master files as warnings. |
| RefAlerts (Owner) | Active alerts of master files that are Owners; Rec_ Type is fixed to 3. | `FROM RefAlerts AS RA LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode WHERE AlertActive = 1 AND GISC.IsOwner = 1` | Bring over active alerts of Owner master files as warnings. |

### Adjustment row
Label `Duplicates removed across UNION branches`: negative adjustment = distinct rows of the untagged UNION minus the sum of the two branch counts (identical rows from both branches collapse into one). It is not a Vpoint table.

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- [Rec_ Type]: 2 Client, 5 Entity (branch 1); 3 Owner (branch 2). AlertCode -> [Warning Code]; DateFrom -> [Effective Date]

## Notes for reconciliation
- A master file that is both Client/Entity and Owner can appear once per branch with different Rec_ Type, so they are not duplicates.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtWarningRegister'
GO

INSERT INTO [MT Warning Register]
(
    [Rec_ Type]
    , [Rec_ No_]
    , [Warning Code]
    , [Rec_ Name]
    , [Effective Date]
    , [NAV_Entry No]
)
SELECT
    *
    , ROW_NUMBER() OVER(ORDER BY [Rec_ No_]) AS [NAV_Entry No]
FROM(
    SELECT
        CASE
            WHEN GISC.IsClient = 1 THEN 2
            WHEN GISC.IsEntity = 1 THEN 5
        END AS [Rec_ Type]

        , RA.RefCode AS [Rec_ No_]
        , AlertCode AS [Warning Code]
        , NULL AS [Rec_ Name]
        , DateFrom AS [Effective Date]
    FROM RefAlerts AS RA LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode
    WHERE AlertActive = 1

    UNION

    SELECT
        3 AS [Rec_ Type]
        , RA.RefCode AS [Rec_ No_]
        , AlertCode AS [Warning Code]
        , NULL AS [Rec_ Name]
        , DateFrom AS [Effective Date]
    FROM RefAlerts AS RA LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode
    WHERE AlertActive = 1 AND GISC.IsOwner = 1
) AS T

GO
```
