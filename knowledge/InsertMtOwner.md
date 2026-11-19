---
staging_table: MT Owner
etl_script: InsertMtOwner.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: Owner linked to a client with IsClient = 1
exact_sources: [1) EntityOwners, 2) EntityOwners + Officers, 3) EntityOwners + Share_Interests, 4) Share_Interests, 5) Share_Interests + Officers, 6) Officers, 7) EntityOwners + Share_Interests + Officers]
lookup_sources: [Entity (lookup), Compliance (lookup), LookComboSave (lookup), IdentityRegister (lookup), RefAddress (lookup), Officers (lookup)]
---
# MT Owner

## Overview
Migrates the Owner Master Files: individuals ('PER') and companies ('COMP') that own, benefit from or administer in-scope clients. Personal data, identification and passport details, PEP / political connections, tax ID, regulatory licence, KYC status, administrator / manager and admin office are all populated from Vpoint lookups.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtOwner.sql` into staging table `[MT Owner]`.

## Scope filter
The owner must be linked (through EntityOwners, Share_Interests BEO or Officers ADM) to an in-scope client: `Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`. The owner must also exist in RefLabels (INNER JOIN).

## Row count behaviour
SELECT DISTINCT over the full output row, so one staging row per owner (an owner linked to several clients still counts once). Owners are discovered through three sources joined with UNION; the reconciliation reports each owner under the exact combination of sources that found it.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| 1) EntityOwners | Owner found only in EntityOwners. | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 2) EntityOwners + Officers | Owner found in EntityOwners and Officers (ADM) but not Share_Interests. | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 3) EntityOwners + Share_Interests | Owner found in EntityOwners and Share_Interests (BEO) but not Officers. | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 4) Share_Interests | Owner found only in Share_Interests (IntType BEO). | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 5) Share_Interests + Officers | Owner found in Share_Interests (BEO) and Officers (ADM) but not EntityOwners. | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 6) Officers | Owner found only in Officers (OfficerType ADM). | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |
| 7) EntityOwners + Share_Interests + Officers | Owner found in all three sources. | `FROM RefMaster AS R LEFT JOIN Entity AS E ... LEFT JOIN Compliance AS C ... INNER JOIN RefLabels AS L ON R.RefCode = L.Code INNER JOIN (SELECT EntCode, RefCode FROM EntityOwners UNION SELECT EntCode, AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT EntCode, AddrCode FROM Officers WHERE OfficerType = 'ADM') AS Z ON R.RefCode = Z.RefCode WHERE Z.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner qualifies through exactly this combination of sources; the owner must exist in RefMaster and RefLabels. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Entity (lookup) | LEFT JOIN Entity ON EntCode = RefMaster.RefCode | [Administrator], [Manager], [Type of Business], incorporation date / place / number (before the IdentityRegister fallback) |
| Compliance (lookup) | LEFT JOIN Compliance ON AddrCode = RefMaster.RefCode | [Date of Birth], [Date of Death], [Gender], [Marital Status], [Profession] |
| LookComboSave (lookup) | Sub-query ON SaveName = Compliance.Nationality | [Nationality], [Nationality 2], [Country of Birth] |
| IdentityRegister (lookup) | Sub-queries (SELECT TOP 1): IdType BCT / PSP / INC / REG / IDC / FIN / FIC / PEPT / PEPC / CTZ with Active = 1 (PEPT / PEPC have no Active filter) on RefCode | [Town of Birth], [Registered No_], [Country of Incorporation], [Date of incorp__formation], [Jurisdiction], [Regulatory Licence], [Regulatory Licence Number], [Passport_ID Number/Country/Issue/Expiry (2)], [Political Connections], [Primary PEP Co of Influence], [Tax ID Number] |
| RefAddress (lookup) | Sub-query (SELECT TOP 1) with Active = 1: AddrType RS / RO / BA / MA (in that priority); the office Code is found in [MT Office Address] through the [Temp] key | [Admin Office] |
| Officers (lookup) | Sub-query: RelClass = 'M' AND OfficerType = 'EMR' AND EntCode = RefCode | [Employer_Name of Own Company] |

