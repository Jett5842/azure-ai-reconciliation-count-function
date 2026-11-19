---
staging_table: MT Comments
etl_script: InsertMtComments.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 OR IsEntity = 1 (RefAlerts.RefCode)
exact_sources: [RefAlerts]
lookup_sources: [qLvALTC (lookup)]
---
# MT Comments

## Overview
Migrates the ACTIVE alert messages (warnings with a note) of in-scope Client and Entity Master Files as comments. The alert type name is placed in front of the note. Long text is split into 250-character pieces, one comment line each.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtComments.sql` into staging table `[MT Comments]`.

## Scope filter
Only alerts of in-scope Clients or Entities: `RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1 OR IsEntity = 1)`.

## Row count behaviour
One staging row per 250-character chunk. A recursive CTE (RecursiveSplit) cuts each alert text (alert type name + ' - ' + note) into chunks, so the staging count is >= the number of qualifying alerts.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefAlerts | Active alerts that have a note, for in-scope Client or Entity master files. Each alert produces one row per 250 characters of text. | `FROM RefAlerts AS RA WHERE RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1 OR IsEntity = 1) AND AlertActive = 1 AND (AlertNote IS NOT NULL OR AlertNote <> '')` | Bring over active alert messages of in-scope Client and Entity master files as comments; long values are split into multiple records. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| qLvALTC (lookup) | LEFT JOIN qLvALTC ON ElCode = RefAlerts.AlertCode | [Description] (alert type name placed before ' - ' and the note) |

## Column mapping highlights
- [Type] = 0 for a Client, 60 for an Entity; [No_] = RefCode for Entity only; [Client No_] = RefCode for Client only
- [Description] = LEFT 250 characters chunk of (alert type name + ' - ' + AlertNote); [Line No_] = ROW_NUMBER() * 1000 per RefCode
- [Related_NAV_Entry_No] and [Description BLOB] are NULL on purpose (not linked to POA / Safe Custody)

## Notes for reconciliation
- Count difference vs source alerts is expected: staging rows are chunks, not alerts.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtComments'
GO

WITH AlertList AS(
    SELECT
        CASE
            WHEN GISC.IsClient = 1 THEN 0
            WHEN GISC.IsEntity = 1 THEN 60
        END AS [Type]

        , CASE
            WHEN GISC.IsClient = 1 THEN NULL
            WHEN GISC.IsEntity = 1 THEN GISC.RefCode
        END AS [No_]

        , DateFrom AS [Date]
        , qlv.Name + ' - ' + AlertNote AS [Description]

        , CASE
            WHEN GISC.IsClient = 1 THEN GISC.RefCode
            WHEN GISC.IsEntity = 1 THEN NULL
        END AS [Client No_]

        , DateFrom AS [Created On]
        , RA.RefCode
        , RA.SeqNr
    FROM RefAlerts AS RA
    LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode
    LEFT JOIN qLvALTC AS qLV ON RA.AlertCode = qLV.ElCode
    WHERE RA.RefCode IN(
        SELECT RefCode
        FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1 OR IsEntity = 1
    )
    AND AlertActive = 1 AND(AlertNote IS NOT NULL OR AlertNote <> '')
)

, RecursiveSplit AS(
    SELECT
        RefCode
        , SeqNr
        , LEFT([Description], 250) AS Chunk
        , IIF(LEN([Description]) > 250, SUBSTRING([Description], 251, LEN([Description]) - 250), NULL) AS RemainingText
        , 1 AS ChunkNumber
    FROM AlertList

    UNION ALL

    SELECT
        RefCode
        , SeqNr
        , LEFT(RemainingText, 250) AS Chunk
        , IIF(LEN(RemainingText) > 250, SUBSTRING(RemainingText, 251, LEN(RemainingText) - 250), NULL) AS RemainingText
        , ChunkNumber + 1
    FROM RecursiveSplit
    WHERE LEN(RemainingText) > 0
)

INSERT INTO [MT Comments]
(
    [Type]
    , [No_]
    , [Line No_]
    , [Date]
    , [Description]
    , [Client No_]
    , [Entry No_]
    , [Extra Key]
    , [Date Key]
    , [User ID]
    , [Created On]
    , [NAV_Entry No]
    , [Related_NAV_Entry_No]
    , [Description BLOB]
)
SELECT
    A.[Type]
    , A.[No_]
    , ROW_NUMBER() OVER(PARTITION BY RP.RefCode ORDER BY RP.RefCode, RP.SeqNr, RP.ChunkNumber) * 1000 AS [Line No_]
    , A.[Date]
    , RP.Chunk AS [Description]
    , A.[Client No_]
    , 0 AS [Entry No_]
    , NULL AS [Extra Key]
    , NULL AS [Date Key]
    , NULL AS [User ID]
    , A.[Created On]
    , ROW_NUMBER() OVER(ORDER BY RP.RefCode) AS [NAV_Entry No]
    , NULL AS [Related_NAV_Entry_No] -- Checked with CK: Related_NAV_Entry No is used by toolkit to link the comment to particular POA/Safe Custody by creating the description BLOB to do so. Hence set to NULL
    , NULL AS [Description BLOB] -- Checked with CK: since not linking to POA/Safe Custody, hence set to NULL
FROM RecursiveSplit AS RP
LEFT JOIN AlertList AS A ON RP.RefCode = A.RefCode AND RP.SeqNr = A.SeqNr
ORDER BY RP.RefCode, RP.SeqNr, RP.ChunkNumber
OPTION(MAXRECURSION 0)

GO
```
