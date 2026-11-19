---
staging_table: MT Address
etl_script: InsertMtAddress.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsEntity = 1 (RefCode of addresses and contacts)
exact_sources: [CR_RefAddresses (MAILING), CR_RefAddresses (nonMAILING, DISTINCT), RefContacts (nonMCONTACT)]
lookup_sources: [qLvCNTR (lookup), RefMaster (lookup), RefContacts (lookup)]
---
# MT Address

## Overview
Migrates the postal addresses and contact details of in-scope Entity Master Files. The MAILING (main) address of each entity is picked by an address-type priority and carries phone, fax, e-mail and web page; all other addresses and all other contact types become additional address rows.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtAddress.sql` into staging table `[MT Address]`.

## Scope filter
All three branches join `fnGetInScopeClients() AS F ON RefCode = F.RefCode AND IsEntity = 1`, so only in-scope Entity master files are used (the Type column is 3 for entities, 1 otherwise).

## Row count behaviour
Three branches combined with UNION ALL: (1) one MAILING row per RefCode, multiplied by any matching active contact rows (phone / fax / e-mail / web) it is LEFT JOINed to; (2) every other address row (DISTINCT); (3) every contact row whose type is not phone / fax / e-mail / web.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| CR_RefAddresses (MAILING) | The first address per RefCode in priority order: non-individuals RO then SR; individuals RA, MA then BA. Must be not cancelled and CardActive = 1. LEFT JOINed to active Phone, Fax, E-Mail and Web contacts (TB/FB/EB for non-individuals, TM/FH/EP for individuals, WB for all), which can add extra rows when several contacts match. | `WITH MAILING AS (SELECT ..., ROW_NUMBER() OVER (PARTITION BY RA.RefCode ORDER BY CASE RA.AddrType WHEN 'RO' THEN 1 WHEN 'SR' THEN 2 WHEN 'RA' THEN 3 WHEN 'MA' THEN 4 WHEN 'BA' THEN 5 END) AS RowNum FROM CR_RefAddresses AS RA INNER JOIN RefMaster AS R ON RA.RefCode = R.RefCode INNER JOIN fnGetInScopeClients() AS F ON RA.RefCode = F.RefCode AND IsEntity = 1 WHERE ((R.RefType <> 'I' AND RA.AddrType IN ('RO','SR')) OR (R.RefType = 'I' AND RA.AddrType IN ('RA','MA','BA'))) AND (RA.Cancelled IS NULL OR RA.Cancelled = '') AND RA.CardActive = 1) ... WHERE M.RowNum = 1` | Bring over the main (mailing) address of in-scope Entity Master Files. |
| CR_RefAddresses (nonMAILING, DISTINCT) | All other address rows of in-scope entities, i.e. every CR_RefAddresses row that is not the chosen MAILING row (including cancelled / inactive ones). DISTINCT. | `SELECT DISTINCT ... FROM CR_RefAddresses AS RA INNER JOIN RefMaster AS R ... INNER JOIN fnGetInScopeClients() AS F ON RA.RefCode = F.RefCode AND IsEntity = 1 LEFT JOIN MAILING AS M ON RA.RefCode = M.No_ AND RA.SeqNr = M.SeqNr WHERE M.No_ IS NULL OR M.RowNum > 1` | Bring over the other addresses of in-scope Entity Master Files aside from the main one. |
| RefContacts (nonMCONTACT) | Every contact row whose type is NOT TM, FH, EP, TB, FB, EB or WB (those are handled on the MAILING row); there is no phone / e-mail not-empty filter any more. | `FROM RefContacts AS RC INNER JOIN RefMaster AS R ON RC.RefCode = R.RefCode INNER JOIN dbo.fnGetInScopeClients() AS F ON RC.RefCode = F.RefCode AND IsEntity = 1 LEFT JOIN qLvCNTR AS LV ON RC.Country = LV.ElCode WHERE RC.Ctype NOT IN ('TM','FH','EP','TB','FB','EB','WB')` | Bring over the other contact records of in-scope Entity Master Files as address rows. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| qLvCNTR (lookup) | LEFT JOIN qLvCNTR ON RefContacts.Country = ElCode | Telephone prefix (area code) used for [Ph_ Area code] / [M_ Area code] / [F_ Area code]; the area code columns are cleared by a final update |
| RefMaster (lookup) | INNER JOIN RefMaster ON RefCode (all address rows) and LEFT JOIN on contact rows | [Surname], [Forename(s)] |
| RefContacts (lookup) | CONTACT CTE: RefContacts of types TB/TM/FB/FH/EB/EP/WB, active (cActive = 1, ToDate empty) on RefCode = No_ for MAILING rows | [Phone No_], [Fax No_], [E-Mail], [Home Page], [Mobile Phone No_] and the Ph_/M_/F_ country and area codes |

## Column mapping highlights
- [Code] = 'MAILING' for the main address, '02', '03', ... for others; [Primary Address] = 1 only for MAILING
- [Residence for Tax Purposes] = 1 when Address Type is RA, RO or SR
- [Service Address] = 1 for nonMAILING rows with address type 'RS'

## Notes for reconciliation
- MAILING rows can exceed one per entity when several active contacts match (row fan-out).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtAddress'
GO

WITH MAILING AS(
    SELECT
        RA.RefCode AS [No_]
        , 'MAILING' AS [Code]
        , CASE WHEN F.IsEntity = 1 THEN 3 ELSE 1 END AS [Type]
        , RA.SeqNr AS [AddrSeqNr]
        , R.[Name] AS [Surname]
        , R.Initials AS [Forename(s)]
        ,(RA.[Address] + ' ' + ISNULL(RA.Address2, '')) AS [Address 1]
        , ISNULL(RA.Address3, '') + ' ' + ISNULL(RA.Address4, '') + ' ' + ISNULL(RA.Address5, '') AS [Address 2]
        , RA.City AS [City]
        , RA.PostalCode AS [Post Code]
        , RA.[State] AS [County]
        , RA.Country AS [Country Code]
        , RA.AddrType AS [Address Type]
        , RA.[Description] AS [Address Explanation]
        , RA.Effective AS [Residence Start Date]
        , RA.Cancelled AS [Residence End Date]
        , RA.CardActive AS [Active]
        , R.RefType

        , ROW_NUMBER() OVER(
            PARTITION BY RA.RefCode ORDER BY
                CASE RA.AddrType
                    WHEN 'RO' THEN 1
                    WHEN 'SR' THEN 2
                    WHEN 'RA' THEN 3
                    WHEN 'MA' THEN 4
                    WHEN 'BA' THEN 5
                END
        ) AS RowNum

        , RA.SeqNr
    FROM CR_RefAddresses AS RA
    INNER JOIN RefMaster AS R ON RA.RefCode = R.RefCode
    INNER JOIN fnGetInScopeClients() AS F ON RA.RefCode = F.RefCode AND IsEntity = 1
    WHERE
        (
            (R.RefType <> 'I' AND RA.AddrType IN('RO', 'SR'))
            OR(R.RefType = 'I' AND RA.AddrType IN('RA', 'MA', 'BA'))
        )
        AND(RA.Cancelled IS NULL OR RA.Cancelled = '') AND RA.CardActive = 1
)

, nonMAILING AS(
    SELECT DISTINCT
        RA.RefCode AS [No_]
        , CASE WHEN F.IsEntity = 1 THEN 3 ELSE 1 END AS [Type]
        , RA.SeqNr AS [AddrSeqNr]
        , R.[Name] AS [Surname]
        , R.Initials AS [Forename(s)]
        ,(RA.[Address] + ' ' + ISNULL(RA.Address2, '')) AS [Address 1]
        , ISNULL(RA.Address3, '') + ' ' + ISNULL(RA.Address4, '') + ' ' + ISNULL(RA.Address5, '') AS [Address 2]
        , RA.City AS [City]
        , RA.PostalCode AS [Post Code]
        , RA.[State] AS [County]
        , RA.Country AS [Country Code]
        , RA.AddrType AS [Address Type]
        , RA.[Description] AS [Address Explanation]
        , RA.Effective AS [Residence Start Date]
        , RA.Cancelled AS [Residence End Date]
        , RA.CardActive AS [Active]
        , R.RefType
        , RA.SeqNr
    FROM CR_RefAddresses AS RA
    INNER JOIN RefMaster AS R ON RA.RefCode = R.RefCode
    INNER JOIN fnGetInScopeClients() AS F ON RA.RefCode = F.RefCode AND IsEntity = 1
    LEFT JOIN MAILING AS M ON RA.RefCode = M.No_ AND RA.SeqNr = M.SeqNr
    WHERE M.No_ IS NULL OR M.RowNum > 1
)

, CONTACT AS(
    SELECT
        RC.RefCode
        , RC.cType
        , RC.Country
        , RC.cText
        , RC.FromDate
        , RC.ToDate
        , RC.SeqNr
        , RC.cActive

        , SUBSTRING(
            ConvertValues
            , CHARINDEX('TELPREFIX', ConvertValues) + 10
            , CHARINDEX(']', ConvertValues, CHARINDEX('TELPREFIX', ConvertValues)) -(CHARINDEX('TELPREFIX', ConvertValues) + 10)
        ) AS AreaCode

    FROM RefContacts AS RC
    INNER JOIN RefMaster AS R ON RC.RefCode = R.RefCode
    INNER JOIN dbo.fnGetInScopeClients() AS F ON RC.RefCode = F.RefCode AND IsEntity = 1
    LEFT JOIN qLvCNTR AS LV ON RC.Country = LV.ElCode
    WHERE RC.Ctype IN('TM', 'FH', 'EP', 'TB', 'FB', 'EB', 'WB')
)

, nonMCONTACT AS(
    SELECT
        RC.RefCode
        , RC.cType
        , RC.Country
        , RC.cText
        , RC.FromDate
        , RC.ToDate
        , RC.SeqNr
        , RC.cActive

        , SUBSTRING(
            ConvertValues
            , CHARINDEX('TELPREFIX', ConvertValues) + 10
            , CHARINDEX(']', ConvertValues, CHARINDEX('TELPREFIX', ConvertValues)) -(CHARINDEX('TELPREFIX', ConvertValues) + 10)
        ) AS AreaCode

        , CASE
            WHEN F.IsEntity = 1 THEN 3
            ELSE 1
        END AS [Type]

    FROM RefContacts AS RC
    INNER JOIN RefMaster AS R ON RC.RefCode = R.RefCode
    INNER JOIN dbo.fnGetInScopeClients() AS F ON RC.RefCode = F.RefCode AND IsEntity = 1
    LEFT JOIN qLvCNTR AS LV ON RC.Country = LV.ElCode
    WHERE RC.Ctype NOT IN('TM', 'FH', 'EP', 'TB', 'FB', 'EB', 'WB')
)

INSERT INTO [MT Address]
(
    No_
    , [Code]
    , Surname
    , [Forename(s)]
    , [Address 1]
    , [Address 2]
    , City
    , [Post Code]
    , County
    , [Phone No_]
    , [Fax No_]
    , [E-Mail]
    , [Country Code]
    , [Type]
    , [Address Type]
    , [Primary Address]
    , [Mobile Phone No_]
    , [Address Explanation]
    , [Ph_ Country Code]
    , [Ph_ Area code]
    , [M_ Country Code]
    , [M_ Area code]
    , [F_ Country Code]
    , [F_ Area code]
    , [Residence for Tax Purposes]
    , [Residence Start Date]
    , [Residence End Date]
    , [Home Page]
    , [External Reference No]
    , [Service Address]
    , [NAV_Entry No]
)
SELECT
    *
    , ROW_NUMBER() OVER(ORDER BY No_) AS RowNr
FROM
    (
        SELECT
            M.No_
            , M.Code
            , M.Surname
            , M.[Forename(s)]
            , M.[Address 1]
            , M.[Address 2]
            , M.City
            , M.[Post Code]
            , M.County
            , Phone.cText AS [Phone]
            , Fax.cText AS [Fax No_]
            , eMail.cText AS [E-Mail]
            , M.[Country Code] AS [Country Code]
            , M.[Type]
            , [Address Type] AS [Address Type]
            , 1 AS [Primary Address]
            , CASE WHEN M.RefType = 'I' THEN Phone.cText END AS [Mobile Phone No_]
            , M.[Address Explanation]
            , Phone.Country AS [Ph_ Country Code]
            , Phone.AreaCode AS [Ph_ Area code]
            , eMail.Country AS [M_ Country Code]
            , eMail.AreaCode AS [M_ Area code]
            , Fax.Country AS [F_ Country Code]
            , Fax.AreaCode AS [F_ Area code]
            , CASE WHEN M.[Address Type] IN('RA', 'RO', 'SR') THEN 1 ELSE 0 END AS [Residence for Tax Purposes]
            , M.[Residence Start Date]
            , M.[Residence End Date]
            , web.cText AS [Home Page]
            , M.No_ AS [External Reference No]
            , 0 AS [Service Address]
        FROM MAILING AS M

        LEFT JOIN CONTACT AS Phone
            ON
                M.No_ = Phone.RefCode
                AND Phone.cType
                = CASE
                    WHEN M.RefType <> 'I' THEN 'TB'
                    ELSE 'TM'
                END
                AND(Phone.ToDate IS NULL OR Phone.ToDate = '') AND Phone.cActive = 1

        LEFT JOIN CONTACT AS Fax
            ON
                M.No_ = Fax.RefCode
                AND Fax.cType
                = CASE
                    WHEN M.RefType <> 'I' THEN 'FB'
                    ELSE 'FH'
                END
                AND(Fax.ToDate IS NULL OR Fax.ToDate = '') AND Fax.cActive = 1

        LEFT JOIN CONTACT AS eMail
            ON
                M.No_ = eMail.RefCode
                AND eMail.cType
                = CASE
                    WHEN M.RefType <> 'I' THEN 'EB'
                    ELSE 'EP'
                END
                AND(eMail.ToDate IS NULL OR eMail.ToDate = '') AND eMail.cActive = 1

        LEFT JOIN CONTACT AS web
            ON
                M.No_ = web.RefCode AND web.cType = 'WB'
                AND(web.ToDate IS NULL OR web.ToDate = '') AND web.cActive = 1

        WHERE M.RowNum = 1

        UNION ALL

        SELECT
            T.No_
            , CONCAT('0', ROW_NUMBER() OVER(PARTITION BY T.No_ ORDER BY T.No_) + 1) AS [Code]
            , T.Surname
            , T.[Forename(s)]
            , T.[Address 1]
            , T.[Address 2]
            , T.City
            , T.[Post Code]
            , T.County
            , T.[Phone]
            , T.[Fax No_]
            , T.[E-Mail]
            , T.[Country Code] AS [Country Code]
            , T.[Type]
            , T.[Address Type] AS [Address Type]
            , 0 AS [Primary Address]
            , T.[Mobile Phone No_]
            , T.[Address Explanation]
            , T.[Ph_ Country Code] AS [Ph_ Country Code]
            , T.[Ph_ Area code]
            , T.[M_ Country Code] AS [M_ Country Code]
            , T.[M_ Area code]
            , T.[F_ Country Code] AS [F_ Country Code]
            , T.[F_ Area code]
            , T.[Residence for Tax Purposes]
            , T.[Residence Start Date]
            , T.[Residence End Date]
            , T.[Home Page]
            , T.[External Reference No]
            , T.[Service Address]
        FROM
            (
                SELECT
                    M.No_
                    , NULL AS [Code]
                    , M.Surname
                    , M.[Forename(s)]
                    , M.[Address 1]
                    , M.[Address 2]
                    , M.City
                    , M.[Post Code]
                    , M.County
                    , NULL AS [Phone]
                    , NULL AS [Fax No_]
                    , NULL AS [E-Mail]
                    , M.[Country Code] AS [Country Code]
                    , M.[Type]
                    , M.[Address Type] AS [Address Type]
                    , NULL AS [Mobile Phone No_]
                    , M.[Address Explanation]
                    , NULL AS [Ph_ Country Code]
                    , NULL AS [Ph_ Area code]
                    , NULL AS [M_ Country Code]
                    , NULL AS [M_ Area code]
                    , NULL AS [F_ Country Code]
                    , NULL AS [F_ Area code]
                    , 0 AS [Residence for Tax Purposes]
                    , M.[Residence Start Date]
                    , M.[Residence End Date]
                    , NULL AS [Home Page]
                    , M.No_ AS [External Reference No]
                    , CASE WHEN M.[Address Type] = 'RS' THEN 1 ELSE 0 END AS [Service Address]
                FROM nonMAILING AS M

                UNION ALL

                SELECT
                    RM.RefCode AS No_
                    , NULL AS Code
                    , RM.[Name] AS [Surname]
                    , RM.Initials AS [Forename(s)]
                    , NULL AS [Address 1]
                    , NULL AS [Address 2]
                    , NULL AS City
                    , NULL AS [Post Code]
                    , NULL AS County
                    , CASE WHEN C.cType IN('TD', 'TH') THEN C.cText END AS [Phone]
                    , NULL AS [Fax No_]
                    , CASE WHEN C.cType IN('EI') THEN C.cText END AS [E-Mail]
                    , NULL AS [Country Code]
                    , C.[Type]
                    , '2' AS [Address Type]
                    , NULL AS [Mobile Phone No_]
                    , NULL AS [Address Explanation]
                    , CASE WHEN C.cType IN('TD', 'TH') THEN C.Country END AS [Ph_ Country Code]
                    , CASE WHEN C.cType IN('TD', 'TH') THEN C.AreaCode END AS [Ph_ Area code]
                    , CASE WHEN C.cType IN('EI') THEN C.Country END AS [M_ Country Code]
                    , CASE WHEN C.cType IN('EI') THEN C.AreaCode END AS [M_ Area code]
                    , NULL AS [F_ Country Code]
                    , NULL AS [F_ Area code]
                    , 0 AS [Residence for Tax Purposes]
                    , NULL AS [Residence Start Date]
                    , NULL AS [Residence End Date]
                    , NULL AS [Home Page]
                    , C.RefCode AS [External Reference No]
                    , 0 AS [Service Address]
                FROM nonMCONTACT AS C
                LEFT JOIN RefMaster AS RM ON C.RefCode = RM.RefCode

            ) AS T

    ) AS List

GO
```
