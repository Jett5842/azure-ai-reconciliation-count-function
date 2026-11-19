---
staging_table: MT Risk Assessment
etl_script: InsertMtRiskAssessment.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: Any in-scope RefCode (fnGetInScopeClients), Client = Type 0
exact_sources: [RefMaster (Client, Type=0), RefMaster (non-Client, one row per Owner/Entity tag)]
lookup_sources: [RefStatus (lookup), Entity (lookup)]
---
# MT Risk Assessment

## Overview
Migrates the KYC risk assessment (risk rating, weighting, review dates, completed date/by, client status) of in-scope master files. Risk group codes 01 / 05 / 10 map to LOW / MEDIUM / HIGH with weighting 0 / 49 / 99. The latest status history row (RefStatus, SType 'C') supplies who completed it and when.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtRiskAssessment.sql` into staging table `[MT Risk Assessment]`.

## Scope filter
`RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients())` - every in-scope master file, whether Client, Entity or Owner. Clients get Type 0; all others get the Owner/Entity tag type.

## Row count behaviour
SELECT DISTINCT. One row per Client RefCode (Type 0). For non-clients, one row per EntityOwnerType tag: Type 2 (Owner-type via Officers ADM / Share_Interests BEO / EntityOwners) and/or Type 3 (Entity, IsEntity = 1). A RefCode with both tags gives 2 rows, with neither gives 1 row with a NULL type.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefMaster (Client, Type=0) | Clients with a risk group set (not NULL, not 'NC') and KYC status 07 or 09. One row per client. | `FROM RefMaster AS RM ... WHERE KYC_RiskGroup IS NOT NULL AND KYC_RiskGroup <> 'NC' AND KYC_Status IN (07, 09) AND RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients()) AND Type = 0 (ISC.IsClient = 1)` | Bring over the risk group data of in-scope Client Master Files. |
| RefMaster (non-Client, one row per Owner/Entity tag) | Same KYC filter for in-scope master files that are not clients; one row per Owner / Entity tag. | `Same WHERE as above; Type = EntityOwnerType.[Type] ('2' Officers ADM / Share_Interests BEO / EntityOwners link; '3' IsEntity = 1) when IsClient is not 1` | Bring over the risk group data of in-scope Owner and Entity Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefStatus (lookup) | LEFT JOIN latest RefStatus (ROW_NUMBER by SeqNr DESC, SType = 'C') ON RefCode AND newStat = RefMaster.KYC_Status | [Date Completed], [Completed By] |
| Entity (lookup) | LEFT JOIN Entity ON EntCode = RefCode | [Client Status], [ClientAnalysisA], [ClientAnalysisB] |

## Column mapping highlights
- KYC_RiskGroup 01 -> LOW (weighting 0); 05 -> MEDIUM (49); 10 -> HIGH (99); other -> NULL
- [Date Completed] / [Completed By] only when KYC_Status IN ('07','09','02')
- [Template Code] = constant 'MIG'; [Status] = 0; [Mandatory Risk Assessment] = 0

## Notes for reconciliation
- Row count can exceed the number of RefCodes because of the two Owner/Entity tags.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtRiskAssessment'
GO

WITH LatestRefStatus AS(
    SELECT *
    FROM(
        SELECT
            *
            , ROW_NUMBER() OVER(PARTITION BY RefCode ORDER BY SeqNr DESC) AS rn
        FROM RefStatus
        WHERE SType = 'C'
    ) AS RSFiltered
    WHERE rn = 1
)

, EntityOwnerType AS(
    SELECT DISTINCT
        '2' AS Type
        , RM.RefCode
    FROM RefMaster AS RM
    LEFT JOIN Officers AS O ON RM.RefCode = O.AddrCode
    LEFT JOIN Share_Interests AS SI ON RM.RefCode = SI.AddrCode AND SI.IntType = 'BEO' AND SI.EntCode IN(SELECT RefCode FROM dbo.fnGetInScopeClients())
    LEFT JOIN EntityOwners AS EO ON RM.RefCode = EO.RefCode AND EO.EntCode IN(SELECT RefCode FROM dbo.fnGetInScopeClients())
    WHERE O.OfficerType = 'ADM' OR SI.IntType = 'BEO' OR RM.RefCode = EO.RefCode

    UNION

    SELECT DISTINCT
        '3' AS Type
        , RM.RefCode
    FROM RefMaster AS RM
    INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode AND ISC.IsEntity = 1
)

INSERT INTO [MT Risk Assessment]
(
    [Type]
    , [No_]
    , [Assessment Date]
    , [Risk Template Code]
    , [Mandatory Risk Assessment]
    , [Status]
    , [Version No_]
    , [Risk Rating]
    , [Assessment Due]
    , [Risk Weighting]
    , [Date Completed]
    , [Completed By]
    , [Client Status]
    , [ClientAnalysisA]
    , [ClientAnalysisB]
    , [Name]
    , [Client No Associated]
    , [NAV_Entry No]
)
SELECT
    RiskAssessment.*
    , ROW_NUMBER() OVER(ORDER BY RiskAssessment.[Type], RiskAssessment.[No]) AS [NAV_Entry No]
FROM(
    SELECT DISTINCT
        CASE
            WHEN ISC.IsClient = 1 THEN 0
            ELSE EOT.[Type]
        END AS [Type]

        , RM.RefCode AS [No]
        , CONVERT(DATETIME, RM.KYC_Reviewed, 103) AS [Assessment Date]
        , 'MIG' AS [Risk Template Code]
        , 0 AS [Mandatory Risk Assessment]
        , 0 AS [Status]
        , NULL AS [Version No_]

        , CASE
            WHEN RM.KYC_RiskGroup = '01' THEN 'LOW'
            WHEN RM.KYC_RiskGroup = '05' THEN 'MEDIUM'
            WHEN RM.KYC_RiskGroup = '10' THEN 'HIGH'
            ELSE NULL
        END AS [Risk Rating]

        , CONVERT(DATETIME, RM.KYC_NextReview, 103) AS [Next Assessment Due] --[Assessment Due]

        , CASE
            WHEN RM.KYC_RiskGroup = '01' THEN '0'
            WHEN RM.KYC_RiskGroup = '05' THEN '49'
            WHEN RM.KYC_RiskGroup = '10' THEN '99'
            ELSE NULL
        END AS [Risk Weighting]

        , CASE
            WHEN RM.KYC_Status IN('07', '09', '02') THEN CONVERT(DATETIME, RS.DateEffective, 103)
            ELSE NULL
        END AS [Date Completed]

        , CASE WHEN RM.KYC_Status IN('07', '09', '02') THEN RS.Ucode END AS [Completed By]

        , CASE
            WHEN ISC.IsClient = 1
                THEN
                    CASE
                        WHEN E.[Status] = '0' THEN 2
                        WHEN E.[Status] = 'G' THEN 3
                        WHEN E.[Status] = 'C' THEN 4
                    END
            WHEN ISC.IsClient <> 1 THEN
                CASE
                    WHEN RM.[Status] = 0 THEN 2
                    WHEN RM.[Status] IN(8, 9) THEN 4
                END
        END AS [Client Status]

        , E.AdminCode AS [ClientAnalysisA]
        , E.Admin2Code AS [ClientAnalysisB]
        , RM.[Name]
        , RM.RefCode AS [Client No Associated]
    FROM RefMaster AS RM
    LEFT JOIN Officers AS O ON RM.RefCode = O.AddrCode AND O.EntCode IN(SELECT RefCode FROM dbo.fnGetInScopeClients())
    LEFT JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode
    LEFT JOIN LatestRefStatus AS RS ON RM.RefCode = RS.RefCode AND RS.SType = 'C' AND RM.KYC_Status = RS.newStat
    LEFT JOIN Entity AS E ON RM.RefCode = E.EntCode
    LEFT JOIN RefLabels AS RL ON RM.RefCode = RL.Code
    LEFT JOIN EntityOwnerType AS EOT ON RM.RefCode = EOT.RefCode
    WHERE
        KYC_RiskGroup IS NOT NULL AND KYC_RiskGroup <> 'NC' AND KYC_Status IN(07, 09)
        AND RM.RefCode IN(SELECT RefCode FROM dbo.fnGetInScopeClients())
) AS RiskAssessment

GO
```
