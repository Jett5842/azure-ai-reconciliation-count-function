---
staging_table: MT Resource
etl_script: InsertMtResource.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: No client scope; users selected by activity / link rules
exact_sources: [VpUser]
lookup_sources: [RefMaster (lookup), Compliance (lookup), LookComboSave (lookup), Administrators (lookup), CR_RefAddresses (lookup), IdentityRegister (lookup), RefContacts (lookup), ServiceRates (lookup)]
---
# MT Resource

## Overview
Migrates Vpoint users as Resources (staff): name, search name, address, job title, employment dates, cost and price rates, blocked flag, passport / ID / PEP data, supervisor flag, chargeability target, e-mail, phone numbers and office address. Personal data is looked up from the master file linked to the user (VpUser.RelMfCode).

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtResource.sql` into staging table `[MT Resource]`.

## Scope filter
Self-contained: no fnGetInScopeClients() filter. Users are taken when they are active, or inactive but linked to a master file, or inactive but still used as an administrator code.

## Row count behaviour
One staging row per VpUser row that passes the filter, multiplied by any matching rows of the LEFT JOINs to Administrators (AdActive = 1) and RmClients (AddrCode = RelMfCode); a user with several matching rows in those tables can produce more than one row.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| VpUser | Active users (InActive = 0); inactive users that are linked to a master file (RelMfCode not NULL); inactive users whose user code is still an administrator code on Entity or RmClients. | `FROM VpUser AS U LEFT JOIN Administrators AS A ON U.Ucode = A.Ucode AND A.AdActive = 1 LEFT JOIN RefMaster AS RM ON U.RelMfCode = RM.RefCode LEFT JOIN RmClients AS RC ON U.RelMfCode = RC.AddrCode LEFT JOIN Compliance AS C ON U.RelMfCode = C.AddrCode LEFT JOIN LookComboSave AS NATI ON C.Nationality = NATI.SaveName WHERE U.InActive = 0 OR (U.InActive = 1 AND U.RelMfCode IS NOT NULL) OR (U.InActive = 1 AND U.Ucode IN (SELECT AdminCode FROM Entity UNION SELECT Admin2Code FROM Entity UNION SELECT Admin3Code FROM Entity UNION SELECT AdminCode FROM RmClients UNION SELECT Admin2Code FROM RmClients UNION SELECT Admin3Code FROM RmClients))` | Bring over Resources: active users, users linked to a master file, and administrator codes still in use. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefMaster (lookup) | LEFT JOIN RefMaster ON RefCode = VpUser.RelMfCode | [TWM Title], [TWM Initials], [TWM Full Name], search name and name 2 |
| Compliance (lookup) | LEFT JOIN Compliance ON AddrCode = VpUser.RelMfCode | [TWM Birth Date], [TWM Former Forename(s)], [TWM Former Surname], [TWM Occupation], [TWM Town of Birth], passport fields |
| LookComboSave (lookup) | LEFT JOIN LookComboSave ON SaveName = Compliance.Nationality | [TWM Nationality] |
| Administrators (lookup) | LEFT JOIN Administrators ON Ucode with AdActive = 1 | [Job Title], [Direct Unit Cost], working-unit fields and [TWM Chargeability Target _] |
| CR_RefAddresses (lookup) | Sub-queries (SELECT TOP 1): AddrType = 'RA' AND Cancelled IS NULL AND CardActive = 1 on RefCode = VpUser.RelMfCode | [Address], [Address 2], [City], [County], [Post Code], [Country_Region Code] |
| IdentityRegister (lookup) | Sub-queries (SELECT TOP 1): IdType BCT / PEPT / EP / IDC / PSP with Active = 1 on RefCode = VpUser.RelMfCode | [TWM Country of Birth], [TWM PEP Country of Influence], [TWM EP], [TWM Politically Exposed], [TWM Passport_ID ...] fields |
| RefContacts (lookup) | Sub-queries (SELECT TOP 1): cType TH / TM / FH with cActive = 1 on RefCode = VpUser.RelMfCode | [TWM Phone No_], [TWM Mobile Phone No_], [TWM Fax No_] |
| ServiceRates (lookup) | Sub-query: RateType = 2, RateList = RmClients.RateList and ServCode = Administrators.RateLevel, currency = base currency setting (Settings VPCROSS / BASECU) | [Unit Price] |

## Column mapping highlights
- [Blocked] = VpUser.InActive; [Employment Date] / [TWM Resource Start Date] = DateJoined; [TWM Employment End Date] / [Leaving Date] = DateResign
- [TWM Supervisor] = 1 when another VpUser has this user as Supervisor; [TWM Chargeability Target _] = TargetUnitCharge / TargetUnits * 100
- [TWM Office Address] = office Code of the user's RS / BA / MA / RA address, looked up in [MT Office Address] through the [Temp] key

## Notes for reconciliation
- No fnGetInScopeClients() filter, so the count does not depend on client scope.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtResource'
GO

INSERT INTO [MT Resource]
(
    [NAV_Entry No]
    , [No_]
    , [Type]
    , [Name]
    , [Search Name]
    , [Name 2]
    , [Address]
    , [Address 2]
    , [City]
    , [Social Security No_]
    , [Job Title]
    , [Education]
    , [Contract Class]
    , [Employment Date]
    , [Resource Group No_]
    , [Global Dimension 1 Code]
    , [Global Dimension 2 Code]
    , [Base Unit of Measure]
    , [Direct Unit Cost]
    , [Indirect Cost _]
    , [Unit Cost]
    , [Profit _]
    , [Price_Profit Calculation]
    , [Unit Price]
    , [Vendor No_]
    , [Last Date Modified]
    , [Blocked]
    , [Gen_ Prod_ Posting Group]
    , [Post Code]
    , [County]
    , [Automatic Ext_ Texts]
    , [No_ Series]
    , [Tax Group Code]
    , [VAT Prod_ Posting Group]
    , [Country_Region Code]
    , [IC Partner Purch_ G_L Acc_ No_]
    , [Image]
    , [Privacy Blocked]
    , [Coupled to CRM]
    , [Use Time Sheet]
    , [Time Sheet Owner User ID]
    , [Time Sheet Approver User ID]
    , [Default Deferral Template Code]
    , [Service Zone Filter]
    , [TWM Hours Worked]
    , [TWM Business Unit Code]
    , [TWM Timezone Adjustment]
    , [TWM Country of Birth]
    , [TWM Town of Birth]
    , [TWM Politically Exposed]
    , [TWM PEP Country of Influence]
    , [TWM EP]
    , [TWM External Reference No]
    , [TWM Ext_ HR Employee No_]
    , [TWM Cert_ Copy of Passport_ID]
    , [TWM First Reference]
    , [TWM First Ref_ Requested Date]
    , [TWM First Ref_ Received Date]
    , [TWM Second Reference]
    , [TWM Second Ref_ Requested Date]
    , [TWM Second Ref_ Received Date]
    , [TWM Second form of ID]
    , [TWM Regulatory Licence Number]
    , [TWM Regulatory Licence]
    , [TWM Regulat Licence Granted By]
    , [TWM Regulated Activities]
    , [TWM Face to Face Meeting]
    , [TWM Identity Verified By]
    , [TWM Identity Verified On]
    , [TWM Identity Verified Using]
    , [TWM Address Verified By (1)]
    , [TWM Address Verified On (1)]
    , [TWM Address Verified using (1)]
    , [TWM Photographic ID]
    , [TWM Photographic ID Desc_]
    , [TWM Address Verified By (2)]
    , [TWM Address Verified On (2)]
    , [TWM Address Verified Using (2)]
    , [TWM First Reference Status]
    , [TWM Second Reference Status]
    , [TWM Cert_ Regulatory Licence]
    , [TWM Cert_ Evidence of Listing]
    , [TWM Speciman Signature Recd]
    , [TWM Signature Authenticated]
    , [TWM Passport_ID Number (2)]
    , [TWM Passport_ID Country (2)]
    , [TWM Passport_ID Exp_ Date (2)]
    , [TWM Cert_ Copy Passport_ID (2)]
    , [TWM Certified Date (2)]
    , [TWM Passport_ID Issue Date (2)]
    , [TWM Partition Group]
    , [TWM Use Partit Group S_filter]
    , [TWM Exclude Country Search]
    , [TWM Passport number]
    , [TWM Passport expiry date]
    , [TWM Passport country of issue]
    , [TWM Certified Date]
    , [TWM Passport_ID Issue Date]
    , [TWM Units - Monday]
    , [TWM Units - Tuesday]
    , [TWM Units - Wednesday]
    , [TWM Units - Thursday]
    , [TWM Units - Friday]
    , [TWM Daily Breakdown Required]
    , [TWM ResShortcutDimension1]
    , [TWM ResShortcutDimension2]
    , [TWM Available Units]
    , [TWM Supervisor]
    , [TWM Timesheet Validation]
    , [TWM Chargeability Target _]
    , [TWM Entity No_]
    , [TWM Login User ID]
    , [TWM Email Address]
    , [TWM View]
    , [TWM Birth Date]
    , [TWM Occupation]
    , [TWM Nationality]
    , [TWM Initials]
    , [TWM Full Name]
    , [TWM Title]
    , [TWM Budgeted Time Percentage]
    , [TWM CPD Allocation]
    , [TWM Former Surname]
    , [TWM Former Forename(s)]
    , [TWM Former Initials]
    , [TWM Office Address]
    , [TWM Authorisation Password]
    , [TWM Password Date]
    , [TWM Phone No_]
    , [TWM Mobile Phone No_]
    , [TWM Fax No_]
    , [TWM E-Mail]
    , [TWM Known As]
    , [TWM Job Jnl Template]
    , [TWM Job Jnl Batch]
    , [TWM Authorisation Level]
    , [TWM Authorisation Super User]
    , [TWM Billing Authoriser]
    , [TWM Fixed Deposit Authoriser]
    , [TWM Employment End Date]
    , [TWM Resource Start Date]
    , [TWM Resource Leaving Date]
    , [TWM Business Group]
    , [TWM Resource Group Level]
    , [TWM Statutory Reference]
    , [TWM Old User ID]
    , [TWM Inv_ Authorisation Level]
    , [TWM Inv_ Auth_ Super User]
    , [TWM Email Account Connector]
    , [TWM Email Account ID]
    , [TWM Email Account Name]
    , [TWM Auth_ Level Practice]
    , [TWM Partitioning Hash]
    , [TWM First Name]
    , [TWM Middle Name]
    , [TWM Unit Number]
    , [TWM Floor Number]
    , [TWM Block]
    , [TWM Building Name]
    , [TWM Street]
    , [TWM Village]
    , [TWM District]
    , [TWM Has Structured Address]
    , [TWM Formal Name Format]
    , [TWM Formal Name]
    , [TWM Gender]
    , [TWM Nationality of Origin]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY U.Ucode ASC) AS [NAV_Entry No]
    , U.Ucode AS [No_]
    , 0 AS [Type]
    , U.Uname AS [Name]

    , CASE
        WHEN U.RelMfCode IS NOT NULL THEN RM.SearchName
        ELSE U.Uname
    END AS [Search Name]

    , CASE
        WHEN U.RelMfCode IS NOT NULL THEN RM.Initials
        ELSE U.Uname
    END AS [Name 2]

    ,(
        SELECT TOP 1
            CASE
                WHEN A.Address2 IS NOT NULL THEN CONCAT(A.[Address], A.Address2)
                ELSE A.[Address]
            END AS [Address]
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [Address]

    ,(
        SELECT
            CONCAT(
                A.Address3
                , CASE
                    WHEN A.Address4 IS NOT NULL AND A.Address4 <> '' THEN CONCAT(', ', A.Address4)
                    ELSE ''
                END
                , CASE
                    WHEN A.Address5 IS NOT NULL AND A.Address5 <> '' THEN CONCAT(', ', A.Address5)
                    ELSE ''
                END
            )
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [Address 2]

    ,(
        SELECT TOP 1 A.City
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [City]

    , NULL AS [Social Security No_]
    , A.Title AS [Job Title]
    , NULL AS [Education]
    , NULL AS [Contract Class]
    , U.DateJoined AS [Employment Date]
    , NULL AS [Resource Group No_] --UG.[Name] AS [Resource Group No_]
    , NULL AS [Global Dimension 1 Code]
    , NULL AS [Global Dimension 2 Code]
    , 'Unit' AS [Base Unit of Measure]
    , A.UnitCost AS [Direct Unit Cost]
    , NULL AS [Indirect Cost _]
    , NULL AS [Unit Cost]
    , NULL AS [Profit _]
    , NULL AS [Price_Profit Calculation]

    ,(
        SELECT TOP 1 SR.UnitPrice
        FROM ServiceRates AS SR
        INNER JOIN Settings AS S ON SR.CurCode = S.SetStr AND APname = 'VPCROSS' AND SETKEY = 'BASECU'
        WHERE SR.RateList = RC.RateList AND SR.ServCode = A.RateLevel AND SR.RateType = 2
    ) AS [Unit Price]

    , NULL AS [Vendor No_]
    , NULL AS [Last Date Modified]
    , U.InActive AS [Blocked]
    , 'GEN' AS [Gen_ Prod_ Posting Group]

    ,(
        SELECT TOP 1 A.PostalCode
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [Post Code]

    ,(
        SELECT TOP 1 A.[State]
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [County]

    , NULL AS [Automatic Ext_ Texts]
    , NULL AS [No_ Series]
    , NULL AS [Tax Group Code]
    , NULL AS [VAT Prod_ Posting Group]

    , (
        SELECT TOP 1 A.Country
        FROM CR_RefAddresses AS A
        WHERE A.AddrType = 'RA' AND A.RefCode = U.RelMfCode AND A.Cancelled IS NULL AND A.CardActive = 1
    ) AS [Country_Region Code]

    , NULL AS [IC Partner Purch_ G_L Acc_ No_]
    , NULL AS [Image] --U.ProfilePicture AS [Image] -- TODO:
    , NULL AS [Privacy Blocked]
    , NULL AS [Coupled to CRM]
    , 1 AS [Use Time Sheet]
    , NULL AS [Time Sheet Owner User ID] --U.Ucode AS [Time Sheet Owner User ID]
    , NULL AS [Time Sheet Approver User ID] --U.SuperVisor AS [Time Sheet Approver User ID]
    , NULL AS [Default Deferral Template Code]
    , NULL AS [Service Zone Filter]
    , NULL AS [TWM Hours Worked]
    , NULL AS [TWM Business Unit Code]
    , NULL AS [TWM Timezone Adjustment]

    , (
        SELECT TOP 1 IR.Country
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'BCT' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM Country of Birth]

    , C.PlaceBirth AS [TWM Town of Birth]

    , CASE
        WHEN EXISTS(
            SELECT IR.IdType FROM IdentityRegister AS IR
            WHERE IR.IdType = 'PEPT' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
        ) THEN 1
        ELSE 0
    END AS [TWM Politically Exposed]

    , (
        SELECT TOP 1 IR.Country
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'PEPT' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM PEP Country of Influence]

    , CASE
        WHEN EXISTS(
            SELECT IR.IdType FROM IdentityRegister AS IR
            WHERE IR.IdType = 'EP' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
        ) THEN 1
        ELSE 0
    END AS [TWM EP]

    , U.Ucode AS [TWM External Reference No]
    , NULL AS [TWM Ext_ HR Employee No_]
    , NULL AS [TWM Cert_ Copy of Passport_ID]
    , NULL AS [TWM First Reference]
    , NULL AS [TWM First Ref_ Requested Date]
    , NULL AS [TWM First Ref_ Received Date]
    , NULL AS [TWM Second Reference]
    , NULL AS [TWM Second Ref_ Requested Date]
    , NULL AS [TWM Second Ref_ Received Date]
    , NULL AS [TWM Second form of ID]
    , NULL AS [TWM Regulatory Licence Number]
    , NULL AS [TWM Regulatory Licence]
    , NULL AS [TWM Regulat Licence Granted By]
    , NULL AS [TWM Regulated Activities]
    , NULL AS [TWM Face to Face Meeting]
    , NULL AS [TWM Identity Verified By]
    , NULL AS [TWM Identity Verified On]
    , NULL AS [TWM Identity Verified Using]
    , NULL AS [TWM Address Verified By (1)]
    , NULL AS [TWM Address Verified On (1)]
    , NULL AS [TWM Address Verified using (1)]
    , NULL AS [TWM Photographic ID]
    , NULL AS [TWM Photographic ID Desc_]
    , NULL AS [TWM Address Verified By (2)]
    , NULL AS [TWM Address Verified On (2)]
    , NULL AS [TWM Address Verified Using (2)]
    , NULL AS [TWM First Reference Status]
    , NULL AS [TWM Second Reference Status]
    , NULL AS [TWM Cert_ Regulatory Licence]
    , NULL AS [TWM Cert_ Evidence of Listing]
    , NULL AS [TWM Speciman Signature Recd]
    , NULL AS [TWM Signature Authenticated]

    ,(
        SELECT TOP 1 IR.IdCode
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'IDC' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM Passport_ID Number (2)]

    , (
        SELECT TOP 1 IR.Country
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'IDC' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM Passport_ID Country (2)]

    ,(
        SELECT TOP 1 IR.ToDate
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'IDC' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM Passport_ID Exp_ Date (2)]

    , NULL AS [TWM Cert_ Copy Passport_ID (2)]
    , NULL AS [TWM Certified Date (2)]

    ,(
        SELECT TOP 1 IR.FromDate
        FROM IdentityRegister AS IR
        WHERE IR.IdType = 'IDC' AND IR.RefCode = U.RelMfCode AND IR.Active = 1
    ) AS [TWM Passport_ID Issue Date (2)]

    , NULL AS [TWM Partition Group]
    , NULL AS [TWM Use Partit Group S_filter]
    , NULL AS [TWM Exclude Country Search]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PassportNr
        ELSE(
            SELECT TOP 1 IdCode FROM IdentityRegister AS IR
            WHERE IR.RefCode = U.RelMfCode AND IR.IdType = 'PSP' AND IR.Active = 1
        )
    END AS [TWM Passport number]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateExpire
        ELSE(
            SELECT TOP 1 ToDate FROM IdentityRegister AS IR
            WHERE IR.RefCode = U.RelMfCode AND IR.IdType = 'PSP' AND IR.Active = 1
        )
    END AS [TWM Passport expiry date]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> ''
            THEN(
                SELECT TOP 1 Country FROM IdentityRegister AS IR
                WHERE IR.RefCode = U.RelMfCode AND IR.IdType = 'PSP' AND IR.Active = 1 AND IdCode = C.PassportNr
            )
        ELSE(
            SELECT TOP 1 Country FROM IdentityRegister AS IR
            WHERE IR.RefCode = U.RelMfCode AND IR.IdType = 'PSP' AND IR.Active = 1
        )
    END AS [TWM Passport country of issue]

    , NULL AS [TWM Certified Date]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateIssue
        ELSE(
            SELECT TOP 1 FromDate FROM IdentityRegister AS IR
            WHERE IR.RefCode = U.RelMfCode AND IR.IdType = 'PSP' AND IR.Active = 1
        )
    END AS [TWM Passport_ID Issue Date]

    , A.TargetUnits AS [TWM Units - Monday]
    , A.TargetUnits AS [TWM Units - Tuesday]
    , A.TargetUnits AS [TWM Units - Wednesday]
    , A.TargetUnits AS [TWM Units - Thursday]
    , A.TargetUnits AS [TWM Units - Friday]
    , 1 AS [TWM Daily Breakdown Required]
    , NULL AS [TWM ResShortcutDimension1]
    , NULL AS [TWM ResShortcutDimension2]
    , A.WkTarget AS [TWM Available Units]

    , CASE
        WHEN(
            SELECT COUNT(*) FROM VpUser
            WHERE Supervisor = U.Ucode
        ) > 0 THEN 1
        ELSE 0
    END AS [TWM Supervisor]

    , 1 AS [TWM Timesheet Validation]
    , A.TargetUnitCharge / NULLIF(A.TargetUnits, 0) * 100 AS [TWM Chargeability Target _]
    , NULL AS [TWM Entity No_]
    , NULL AS [TWM Login User ID]
    , U.MailID AS [TWM Email Address]
    , NULL AS [TWM View]
    , C.BirthDate AS [TWM Birth Date]
    , C.Occupation AS [TWM Occupation]
    , NATI.CountryCode AS [TWM Nationality]
    , RM.Initials AS [TWM Initials]
    , RM.[Name] AS [TWM Full Name]
    , RM.Title AS [TWM Title]
    , NULL AS [TWM Budgeted Time Percentage]
    , NULL AS [TWM CPD Allocation]
    , C.FormerName AS [TWM Former Surname]
    , C.FormerGivenNames AS [TWM Former Forename(s)]
    , NULL AS [TWM Former Initials]

    ,(
        SELECT TOP 1 O.Code
        FROM RefAddress AS A
        LEFT JOIN [MT Office Address] AS O
            ON
                (
                    (
                        (
                            SELECT TOP 1 C.cText
                            FROM RefContacts AS C
                            WHERE A.RefCode = C.RefCode AND C.cType IN('TB', 'FB', 'EB', 'WB')
                        ) IS NULL
                        AND CONCAT(A.AddrNr, 'GEN') = O.Temp
                    )
                    OR
                    (
                        (
                            SELECT TOP 1 C.cText
                            FROM RefContacts AS C
                            WHERE A.RefCode = C.RefCode AND C.cType IN('TB', 'FB', 'EB', 'WB')
                        ) IS NOT NULL
                        AND CONCAT(A.AddrNr, A.RefCode) = O.Temp
                    )
                )
        WHERE A.RefCode = U.RelMfCode AND A.Active = 1 AND AddrType IN('RS', 'BA', 'MA', 'RA')
        ORDER BY
            CASE A.AddrType
                WHEN 'RS' THEN 1
                WHEN 'BA' THEN 2
                WHEN 'MA' THEN 3
                WHEN 'RA' THEN 4
            END
    ) AS [TWM Office Address]

    , NULL AS [TWM Authorisation Password]
    , NULL AS [TWM Password Date]

    ,(
        SELECT TOP 1 C.cText
        FROM RefContacts AS C
        WHERE C.cType = 'TH' AND C.RefCode = U.RelMfCode AND C.cActive = 1
    ) AS [TWM Phone No_]

    ,(
        SELECT TOP 1 C.cText
        FROM RefContacts AS C
        WHERE C.cType = 'TM' AND C.RefCode = U.RelMfCode AND C.cActive = 1
    ) AS [TWM Mobile Phone No_]

    ,(
        SELECT TOP 1 C.cText
        FROM RefContacts AS C
        WHERE C.cType = 'FH' AND C.RefCode = U.RelMfCode AND C.cActive = 1
    ) AS [TWM Fax No_]

    , U.MailID AS [TWM E-Mail]
    , NULL AS [TWM Known As]
    , NULL AS [TWM Job Jnl Template]
    , NULL AS [TWM Job Jnl Batch]
    , NULL AS [TWM Authorisation Level]
    , NULL AS [TWM Authorisation Super User]
    , NULL AS [TWM Billing Authoriser]
    , NULL AS [TWM Fixed Deposit Authoriser]
    , U.DateResign AS [TWM Employment End Date]
    , U.DateJoined AS [TWM Resource Start Date]
    , U.DateResign AS [TWM Resource Leaving Date]
    , NULL AS [TWM Business Group] --U.Ugroup AS [TWM Business Group]
    , NULL AS [TWM Resource Group Level]
    , NULL AS [TWM Statutory Reference]
    , NULL AS [TWM Old User ID]
    , NULL AS [TWM Inv_ Authorisation Level]
    , NULL AS [TWM Inv_ Auth_ Super User]
    , NULL AS [TWM Email Account Connector]
    , NULL AS [TWM Email Account ID]
    , NULL AS [TWM Email Account Name]
    , NULL AS [TWM Auth_ Level Practice]
    , NULL AS [TWM Partitioning Hash]
    , NULL AS [TWM First Name]
    , NULL AS [TWM Middle Name]
    , NULL AS [TWM Unit Number]
    , NULL AS [TWM Floor Number]
    , NULL AS [TWM Block]
    , NULL AS [TWM Building Name]
    , NULL AS [TWM Street]
    , NULL AS [TWM Village]
    , NULL AS [TWM District]
    , NULL AS [TWM Has Structured Address]
    , NULL AS [TWM Formal Name Format]
    , NULL AS [TWM Formal Name]
    , NULL AS [TWM Gender]
    , NULL AS [TWM Nationality of Origin]

FROM VpUser AS U
LEFT JOIN Administrators AS A ON U.Ucode = A.Ucode AND A.AdActive = 1
LEFT JOIN RefMaster AS RM ON U.RelMfCode = RM.RefCode
LEFT JOIN RmClients AS RC ON U.RelMfCode = RC.AddrCode
LEFT JOIN Compliance AS C ON U.RelMfCode = C.AddrCode
LEFT JOIN LookComboSave AS NATI ON C.Nationality = NATI.SaveName
WHERE
    U.InActive = 0
    OR(U.InActive = 1 AND U.RelMfCode IS NOT NULL)
    OR(
        U.InActive = 1 AND U.Ucode IN(
            SELECT AdminCode FROM Entity
            UNION
            SELECT Admin2Code FROM Entity
            UNION
            SELECT Admin3Code FROM Entity
            UNION
            SELECT AdminCode FROM RmClients
            UNION
            SELECT Admin2Code FROM RmClients
            UNION
            SELECT Admin3Code FROM RmClients
        )
    )

GO
```
