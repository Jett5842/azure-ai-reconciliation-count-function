---
staging_table: MT Client Alternate Directors
etl_script: InsertMtClientAlternateDirectors.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Officers.EntCode)
exact_sources: [Officers]
lookup_sources: [RefMaster (lookup)]
---
# MT Client Alternate Directors

## Overview
Migrates Alternate Director relations (officer type DAL) of in-scope Client Master Files, including the director being covered (RelatedAddress), appointment/resignation dates and retirement date.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtClientAlternateDirectors.sql` into staging table `[MT Client Alternate Directors]`.

## Scope filter
Only officers linked to in-scope Client Master Files: `O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per Officers row with OfficerType = 'DAL' of an in-scope client (active and resigned both included). The LEFT JOINs to RefMaster and fnGetInScopeClients are 1:1 and do not change the count.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Officers | Officers rows whose type is Alternate Director (DAL); both active and resigned records. | `FROM Officers AS O WHERE O.OfficerType = 'DAL' AND O.EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the Alternate Director relations of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| RefMaster (lookup) | LEFT JOIN RefMaster ON RefCode = O.EntCode (client) and ON RefCode = O.AddrCode (entity) | [Client Name], [Entity Name], [Entity Title], [Entity Forename(s)] |

## Column mapping highlights
- EntCode -> [Client No_]; AddrCode -> [Entity No_]; RelatedAddress -> [Related Entity No_]; [Related Entity Type] = constant 'DIR'
- [Date of Retirement] = DateResign only when ReasonResign = '5' (retirement), otherwise NULL
- [Type] / [Related Type] = 1 Client, 0 Entity, 2 Resource, derived from dbo.fnGetInScopeClients() (IsClient / IsEntity / IsResource) for AddrCode and RelatedAddress

## Notes for reconciliation
- The Officers type DAL is excluded from MT Client Entity on purpose (handled here).

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtClientAlternateDirectors'
GO

INSERT INTO [MT Client Alternate Directors]
(
    [NAV_Entry No]
    , [Client No_]
    , [Entity No_]
    , [Related Entity No_]
    , [Related Entity Type]
    , [Client Name] -- entcode.name
    , [Entity Name] -- addrcode.name
    , [Date Appointed]
    , [Notes]
    , [Replaced by Entity]
    , [Date Resigned]
    , [Resignation Notes]
    , [Date of Retirement] -- if reason of resign = retirement, then append with DateResign
    , [Entity Title]
    , [Entity Forename(s)]
    , [Type] -- follow the EntityNo
    , [Related Type] -- follow the RelatedEntityNo
    , [Replaced By Entity Type]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY O.EntCode) AS [NAV_Entry No]
    , O.EntCode AS [Client No_]
    , O.AddrCode AS [Entity No_]
    , O.RelatedAddress AS [Related Entity No_]
    , 'DIR' AS [Related Entity Type]
    , RM.Name AS [Client Name]
    , RM2.Name AS [Entity Name]
    , O.DateAppoint AS [Date Appointed]
    , O.Note AS [Notes]
    , NULL AS [Replaced by Entity]
    , O.DateResign AS [Date Resigned]
    , NULL AS [Resignation Notes]

    , CASE
        WHEN O.ReasonResign = '5' THEN O.DateResign
        ELSE NULL
    END AS [Date of Retirement]

    , RM2.Title AS [EntityTitle]
    , RM2.Initials AS [Entity Forename(s)]

    , CASE
        WHEN GISC.IsClient = 1 THEN 1
        WHEN GISC.IsEntity = 1 THEN 0
        WHEN GISC.IsResource = 1 THEN 2
    END AS [Type]

    , CASE
        WHEN GISC2.IsClient = 1 THEN 1
        WHEN GISC2.IsEntity = 1 THEN 0
        WHEN GISC2.IsResource = 1 THEN 2
    END AS [Related Type]

    , NULL AS [Replaced By Entity Type]
FROM Officers AS O
LEFT JOIN RefMaster AS RM ON O.EntCode = RM.RefCode
LEFT JOIN RefMaster AS RM2 ON O.AddrCode = RM2.RefCode
LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON O.AddrCode = GISC.RefCode
LEFT JOIN dbo.fnGetInScopeClients() AS GISC2 ON O.RelatedAddress = GISC2.RefCode
WHERE
    O.OfficerType = 'DAL' AND O.EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
