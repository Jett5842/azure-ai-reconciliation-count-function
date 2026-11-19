---
staging_table: MT Entity
etl_script: InsertMtEntity.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsEntity = 1 (RefMaster.RefCode)
exact_sources: [RefMaster]
lookup_sources: [Entity (lookup), Compliance (lookup), RefLabels (lookup), LookComboSave (lookup), qLvCNTR (lookup), IdentityRegister (lookup), CR_RefAddresses (lookup), RefStatus (lookup), BankAccounts (lookup), Officers (lookup)]
---
# MT Entity

## Overview
Migrates the in-scope Entity Master Files (individuals and companies related to clients): name, date of birth, nationality, residence, identification and passport data, PEP flag, tax ID, FATCA / CRS classification, regulatory licence, employer and administrator codes. Almost every column is looked up from related Vpoint tables.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtEntity.sql` into staging table `[MT Entity]`.

## Scope filter
`RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)`.

## Row count behaviour
No DISTINCT: one staging row per RefMaster row plus its LEFT JOINs (Entity, Compliance, RefLabels, LookComboSave, qLvCNTR), so the count equals the in-scope RefMaster rows unless a join fans out.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefMaster | Every RefMaster record that is an in-scope Entity; no other extraction filter. | `FROM RefMaster AS RM LEFT JOIN Entity AS E ON RM.RefCode = E.EntCode LEFT JOIN Compliance AS C ON RM.RefCode = C.AddrCode LEFT JOIN RefLabels AS RL ON RM.RefCode = RL.Code LEFT JOIN LookComboSave AS NATI ON C.Nationality = NATI.SaveName LEFT JOIN qLvCNTR AS CT ON C.PasPlaceIssue = CT.[Name] WHERE RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)` | Bring over the in-scope Entity Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Entity (lookup) | LEFT JOIN Entity ON EntCode = External Reference No | [Registered No_], [Date of incorp__formation], [Manager], [Administrator] |
| Compliance (lookup) | LEFT JOIN Compliance ON AddrCode = External Reference No | [Date of Birth], [Profession], [Marital Status], [Gender], [Former Name], [Town of Birth], [Date of Death], [Occupation] and ID card / passport fields |
| RefLabels (lookup) | LEFT JOIN RefLabels ON Code = External Reference No | [Inactive], [Date Inactive] |
| LookComboSave (lookup) | LEFT JOIN LookComboSave ON SaveName = Compliance.Nationality | [Nationality] |
| qLvCNTR (lookup) | LEFT JOIN qLvCNTR ON [Name] = Compliance.PasPlaceIssue | [Country of Incorporation], [Jurisdiction] |
| IdentityRegister (lookup) | Sub-queries (SELECT TOP 1) with Active = 1 (PEPT without Active filter) on RefCode: IdType FCSC / FCRS / BCT / INC / REG / IDC / PSP / PEPC / PEPT / CTZ / FIN / FIC; FIN / FIC only where IdCode is populated | [FATCA Classification], [CRS Classification], [Country of Birth], [Country of Incorporation], [Jurisdiction], [Regulatory Licence], [Regulatory Licence Number], [Regulated Activities], [Regulated Body], [Regulatory Jurisdiction], [Passport_ID Number/Country/Expiry/Issue Date (2)], [Passport number], [Passport expiry date], [Passport country of issue], [Passport_ID Issue Date], [PEP], [Primary PEP Co of Influence], [Nationality 2], [Tax ID Number] |
| CR_RefAddresses (lookup) | Sub-query (SELECT TOP 1): AddrType = 'RA' AND Active = 1 on RefCode | [Residence] |
| RefStatus (lookup) | Sub-query (SELECT TOP 1) where NewStat = 'C' (earliest SeqNr) on RefCode | [Date Inactive] |
| BankAccounts (lookup) | Sub-queries (SELECT TOP 1) on BankAddrCode = RefCode | [Bank Swift Code], [Bank Sort Code] |
| Officers (lookup) | Sub-query on OfficerType = 'EMR' AND EntCode = RefCode | [Employer_Name of Own Company] |

## Column mapping highlights
- [Entity Type] = 1 when RefMaster.BA = 1 (business) otherwise 0; [Personal_Corporate] = 0 for RefType 'I' (individual), 1 otherwise
- [Gender]: 'M' -> 1, 'F' -> 2; [Formal Name] = Title + Initials + Name for individuals, Name otherwise

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtEntity'
GO

INSERT INTO [MT Entity]
(
    [Name]
    , [Search Name]
    , [Date of Birth]
    , [Nationality]
    , [Profession]
    , [Domicile]
    , [Residence]
    , [Title]
    , [Name 2]
    , [Entity Type]
    , [FATCA Classification]
    , [CRS Classification]
    , [Date Inactive]
    , [Marital Status]
    , [Known As]
    , [Religion]
    , [Country of Birth]
    , [Gender]
    , [Initials]
    , [Personal_Corporate]
    , [Former Name]
    , [Country of Incorporation]
    , [Jurisdiction]
    , [Identity Verified By]
    , [Identity Verified On]
    , [Regulatory Licence]
    , [Regulatory Licence Number]
    , [Regulated Activities]
    , [Formal Name]
    , [Bank Swift Code]
    , [Bank Sort Code]
    , [External Reference No]
    , [Regulated Body]
    , [Regulatory Jurisdiction]
    , [Passport_ID Number (2)]
    , [Passport_ID Country (2)]
    , [Passport_ID Expiry Date (2)]
    , [Passport_ID Issue Date (2)]
    , [Passport number]
    , [Passport expiry date]
    , [Passport country of issue]
    , [PEP]
    , [Primary PEP Co of Influence]
    , [Passport_ID Issue Date]
    , [Salutation]
    , [Town of Birth]
    , [Inactive]
    , [Registered No_]
    , [Date of incorp__formation]
    , [Date of Death]
    , [Occupation]
    , [Nationality 2]
    , [Manager]
    , [Administrator]
    , [Employer_Name of Own Company]
    , [Second form of ID]
    , [Tax ID Number]
    , [Legal Status]
)
SELECT
    CASE
        WHEN RM.BA = 1 THEN RM.SearchName
        ELSE RM.[Name]
    END AS [Name]

    , RM.SearchName AS [Search Name]
    , C.BirthDate AS [Date of Birth]
    , NATI.CountryCode AS [Nationality]
    , C.Occupation AS [Profession]
    , RM.KYC_Country2 AS [Domicile]

    , (
        SELECT TOP 1 A.Country FROM CR_RefAddresses AS A
        WHERE A.RefCode = RM.RefCode AND A.AddrType = 'RA' AND A.Active = 1
    ) AS [Residence]

    , RM.Title AS [Title]
    , RM.Initials AS [Name 2]

    , CASE
        WHEN RM.BA = 1 THEN 1
        ELSE 0
    END AS [Entity Type]

    , (
        SELECT TOP 1 IR.UdCode FROM IdentityRegister AS IR
        WHERE IR.IdType = 'FCSC' AND IR.RefCode = RM.RefCode AND IR.Active = 1
    ) AS [FATCA Classification]

    , (
        SELECT TOP 1 IR.UdCode FROM IdentityRegister AS IR
        WHERE IR.IdType = 'FCRS' AND IR.RefCode = RM.RefCode AND IR.Active = 1
    ) AS [CRS Classification]

    ,(
        SELECT TOP 1 DateEffective FROM RefStatus AS S
        WHERE S.NewStat = 'C' AND S.RefCode = RM.RefCode
        ORDER BY S.SeqNr
    ) AS [Date Inactive]

    , C.MaritalStatus AS [Marital Status]
    , RM.Salutation AS [Known As]

    ,(
        SELECT TOP 1 IR.[Description] FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'CTZ' AND IR.Active = 1
    ) AS [Religion]

    ,(
        SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'BCT' AND IR.Active = 1
    ) AS [Country of Birth]

    , CASE
        WHEN C.Gender = 'M' THEN 1
        WHEN C.Gender = 'F' THEN 2
    END AS [Gender]

    , LEFT(RM.Initials, 1) AS [Initials]

    , CASE
        WHEN RM.RefType = 'I' THEN 0
        WHEN RM.RefType <> 'I' THEN 1
    END AS [Personal_Corporate]

    , C.FormerName AS [Former Name]

    , CASE
        WHEN(
            SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
            WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'INC' AND IR.Active = 1
        ) IS NOT NULL
            THEN(
                SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
                WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'INC' AND IR.Active = 1
            )
        ELSE CT.ElCode
    END AS [Country of Incorporation]

    , CASE
        WHEN(
            SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
            WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'INC' AND IR.Active = 1
        ) IS NOT NULL
            THEN(
                SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
                WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'INC' AND IR.Active = 1
            )
        ELSE CT.ElCode
    END AS [Jurisdiction]

    , RM.KYC_Officer AS [Identity Verified By]
    , RM.KYC_Obtained AS [Identity Verified On]

    ,(
        SELECT TOP 1 IR.FromDate FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'REG' AND IR.Active = 1
    ) AS [Regulatory Licence]

    ,(
        SELECT TOP 1 IR.IdCode FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'REG' AND IR.Active = 1
    ) AS [Regulatory Licence Number]

    ,(
        SELECT TOP 1 IR.AdCode FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'REG' AND IR.Active = 1
    ) AS [Regulated Activities]

    , CASE
        WHEN RM.RefType = 'I' AND RM.Title IS NOT NULL THEN CONCAT(RM.Title, ' ', RM.Initials, ' ', RM.[Name])
        WHEN RM.RefType = 'I' AND RM.Title IS NULL THEN CONCAT(RM.Initials, ' ', RM.[Name])
        ELSE RM.[Name]
    END AS [Formal Name]

    ,(
        SELECT TOP 1 BA.SortCode FROM BankAccounts AS BA
        WHERE BA.BankAddrCode = RM.RefCode
    ) AS [Bank Swift Code]

    ,(
        SELECT TOP 1 BA.SortCode FROM BankAccounts AS BA
        WHERE BA.BankAddrCode = RM.RefCode
    ) AS [Bank Sort Code]

    , RM.RefCode AS [External Reference No]

    , CASE
        WHEN(
            SELECT TOP 1 IR.IdCode FROM IdentityRegister AS IR
            WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'REG' AND IR.Active = 1
        ) IS NOT NULL THEN 1
        ELSE 2
    END AS [Regulated Body]

    ,(
        SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'REG' AND IR.Active = 1
    ) AS [Regulatory Jurisdiction]

    , CASE
        WHEN ISNULL(C.IDcardNr, '') <> '' THEN C.IDcardNr
        ELSE(
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE RefCode = RM.RefCode AND IdType = 'IDC' AND Active = 1
        )
    END AS [Passport_ID Number (2)]

    ,(
        SELECT TOP 1 Country FROM IdentityRegister
        WHERE RefCode = RM.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Country (2)]

    ,(
        SELECT TOP 1 ToDate FROM IdentityRegister
        WHERE RefCode = RM.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Expiry Date (2)]

    , CASE
        WHEN ISNULL(C.IDCardDateIssue, '') <> '' THEN C.IDCardDateIssue
        ELSE(
            SELECT TOP 1 FromDate FROM IdentityRegister
            WHERE RefCode = RM.RefCode AND IdType = 'IDC' AND Active = 1
        )
    END AS [Passport_ID Issue Date (2)]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PassportNr
        ELSE(
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE RefCode = RM.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport number]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateExpire
        ELSE(
            SELECT TOP 1 ToDate FROM IdentityRegister
            WHERE RefCode = RM.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport expiry date]

    ,(
        SELECT TOP 1 Country FROM IdentityRegister
        WHERE RefCode = RM.RefCode AND IdType = 'PSP' AND Active = 1
    ) AS [Passport country of issue]

    , CASE
        WHEN EXISTS(
            SELECT IR.IdType FROM IdentityRegister AS IR
            WHERE IR.RefCode = RM.RefCode AND IR.IdType IN('PEPC', 'PEPT') AND IR.Active = 1
        ) THEN 1
        ELSE 0
    END AS [PEP]

    ,(
        SELECT TOP 1 IR.Country FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'PEPT'
    ) AS [Primary PEP Co of Influence]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateIssue
        ELSE(
            SELECT TOP 1 FromDate FROM IdentityRegister
            WHERE RefCode = RM.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport_ID Issue Date]

    , RM.Salutation AS [Salutation]
    , C.PlaceBirth AS [Town of Birth]

    , CASE
        WHEN RL.Active = 0 THEN 1
        ELSE 0
    END AS [Inactive]

    , E.IncorpNr AS [Registered No_]
    , E.IncorpDate AS [Date of incorp__formation]
    , C.DateDeath AS [Date of Death]
    , C.Occupation AS [Occupation]

    , (
        SELECT TOP 1 IR.[Description] FROM IdentityRegister AS IR
        WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'CTZ' AND IR.Active = 1
    ) AS [Nationality 2]

    , E.Admin2Code AS [Manager]
    , E.AdminCode AS [Administrator]

    ,(
        SELECT O.AddrCode
        FROM Officers AS O
        WHERE O.EntCode = RM.RefCode AND O.OfficerType = 'EMR'
    ) AS [Employer_Name of Own Company]

    , CASE
        WHEN RM.RefType = 'I' THEN 'ID Card'
        ELSE NULL
    END AS [Second form of ID]

    ,(
        SELECT TOP 1 IdCode FROM IdentityRegister
        WHERE IdType IN('FIN', 'FIC') AND RefCode = RM.RefCode AND Active = 1 AND LEN(IdCode) <> 0
    ) AS [Tax ID Number]

    , NULL AS [Legal Status]

FROM RefMaster AS RM
LEFT JOIN Entity AS E ON RM.RefCode = E.EntCode
LEFT JOIN Compliance AS C ON RM.RefCode = C.AddrCode
LEFT JOIN RefLabels AS RL ON RM.RefCode = RL.Code
LEFT JOIN LookComboSave AS NATI ON C.Nationality = NATI.SaveName
LEFT JOIN qLvCNTR AS CT ON C.PasPlaceIssue = CT.[Name]
WHERE
    RM.RefCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsEntity = 1
    )

GO
```
