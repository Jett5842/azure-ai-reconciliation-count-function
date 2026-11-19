---
staging_table: MT Client
etl_script: InsertMtClient.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (RefMaster.RefCode), non-individual
exact_sources: [RefMaster]
lookup_sources: [Entity (lookup), EntityAccount (lookup), IdentityRegister (lookup), EntityTypes (lookup), RefAddress (lookup)]
---
# MT Client

## Overview
Migrates the in-scope Client Master Files (companies, trusts, funds etc., never individuals): name, incorporation details, registered / administrative office, AGM and annual return requirements, status, FATCA / CRS classification, LEI, closure / dissolution dates, client analysis codes and lead client link. Most columns are looked up from other Vpoint tables.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClient.sql` into staging table `[MT Client]`.

## Scope filter
`RM.RefType <> 'I'` (non-individual) AND `RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE isClient = 1)`.

## Row count behaviour
One staging row per RefMaster row of an in-scope client. RefMaster is LEFT JOINed to Entity and EntityAccount, so a client with several EntityAccount rows can produce more than one row.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefMaster | Non-individual RefMaster records that are in-scope clients. | `FROM RefMaster AS RM LEFT JOIN Entity AS E ON RM.RefCode = E.EntCode LEFT JOIN EntityAccount AS EA ON RM.RefCode = EA.EntCode WHERE RM.RefType <> 'I' AND RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE isClient = 1)` | Bring over the in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Entity (lookup) | LEFT JOIN Entity ON EntCode = RefMaster.RefCode | [Country of Incorporation], [Date of Incorporation], [Registered Number], [Financial Year End], [Jurisdiction], [Legal Type], [Status], [ClientAnalysisA/B/C], [Discretionary], [Properlaw], [Lead Client Link], [Period Length], [Max_ Trust Period], [Perpetuity Date], last/next AGM, annual return, audit and review dates and other entity particulars |
| EntityAccount (lookup) | LEFT JOIN EntityAccount ON EntCode = RefMaster.RefCode | [Currency Code] |
| IdentityRegister (lookup) | Sub-queries (SELECT TOP 1) with Active = 1 on RefCode: IdType CTDT / FSPR / FRFI / FCSC / CRFI / FCRS, and LEI (no Active filter); CPTFI / CRFI / FPTFI / FRFI through MasterFileLink | [Account is CRS RFI], [Account is FATCA RFI], [FATCA Filer Category], [FATCA Classification], [CRS Classification], [Legal Entity Identifier (LEI)], [Next LEI Renewal Date] |
| EntityTypes (lookup) | Sub-query (SELECT TOP 1) ON JurisDic = Entity.IncorpPlace AND EType = Entity.EntType | [AGM Required], [Annual Return Required] |
| RefAddress (lookup) | Sub-queries (SELECT TOP 1) with Active = 1: AddrType RS / BA / MA (Administrative), SR / RO (Registered), S% (Statutory), SS (Seal); the office code is then found in [MT Office Address] through the [Temp] key (GEN key when no business contacts, otherwise RefCode key) | [Administrative Office], [Registered Office], [Company Seal], [Statutory Record Location], [Location of Seal] |

## Column mapping highlights
- [Status]: Entity.Status, or RefMaster.Status when Entity is missing; '0' when Entity is not active but RefMaster is live
- [Date Dissolved_Struck off] and [Date Of Closure] / [Reason for Closure] come from the latest RefStatus rows (SType 'ES' / 'E' with NewStat 'C')
- [Protector Appointed] / [Co Trustee] = 1 when an active Officers row of type PRO / COT exists

## Post-insert updates
- UPDATE [MT Client] SET [Date Dissolved_Struck off] = NULL WHERE Status = '0' (live clients keep no dissolution date)

## Notes for reconciliation
- Individuals (RefType 'I') never become clients; they are covered by MT Entity.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClient'
GO

INSERT INTO [MT Client]
(
    [Type]
    , [Name]
    , [Search Name]
    , [Country of Incorporation]
    , [Date of Incorporation]
    , [Registered Number]
    , [Administrative Office]
    , [Registered Office]
    , [Company Seal]
    , [Directors_ Quorum]
    , [Last Review Completed]
    , [Last Review Year]
    , [Actual Trust Closing Date]
    , [Max_ Trust Period]
    , [Statutory Record Location]
    , [AGM Required]
    , [Last AGM Held Date]
    , [Next AGM To Be Held Date]
    , [Next Year End]
    , [Jurisdiction]
    , [Protector Appointed]
    , [Co Trustee]
    , [Status]
    , [Revocable_Irrevocable]
    , [Annual Return Filing Date]
    , [Annual Return Required]
    , [Last Annual Return Made up to]
    , [Client Formal Name]
    , [Legal Type]
    , [External Reference No]
    , [Location of Seal]
    , [Audit Status]
    , [Audit Status Date]
    , [Perpetuity Date]
    , [Dissolved_Struck off]
    , [Date Dissolved_Struck off]
    , [Purpose_Objective]
    , [Type of Trust]
    , [Account is CRS RFI]
    , [Account is FATCA RFI]
    , [FATCA Filer Category]
    , [FATCA Classification]
    , [CRS Classification]
    , [Legal Entity Identifier (LEI)]
    , [Next LEI Renewal Date]
    , [Purpose-Activity Code]
    , [Date Of Closure]
    , [Reason for Closure]
    , [Financial Year End]
    , [Exclude from Scrutiny]
    , [Modified For Scrutiny Search]
    , [Currency Code]
    , [ClientAnalysisA]
    , [ClientAnalysisB]
    , [ClientAnalysisC]
    , [Discretionary]
    , [Proper law]
    , [Lead Client]
    , [Lead Client Link]
    , [Period Length]
    , [Dont Create Job]
)
SELECT
    RM.RefType AS [Type]
    , RM.[Name]
    , RM.SearchName AS [Search Name]
    , E.IncorpPlace AS [Country of Incorporation]
    , E.IncorpDate AS [Date of Incorporation]
    , E.IncorpNr AS [Registered Number]

    ,(
        SELECT TOP 1 O.Code FROM RefAddress AS A
        LEFT JOIN [MT Office Address] AS O
            ON(
                (
                    (
                        SELECT TOP 1 C.cText
                        FROM RefContacts AS C
                        WHERE
                            A.RefCode = C.RefCode
                            AND C.cType IN('TB', 'FB', 'EB', 'WB')
                    ) IS NULL
                    AND CONCAT(A.AddrNr, 'GEN') = O.Temp
                )
                OR
                (
                    (
                        SELECT TOP 1 C.cText
                        FROM RefContacts AS C
                        WHERE
                            A.RefCode = C.RefCode
                            AND C.cType IN('TB', 'FB', 'EB', 'WB')
                    ) IS NOT NULL
                    AND CONCAT(A.AddrNr, A.RefCode) = O.Temp
                )
            )
        LEFT JOIN RefContacts AS C ON A.RefCode = C.RefCode
        WHERE A.RefCode = RM.RefCode AND A.Active = 1 AND AddrType IN('RS', 'BA', 'MA')
        ORDER BY
            CASE A.AddrType
                WHEN 'RS' THEN 1
                WHEN 'BA' THEN 2
                WHEN 'MA' THEN 3
            END
    ) AS [Administrative Office]

    ,(
        SELECT TOP 1 O.Code FROM RefAddress AS A
        LEFT JOIN [MT Office Address] AS O
            ON(
                (
                    (
                        SELECT TOP 1 C.cText
                        FROM RefContacts AS C
                        WHERE
                            A.RefCode = C.RefCode
                            AND C.cType IN('TB', 'FB', 'EB', 'WB')
                    ) IS NULL
                    AND CONCAT(A.AddrNr, 'GEN') = O.Temp
                )
                OR
                (
                    (
                        SELECT TOP 1 C.cText
                        FROM RefContacts AS C
                        WHERE
                            A.RefCode = C.RefCode
                            AND C.cType IN('TB', 'FB', 'EB', 'WB')
                    ) IS NOT NULL
                    AND CONCAT(A.AddrNr, A.RefCode) = O.Temp
                )
            )
        LEFT JOIN RefContacts AS C ON A.RefCode = C.RefCode
        WHERE A.RefCode = RM.RefCode AND A.Active = 1 AND A.AddrType IN('SR', 'RO')
        ORDER BY
            CASE A.AddrType
                WHEN 'SR' THEN 1
                WHEN 'RO' THEN 2
            END
    ) AS [Registered Office]

    , CASE
        WHEN(
            SELECT TOP 1 A.AddrNr FROM RefAddress AS A
            WHERE A.AddrType = 'SS' AND A.RefCode = RM.RefCode
        ) IS NOT NULL THEN 1
        ELSE 0
    END AS [Company Seal]

    , E.MA_DirQuorum AS [Directors_ Quorum]
    , E.LastReview AS [Last Review Completed]
    , YEAR(E.LastReview) AS [Last Review Year]
    , NULL AS [Actual Trust Closing Date]
    , E.TrustPerpetuity AS [Max_ Trust Period]

    ,(
        (
            SELECT TOP 1 O.Code FROM RefAddress AS A
            LEFT JOIN [MT Office Address] AS O
                ON(
                    (
                        (
                            SELECT TOP 1 C.cText
                            FROM RefContacts AS C
                            WHERE
                                A.RefCode = C.RefCode
                                AND C.cType IN('TB', 'FB', 'EB', 'WB')
                        ) IS NULL
                        AND CONCAT(A.AddrNr, 'GEN') = O.Temp
                    )
                    OR
                    (
                        (
                            SELECT TOP 1 C.cText
                            FROM RefContacts AS C
                            WHERE
                                A.RefCode = C.RefCode
                                AND C.cType IN('TB', 'FB', 'EB', 'WB')
                        ) IS NOT NULL
                        AND CONCAT(A.AddrNr, A.RefCode) = O.Temp
                    )
                )
            LEFT JOIN RefContacts AS C ON A.RefCode = C.RefCode
            WHERE A.AddrType LIKE 'S%' AND A.RefCode = RM.RefCode AND A.Active = 1
        )
    ) AS [Statutory Record Location]

    , CASE
        WHEN(
            SELECT TOP 1 ET.ST_ReqAGM FROM EntityTypes AS ET
            WHERE E.IncorpPlace = ET.JurisDic AND ET.EType = E.EntType
        ) = 'R' THEN 0
        ELSE 1
    END AS [AGM Required]

    , E.DateLastAGM AS [Last AGM Held Date]
    , E.DateNextAGM AS [Next AGM To Be Held Date]
    , E.AcctYearEnd AS [Next Year End]
    , E.IncorpPlace AS [Jurisdiction]

    , CASE
        WHEN EXISTS(
            SELECT 1 FROM Officers AS O
            WHERE
                O.EntCode = RM.RefCode
                AND O.OfficerType = 'PRO'
                AND(O.DateResign IS NULL OR O.DateResign > GETDATE())
        ) THEN 1
        ELSE 0
    END AS [Protector Appointed]

    , CASE
        WHEN EXISTS(
            SELECT 1 FROM Officers AS O
            WHERE
                O.EntCode = RM.RefCode
                AND O.OfficerType = 'COT'
                AND(O.DateResign IS NULL OR O.DateResign > GETDATE())
        ) THEN 1
        ELSE 0
    END AS [Co Trustee]

    , CASE
        WHEN E.Status <> '0' AND RM.Status = '0' THEN '0'
        WHEN E.Status IS NULL THEN RM.Status
        ELSE E.Status
    END AS [Status]
    , E.Revocable AS [Revocable_Irrevocable]
    , NULL AS [Annual Return Filing Date]

    , CASE
        WHEN(
            SELECT TOP 1 ET.ST_ReqAR FROM EntityTypes AS ET
            WHERE E.IncorpPlace = ET.JurisDic AND ET.EType = E.EntType
        ) = 'R' THEN 2
        ELSE 3
    END AS [Annual Return Required]

    , E.DateLastAnRe AS [Last Annual Return Made up to]
    , RM.Name AS [Client Formal Name]
    , E.EntType AS [Legal Type]
    , RM.RefCode AS [External Reference No]

    , CASE
        WHEN(
            SELECT TOP 1 A.AddrNr FROM RefAddress AS A
            WHERE A.AddrType = 'SS' AND A.RefCode = RM.RefCode
        ) IS NOT NULL
            THEN(
                SELECT TOP 1 O.Code FROM RefAddress AS A
                LEFT JOIN [MT Office Address] AS O
                    ON(
                        (
                            (
                                SELECT TOP 1 C.cText
                                FROM RefContacts AS C
                                WHERE
                                    A.RefCode = C.RefCode
                                    AND C.cType IN('TB', 'FB', 'EB', 'WB')
                            ) IS NULL
                            AND CONCAT(A.AddrNr, 'GEN') = O.Temp
                        )
                        OR
                        (
                            (
                                SELECT TOP 1 C.cText
                                FROM RefContacts AS C
                                WHERE
                                    A.RefCode = C.RefCode
                                    AND C.cType IN('TB', 'FB', 'EB', 'WB')
                            ) IS NOT NULL
                            AND CONCAT(A.AddrNr, A.RefCode) = O.Temp
                        )
                    )
                LEFT JOIN RefContacts AS C ON A.RefCode = C.RefCode
                WHERE A.AddrType = 'SS' AND A.RefCode = RM.RefCode AND A.Active = 1
            )
        ELSE NULL
    END AS [Location of Seal]

    , E.AuditReq AS [Audit Status]
    , E.DateLastAudit AS [Audit Status Date]
    , E.PerpepuityDate AS [Perpetuity Date]
    , E.SubStatus AS [Dissolved _Struck off]

    ,(
        SELECT TOP 1 DateEffective
        FROM RefStatus AS S
        WHERE S.SType = 'ES' AND S.RefCode = RM.RefCode
        ORDER BY SeqNr DESC
    ) AS [Date Dissolved_Struck off]

    , E.MA_Purpose AS [Purpose_Objective]
    , NULL AS [Type of Trust]

    , CASE
        WHEN EXISTS(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.MasterFileLink = RM.RefCode AND IR.IdType IN('CPTFI', 'CRFI') AND IR.Active = 1) OR EXISTS(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'CTDT' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        ) THEN 1
        ELSE 0
    END AS [Account is CRS RFI]

    , CASE
        WHEN EXISTS(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.MasterFileLink = RM.RefCode AND IR.IdType IN('FPTFI', 'FRFI') AND IR.Active = 1) OR EXISTS(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'FSPR' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        ) THEN 1
        ELSE 0
    END AS [Account is FATCA RFI]

    , CASE
        WHEN EXISTS(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE
                IR.IdType = 'FRFI' AND IR.RefCode = RM.RefCode AND IR.Active = 1) THEN(
            SELECT TOP 1 IR.UdCode FROM IdentityRegister AS IR
            WHERE IR.RefCode = RM.RefCode AND IR.IdType = 'FRFI' AND IR.Active = 1
        )
    END AS [FATCA Filer Category]

    , CASE
        WHEN(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'FRFI' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        ) IS NOT NULL THEN 'RFI'
        ELSE(
            SELECT TOP 1 IR.UdCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'FCSC' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        )
    END AS [FATCA Classification]

    , CASE
        WHEN(
            SELECT TOP 1 IR.RefCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'CRFI' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        ) IS NOT NULL THEN 'RFI'
        ELSE(
            SELECT TOP 1 IR.UdCode FROM IdentityRegister AS IR
            WHERE IR.IdType = 'FCRS' AND IR.RefCode = RM.RefCode AND IR.Active = 1
        )
    END AS [CRS Classification]

    ,(
        SELECT TOP 1 I.IdCode
        FROM IdentityRegister AS I
        WHERE I.IdType = 'LEI' AND I.RefCode = RM.RefCode
    ) AS [Legal Entity Identifier (LEI)]

    ,(
        SELECT TOP 1 I.ReminderDate
        FROM IdentityRegister AS I
        WHERE I.IdType = 'LEI' AND I.RefCode = RM.RefCode
    ) AS [Next LEI Renewal Date]

    , NULL AS [Purpose-Activity Code]

    ,(
        SELECT TOP 1 S.DateEffective
        FROM RefStatus AS S
        WHERE S.SType = 'E' AND S.NewStat = 'C' AND S.RefCode = RM.RefCode
        ORDER BY SeqNr DESC
    ) AS [Date Of Closure]

    ,(
        SELECT TOP 1 S.CNote
        FROM RefStatus AS S
        WHERE S.SType = 'E' AND S.NewStat = 'C' AND S.RefCode = RM.RefCode
        ORDER BY SeqNr DESC
    ) AS [Reason for Closure]

    , E.AcctYearEnd AS [Financial Year End]
    , 0 AS [Exclude from Scrutiny]
    , NULL AS [Modified For Scrutiny Search]
    , EA.BaseCur AS [Currency Code]
    , E.AdminCode AS [ClientAnalysisA]
    , E.Admin2Code AS [ClientAnalysisB]
    , E.Admin3Code AS [ClientAnalysisC]
    , E.NatureTrust AS [Discretionary]
    , E.IncorpPlace AS [Properlaw]
    , CASE WHEN RM.CL = 1 THEN 1 ELSE 0 END AS [Lead Client]
    , E.EntClient AS [Lead Client Link]
    , CASE WHEN E.TrustPerpetuity = 'HY' THEN '100Y' ELSE NULL END AS [Period Length]
    , 1 AS [Dont Create Job]

FROM RefMaster AS RM
LEFT JOIN Entity AS E ON RM.RefCode = E.EntCode
LEFT JOIN EntityAccount AS EA ON RM.RefCode = EA.EntCode
WHERE
    RM.RefType <> 'I' AND RM.RefCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE isClient = 1
    )

-- Update the field to NULL if the status is Live/Active
UPDATE [MT Client] SET [Date Dissolved_Struck off] = NULL
WHERE Status = '0'

GO
```
