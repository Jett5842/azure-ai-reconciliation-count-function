---
staging_table: MT Tax Details
etl_script: InsertMtTaxDetails.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: Record No_ in-scope (fnGetInScopeClients); TaxDetails branch IsClient = 1
exact_sources: [RefMaster + IdentityRegister (TaxDetails), RefMaster + IdentityRegister/ReportAccounts (TIN, NOT EXISTS dedup)]
lookup_sources: [IdentityRegister (lookup), ReportAccounts (lookup)]
---
# MT Tax Details

## Overview
Migrates the tax reporting details (FATCA / CRS): reporting financial institution (RFI) details for in-scope Clients, and TIN / account-holder (AH) details for Clients, Entities and Owners that have no RFI record. Includes tax return country, AEOI scope (reportable or not) and TIN. A TIN row is only created for a master file that does not already have a TaxDetails (RFI) row.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtTaxDetails.sql` into staging table `[MT Tax Details]`.

## Scope filter
Final filter: `[Record No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients())` and a non-NULL [Tax Return Country Code]. The TaxDetails branch additionally requires `ISC.IsClient = 1`; the TIN branch accepts any in-scope type (Client, Entity, Owner).

## Row count behaviour
Two CTEs combined with UNION: TaxDetails (SELECT DISTINCT FATCA_RFI branch UNION SELECT DISTINCT CRS_RFI branch) and TIN (FATCA_AH-style branch UNION CRS-style branch, each with NOT EXISTS against TaxDetails). Rows without a tax return country are removed in the final filter.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefMaster + IdentityRegister (TaxDetails) | FATCA_RFI rows (IdentityRegister FSPR, FPTFI or FRFI linked to itself) and CRS_RFI rows (CTDT, CPTFI or CRFI linked to itself) of in-scope clients, active records only. US / UM country codes are excluded from the tax return country. | `FROM RefMaster AS RM INNER JOIN IdentityRegister AS IR ON RM.RefCode = IR.RefCode AND (IR.IdType IN ('FSPR','FPTFI') OR (IR.IdType = 'FRFI' AND IR.MasterFileLink = IR.RefCode)) AND IR.Active = 1 [CRS: IdType IN ('CTDT','CPTFI') OR (IdType = 'CRFI' AND MasterFileLink = RefCode)] INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode AND ISC.IsClient = 1 ... ; final: [Record No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients()) AND [Tax Return Country Code] IS NOT NULL` | Bring over FATCA / CRS Reporting Financial Institution tax details of in-scope Client Master Files. |
| RefMaster + IdentityRegister/ReportAccounts (TIN, NOT EXISTS dedup) | Fallback tax details for in-scope master files that have a TIN (FIC / GIIN / FIN) or an active reportable account, and that do not already have a TaxDetails row. FATCA branch needs ReportAccounts.RepAuthority like 'F%'; the CRS branch excludes US / UM TINs. | `FROM RefMaster AS RM LEFT JOIN ReportAccounts AS RA ON RM.RefCode = RA.AcctHolder AND RA.AcctStatus = 'A' INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode LEFT JOIN IdentityRegister FIC / GIIN / FIN (IdType, Active = 1) WHERE NOT EXISTS (SELECT 1 FROM TaxDetails AS TD WHERE TD.[Record No_] = RM.RefCode) AND (FIC / GIIN / FIN / RA.AcctHolder present) [FATCA branch also: AND RA.RepAuthority LIKE 'F%']` | Bring over TIN numbers (account holder tax details) related to in-scope master files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| IdentityRegister (lookup) | LEFT JOINs with Active = 1: IdType FIC / GIIN / FIN / FCSC / FCRS / CRFI on RefCode; GIINSP via FSPR.MasterFileLink; FIC via CTDT.MasterFileLink | [Tax Return Country Code], [AEOI Scope], [TIN], [RFI Sending Company IN] |
| ReportAccounts (lookup) | LEFT JOIN ReportAccounts ON AcctHolder = RefCode AND AcctStatus = 'A' | [AEOI Scope] |

## Column mapping highlights
- [Record Type]: 2 Client, 3 Entity (not owner), 1 Owner (TIN branch); the TaxDetails branch is always 2
- [AEOI Scope] = 1 (reportable) when FCSC / FCRS lookup value is 'R' (RFI branches) or a ReportAccounts file code exists, otherwise 2

## Post-insert updates
- UPDATE [AEOI Scope] = 1 for master files with an active ReportAccounts row
- UPDATE [Tax Return Country Code] = 'GB' where it is GB-EAW, GB-ENG or GB-NIR

## Notes for reconciliation
- The two source labels are two branches of one result set, combined with UNION, so they can overlap only when identical.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtTaxDetails'
GO

WITH TaxDetails AS(
    -- FATCA
    SELECT DISTINCT
        2 AS [Record Type]
        , RM.RefCode AS [Record No_]
        , 'FATCA_RFI' AS [Tax Code]

        , CASE
            --GIIN.Country IN ('UM','US') THEN NULL -- US Country is required for FATCA_AH only
            WHEN IR.IdType = 'FSPR' AND FIC.Country NOT IN('UM', 'US') THEN FIC.Country
            WHEN GIIN.Country NOT IN('UM', 'US') THEN GIIN.Country
        END AS [Tax Return Country Code]

        , RM.RefCode AS [No_]
        , NULL AS [Entity No_]

        , CASE
            WHEN FATCAScope.LookupValue = 'R' THEN 1
            ELSE 2
        END AS [AEOI Scope]

        , NULL AS [TIN Type]

        , CASE
            WHEN IR.IdType = 'FSPR' THEN FIC.IdCode
            ELSE GIIN.IdCode
        END AS [TIN]

        , CASE
            WHEN IR.IdType = 'FSPR' THEN GIINSP.IdCode
            WHEN IR.IdType = 'FRFI' THEN GIIN.IdCode
            ELSE NULL
        END AS [RFI Sending Company IN]

        , NULL AS [RFI Sending Company IN Type]
        , NULL AS [Initial Registration Date]
        , NULL AS [Registration Expiry Date]
    FROM RefMaster AS RM
    INNER JOIN IdentityRegister AS IR ON RM.RefCode = IR.RefCode AND(IR.IdType IN('FSPR', 'FPTFI') OR(IR.IdType = 'FRFI' AND IR.MasterFileLink = IR.RefCode)) AND IR.Active = 1
    INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode AND ISC.IsClient = 1
    LEFT JOIN IdentityRegister AS FIC ON RM.RefCode = FIC.RefCode AND FIC.IdType = 'FIC' AND FIC.Active = 1
    LEFT JOIN IdentityRegister AS FSPR ON IR.RefCode = FSPR.RefCode AND FSPR.IdType = 'FSPR' AND FSPR.Active = 1
    LEFT JOIN IdentityRegister AS GIINSP ON FSPR.MasterFileLink = GIINSP.RefCode AND GIINSP.IdType = 'GIINSP' AND GIINSP.Active = 1
    LEFT JOIN IdentityRegister AS GIIN ON RM.RefCode = GIIN.RefCode AND GIIN.IdType = 'GIIN' AND GIIN.Active = 1
    LEFT JOIN IdentityRegister AS FPTFI ON IR.RefCode = FPTFI.RefCode AND FPTFI.IdType = 'FPTFI' AND FPTFI.Active = 1
    LEFT JOIN IdentityRegister AS FATCAScope ON RM.RefCode = FATCAScope.RefCode AND FATCAScope.IdType = 'FCSC' AND FATCAScope.Active = 1

    UNION

    -- CRS
    SELECT DISTINCT
        2 AS [Record Type]
        , RM.RefCode AS [Record No_]
        , 'CRS_RFI' AS [Tax Code]

        , CASE
            WHEN IR.IdType IN('CTDT', 'CRFI') THEN CRFI.Country
            WHEN FIC.RefCode IS NOT NULL THEN FIC.Country
        END AS [Tax Return Country Code]

        , RM.RefCode AS [No_]
        , NULL AS [Entity No_]

        , CASE
            WHEN CRSScope.LookupValue = 'R' THEN 1
            ELSE 2
        END AS [AEOI Scope]

        , NULL AS [TIN Type]
        , FIC.IdCode AS [TIN]

        , CASE
            WHEN EXISTS(
                SELECT 1 FROM IdentityRegister AS IR1
                WHERE IR1.RefCode = IR.RefCode AND IR1.IdType = 'CTDT'
            ) THEN CTDTFIC.IdCode
            WHEN EXISTS(
                SELECT 1 FROM IdentityRegister AS IR2
                WHERE IR2.RefCode = IR.RefCode AND IR2.IdType = 'CRFI' AND NOT EXISTS(
                    SELECT 1 FROM IdentityRegister AS IR3
                    WHERE IR3.RefCode = IR.RefCode AND IR3.IdType IN('CTDT', 'CPTFI')
                )
            ) THEN FIC.IdCode
            WHEN EXISTS(
                SELECT 1 FROM IdentityRegister AS IR4
                WHERE IR4.RefCode = IR.RefCode AND IR4.IdType = 'CPTFI'
            ) THEN NULL
        END AS [RFI Sending Company IN]

        , NULL AS [RFI Sending Company IN Type]
        , NULL AS [Initial Registration Date]
        , NULL AS [Registration Expiry Date]
    FROM RefMaster AS RM
    INNER JOIN IdentityRegister AS IR ON RM.RefCode = IR.RefCode AND(IR.IdType IN('CTDT', 'CPTFI') OR(IR.IdType = 'CRFI' AND IR.MasterFileLink = IR.RefCode)) AND IR.Active = 1
    INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode AND ISC.IsClient = 1
    LEFT JOIN IdentityRegister AS CRFI ON RM.RefCode = CRFI.RefCode AND CRFI.IdType = 'CRFI' AND CRFI.Active = 1 AND CRFI.Country NOT IN('UM', 'US')
    LEFT JOIN IdentityRegister AS FIC ON RM.RefCode = FIC.RefCode AND FIC.IdType = 'FIC' AND FIC.Active = 1 AND FIC.Country NOT IN('UM', 'US')
    LEFT JOIN IdentityRegister AS CRSScope ON RM.RefCode = CRSScope.RefCode AND CRSScope.IdType = 'FCRS' AND CRSScope.Active = 1
    LEFT JOIN IdentityRegister AS CTDT ON IR.RefCode = CTDT.RefCode AND CTDT.IdType = 'CTDT' AND CTDT.Active = 1
    LEFT JOIN IdentityRegister AS CTDTFIC ON CTDT.MasterFileLink = CTDTFIC.RefCode AND CTDTFIC.IdType = 'FIC' AND CTDTFIC.Active = 1
)

, TIN AS(
    SELECT
        CASE
            WHEN ISC.IsClient = 1 THEN 2
            WHEN ISC.IsEntity = 1 AND ISC.IsOwner = 0 THEN 3
            WHEN ISC.IsEntity = 1 AND ISC.IsOwner = 1 THEN 1
            ELSE NULL
        END AS [Record Type]

        , RM.RefCode AS [Record No_]

        , CASE
            WHEN ISC.IsClient = 1 THEN 'FATCA_RFI'
            WHEN ISC.IsEntity = 1 AND EXISTS(
                SELECT 1 FROM ReportAccounts AS RA
                WHERE RM.RefCode = RA.AcctHolder AND RA.RepAuthority LIKE 'F%'
            ) THEN 'FATCA_AH'
        END AS [Tax Code]

        , CASE
            WHEN ISC.IsClient = 1
                THEN(
                    CASE
                        WHEN GIIN.RefCode IS NOT NULL THEN GIIN.Country
                        WHEN FIC.RefCode IS NOT NULL THEN FIC.Country
                        WHEN FIN.RefCode IS NOT NULL THEN FIN.Country
                    END
                )
            WHEN
                ISC.IsEntity = 1 AND EXISTS(
                    SELECT 1 FROM ReportAccounts AS RA
                    WHERE RM.RefCode = RA.AcctHolder AND RA.RepAuthority LIKE 'F%'
                )
                THEN 'US'
        END AS [Tax Return Country Code]

        , CASE
            WHEN ISC.IsClient = 1 OR ISC.IsEntity = 1 THEN RM.RefCode
            ELSE NULL
        END AS [No_]

        , CASE
            WHEN ISC.IsEntity = 1 THEN RM.RefCode
            ELSE NULL
        END AS [Entity No_]

        , CASE
            WHEN RA.FileCode IS NOT NULL THEN 1
            ELSE 2
        END AS [AEOI Scope]

        , NULL AS [TIN Type]

        , CASE
            WHEN GIIN.RefCode IS NOT NULL THEN GIIN.IdCode
            WHEN FIC.RefCode IS NOT NULL THEN FIC.IdCode
            WHEN FIN.RefCode IS NOT NULL THEN FIN.IdCode
        END AS [TIN]

        , NULL AS [RFI Sending Company IN]
        , NULL AS [RFI Sending Company IN Type]
        , NULL AS [Initial Registration Date]
        , NULL AS [Registration Expiry Date]
    FROM RefMaster AS RM
    LEFT JOIN ReportAccounts AS RA ON RM.RefCode = RA.AcctHolder AND RA.AcctStatus = 'A'
    INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode
    LEFT JOIN IdentityRegister AS FIC ON RM.RefCode = FIC.RefCode AND FIC.IdType = 'FIC' AND FIC.Active = 1
    LEFT JOIN IdentityRegister AS GIIN ON RM.RefCode = GIIN.RefCode AND GIIN.IdType = 'GIIN' AND GIIN.Active = 1
    LEFT JOIN IdentityRegister AS FIN ON RM.RefCode = FIN.RefCode AND FIN.IdType = 'FIN' AND FIN.Active = 1
    WHERE
        NOT EXISTS(
            SELECT 1
            FROM TaxDetails AS TD
            WHERE TD.[Record No_] = RM.RefCode
        ) AND(FIC.RefCode IS NOT NULL OR GIIN.RefCode IS NOT NULL OR FIN.RefCode IS NOT NULL OR RA.AcctHolder IS NOT NULL) AND RA.RepAuthority LIKE 'F%'

    UNION

    SELECT
        CASE
            WHEN ISC.IsClient = 1 THEN 2
            WHEN ISC.IsEntity = 1 AND ISC.IsOwner = 0 THEN 3
            WHEN ISC.IsEntity = 1 AND ISC.IsOwner = 1 THEN 1
            ELSE NULL
        END AS [Record Type]

        , RM.RefCode AS [Record No_]

        , CASE
            WHEN ISC.IsClient = 1 THEN 'CRS_RFI'
            WHEN ISC.IsEntity = 1  --AND EXISTS(SELECT 1 FROM ReportAccounts RA WHERE RM.RefCode = RA.AcctHolder AND RA.RepAuthority LIKE 'C%') 
                THEN 'CRS_AH'
        END AS [Tax Code]

        , CASE
            WHEN FIC.RefCode IS NOT NULL THEN FIC.Country
            WHEN FIN.RefCode IS NOT NULL THEN FIN.Country
        END AS [Tax Return Country Code]

        , CASE
            WHEN ISC.IsClient = 1 OR ISC.IsEntity = 1 THEN RM.RefCode
            ELSE NULL
        END AS [No_]

        , CASE
            WHEN ISC.IsEntity = 1 THEN RM.RefCode
            ELSE NULL
        END AS [Entity No_]

        , CASE
            WHEN RA.FileCode IS NOT NULL THEN 1
            ELSE 2
        END AS [AEOI Scope]

        , NULL AS [TIN Type]

        , CASE
            WHEN FIC.RefCode IS NOT NULL THEN FIC.IdCode
            WHEN FIN.RefCode IS NOT NULL THEN FIN.IdCode
        END AS [TIN]

        , NULL AS [RFI Sending Company IN]
        , NULL AS [RFI Sending Company IN Type]
        , NULL AS [Initial Registration Date]
        , NULL AS [Registration Expiry Date]
    FROM RefMaster AS RM
    LEFT JOIN ReportAccounts AS RA ON RM.RefCode = RA.AcctHolder AND RA.AcctStatus = 'A'
    INNER JOIN dbo.fnGetInScopeClients() AS ISC ON RM.RefCode = ISC.RefCode
    LEFT JOIN IdentityRegister AS FIC ON RM.RefCode = FIC.RefCode AND FIC.IdType = 'FIC' AND FIC.Active = 1 AND FIC.Country NOT IN('UM', 'US')
    LEFT JOIN IdentityRegister AS FIN ON RM.RefCode = FIN.RefCode AND FIN.IdType = 'FIN' AND FIN.Active = 1 AND FIN.Country NOT IN('UM', 'US')
    WHERE NOT EXISTS(
        SELECT 1
        FROM TaxDetails AS TD
        WHERE TD.[Record No_] = RM.RefCode
    ) AND(FIC.RefCode IS NOT NULL OR FIN.RefCode IS NOT NULL OR RA.AcctHolder IS NOT NULL)
)

INSERT INTO [MT Tax Details]
(
    [Record Type]
    , [Record No_]
    , [Tax Code]
    , [Tax Return Country Code]
    , [No_]
    , [Entity No_]
    , [AEOI Scope]
    , [TIN Type]
    , [TIN]
    , [RFI Sending Company IN]
    , [RFI Sending Company IN Type]
    , [Initial Registration Date]
    , [Registration Expiry Date]
    , [NAV_Entry No]
)
SELECT
    *
    , ROW_NUMBER() OVER(ORDER BY [Record No_]) AS [NAV_Entry No]
FROM(
    SELECT * FROM TaxDetails
    UNION
    SELECT * FROM TIN
) AS CombinedResult
WHERE [Record No_] IN(SELECT RefCode FROM dbo.fnGetInScopeClients()) AND([Tax Return Country Code] <> '' OR [Tax Return Country Code] IS NOT NULL)

-- Update AEOI Scope for active Reportable Accounts
UPDATE M SET [AEOI Scope] = 1
FROM [MT Tax Details] AS M
INNER JOIN ReportAccounts AS RA ON M.[Record No_] = RA.AcctHolder AND RA.AcctStatus = 'A'

-- Update Country Code if in GB-EAW, GB-ENG, GB-NIR
UPDATE M SET [Tax Return Country Code] = 'GB'
FROM [MT Tax Details] AS M
WHERE [Tax Return Country Code] IN('GB-EAW', 'GB-ENG', 'GB-NIR')

GO
```
