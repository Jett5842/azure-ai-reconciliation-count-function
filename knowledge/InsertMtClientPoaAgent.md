---
staging_table: MT Client POA Agent
etl_script: InsertMtClientPoaAgent.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Officers.EntCode)
exact_sources: [Officers]
lookup_sources: [RefMaster (lookup)]
---
# MT Client POA Agent

## Overview
Migrates the ACTIVE Power of Attorney agents of in-scope Client Master Files (appointed agent, appointment date). Resigned agents go to MT Client POA Agent History.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClientPoaAgent.sql` into staging table `[MT Client POA Agent]`.

## Scope filter
Only POA agents of in-scope Client Master Files: `O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per active POA officer of an in-scope client. A derived table numbers all POA officers per client (ROW_NUMBER by SeqNr) and is joined 1:1 back on EntCode + SeqNr, so it does not multiply rows.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | POA officers that are still active: no resignation date and status not 'R'. | `FROM Officers AS O WHERE O.OfficerType = 'POA' AND (O.DateResign IS NULL OR O.DateResign = '') AND O.[Status] <> 'R' AND O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the active Power of Attorney agent relations of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefMaster (lookup) | LEFT JOIN RefMaster ON RefCode = O.AddrCode (the agent) | [Agent Title], [Agent Name], [Agent Name 2] |

## Column mapping highlights
- [POA Entry No_] = ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY SeqNr) computed over ALL POA officers (active and resigned), so numbers line up with MT Power Of Attorney Register
- AddrCode -> [Agent No_]; DateAppoint -> [Date Agent Appointed]; [Agent Type] = 1 Client / 0 Entity / 2 Resource from fnGetInScopeClients()

## Notes for reconciliation
- Complement of MT Client POA Agent History (same source, opposite resigned condition).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClientPoaAgent'
GO

INSERT INTO [MT Client POA Agent]
(
    [NAV_Entry No]
    , [Client No_]
    , [POA Entry No_]
    , [Agent Type]
    , [Agent No_]
    , [POA Reference]
    , [Agent Title]
    , [Agent Name]
    , [Agent Name 2]
    , [Date Agent Appointed]
    , [Time Agent Appointed]
    , [User Appointing]
    , [Date Agent Resigned]
    , [Time Agent Resigned]
    , [User Resigning]
    , [Resignation Notes]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY O.EntCode) AS [NAV_Entry No]
    , O.EntCode AS [Client No_]
    , CTE.[POA Entry No_]

    , CASE
        WHEN GISC.IsClient = 1 THEN 1
        WHEN GISC.IsEntity = 1 THEN 0
        WHEN GISC.IsResource = 1 THEN 2
    END AS [Agent Type]

    , O.AddrCode AS [Agent No_]
    , NULL AS [POA Reference]
    , RM.Title AS [Agent Title]
    , RM.Name AS [Agent Name]
    , RM.Initials AS [Agent Name 2]
    , O.DateAppoint AS [Date Agent Appointed]
    , NULL AS [Time Agent Appointed]
    , NULL AS [User Appointing]
    , NULL AS [Date Agent Resigned]
    , NULL AS [Time Agent Resigned]
    , NULL AS [User Resigning]
    , NULL AS [Resignation Notes]
FROM
    (
        SELECT
            O.EntCode
            , O.SeqNr
            , ROW_NUMBER() OVER(PARTITION BY O.EntCode ORDER BY O.SeqNr) AS [POA Entry No_]
        FROM Officers AS O
        WHERE O.OfficerType = 'POA'
    ) AS CTE

INNER JOIN Officers AS O ON CTE.EntCode = O.EntCode AND CTE.SeqNr = O.SeqNr
LEFT JOIN RefMaster AS RM ON O.AddrCode = RM.RefCode
LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON O.AddrCode = GISC.RefCode
WHERE
    O.OfficerType = 'POA'
    AND(O.DateResign IS NULL OR O.DateResign = '')
    AND O.[Status] <> 'R'
    AND O.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
