---
staging_table: MT Client POA Agent History
etl_script: InsertMtClientPoaAgentHistory.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Officers.EntCode)
exact_sources: [Officers]
lookup_sources: [RefMaster (lookup)]
---
# MT Client POA Agent History

## Overview
Migrates the RESIGNED Power of Attorney agents (history) of in-scope Client Master Files, with power granted / ended dates taken from appointment and resignation dates.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClientPoaAgentHistory.sql` into staging table `[MT Client POA Agent History]`.

## Scope filter
Only POA agents of in-scope Client Master Files: `O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per resigned POA officer of an in-scope client. Same numbering derived table as MT Client POA Agent (1:1 join, no row multiplication).

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | POA officers that have resigned: resignation date populated and status = 'R'. | `FROM Officers AS O WHERE O.OfficerType = 'POA' AND (O.DateResign IS NOT NULL OR O.DateResign <> '') AND O.[Status] = 'R' AND O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the resigned Power of Attorney agent relations of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefMaster (lookup) | LEFT JOIN RefMaster ON RefCode = O.AddrCode (agent) and ON RefCode = O.EntCode (client) | [Agent Title], [Agent Name], [Agent Name 2], [Client Name] |

## Column mapping highlights
- DateAppoint -> [Date Power Granted] and [Date Agent Appointed]; DateResign -> [Date Power Ends] and [Date Agent Resigned]
- [Entry No_] = [POA Entry No_] = ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY SeqNr) over all POA officers

## Notes for reconciliation
- Complement of MT Client POA Agent (same source, opposite resigned condition).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClientPoaAgentHistory'
GO

INSERT INTO [MT Client POA Agent History]
(
    [Client No_]
    , [POA Entry No_]
    , [Agent Type]
    , [Agent No_]
    , [Entry No_]
    , [POA Reference]
    , [POA Status]
    , [Agent Title]
    , [Agent Name]
    , [Agent Name 2]
    , [POA Description]
    , [Purpose]
    , [Date Power Granted]
    , [Date Power Ends]
    , [Date Power Revoked]
    , [Law Applicable]
    , [Registered]
    , [Irrevocable]
    , [Asset Type]
    , [Asset No_]
    , [Date Agent Appointed]
    , [Time Agent Appointed]
    , [User Appointing]
    , [Date Agent Resigned]
    , [Time Agent Resigned]
    , [User Resigning]
    , [Resignation Notes]
    , [Client Name]
    , [NAV_Entry No]
)
SELECT
    O.EntCode AS [Client No_]
    , CTE.[POA Entry No_]

    , CASE
        WHEN GISC.IsClient = 1 THEN 1
        WHEN GISC.IsEntity = 1 THEN 0
        WHEN GISC.IsResource = 1 THEN 2
    END AS [Agent Type]

    , O.AddrCode AS [Agent No_]
    , CTE.[POA Entry No_] AS [Entry No_]
    , NULL AS [POA Reference]
    , NULL AS [POA Status]
    , RM.Title AS [Agent Title]
    , RM.Name AS [Agent Name]
    , RM.Initials AS [Agent Name 2]
    , NULL AS [POA Description]
    , NULL AS [Purpose]
    , O.DateAppoint AS [Date Power Granted]
    , O.DateResign AS [Date Power Ends]
    , NULL AS [Date Power Revoked]
    , NULL AS [Law Applicable]
    , NULL AS [Registered]
    , NULL AS [Irrevocable]
    , NULL AS [Asset Type]
    , NULL AS [Asset No_]
    , O.DateAppoint AS [Date Agent Appointed]
    , NULL AS [Time Agent Appointed]
    , NULL AS [User Appointing]
    , O.DateResign AS [Date Agent Resigned]
    , NULL AS [Time Agent Resigned]
    , NULL AS [User Resigning]
    , NULL AS [Resignation Notes]
    , RM2.Name AS [Client Name]
    , ROW_NUMBER() OVER(ORDER BY O.EntCode) AS [NAV_Entry No]
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
LEFT JOIN RefMaster AS RM2 ON O.EntCode = RM2.RefCode
LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON O.AddrCode = GISC.RefCode
WHERE
    O.OfficerType = 'POA'
    AND(O.DateResign IS NOT NULL OR O.DateResign <> '')
    AND O.[Status] = 'R'
    AND O.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
