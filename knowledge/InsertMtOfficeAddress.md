---
staging_table: MT Office Address
etl_script: InsertMtOfficeAddress.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: Embedded: Client IsClient = 1 OR Owner sources OR VpUser.RelMfCode
exact_sources: [RefAddress + Addresses (DISTINCT address + contacts + Temp key)]
lookup_sources: [Addresses (lookup), RefContacts (lookup)]
---
# MT Office Address

## Overview
Migrates the office address master list (address text, phone, fax, e-mail, web page) used by Clients, Owners and Resources. Each address gets a generated code 'ADD000001' etc. and a [Temp] key (address number + RefCode, or address number + 'GEN' when the RefCode has no business contacts) that other tables use to find their office address.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtOfficeAddress.sql` into staging table `[MT Office Address]`.

## Scope filter
Addresses of master files that are in-scope Clients (`IsClient = 1`), OR Owners (RefCode found in EntityOwners, Share_Interests IntType 'BEO', or Officers OfficerType 'ADM'), OR Resources (`RefCode IN (SELECT RelMfCode FROM VpUser)`).

## Row count behaviour
SELECT DISTINCT over address text + Phone/Fax/E-Mail/Web + Temp key. The same physical address can therefore appear once per RefCode when that RefCode has business contacts.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefAddress + Addresses (DISTINCT address + contacts + Temp key) | Active, non-cancelled addresses (Addresses.IsActive = 1, RefAddress.Active = 1) of in-scope Clients, Owner-source master files or VpUser-linked master files; distinct over address text, contacts and Temp key. | `FROM RefAddress AS RA LEFT JOIN Addresses AS A ON RA.AddrNr = A.AddrNr WHERE A.IsActive = 1 AND RA.Active = 1 AND RA.Cancelled IS NULL AND (RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1) OR RA.RefCode IN (SELECT RefCode FROM EntityOwners UNION SELECT AddrCode FROM Share_Interests WHERE IntType = 'BEO' UNION SELECT AddrCode FROM Officers WHERE OfficerType = 'ADM') OR RA.RefCode IN (SELECT RelMfCode FROM VpUser))` | Bring over office addresses of in-scope Clients, Owners and Resources. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Addresses (lookup) | LEFT JOIN Addresses ON AddrNr = RefAddress.AddrNr | [Address], [Address 2], [City], [County], [Country], [Post Code], [Temp] |
| RefContacts (lookup) | Scalar sub-queries on RefContacts WHERE RefCode = RA.RefCode AND cType = 'TB' / 'FB' / 'EB' / 'WB' (and RA.Active = 1); TOP 1 check on the same types decides the [Temp] key | [Phone No_], [Fax No_], [E-Mail], [Home Page], [Temp] |

## Column mapping highlights
- [Code] = 'ADD' + 6-digit ROW_NUMBER() ordered by Address; [County] = Addresses.State
- [Temp] = AddrNr + 'GEN' when the RefCode has no TB/FB/EB/WB contact, otherwise AddrNr + RefCode

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtOfficeAddress'
GO

INSERT INTO [MT Office Address]
(
    [NAV_Entry No]
    , [Code]
    , [Description]
    , [Address]
    , [Address 2]
    , [City]
    , [County]
    , [Country]
    , [Post Code]
    , [Phone No_]
    , [Fax No_]
    , [E-Mail]
    , [Home Page]
    , [Telex No_]
    , [Telex Answer Back]
    , [Contact Name]
    , [Temp]
    , [Temporary Address]
    , [Care-of]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY OfficeAddress.[Address]) AS [NAV_EntryNo]
    , 'ADD' + RIGHT('000000' + CONVERT(VARCHAR, ROW_NUMBER() OVER(ORDER BY OfficeAddress.[Address])), 6) AS [Code]
    , OfficeAddress.*
FROM(
    SELECT DISTINCT
        A.[Description]

        , CONCAT(A.Address, CASE
            WHEN A.Address2 IS NOT NULL AND A.Address2 <> '' THEN CONCAT(', ', A.Address2)
            ELSE ''
        END) AS [Address]

        , CONCAT(
            A.Address3
            , CASE
                WHEN A.Address4 IS NOT NULL AND A.Address4 <> '' THEN CONCAT(', ', A.Address4)
                ELSE ''
            END
            , CASE
                WHEN A.Address5 IS NOT NULL AND A.Address5 <> '' THEN CONCAT(', ', A.Address5)
                ELSE ''
            END
        ) AS [Address 2]

        , A.[City]
        , A.[State] AS [County]
        , A.[Country] AS [Country]
        , A.PostalCode AS [Post Code]

        ,(
            SELECT C.cText FROM RefContacts AS C
            WHERE RA.RefCode = C.RefCode AND C.cType = 'TB' AND RA.Active = 1
        ) AS [Phone No_]

        ,(
            SELECT C.cText FROM RefContacts AS C
            WHERE RA.RefCode = C.RefCode AND C.cType = 'FB' AND RA.Active = 1
        ) AS [Fax No_]

        ,(
            SELECT C.cText FROM RefContacts AS C
            WHERE RA.RefCode = C.RefCode AND C.cType = 'EB' AND RA.Active = 1
        ) AS [E-Mail]

        ,(
            SELECT C.cText FROM RefContacts AS C
            WHERE RA.RefCode = C.RefCode AND C.cType = 'WB' AND RA.Active = 1
        ) AS [Home Page]

        , NULL AS [Telex No_]
        , NULL AS [Telex Answer Back]
        , NULL AS [Contact Name]

        , CASE
            WHEN(
                SELECT TOP 1 C.cText FROM RefContacts AS C
                WHERE RA.RefCode = C.RefCode AND C.cType IN('TB', 'FB', 'EB', 'WB')
            ) IS NULL THEN CONCAT(A.AddrNr, 'GEN')
            ELSE CONCAT(A.AddrNr, RA.RefCode)
        END AS [Temp]

        , NULL AS [Temporary Address]
        , NULL AS [Care-of]
    FROM RefAddress AS RA
    LEFT JOIN Addresses AS A ON RA.AddrNr = A.AddrNr
    WHERE
        A.IsActive = 1 AND RA.Active = 1 AND RA.Cancelled IS NULL
        AND(
            RA.RefCode IN(
                SELECT RefCode
                FROM dbo.fnGetInScopeClients()
                WHERE IsClient = 1
            )
            OR RA.RefCode IN(
                SELECT RefCode FROM EntityOwners
                UNION
                SELECT AddrCode FROM Share_Interests
                WHERE IntType = 'BEO'
                UNION
                SELECT AddrCode FROM Officers
                WHERE OfficerType = 'ADM'
            )
            OR RA.RefCode IN(SELECT RelMfCode FROM VpUser)
        )
) AS OfficeAddress

GO
```
