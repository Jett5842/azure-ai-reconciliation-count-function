---
staging_table: MT CM Address
etl_script: InsertMtCmAddress.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (RefAddress.RefCode)
exact_sources: [RefAddress + Addresses]
lookup_sources: [Addresses (lookup), AddrRegion (lookup)]
---
# MT CM Address

## Overview
Migrates the client Billing (BI) addresses of in-scope Client Master Files (address lines, city, county, post code, country).

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtCmAddress.sql` into staging table `[MT CM Address]`.

## Scope filter
Only billing addresses of in-scope Clients: `RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
SELECT DISTINCT over the address text columns and client code, so repeated identical billing addresses collapse into one row.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefAddress + Addresses | Active billing addresses (address type 'BI') that are not cancelled, of in-scope clients; duplicates removed. | `FROM RefAddress AS RA LEFT JOIN Addresses AS A ON RA.AddrNr = A.AddrNr LEFT JOIN AddrRegion AS CR ON A.RegionNr = CR.RegionNr WHERE A.IsActive = 1 AND RA.AddrType = 'BI' AND RA.Cancelled IS NULL AND RA.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the Billing (BI) address of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Addresses (lookup) | LEFT JOIN Addresses ON AddrNr = RefAddress.AddrNr (IsActive = 1) | [Address], [Address 2], [City], [Post Code], [Country Code] |
| AddrRegion (lookup) | LEFT JOIN AddrRegion ON RegionNr = Addresses.RegionNr | [County] |

## Column mapping highlights
- [Address] = Address + ', ' + Address2 when Address2 is filled; [Address 2] = Address3 + Address4 + Address5 joined with ', '
- [Address Type] = constant 0; [Addressee] = empty string

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtCmAddress'
GO

INSERT INTO [MT CM Address]
(
    [NAV_Entry No]
    , [Client No_ _ Customer No_]
    , [Addressee]
    , [Address]
    , [Address 2]
    , [City]
    , [County]
    , [Post Code]
    , [Country Code]
    , [Address Type]
    , [Salutation]
    , [Contact Name]
    , [Phone No_]
    , [Fax No_]
    , [E-Mail]
    , [Care-of]
    , [Update Customer Card]
    , [Exclude from Country Search]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY BillingAddress.[Address]) AS [NAV_EntryNo]
    , BillingAddress.*
FROM(
    SELECT DISTINCT
        RA.RefCode AS [Client No_ _ Customer No_]
        , '' AS [Addressee]

        , CONCAT(
            A.Address
            , CASE
                WHEN A.Address2 IS NOT NULL AND A.Address2 <> '' THEN CONCAT(', ', A.Address2)
                ELSE ''
            END
        ) AS [Address]

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
        , CR.RegionDesc AS [County]
        , A.PostalCode AS [Post Code]
        , A.Country AS [Country Code]
        , 0 AS [Address Type]
        , NULL AS [Salutation]
        , NULL AS [Contact Name]
        , NULL AS [Phone No_]
        , NULL AS [Fax No_]
        , NULL AS [E-Mail]
        , NULL AS [Care-of]
        , NULL AS [Update Customer Card]
        , NULL AS [Exclude from Country Search]
    FROM RefAddress AS RA
    LEFT JOIN Addresses AS A ON RA.AddrNr = A.AddrNr
    LEFT JOIN AddrRegion AS CR ON A.RegionNr = CR.RegionNr
    WHERE
        A.IsActive = 1
        AND RA.AddrType = 'BI'
        AND RA.Cancelled IS NULL
        AND RA.RefCode IN(
            SELECT RefCode FROM dbo.fnGetInScopeClients()
            WHERE IsClient = 1
        )
) AS BillingAddress

GO
```
