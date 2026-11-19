---
staging_table: MT Safe Custody Ledger Entry
etl_script: InsertMtSafeCustodyLedgerEntry.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (DocuIndexMoves.EntCode)
exact_sources: [DocuIndexMoves]
lookup_sources: [RefMaster (lookup)]
---
# MT Safe Custody Ledger Entry

## Overview
Migrates the movement history (ledger entries) of safe custody documents: deposit / withdrawal type, date, sub-location, who requested it and who it was transferred to, for in-scope Client Master Files.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtSafeCustodyLedgerEntry.sql` into staging table `[MT Safe Custody Ledger Entry]`.

## Scope filter
Only movements of in-scope Clients: `CE3.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per DocuIndexMoves row that matches a DocuIndex document on EntCode + LineNr (INNER JOIN). The Safe Custody Code is generated per client by ROW_NUMBER over DocuIndex.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| DocuIndexMoves | All movement rows of documents of in-scope clients; only movements whose document exists in DocuIndex (join on EntCode + LineNr). | `FROM DocuIndex ... INNER JOIN DocuIndexMoves AS DIM ON CE2.No_ = DIM.EntCode AND CE2.[Line Nr] = DIM.LineNr WHERE CE3.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the safe custody movement ledger entries of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefMaster (lookup) | LEFT JOIN RefMaster ON RefCode = DocuIndexMoves.DepotCode | [Transferred To] (Title + Name + Initials for individuals, Name for others) |

## Column mapping highlights
- [Movement Type] = 0 when DiActionType = 'LD', otherwise 1 (DS, MV, RM, RV); DiActionType -> [Movement Sub Type]
- DateAction -> [Movement Date]; AddressNo -> [Sub-Location]; UserRequest -> [Logged By 1]; ReasonAction -> [Reason]
- [Type] = 0 Client / 3 Entity / 4 Resource from fnGetInScopeClients(); [Safe Custody Code] = 'SC' + 4-digit ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY EntCode)

## Notes for reconciliation
- The Safe Custody Code uses the same ROW_NUMBER expression as MT Safe Custody Records. Ties on ORDER BY EntCode are not deterministic, so the codes of the two tables should be checked for consistency.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtSafeCustodyLedgerEntry'
GO

INSERT INTO [MT Safe Custody Ledger Entry]
(
    [Type]
    , [No_]
    , [Safe Custody Code]
    , [Entry No_]
    , [Movement Type]
    , [Movement Date]
    , [Movement Time]
    , [Movement Date Time]
    , [Movement Sub Type]
    , [Location]
    , [Sub-Location]
    , [Logged By 1]
    , [Logged By 2]
    , [Transferred To]
    , [Reason]
    , [Reconciled]
    , [Reconciled Date]
    , [Reconciled By]
    , [Most Recent Record]
    , [NAV_Entry No]
    , [Safe_Custody_NAV_Entry_No]
)
SELECT
    CASE
        WHEN GISC.IsClient = 1 THEN 0
        WHEN GISC.IsEntity = 1 THEN 3
        WHEN GISC.IsResource = 1 THEN 4
    END AS [Type]

    , EntCode AS [No_]
    , [Safe Custody Code]
    , NULL AS [Entry No_]

    , CASE
        WHEN DiActionType = 'DS' THEN 1
        WHEN DiActionType = 'LD' THEN 0
        WHEN DiActionType = 'MV' THEN 1
        WHEN DiActionType = 'RM' THEN 1
        WHEN DiActionType = 'RV' THEN 1
    END AS [Movement Type]

    , DateAction AS [Movement Date]
    , NULL AS [Movement Time]
    , NULL AS [Movement Date Time]
    , DiActionType AS [Movement Sub Type]
    , NULL AS [Location]
    , AddressNo AS [Sub-Location]
    , UserRequest AS [Logged By 1]
    , NULL AS [Logged By 2]

    , CASE
        WHEN RM.RefType = 'I' THEN RM.Title + ' ' + RM.Name + ' ' + RM.Initials
        ELSE RM.Name
    END AS [Transferred To]

    , ReasonAction AS [Reason]
    , 0 AS [Reconciled]
    , NULL AS [Reconciled Date]
    , NULL AS [Reconciled By]
    , 0 AS [Most Recent Record]
    , ROW_NUMBER() OVER(ORDER BY EntCode) AS [NAV_Entry No]
    , NULL AS [Safe_Custody_NAV_Entry_No]

FROM(
    SELECT
        CE2.[Safe Custody Code]
        , CE2.Location
        , DIM.*
    FROM(
        SELECT
            EntCode AS [No_]
            , CONVERT (NVARCHAR(20), 'SC' + RIGHT('0000' + CONVERT (VARCHAR, ROW_NUMBER() OVER(PARTITION BY EntCode ORDER BY EntCode)), 4)) AS [Safe Custody Code]
            , LineNr AS [Line Nr]
            , Location AS [Location]
        FROM DocuIndex
    ) AS CE2
    INNER JOIN DocuIndexMoves AS DIM ON CE2.No_ = DIM.EntCode AND CE2.[Line Nr] = DIM.LineNr
) AS CE3

LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON CE3.EntCode = GISC.RefCode
LEFT JOIN RefMaster AS RM ON CE3.DepotCode = RM.RefCode
WHERE
    CE3.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
