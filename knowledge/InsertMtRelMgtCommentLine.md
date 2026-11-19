---
staging_table: MT Rel_ Mgt_ Comment Line
etl_script: InsertMtRelMgtCommentLine.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsOwner = 1 (RefAlerts.RefCode)
exact_sources: [RefAlerts (Owner, 250-char chunks)]
lookup_sources: [qLvALTC (lookup)]
---
# MT Rel_ Mgt_ Comment Line

## Overview
Migrates the ACTIVE alert messages of in-scope Owner Master Files as relationship-management comment lines (Table Name '18'). The alert type name is placed in front of the note; long text is split into 250-character lines.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtRelMgtCommentLine.sql` into staging table `[MT Rel_ Mgt_ Comment Line]`.

## Scope filter
Only Owner master files: `RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsOwner = 1)`.

## Row count behaviour
One staging row per 250-character chunk (recursive CTE RecursiveSplit), so staging count >= number of qualifying Owner alerts.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefAlerts (Owner, 250-char chunks) | Active alerts with a note on Owner master files, split into 250-character rows. | `FROM RefAlerts AS RA WHERE RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsOwner = 1) AND AlertActive = 1 AND (AlertNote IS NOT NULL OR AlertNote <> '')` | Bring over active alert messages of in-scope Owner master files; long notes are split into 250-character rows. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| qLvALTC (lookup) | LEFT JOIN qLvALTC ON ElCode = RefAlerts.AlertCode | [Comment] (alert type name placed before ' - ' and the note) |

## Column mapping highlights
- [Table Name] = constant '18'; [Line No_] = ROW_NUMBER() * 1000 per RefCode; [Comment] = LEFT 250 characters chunk

## Notes for reconciliation
- Owner counterpart of MT Comments (which covers Client and Entity alerts).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtRelMgtCommentLine'
GO

WITH AlertList AS(
    SELECT
        RA.RefCode AS [No_]
        , DateFrom AS [Date]
        , qlv.Name + ' - ' + AlertNote AS [Description]
        , RA.RefCode
        , RA.SeqNr
    FROM RefAlerts AS RA
    LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON RA.RefCode = GISC.RefCode
    LEFT JOIN qLvALTC AS qLV ON RA.AlertCode = qLV.ElCode
    WHERE
        RA.RefCode IN(
            SELECT RefCode FROM dbo.fnGetInScopeClients()
            WHERE IsOwner = 1
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
        , ChunkNumber + 1 AS ChunkNumber
    FROM RecursiveSplit
    WHERE LEN(RemainingText) > 0
)

INSERT INTO [MT Rel_ Mgt_ Comment Line]
(
    [Table Name]
    , [No_]
    , [Line No_]
    , [Date]
    , [Code]
    , [Comment]
    , [Last Date Modified]
    , [Table Entry No_]
    , [Table Code]
    , [NAV_Entry No]
    , [Comment BLOB]
)
SELECT
    '18' AS [Table Name]
    , A.RefCode AS [No_]
    , ROW_NUMBER() OVER(PARTITION BY RP.RefCode ORDER BY RP.RefCode, RP.SeqNr, RP.ChunkNumber) * 1000 AS [Line No_]
    , A.[Date]
    , NULL AS [Code]
    , RP.Chunk AS [Comment]
    , NULL AS [Last Date Modified]
    , NULL AS [Table Entry No_]
    , NULL AS [Table Code]
    , ROW_NUMBER() OVER(ORDER BY RP.RefCode) AS [NAV_Entry No]
    , NULL AS [Comment BLOB]
FROM RecursiveSplit AS RP
LEFT JOIN AlertList AS A ON RP.RefCode = A.RefCode AND RP.SeqNr = A.SeqNr
ORDER BY RP.RefCode, RP.SeqNr, RP.ChunkNumber
OPTION(MAXRECURSION 0)

GO
```
