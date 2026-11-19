---
staging_table: MT Owner Clients
etl_script: InsertMtOwnerClients.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Client No_)
exact_sources: [1) EntityOwners, 2) EntityOwners + Officers, 3) EntityOwners + Share_Interests, 4) Share_Interests, 5) Share_Interests + Officers, 6) Officers, 7) EntityOwners + Share_Interests + Officers]
lookup_sources: []
---
# MT Owner Clients

## Overview
Migrates the link between Owners and in-scope Client Master Files (linked date, exit date, ownership percentage). An Owner-Client pair can come from three Vpoint sources: EntityOwners, Share_Interests (BEO/MST/UBO) and Officers (ADM). The three branches are combined with UNION.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtOwnerClients.sql` into staging table `[MT Owner Clients]`.

## Scope filter
Only owner links of in-scope Clients: `OC.[Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
UNION of 3 branches (duplicates removed on Owner + Client + Linked Date + Exit Date + Ownership Percentage), then the client scope filter. Ownership percentage is multiplied by 100. In the reconciliation each pair is reported under the combination of sources it appears in.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| 1) EntityOwners | Pair found only in EntityOwners. | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 2) EntityOwners + Officers | Pair found in EntityOwners and Officers (ADM) but not Share_Interests. | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 3) EntityOwners + Share_Interests | Pair found in EntityOwners and Share_Interests but not Officers. | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 4) Share_Interests | Pair found only in Share_Interests (IntType BEO/MST/UBO). | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 5) Share_Interests + Officers | Pair found in Share_Interests and Officers (ADM) but not EntityOwners. | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 6) Officers | Pair found only in Officers (OfficerType ADM). | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |
| 7) EntityOwners + Share_Interests + Officers | Pair found in all three sources. | `Branches: EntityOwners (no filter) UNION Share_Interests WHERE IntType IN ('BEO','MST','UBO') UNION Officers WHERE OfficerType IN ('ADM'); then WHERE [Client No_] IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Owner-Client pair that qualifies through exactly this combination of sources. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- EntityOwners: RefCode -> Owner, EntCode -> Client, DateFrom/DateTo -> Linked/Exit Date, PercInterest -> Ownership Percentage
- Share_Interests: AddrCode -> Owner, EntCode -> Client, DateStart/DateEnd, PercentCap
- Officers (ADM): AddrCode -> Owner, EntCode -> Client, DateAppoint/DateResign, Ownership Percentage NULL

## Notes for reconciliation
- The seven source labels are mutually exclusive categories of the same staging rows, not seven separate tables. The sum of the categories is the Exact total.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtOwnerClients'
GO

INSERT INTO [MT Owner Clients]
(
    [NAV_Entry No]
    , [Owner No_]
    , [Client No_]
    , [Line No_]
    , [Comments]
    , [Linked  Date]
    , [Exit Date]
    , [Ownership Percentage]
    , [Primary Client Owner]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY OC.[Owner No_] ASC) AS [NAV_Entry No]
    , OC.[Owner No_]
    , OC.[Client No_]
    , OC.[Line No_]
    , OC.[Comments]
    , OC.[Linked  Date]
    , OC.[Exit Date]
    , OC.[Ownership Percentage] * 100 AS [Ownership Percentage]
    , OC.[Primary Client Owner]
FROM
    (
        SELECT
            E.RefCode AS [Owner No_]
            , E.EntCode AS [Client No_]
            , NULL AS [Line No_]
            , NULL AS [Comments]
            , E.DateFrom AS [Linked  Date]
            , E.DateTo AS [Exit Date]
            , E.PercInterest AS [Ownership Percentage]
            , NULL AS [Primary Client Owner]
        FROM EntityOwners AS E

        UNION

        SELECT
            S.AddrCode AS [Owner No_]
            , S.EntCode AS [Client No_]
            , NULL AS [Line No_]
            , NULL AS [Comments]
            , S.DateStart AS [Linked  Date]
            , S.DateEnd AS [Exit Date]
            , S.PercentCap AS [Ownership Percentage]
            , NULL AS [Primary Client Owner]
        FROM Share_Interests AS S
        WHERE S.IntType IN('BEO', 'MST', 'UBO')

        UNION

        SELECT
            O.AddrCode AS [Owner No_]
            , O.EntCode AS [Client No_]
            , NULL AS [Line No_]
            , NULL AS [Comments]
            , O.DateAppoint AS [Linked  Date]
            , O.DateResign AS [Exit Date]
            , NULL AS [Ownership Percentage]
            , NULL AS [Primary Client Owner]
        FROM Officers AS O
        WHERE O.OfficerType IN('ADM')
    ) AS OC

WHERE
    OC.[Client No_] IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
