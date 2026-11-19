---
staging_table: MT Client Entity History
etl_script: InsertMtClientEntityHistory.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Client No_)
exact_sources: [Officers, Share_Interests (UBO), Share_Interests (BEO), Beneficiaries, CR_Shareholders (SHR/etc), CR_Shareholders (LIP), CR_Shareholders (GPA)]
lookup_sources: [Share_Interests (lookup), Officers (lookup)]
---
# MT Client Entity History

## Overview
Migrates the ENDED relationships (resigned officers, ended Beneficial Owner / UBO interests, revoked beneficiaries, shareholders who no longer hold shares) between in-scope Clients and other master files. Counterpart of MT Client Entity, which holds the active ones.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClientEntityHistory.sql` into staging table `[MT Client Entity History]`.

## Scope filter
Final filter on the combined result: `CE2.[Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One untagged UNION of 7 branches (identical rows collapse; DISTINCT inside the CR_Shareholders branches), filtered to in-scope clients. [Percentage Ownership] is multiplied by 100.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | Resigned officers: resignation date populated and status = 'R'; Substantial Owner (SOW) and Controlling Person (CNP) excluded. | `FROM Officers WHERE (DateResign IS NOT NULL OR DateResign <> '') AND [Status] = 'R' AND OfficerType NOT IN ('SOW','CNP')` | Bring over the resigned officer relations of in-scope clients. |
| Share_Interests (UBO) | Ended UBO interests (end date populated). | `FROM Share_Interests WHERE (DateEnd IS NOT NULL OR DateEnd <> '') AND IntType = 'UBO'` | Bring over the ended Ultimate Beneficial Owner relations. |
| Share_Interests (BEO) | Ended Beneficial Owner interests (end date populated); same NOM / SHR / TST / BEN type logic as MT Client Entity. | `FROM Share_Interests WHERE (DateEnd IS NOT NULL OR DateEnd <> '') AND IntType = 'BEO'` | Bring over the ended Beneficial Owner relations. |
| Beneficiaries | Revoked beneficiaries (revoked date populated). | `FROM Beneficiaries WHERE (DateRevoked IS NOT NULL OR DateRevoked <> '')` | Bring over the revoked beneficiary relations. |
| CR_Shareholders (SHR/etc) | Past shareholders: shares held = 0, not '/L' or '/G' share types. DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld = 0 AND ShareTypeCode NOT IN ('/L','/G')` | Bring over past shareholders (other than LP / GP). |
| CR_Shareholders (LIP) | Past Limited Partnership holders (shares held = 0, '/L'). DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld = 0 AND ShareTypeCode IN ('/L')` | Bring over past Limited Partners. |
| CR_Shareholders (GPA) | Past General Partner holders (shares held = 0, '/G'). DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld = 0 AND ShareTypeCode IN ('/G')` | Bring over past General Partners. |

### Adjustment row
Label `Duplicates removed across UNION branches`: negative adjustment = distinct rows of the ETL's untagged UNION minus the sum of the branch counts above (identical rows produced by two branches collapse into one). It is not a Vpoint table.

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Share_Interests (lookup) | Post-insert UPDATE: BenOwn = Share_Interests WHERE IntType IN ('BEO','UBO'), joined on EntCode = Client No_ and AddrCode = Entity No_ | [Ben Own_CP] |
| Officers (lookup) | Post-insert UPDATE: CNP = Officers WHERE OfficerType = 'CNP', joined on EntCode and AddrCode | [Ben Own_CP] |

## Column mapping highlights
- DateEnd / DateResign / DateRevoked / LastOfTransferDate -> [Date Resigned]; [Entity Type] mapping identical to MT Client Entity

## Post-insert updates
- UPDATE [Ben Own_CP] (3 = BO + CP, 1 = BO only, 2 = CP only, 0 none). The statement appears twice in the script; it is idempotent.

## Notes for reconciliation
- Alternate Director (DAL) is not excluded here, unlike MT Client Entity (active).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClientEntityHistory'
GO

INSERT INTO [MT Client Entity History]
(
    [NAV_Entry No]
    , [Entry No_]
    , [Client No_]
    , [Entity No_]
    , [Entity Type]
    , [Date Appointed]
    , [Notes]
    , [Date Resigned]
    , [Resignation Notes]
    , [Type]
    , [First Officer]
    , [Percentage Ownership]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY CE2.[Client No_]) AS [NAV_Entry No]
    , ROW_NUMBER() OVER(ORDER BY CE2.[Client No_]) AS [Entry No_]
    , CE2.[Client No_]
    , CE2.[Entity No_]
    , CE2.[Entity Type] AS [Entity Type]
    , CE2.[Date Appointed]
    , CE2.[Notes]
    , CE2.[Date Resigned]
    , NULL AS [Resignation Notes]

    , CASE
        WHEN GISC.IsClient = 1 THEN 1
        WHEN GISC.IsEntity = 1 THEN 0
        WHEN GISC.IsResource = 1 THEN 2
    END AS [Type]

    , CE2.[First Officer]
    , CE2.[Percentage Ownership] * 100 AS [Percentage Ownership]
FROM
    (
        SELECT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , OfficerType AS [Entity Type]
            , DateAppoint AS [Date Appointed]
            , Note AS [Notes]
            , DateResign AS [Date Resigned]
            , NULL AS [Type]
            , FirstOf AS [First Officer]
            , NULL AS [Percentage Ownership]
        FROM Officers
        WHERE(DateResign IS NOT NULL OR DateResign <> '') AND [Status] = 'R' AND OfficerType NOT IN('SOW', 'CNP')

        UNION

        SELECT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'BEN' AS [Entity Type]
            , DateStart AS [Date Appointed]
            , iNote AS [Notes]
            , DateEnd AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , PercentCap AS [Percentage Ownership]
        FROM Share_Interests
        WHERE(DateEnd IS NOT NULL OR DateEnd <> '') AND IntType = 'UBO'

        UNION

        SELECT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]

            , CASE
                WHEN UserTabCode1 = 'SHRHELD' AND UserCode1 = 'NOM' THEN 'NOM'
                WHEN UserTabCode1 = 'SHRHELD' AND UserCode1 = 'JSH' THEN 'SHR'
                WHEN UserTabCode1 = 'SHRHELD' AND UserCode1 = 'TRT' THEN 'TST'
                ELSE 'BEN'
            END AS [Entity Type]

            , DateStart AS [Date Appointed]
            , iNote AS [Notes]
            , DateEnd AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , PercentCap AS [Percentage Ownership]
        FROM Share_Interests
        WHERE(DateEnd IS NOT NULL OR DateEnd <> '') AND IntType = 'BEO'

        UNION

        SELECT
            EntCode AS [Client No_]
            , Beneficiary AS [Entity No_]

            , CASE
                WHEN BenfType = 'X' THEN 'EXB'
                ELSE 'BNF'
            END AS [Entity Type]

            , DateAppoint AS [Date Appointed]
            , Benefits AS [Notes]
            , DateRevoked AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , NULL AS [Percentage Ownership]
        FROM Beneficiaries
        WHERE(DateRevoked IS NOT NULL OR DateRevoked <> '')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'SHR' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , LastOfTransferDate AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , NULL AS [Percentage Ownership]
        FROM CR_Shareholders
        WHERE SharesHeld = 0 AND ShareTypeCode NOT IN('/L', '/G')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'LIP' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , LastOfTransferDate AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , NULL AS [Percentage Ownership]
        FROM CR_Shareholders
        WHERE SharesHeld = 0 AND ShareTypeCode IN('/L')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'GPA' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , LastOfTransferDate AS [Date Resigned]
            , NULL AS [Type]
            , NULL AS [First Officer]
            , NULL AS [Percentage Ownership]
        FROM CR_Shareholders
        WHERE SharesHeld = 0 AND ShareTypeCode IN('/G')
    ) AS CE2

LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON CE2.[Entity No_] = GISC.RefCode
WHERE CE2.[Client No_] IN(
    SELECT RefCode FROM dbo.fnGetInScopeClients()
    WHERE IsClient = 1
);

GO

WITH BenOwn AS(
    SELECT
        EntCode
        , AddrCode
    FROM Share_Interests
    WHERE IntType IN('BEO', 'UBO')
)

, CNP AS(
    SELECT
        EntCode
        , AddrCode
    FROM Officers
    WHERE OfficerType = 'CNP'
)

UPDATE M SET
    [Ben Own_CP] = CASE
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NOT NULL THEN 3
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NULL THEN 1
        WHEN BO.EntCode IS NULL AND CNP.EntCode IS NOT NULL THEN 2
        ELSE 0
    END
FROM [MT Client Entity History] AS M
LEFT JOIN BenOwn AS BO ON M.[Client No_] = BO.EntCode AND M.[Entity No_] = BO.AddrCode
LEFT JOIN CNP ON M.[Client No_] = CNP.EntCode AND M.[Entity No_] = CNP.AddrCode;

WITH BenOwn AS(
    SELECT
        EntCode
        , AddrCode
    FROM Share_Interests
    WHERE IntType IN('BEO', 'UBO')
)

, CNP AS(
    SELECT
        EntCode
        , AddrCode
    FROM Officers
    WHERE OfficerType = 'CNP'
)

UPDATE M SET
    [Ben Own_CP] = CASE
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NOT NULL THEN 3
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NULL THEN 1
        WHEN BO.EntCode IS NULL AND CNP.EntCode IS NOT NULL THEN 2
        ELSE 0
    END
FROM [MT Client Entity History] AS M
LEFT JOIN BenOwn AS BO ON M.[Client No_] = BO.EntCode AND M.[Entity No_] = BO.AddrCode
LEFT JOIN CNP ON M.[Client No_] = CNP.EntCode AND M.[Entity No_] = CNP.AddrCode

GO
```
