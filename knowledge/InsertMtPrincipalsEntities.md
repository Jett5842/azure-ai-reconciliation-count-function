---
staging_table: MT Principals _ Entities
etl_script: InsertMtPrincipalsEntities.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsEntity = 1 (Linked To No_ / EntCode)
exact_sources: [Officers (RelClass M/I), Share_Interests]
lookup_sources: [Share_Interests (lookup), Officers (lookup)]
---
# MT Principals _ Entities

## Overview
Migrates the principals of in-scope Entity Master Files: officer relations (RelClass M or I, all officer types) and share interest relations (all interest types), with appointment / resignation dates, shares and percentage ownership. Flags for beneficial owner / controlling person / substantial owner are set afterwards.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtPrincipalsEntities.sql` into staging table `[MT Principals _ Entities]`.

## Scope filter
Both branches keep only rows linked to in-scope Entities: `EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)`.

## Row count behaviour
Two branches combined with an untagged UNION (identical rows collapse).

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers (RelClass M/I) | Officer relations whose RelClass is 'M' or 'I' (all OfficerTypes) linked to in-scope entities; Status = resigned (1) when a resign date exists or status = 'R'. | `FROM Officers AS O LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON O.AddrCode = GISC.RefCode LEFT JOIN RefMaster AS RM ON O.AddrCode = RM.RefCode WHERE RelClass IN ('M','I') AND O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)` | Bring over officer relations of in-scope Entity Master Files. |
| Share_Interests | All share interest rows (every IntType) linked to in-scope entities; Status = ended (1) when an end date exists. Percentage = PercentCap * 100. | `FROM Share_Interests AS SI LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON SI.AddrCode = GISC.RefCode LEFT JOIN RefMaster AS RM ON SI.AddrCode = RM.RefCode WHERE EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)` | Bring over share interest relations of in-scope Entity Master Files. |

### Adjustment row
Label `Duplicates removed across UNION branches`: negative adjustment = distinct rows of the ETL's untagged UNION minus the sum of the branch counts above (identical rows produced by two branches collapse into one). It is not a Vpoint table.

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Share_Interests (lookup) | Post-insert UPDATE: BenOwn = Share_Interests WHERE IntType IN ('BEO','UBO') AND DateEnd IS NULL, joined on EntCode = Linked To No_ and AddrCode = Code | [Ben Own_CP] |
| Officers (lookup) | Post-insert UPDATE: CNP / SOW = Officers WHERE OfficerType = 'CNP' / 'SOW' AND DateResign IS NULL | [Ben Own_CP], [CRS Controlling Person Code], [FATCA Substantial Owner] |

## Column mapping highlights
- [Linked To] = constant 0; [Function] = OfficerType or IntType; [Type] = 1 Client / 0 Entity / 2 Resource of the principal (Code)

## Post-insert updates
- UPDATE [Ben Own_CP], [CRS Controlling Person Code], [FATCA Substantial Owner] using Share_Interests (BEO/UBO) and Officers (CNP/SOW) where the end / resign date is NULL

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtPrincipalsEntities'
GO

INSERT INTO [MT Principals _ Entities]
(
    [Linked To]
    , [Linked To No_]
    , [Total Units _ Shares]
    , [Percentage Ownership]
    , [Type]
    , [Code]
    , [Function]
    , [Status]
    , [Appointment Date]
    , [Resignation Date]
    , [Details]
    , [Entity No_]
    , [CRS Controlling Person Code]
    , [Ben Own_CP]
    , [External Reference No]
    , [External Reference No 2]
    , [External Reference No 3]
    , [NAV_Entry No]
)
SELECT
    CE2.*
    , ROW_NUMBER() OVER(ORDER BY CE2.[Entity No_]) AS [NAV_Entry No]
FROM
    (
        SELECT
            0 AS [Linked To]
            , O.EntCode AS [Linked To No_]
            , NULL AS [Total Units _ Shares]
            , NULL AS [Percentage Ownership]

            , CASE
                WHEN GISC.IsClient = 1 THEN 1
                WHEN GISC.IsEntity = 1 THEN 0
                WHEN GISC.IsResource = 1 THEN 2
            END AS [Type]

            , AddrCode AS [Code]
            , OfficerType AS [Function]

            , CASE
                WHEN(DateResign IS NOT NULL OR DateResign <> '' OR O.Status = 'R') THEN 1
                ELSE 0
            END AS [Status]

            , DateAppoint AS [Appointment Date]
            , DateResign AS [Resignation Date]
            , O.Note AS [Details]
            , EntCode AS [Entity No_]
            , NULL AS [CRS Controlling Person Code]
            , NULL AS [Ben Own_CP]
            , NULL AS [External Reference No]
            , NULL AS [External Reference No 2]
            , NULL AS [External Reference No 3]
        FROM Officers AS O LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON O.AddrCode = GISC.RefCode
        LEFT JOIN RefMaster AS RM ON O.AddrCode = RM.RefCode
        WHERE
            RelClass IN(
                'M', 'I') AND O.EntCode IN(
                SELECT RefCode FROM dbo.fnGetInScopeClients()
                WHERE IsEntity = 1
            )

        UNION

        SELECT
            0 AS [Linked To]
            , EntCode AS [Linked To No_]
            , NrShare AS [Total Units _ Shares]
            , PercentCap * 100 AS [Percentage Ownership]

            , CASE
                WHEN GISC.IsClient = 1 THEN 1
                WHEN GISC.IsEntity = 1 THEN 0
                WHEN GISC.IsResource = 1 THEN 2
            END AS [Type]

            , AddrCode AS [Code]
            , IntType AS [Function]

            , CASE
                WHEN(DateEnd IS NOT NULL OR DateEnd <> '') THEN 1
                ELSE 0
            END AS [Status]

            , DateStart AS [Appointment Date]
            , DateEnd AS [Resignation Date]
            , iNote AS [Details]
            , EntCode AS [Entity No_]
            , NULL AS [CRS Controlling Person Code]
            , NULL AS [Ben Own_CP]
            , NULL AS [External Reference No]
            , NULL AS [External Reference No 2]
            , NULL AS [External Reference No 3]
        FROM Share_Interests AS SI LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON SI.AddrCode = GISC.RefCode
        LEFT JOIN RefMaster AS RM ON SI.AddrCode = RM.RefCode
        WHERE EntCode IN(
            SELECT RefCode FROM dbo.fnGetInScopeClients()
            WHERE IsEntity = 1
        )
    ) AS CE2;

WITH BenOwn AS(
    SELECT
        EntCode
        , AddrCode
    FROM Share_Interests
    WHERE IntType IN('BEO', 'UBO') AND DateEnd IS NULL
)

, CNP AS(
    SELECT
        EntCode
        , AddrCode
        , UdCode
    FROM Officers
    WHERE OfficerType = 'CNP' AND DateResign IS NULL
)

, SOW AS(
    SELECT
        EntCode
        , AddrCode
    FROM Officers
    WHERE OfficerType = 'SOW' AND DateResign IS NULL
)

UPDATE M SET
    [Ben Own_CP] = CASE
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NOT NULL THEN 3
        WHEN BO.EntCode IS NOT NULL AND CNP.EntCode IS NULL THEN 1
        WHEN BO.EntCode IS NULL AND CNP.EntCode IS NOT NULL THEN 2
        ELSE 0
    END

    , [CRS Controlling Person Code] = CNP.UdCode

    , [FATCA Substantial Owner] = CASE
        WHEN EXISTS(
            SELECT SOW.EntCode FROM SOW
            WHERE SOW.EntCode = M.[Linked To No_] AND SOW.AddrCode = M.[Code]
        ) THEN 1
        ELSE NULL
    END
FROM [MT Principals _ Entities] AS M
LEFT JOIN BenOwn AS BO ON M.[Linked To No_] = BO.EntCode AND M.[Code] = BO.AddrCode
LEFT JOIN CNP ON M.[Linked To No_] = CNP.EntCode AND M.[Code] = CNP.AddrCode

GO
```
