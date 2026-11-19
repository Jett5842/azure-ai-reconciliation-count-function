---
staging_table: MT Safe Custody Records
etl_script: InsertMtSafeCustodyRecords.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (DocuIndex.EntCode)
exact_sources: [DocuIndex]
lookup_sources: []
---
# MT Safe Custody Records

## Overview
Migrates the safe custody document records (description, dates, barcode, signatories, category, review dates, packet number) of in-scope Client Master Files from the Vpoint document index.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtSafeCustodyRecords.sql` into staging table `[MT Safe Custody Records]`.

## Scope filter
Only documents of in-scope Clients: `EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per DocuIndex row of an in-scope client. No DISTINCT; the LEFT JOIN to fnGetInScopeClients is 1:1.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| DocuIndex | All document index rows of in-scope clients. No extraction filter other than the client scope. | `FROM DocuIndex AS DI LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON DI.EntCode = GISC.RefCode WHERE EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the safe custody document records of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- Content -> first 150 characters in [Description], the rest in [Additional Description]
- DateStarted -> [Date of Document]; RefNumber -> [Barcode]; Signatories -> [Document Signed By]; Category / SubCategory -> [Safe Custody Type / Sub Type]; DateRenewal -> [Last Review Date]; DateDue -> [Next Review Date]; DocNumber -> [Packet Number]
- [Safe Custody Code] = 'SC' + 4-digit ROW_NUMBER() OVER (PARTITION BY EntCode ORDER BY EntCode)

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtSafeCustodyRecords'
GO

INSERT INTO [MT Safe Custody Records]
(
    [Type]
    , [No_]
    , [Safe Custody Code]
    , [Description]
    , [Date of Document]
    , [Expiry Date of Document]
    , [Temporarily Held By]
    , [Barcode]
    , [Date Sent]
    , [Date Received]
    , [Document Signed By]
    , [Value]
    , [Safe Custody Type]
    , [Safe Custody Sub Type]
    , [Dual Control User 1]
    , [Dual Control User 2]
    , [Safe Custody Agreement]
    , [Insurance Required]
    , [Fees]
    , [Last Review Date]
    , [Last Review By]
    , [Next Review Date]
    , [Packet Number]
    , [Last Date Received]
    , [Last Received By]
    , [Additional Description]
    , [Risk]
    , [Multiple Items Detail]
    , [Status]
    , [Valuation Currency]
    , [Temporarily Held Date]
    , [External Reference No_]
    , [NAV_Entry No]
)
SELECT
    CASE
        WHEN GISC.IsClient = 1 THEN 0
        WHEN GISC.IsEntity = 1 THEN 3
        WHEN GISC.IsResource = 1 THEN 4
    END AS [Type]

    , EntCode AS [No_]
    , CONVERT (NVARCHAR(20), 'SC' + RIGHT('0000' + CONVERT (VARCHAR, ROW_NUMBER() OVER(PARTITION BY EntCode ORDER BY EntCode)), 4)) AS [Safe Custody Code]
    , LEFT(Content, 150) AS [Description]
    , DateStarted AS [Date of Document]
    , NULL AS [Expiry Date of Document]
    , NULL AS [Temporarily Held By]
    , RefNumber AS [Barcode]
    , NULL AS [Date Sent]
    , NULL AS [Date Received]
    , Signatories AS [Document Signed By]
    , NULL AS [Value]
    , Category AS [Safe Custody Type]
    , SubCategory AS [Safe Custody Sub Type]
    , NULL AS [Dual Control User 1]
    , NULL AS [Dual Control User 2]
    , 0 AS [Safe Custody Agreement]
    , 0 AS [Insurance Required]
    , 0 AS [Fees]
    , DateRenewal AS [Last Review Date]
    , NULL AS [Last Review By]
    , DateDue AS [Next Review Date]
    , DocNumber AS [Packet Number]
    , NULL AS [Last Date Received]
    , NULL AS [Last Received By]
    , IIF(LEN(Content) > 150, SUBSTRING(Content, 151, LEN(Content) - 150), NULL) AS [Additional Description]
    , NULL AS [Risk]
    , NULL AS [Multiple Items Detail]
    , NULL AS [Status]
    , NULL AS [Valuation Currency]
    , NULL AS [Temporarily Held Date]
    , NULL AS [External Reference No_]
    , ROW_NUMBER() OVER(ORDER BY EntCode) AS [NAV_Entry No]
FROM DocuIndex AS DI LEFT JOIN dbo.fnGetInScopeClients() AS GISC ON DI.EntCode = GISC.RefCode
WHERE
    EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
