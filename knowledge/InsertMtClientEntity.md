---
staging_table: MT Client Entity
etl_script: InsertMtClientEntity.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Client No_)
exact_sources: [Officers, Share_Interests (UBO), Share_Interests (BEO), Beneficiaries, CR_Shareholders (SHR/etc), CR_Shareholders (LIP), CR_Shareholders (GPA), Entity, IdentityRegister (FSPR), IdentityRegister (FPTFI/CPTFI)]
lookup_sources: [Entity (lookup), IdentityRegister (lookup), Share_Interests (lookup), Officers (lookup)]
---
# MT Client Entity

## Overview
Migrates the ACTIVE relationships between an in-scope Client and other master files (officers, beneficial owners, UBOs, beneficiaries, shareholders, limited / general partners, structure-diagram links, FATCA sponsoring entity and reporting FI). Ended / resigned relationships are migrated by MT Client Entity History.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClientEntity.sql` into staging table `[MT Client Entity]`.

## Scope filter
Final filter on the combined result: `CE2.[Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`. [Type] of the related entity comes from fnGetInScopeClients().

## Row count behaviour
One untagged UNION of 10 branches (identical rows collapse; SELECT DISTINCT inside the CR_Shareholders and RFI branches), filtered to in-scope clients. Notes are split: first 50 characters in [Notes], the rest in [Add_ Notes].

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | Active officers: no resignation date and status not 'R'; Controlling Person (CNP), Substantial Owner (SOW) and Alternate Director (DAL) are excluded. | `FROM Officers WHERE (DateResign IS NULL OR DateResign = '') AND [Status] <> 'R' AND OfficerType NOT IN ('CNP','SOW','DAL')` | Bring over active client relations with other master files (officers). |
| Share_Interests (UBO) | Active Ultimate Beneficial Owner interests (no end date); Entity Type is 'BEN'. | `FROM Share_Interests WHERE (DateEnd IS NULL OR DateEnd = '') AND IntType = 'UBO'` | Bring over the active Ultimate Beneficial Owner relations of in-scope clients. |
| Share_Interests (BEO) | Active Beneficial Owner interests (no end date). Entity Type: NOM / SHR / TST when user table SHRHELD has code NOM / JSH / TRT, otherwise BEN. | `FROM Share_Interests WHERE (DateEnd IS NULL OR DateEnd = '') AND IntType = 'BEO'` | Bring over the active Beneficial Owner (BEO) relations of in-scope clients. |
| Beneficiaries | Beneficiaries that are not revoked; Entity Type 'EXB' when BenfType = 'X', otherwise 'BNF'. | `FROM Beneficiaries WHERE (DateRevoked IS NULL OR DateRevoked = '')` | Bring over the active beneficiary relations of in-scope clients. |
| CR_Shareholders (SHR/etc) | Current shareholders (shares held <> 0) that are not Limited Partner ('/L') or General Partner ('/G') types. DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld <> 0 AND ShareTypeCode NOT IN ('/L','/G')` | Bring over the active shareholders (other than LP / GP) of in-scope clients. |
| CR_Shareholders (LIP) | Current Limited Partnership holders (shares held <> 0, share type '/L'). DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld <> 0 AND ShareTypeCode IN ('/L')` | Bring over the active Limited Partners of in-scope clients. |
| CR_Shareholders (GPA) | Current General Partner holders (shares held <> 0, share type '/G'). DISTINCT. | `SELECT DISTINCT ... FROM CR_Shareholders WHERE SharesHeld <> 0 AND ShareTypeCode IN ('/G')` | Bring over the active General Partners of in-scope clients. |
| Entity | Every Entity row (client -> EntClient link), no extraction filter; Entity Type 'SDL' (Structure Diagram Link) and date appointed = incorporation date. | `FROM Entity (no WHERE; EntCode -> Client No_, EntClient -> Entity No_)` | Bring over entity-to-client relations as Structure Diagram Links. |
| IdentityRegister (FSPR) | Active FATCA Sponsoring Entity identity records; Entity Type 'FSP'. | `FROM IdentityRegister AS IR LEFT JOIN Entity AS E ON IR.RefCode = E.EntCode WHERE IR.IdType = 'FSPR' AND IR.Active = 1` | Bring over the FATCA Sponsoring entity relations of in-scope clients. |
| IdentityRegister (FPTFI/CPTFI) | Active records reporting through a Financial Institution (FATCA FPTFI / CRS CPTFI); Entity Type 'RFI'. DISTINCT. | `SELECT DISTINCT ... FROM IdentityRegister AS IR LEFT JOIN Entity AS E ON IR.RefCode = E.EntCode WHERE IR.IdType IN ('FPTFI','CPTFI') AND IR.Active = 1` | Bring over the Reporting Financial Institution relations of in-scope clients. |

### Adjustment row
Label `Duplicates removed across UNION branches`: negative adjustment = distinct rows of the ETL's untagged UNION minus the sum of the branch counts above (identical rows produced by two branches collapse into one). It is not a Vpoint table.

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Entity (lookup) | LEFT JOIN Entity ON EntCode = Client No_ (FSPR / FPTFI / CPTFI branches) | [Date Appointed] for FSP and RFI relations |
| IdentityRegister (lookup) | Post-insert UPDATE joins IdentityRegister (IdType FPTFI/CPTFI -> FRFI record of the entity; FSPR) to rows with Entity Type RFI / FSP | [FATCA Filer Category], [FATCA Reporting FI] |
| Share_Interests (lookup) | Post-insert UPDATE: BenOwn = Share_Interests WHERE IntType IN ('BEO','UBO') AND DateEnd IS NULL, joined on EntCode = Client No_ and AddrCode = Entity No_ | [Ben Own_CP] |
| Officers (lookup) | Post-insert UPDATE: CNP / SOW = Officers WHERE OfficerType = 'CNP' / 'SOW' AND DateResign IS NULL, joined on EntCode and AddrCode | [Ben Own_CP], [CRS Controlling Person Code], [FATCA Substantial Owner] |

## Column mapping highlights
- [Ben Own_CP] = 3 when both a Beneficial Owner and Controlling Person exist, 1 BO only, 2 CP only, otherwise 0
- [Percentage Ownership] = PercentCap * 100; [Type] = 1 Client / 0 Entity / 2 Resource of the Entity No_

## Post-insert updates
- UPDATE [Ben Own_CP], [CRS Controlling Person Code], [FATCA Substantial Owner] from Share_Interests (BEO/UBO) and Officers (CNP, SOW)
- UPDATE [FATCA Reporting FI] / [FATCA Filer Category] for RFI rows; UPDATE [FATCA Filer Category] for FSP rows

## Notes for reconciliation
- CNP and SOW officers are not rows of this table; they only set flags on matching BEO / UBO rows.
- Settlor (MST) interests are not included in this version.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClientEntity'
GO

INSERT INTO [MT Client Entity]
(
    [NAV_Entry No]
    , [Client No_]
    , [Entity No_]
    , [Entity Type]
    , [Date Appointed]
    , [Notes]
    , [Ben Own_CP]
    , [BO_CP Manual Overwrite]
    , [BO_CP Transaction No_]
    , [Date of Change Notification]
    , [Date of Retirement]
    , [Type]
    , [Percentage Ownership]
    , [Compliance Required]
    , [Add_ Notes]
    , [First Officer]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY CE2.[Client No_]) AS [NAV_Entry No]
    , CE2.[Client No_]
    , CE2.[Entity No_]
    , CE2.[Entity Type] AS [Entity Type]
    , CE2.[Date Appointed]
    , LEFT(CE2.[Notes], 50) AS [Notes]
    , CE2.[Ben Own_CP]
    , CE2.[BO_CP Manual Overwrite]
    , CE2.[BO_CP Transaction No_]
    , CE2.[Date of Change Notification]
    , CE2.[Date of Retirement]

    , CASE
        WHEN GISC.IsClient = 1 THEN 1
        WHEN GISC.IsEntity = 1 THEN 0
        WHEN GISC.IsResource = 1 THEN 2
    END AS [Type]

    , CE2.[Percentage Ownership] * 100 AS [Percentage Ownership]
    , NULL AS [Compliance Required]
    , SUBSTRING(CE2.[Notes], 51, LEN(CE2.[Notes])) AS [Add_ Notes]
    , CE2.[First Officer]
FROM
    (
        SELECT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , OfficerType AS [Entity Type]
            , DateAppoint AS [Date Appointed]
            , Note AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , FirstOf AS [First Officer]
        FROM Officers
        WHERE(DateResign IS NULL OR DateResign = '') AND [Status] <> 'R' AND OfficerType NOT IN('CNP', 'SOW', 'DAL')

        UNION

        SELECT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'BEN' AS [Entity Type]
            , DateStart AS [Date Appointed]
            , iNote AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , PercentCap AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM Share_Interests
        WHERE(DateEnd IS NULL OR DateEnd = '') AND IntType = 'UBO'

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
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , PercentCap AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM Share_Interests
        WHERE(DateEnd IS NULL OR DateEnd = '') AND IntType = 'BEO'

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
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM Beneficiaries
        WHERE(DateRevoked IS NULL OR DateRevoked = '')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'SHR' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM CR_Shareholders
        WHERE SharesHeld <> 0 AND ShareTypeCode NOT IN('/L', '/G')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'LIP' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM CR_Shareholders
        WHERE SharesHeld <> 0 AND ShareTypeCode IN('/L')

        UNION

        SELECT DISTINCT
            EntCode AS [Client No_]
            , AddrCode AS [Entity No_]
            , 'GPA' AS [Entity Type]
            , FirstOfTransferDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM CR_Shareholders
        WHERE SharesHeld <> 0 AND ShareTypeCode IN('/G')

        UNION

        SELECT
            EntCode AS [Client No_]
            , EntClient AS [Entity No_]
            , 'SDL' AS [Entity Type]
            , IncorpDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM Entity

        UNION

        SELECT
            IR.RefCode AS [Client No_]
            , IR.MasterFileLink AS [Entity No_]
            , 'FSP' AS [Entity Type]
            , E.IncorpDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM IdentityRegister AS IR
        LEFT JOIN Entity AS E ON IR.RefCode = E.EntCode
        WHERE IR.IdType = 'FSPR' AND IR.Active = 1

        UNION

        SELECT DISTINCT
            IR.RefCode AS [Client No_]
            , IR.MasterFileLink AS [Entity No_]
            , 'RFI' AS [Entity Type]
            , E.IncorpDate AS [Date Appointed]
            , NULL AS [Notes]
            , NULL AS [Ben Own_CP]
            , 0 AS [BO_CP Manual Overwrite]
            , NULL AS [BO_CP Transaction No_]
            , NULL AS [Date of Change Notification]
            , NULL AS [Date of Retirement]
            , NULL AS [Type]
            , NULL AS [Percentage Ownership]
            , NULL AS [Add_ Notes]
            , NULL AS [First Officer]
        FROM IdentityRegister AS IR
        LEFT JOIN Entity AS E ON IR.RefCode = E.EntCode
        WHERE IR.IdType IN('FPTFI', 'CPTFI') AND IR.Active = 1
    ) AS CE2

LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON CE2.[Entity No_] = GISC.RefCode
WHERE CE2.[Client No_] IN(
    SELECT RefCode FROM dbo.fnGetInScopeClients()
    WHERE IsClient = 1
);

GO

-- Ben Owner/Controlling Person/Substantial Owner update
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
            WHERE SOW.EntCode = M.[Client No_] AND SOW.AddrCode = M.[Entity No_]
        ) THEN 1
        ELSE NULL
    END
FROM [MT Client Entity] AS M
LEFT JOIN BenOwn AS BO ON M.[Client No_] = BO.EntCode AND M.[Entity No_] = BO.AddrCode
LEFT JOIN CNP ON M.[Client No_] = CNP.EntCode AND M.[Entity No_] = CNP.AddrCode

-- Update FATCA/CRS fields
-- Reporting through FI
UPDATE [MT Client Entity] SET
    [FATCA Reporting FI] = 1
    , [FATCA Filer Category] = RP.UdCode
FROM IdentityRegister AS IR
INNER JOIN [MT Client Entity] AS C ON IR.RefCode = C.[Client No_] AND IR.MasterFileLink = C.[Entity No_]
LEFT JOIN IdentityRegister AS RP ON IR.MasterFileLink = RP.RefCode
WHERE IR.IdType IN('FPTFI', 'CPTFI') AND RP.IdType = 'FRFI' AND C.[Entity Type] = 'RFI'

-- Sponsoring Entity
UPDATE [MT Client Entity] SET
    [FATCA Filer Category] = IR.UdCode
FROM IdentityRegister AS IR
INNER JOIN [MT Client Entity] AS C ON IR.RefCode = C.[Client No_] AND IR.MasterFileLink = C.[Entity No_]
WHERE IR.IdType = 'FSPR' AND C.[Entity Type] = 'FSP'

GO
```