## Column mapping highlights
- [Type] = 'PER' for individuals (RefType 'I') else 'COMP'; [Owner Type] = 0 individual / 1 corporate
- [Initial Risk Assessment]: KYC_RiskGroup 'H' -> 3, '05' -> 2, '01' -> 1, else 0
- [Closed] = 0 when RefLabels.Active = 1 else 1; [Legal status] derived from Compliance.Occupation text; [Entity No_] = RefCode only when the owner is also an in-scope Entity

## Post-insert updates
- UPDATE [Dual Nationality] = 1 when both [Nationality] and [Nationality 2] are filled, = 0 when [Nationality 2] is NULL

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtOwner'
GO

INSERT INTO [MT Owner]
(
    [No_]
    , [Surname]
    , [Search Name]
    , [Forename(s)]
    , [Type]
    , [Suffix]
    , [Anonimised Name]
    , [Territory Code]
    , [Currency Code]
    , [Last Date Modified]
    , [Last Review Completed]
    , [Next Review Due]
    , [Review Scheduled Completion]
    , [No_ Series]
    , [Status Code]
    , [Include in Campaigns]
    , [Market Groups]
    , [Date of Birth]
    , [Date of marriage]
    , [English speaking]
    , [Marital Status]
    , [Profession]
    , [Residence for Tax Purposes]
    , [Domicile]
    , [Politically Exposed]
    , [Head Office Aware]
    , [Relationship Manager]
    , [Date Created]
    , [Title]
    , [Nationality]
    , [Investment base currency]
    , [Investment risk attitude]
    , [Investment objectives]
    , [Country of Birth]
    , [1st_ Language]
    , [Gender]
    , [Passport number]
    , [Passport expiry date]
    , [Passport country of issue]
    , [Second form of ID]
    , [First Reference]
    , [Second Reference]
    , [Mothers Maiden Name]
    , [Spouse_partner]
    , [Administrator]
    , [Product Provided]
    , [Passport_ID Issue Date]
    , [Ext_ Relationship Manager]
    , [Green Card Holder]
    , [Commission Payable]
    --,[Introduced by No_]
    , [Business Gained From]
    , [Introduced by Contact]
    , [Endorsement Letter]
    , [Source of initial funds]
    , [Special instructions]
    , [Password]
    , [Communication with client]
    , [Fax indemnity held]
    , [Codeword System]
    , [Endorsement Letter Dated]
    , [Telephone Indemnity Held]
    , [Estimated Fees]
    , [Estimated AUM]
    , [Initial Risk Assessment]
    , [Initial Complexity Assessment]
    , [Relationship Manager 2]
    , [Face to Face Meeting]
    , [Date of incorp__formation]
    , [Jurisdiction]
    , [Memo & Articles of Association]
    , [Certificate of Incorporation]
    , [Partnership Agreement]
    , [Register of Members]
    , [Certificate of Good Standing]
    , [Certificate of Trading]
    , [Regulatory Licence]
    , [Regulatory Licence Granted By]
    , [Legal status]
    , [Client Agreement Dated]
    , [Country of Incorporation]
    , [Identity Verified By]
    , [Identity Verified On]
    , [Identity Verified Using]
    , [Regulatory Licence Number]
    , [Regulated Activities]
    , [Company Class]
    , [Country of Initial funds]
    , [Register of Directors]
    , [Extract of Trust Deed]
    , [Letter from Trustee]
    , [Certificate of Registration]
    , [Register of General Partners]
    , [Register of Limited Partners]
    , [Foundation Charter]
    , [Listed Company]
    , [Certified Copy of Latest Acc_]
    , [Company Registry]
    , [Owner Type]
    , [Date KYC Signed Off]
    , [Closed]
    , [KYC Status]
    , [Political Connections]
    , [Client Profile]
    , [High Risk National]
    , [Establishment Questionnaire]
    , [New Client Authorisation Form]
    , [Cert_ Copy of Passport or ID]
    , [Uncert_ Copy of Passport or ID]
    , [1st Independent Reference]
    , [2nd Independent Reference]
    , [Conf_ of Residential Address]
    , [Entity No_]
    , [Initials]
    , [Date of Death]
    , [Director]
    , [Communication Details]
    , [Other Communication Frequency]
    , [Communication Frequency]
    , [Estimated Fees Currency]
    , [Estimated AUM Currency]
    , [First Ref_ Requested Date]
    , [First Ref_ Received Date]
    , [Second Ref_ Requested Date]
    , [Second Ref_ Received Date]
    , [Address Verified By (1)]
    , [Address Verified On (1)]
    , [Date Agreement Sent]
    , [Date Agreement Received]
    , [Address Verified Using (1)]
    , [Photographic ID]
    , [Photographic ID Description]
    , [Address Verified By (2)]
    , [Address Verified On (2)]
    , [Address Verified Using (2)]
    , [First Reference Status]
    , [Second Reference Status]
    , [Certified Regulatory Licence]
    , [Certified Evidence of Listing]
    , [Specimen Signature Received]
    , [Signature Authenticated]
    , [Maj_ Sharehold_ of Third Party]
    , [Regulated Body]
    , [Regulatory Jurisdiction]
    , [Passport_ID Number (2)]
    , [Passport_ID Country (2)]
    , [Passport_ID Expiry Date (2)]
    , [Cert_ Copy of Passport_ID (2)]
    , [Certified Date (2)]
    , [2nd Residence for Tax Purpose]
    , [Expatriate of]
    , [Date of Expatriate]
    , [Passport_ID Issue Date (2)]
    , [Initial Fees Currency]
    , [Estimated Initial Fees]
    , [Tax ID Number]
    , [Registered No_]
    , [Classification]
    , [Exclude from Scrutiny]
    , [Modified For Scrutiny Search]
    , [Exclude from Country Search]
    , [Primary PEP Co of Influence]
    , [Global Market Country Code]
    , [Type of Business]
    , [In scope for EUSTD]
    , [In Scope Manually Entered]
    , [Reason for manual entry]
    , [Date last status change]
    , [EUSTD Preference]
    , [Town of Birth]
    , [Salutation]
    , [Hold Mail]
    , [Description of Tax Structure]
    , [Last Tax Review]
    , [Tax Status]
    , [Other Relation_ Within Group]
    , [Employment Status]
    , [External Reference No_]
    , [Sanctioned]
    , [First Partition Code]
    , [Second Partition Code]
    , [Data Protection Level]
    , [Attribution of Introduction]
    , [Admin Office]
    , [Fiduciary_Trustee]
    , [View]
    , [Nationality 2]
    , [Dual Nationality]
    , [E-mail Indemnity Held]
    , [Audited Accounts Received]
    , [Certified Date]
    , [Trust Date Executed]
    , [Type of Deed]
    , [Reference]
    , [Manager]
    , [Formal Name]
    , [Service Tier]
    , [Sensitive Country Connection]
    , [EP]
    , [Position]
    , [Employer_Name of Own Company]
    , [Risk Sector]
    , [Approx_ Income Per Year]
    , [Approx Net Worth]
    , [Known by introducer since]
    , [Introduction Date]
    , [Next Date of Communication]
    , [Power of Attorney Held]
    , [Power of Attorney]
    , [Type of Power of Attorney]
)
SELECT DISTINCT
    NULL AS [No_]
    , R.Name AS [Surname]
    , R.SearchName AS [Search Name]
    , R.Initials AS [Forename(s)]
    , CASE WHEN R.RefType = 'I' THEN 'PER' ELSE 'COMP' END AS [Type]
    , NULL AS [Suffix]
    , NULL AS [Anonimised Name]
    , NULL AS [Territory Code]
    , NULL AS [Currency Code]
    , NULL AS [Last Date Modified]
    , NULL AS [Last Review Completed]
    , NULL AS [Next Review Due]
    , NULL AS [Review Scheduled Completion]
    , NULL AS [No_ Series]
    , NULL AS [Status Code]
    , NULL AS [Include in Campaigns]
    , NULL AS [Market Groups]
    , FORMAT(C.BirthDate, 'yyyy-MM-dd') AS [Date of Birth]
    , NULL AS [Date of marriage]
    , NULL AS [English speaking]
    , C.MaritalStatus AS [Marital Status]
    , C.Occupation AS [Profession]
    , NULL AS [Residence for Tax Purposes]
    , R.KYC_Country2 AS [Domicile]

    , CASE
        WHEN ISNULL((
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'PEPT'
        ), '') = '' THEN 0
        ELSE 1
    END AS [Politically Exposed]

    , NULL AS [Head Office Aware]
    , NULL AS [Relationship Manager]
    , NULL AS [Date Created]
    , R.Title AS [Title]

    , (
        SELECT CountryCode FROM LookComboSave
        WHERE SaveName = C.Nationality
    ) AS [Nationality]

    , NULL AS [Investment base currency]
    , NULL AS [Investment risk attitude]
    , NULL AS [Investment objectives]

    , (
        SELECT TOP 1 Country FROM IdentityRegister
        WHERE IdType = 'BCT' AND RefCode = R.RefCode
    ) AS [Country of Birth]

    , NULL AS [1st_ Language]
    , C.Gender AS [Gender]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PassportNr
        ELSE(
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport number]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateExpire
        ELSE(
            SELECT TOP 1 ToDate FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport expiry date]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> ''
            THEN(
                SELECT Country FROM IdentityRegister
                WHERE RefCode = R.RefCode AND IdType = 'PSP' AND Active = 1 AND IdCode = C.PassportNr
            )
        ELSE(
            SELECT TOP 1 Country FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport country of issue]

    , NULL AS [Second form of ID]
    , NULL AS [First Reference]
    , NULL AS [Second Reference]
    , NULL AS [Mothers Maiden Name]
    , NULL AS [Spouse_partner]
    , E.AdminCode AS [Administrator]
    , NULL AS [Product Provided]

    , CASE
        WHEN ISNULL(C.PassportNr, '') <> '' THEN C.PasDateIssue
        ELSE(
            SELECT TOP 1 FromDate FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'PSP' AND Active = 1
        )
    END AS [Passport_ID Issue Date]

    , NULL AS [Ext_ Relationship Manager]
    , NULL AS [Green Card Holder]
    , NULL AS [Commission Payable]
    --,NULL AS [Introduced by No_]
    , NULL AS [Business Gained From]
    , NULL AS [Introduced by Contact]
    , NULL AS [Endorsement Letter]
    , R.KCY_SourceFunds AS [Source of initial funds]
    , NULL AS [Special instructions]
    , NULL AS [Password]
    , NULL AS [Communication with client]
    , NULL AS [Fax indemnity held]
    , NULL AS [Codeword System]
    , NULL AS [Endorsement Letter Dated]
    , NULL AS [Telephone Indemnity Held]
    , NULL AS [Estimated Fees]
    , NULL AS [Estimated AUM]

    , CASE
        WHEN R.KYC_RiskGroup = 'H' THEN 3
        WHEN R.KYC_RiskGroup = '05' THEN 2
        WHEN R.KYC_RiskGroup = '01' THEN 1
        ELSE 0
    END AS [Initial Risk Assessment]

    , NULL AS [Initial Complexity Assessment]
    , NULL AS [Relationship Manager 2]
    , NULL AS [Face to Face Meeting]

    , ISNULL(
        E.IncorpDate
        ,(
            SELECT TOP 1 FromDate FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'INC' AND Active = 1
        )
    ) AS [Date of incorp__formation]

    , ISNULL(
        E.IncorpPlace
        ,(
            SELECT TOP 1 Country FROM IdentityRegister
            WHERE IdType = 'INC' AND RefCode = R.RefCode AND Active = 1
        )
    ) AS [Jurisdiction]

    , NULL AS [Memo & Articles of Association]
    , NULL AS [Certificate of Incorporation]
    , NULL AS [Partnership Agreement]
    , NULL AS [Register of Members]
    , NULL AS [Certificate of Good Standing]
    , NULL AS [Certificate of Trading]

    ,(
        SELECT TOP 1 FromDate FROM IdentityRegister
        WHERE IdType = 'REG' AND RefCode = R.RefCode AND Active = 1
    ) AS [Regulatory Licence]

    , NULL AS [Regulatory Licence Granted By]

    , CASE
        WHEN C.Occupation = 'Trust' THEN 1
        WHEN C.Occupation = 'Partnership' THEN 2
        WHEN C.Occupation = 'Private Limited Company' THEN 5
        WHEN C.Occupation = 'Limited Liability Company' THEN 6
        WHEN C.Occupation = 'Limited Partnership' THEN 7
        WHEN C.Occupation = 'Public Company' THEN 8
        WHEN C.Occupation = 'Foundation' THEN 9
        ELSE 0
    END AS [Legal status]

    , NULL AS [Client Agreement Dated]

    , ISNULL(
        E.IncorpPlace
        ,(
            SELECT TOP 1 Country FROM IdentityRegister
            WHERE IdType = 'INC' AND RefCode = R.RefCode AND Active = 1
        )
    ) AS [Country of Incorporation]

    , R.KYC_Officer AS [Identity Verified By]
    , R.KYC_Obtained AS [Identity Verified On]
    , NULL AS [Identity Verified Using]

    ,(
        SELECT TOP 1 IdCode FROM IdentityRegister
        WHERE IdType = 'REG' AND RefCode = R.RefCode AND Active = 1
    ) AS [Regulatory Licence Number]

    ,(
        SELECT TOP 1 AdCode FROM IdentityRegister
        WHERE IdType = 'REG' AND RefCode = R.RefCode AND Active = 1
    ) AS [Regulated Activities]

    , NULL AS [Company Class]
    , NULL AS [Country of Initial funds]
    , NULL AS [Register of Directors]
    , NULL AS [Extract of Trust Deed]
    , NULL AS [Letter from Trustee]
    , NULL AS [Certificate of Registration]
    , NULL AS [Register of General Partners]
    , NULL AS [Register of Limited Partners]
    , NULL AS [Foundation Charter]
    , NULL AS [Listed Company]
    , NULL AS [Certified Copy of Latest Acc_]
    , NULL AS [Company Registry]

    , CASE
        WHEN R.RefType = 'I' THEN 0
        ELSE 1
    END AS [Owner Type]

    , CASE
        WHEN KYC_Status = '09' THEN R.KYC_Obtained
        ELSE NULL
    END AS [Date KYC Signed Off]

    , CASE
        WHEN L.Active = 1 THEN 0
        ELSE 1
    END AS [Closed]

    , R.KYC_Status AS [KYC Status]

    ,(
        SELECT TOP 1 LookupValue FROM IdentityRegister
        WHERE IdType IN('PEPT', 'PEPC') AND RefCode = R.RefCode
    ) AS [Political Connections]

    , R.KYC_Profile AS [Client Profile]
    , NULL AS [High Risk National]
    , NULL AS [Establishment Questionnaire]
    , NULL AS [New Client Authorisation Form]
    , NULL AS [Cert_ Copy of Passport or ID]
    , NULL AS [Uncert_ Copy of Passport or ID]
    , NULL AS [1st Independent Reference]
    , NULL AS [2nd Independent Reference]
    , NULL AS [Conf_ of Residential Address]

    , CASE
        WHEN(
            SELECT IsEntity FROM dbo.fnGetInScopeClients()
            WHERE RefCode = R.RefCode
        ) = 1 THEN R.RefCode
        ELSE NULL
    END AS [Entity No_]

    ,(
        SELECT STRING_AGG(LEFT(value, 1) + '.', '')
        FROM STRING_SPLIT(LTRIM(RTRIM(R.Initials)), ' ')
        WHERE value <> ''
    ) AS [Initials]

    , C.DateDeath AS [Date of Death]
    , NULL AS [Director]
    , NULL AS [Communication Details]
    , NULL AS [Other Communication Frequency]
    , NULL AS [Communication Frequency]
    , NULL AS [Estimated Fees Currency]
    , NULL AS [Estimated AUM Currency]
    , NULL AS [First Ref_ Requested Date]
    , NULL AS [First Ref_ Received Date]
    , NULL AS [Second Ref_ Requested Date]
    , NULL AS [Second Ref_ Received Date]
    , NULL AS [Address Verified By (1)]
    , NULL AS [Address Verified On (1)]
    , NULL AS [Date Agreement Sent]
    , NULL AS [Date Agreement Received]
    , NULL AS [Address Verified Using (1)]
    , NULL AS [Photographic ID]
    , NULL AS [Photographic ID Description]
    , NULL AS [Address Verified By (2)]
    , NULL AS [Address Verified On (2)]
    , NULL AS [Address Verified Using (2)]
    , NULL AS [First Reference Status]
    , NULL AS [Second Reference Status]
    , NULL AS [Certified Regulatory Licence]
    , NULL AS [Certified Evidence of Listing]
    , NULL AS [Specimen Signature Received]
    , NULL AS [Signature Authenticated]
    , NULL AS [Maj_ Sharehold_ of Third Party]

    , CASE
        WHEN ISNULL((
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE IdType = 'REG' AND RefCode = R.RefCode AND Active = 1
        ), '') = '' THEN 2
        ELSE 1
    END AS [Regulated Body]

    , CASE
        WHEN R.RefType <> 'I'
            THEN(
                SELECT TOP 1 Country FROM IdentityRegister
                WHERE IdType = 'REG' AND RefCode = R.RefCode AND Active = 1
            )
        ELSE NULL
    END AS [Regulatory Jurisdiction]

    ,(
        SELECT TOP 1 IdCode FROM IdentityRegister
        WHERE RefCode = R.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Number (2)]

    , (
        SELECT TOP 1 Country FROM IdentityRegister
        WHERE RefCode = R.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Country (2)]

    ,(
        SELECT TOP 1 ToDate FROM IdentityRegister
        WHERE RefCode = R.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Expiry Date (2)]

    , NULL AS [Cert_ Copy of Passport_ID (2)]
    , NULL AS [Certified Date (2)]
    , NULL AS [2nd Residence for Tax Purpose]
    , NULL AS [Expatriate of]
    , NULL AS [Date of Expatriate]

    ,(
        SELECT TOP 1 FromDate FROM IdentityRegister
        WHERE RefCode = R.RefCode AND IdType = 'IDC' AND Active = 1
    ) AS [Passport_ID Issue Date (2)]

    , NULL AS [Initial Fees Currency]
    , NULL AS [Estimated Initial Fees]

    ,(
        SELECT TOP 1 IdCode FROM IdentityRegister
        WHERE IdType IN('FIN', 'FIC') AND RefCode = R.RefCode AND Active = 1 AND LEN(IdCode) <> 0
    ) AS [Tax ID Number]

    , ISNULL(
        E.IncorpNr
        ,(
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE RefCode = R.RefCode AND IdType = 'INC' AND Active = 1
        )
    ) AS [Registered No_]

    , NULL AS [Classification]
    , NULL AS [Exclude from Scrutiny]
    , NULL AS [Modified For Scrutiny Search]
    , NULL AS [Exclude from Country Search]

    ,(
        SELECT TOP 1 Country FROM IdentityRegister
        WHERE IdType = 'PEPT' AND RefCode = R.RefCode
    ) AS [Primary PEP Co of Influence]

    , NULL AS [Global Market Country Code]
    , E.UserCombo2 AS [Type of Business]
    , NULL AS [In scope for EUSTD]
    , NULL AS [In Scope Manually Entered]
    , NULL AS [Reason for manual entry]
    , NULL AS [Date last status change]
    , NULL AS [EUSTD Preference]

    , ISNULL(
        (
            SELECT TOP 1 IdCode FROM IdentityRegister
            WHERE IdType = 'BCT' AND RefCode = R.RefCode AND Active = 1
        )
        , C.PlaceBirth
    ) AS [Town of Birth]

    , R.Salutation AS [Salutation]
    , NULL AS [Hold Mail]
    , NULL AS [Description of Tax Structure] -- To be amended [Description of Tax Structure]
    , NULL AS [Last Tax Review] -- To be amended [Last Tax Review]
    , NULL AS [Tax Status] -- To be amended [Tax Status]
    , NULL AS [Other Relation_ Within Group]
    , NULL AS [Employment Status]
    , R.RefCode AS [External Reference No_]
    , NULL AS [Sanctioned]
    , NULL AS [First Partition Code]
    , NULL AS [Second Partition Code]
    , NULL AS [Data Protection Level]
    , NULL AS [Attribution of Introduction]

    ,(
        SELECT TOP 1 O.Code FROM RefAddress AS A
        LEFT JOIN [MT Office Address] AS O
            ON(
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
        LEFT JOIN RefContacts AS C ON A.RefCode = C.RefCode
        WHERE A.RefCode = R.RefCode AND A.Active = 1 AND AddrType IN('RS', 'RO', 'BA', 'MA')
        ORDER BY
            CASE A.AddrType
                WHEN 'RS' THEN 1
                WHEN 'RO' THEN 2
                WHEN 'BA' THEN 3
                WHEN 'MA' THEN 4
            END
    ) AS [Admin Office]

    , NULL AS [Fiduciary_Trustee]
    , NULL AS [View]

    , (
        SELECT TOP 1 Country
        FROM IdentityRegister
        WHERE
            RefCode = R.RefCode AND IdType = 'CTZ' AND Active = 1
            AND Country <>(
                SELECT CountryCode FROM LookComboSave
                WHERE SaveName = C.Nationality
            )
    ) AS [Nationality 2]

    , NULL AS [Dual Nationality] -- To be amended [Dual Nationality]
    , NULL AS [E-mail Indemnity Held]
    , NULL AS [Audited Accounts Received]
    , NULL AS [Certified Date]
    , NULL AS [Trust Date Executed]
    , NULL AS [Type of Deed]
    , NULL AS [Reference]
    , E.Admin2Code AS [Manager]
    , R.Name AS [Formal Name]
    , NULL AS [Service Tier]
    , NULL AS [Sensitive Country Connection]
    , NULL AS [EP]
    , NULL AS [Position]

    ,(
        SELECT Name
        FROM RefMaster
        WHERE
            RefCode
            =(
                SELECT TOP 1 AddrCode FROM Officers
                WHERE RelClass = 'M' AND OfficerType = 'EMR' AND EntCode = R.RefCode
            )
    ) AS [Employer_Name of Own Company]

    , NULL AS [Risk Sector]
    , NULL AS [Approx_ Income Per Year]
    , NULL AS [Approx Net Worth]
    , NULL AS [Known by introducer since]
    , NULL AS [Introduction Date]
    , NULL AS [Next Date of Communication]
    , NULL AS [Power of Attorney Held]
    , NULL AS [Power of Attorney]
    , NULL AS [Type of Power of Attorney]

FROM RefMaster AS R
LEFT JOIN Entity AS E ON R.RefCode = E.EntCode
LEFT JOIN Compliance AS C ON R.RefCode = C.AddrCode
INNER JOIN RefLabels AS L ON R.RefCode = L.Code
INNER JOIN
    (
        SELECT
            EntCode
            , RefCode
        FROM EntityOwners
        UNION
        SELECT
            EntCode
            , AddrCode
        FROM Share_Interests
        WHERE IntType = 'BEO'
        UNION
        SELECT
            EntCode
            , AddrCode
        FROM Officers
        WHERE OfficerType = 'ADM'
    ) AS Z
    ON R.RefCode = Z.RefCode
WHERE
    Z.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

UPDATE [MT Owner]
SET [Dual Nationality] = 1
WHERE [Nationality] IS NOT NULL AND [Nationality 2] IS NOT NULL

UPDATE [MT Owner]
SET [Dual Nationality] = 0
WHERE [Nationality 2] IS NULL

GO
```
