---
staging_table: MT Beneficiary Details
etl_script: InsertMtBeneficiaryDetails.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (EntCode)
exact_sources: [Beneficiaries]
lookup_sources: []
---
# MT Beneficiary Details

## Overview
Migrates the beneficiary entitlement details (who benefits, level/order, entitlements, conditions) of each in-scope Client Master File from the Vpoint Beneficiaries table. Only the core columns are filled; all partnership / membership / deed columns are set to NULL.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtBeneficiaryDetails.sql` into staging table `[MT Beneficiary Details]`.

## Scope filter
Only beneficiaries of in-scope Client Master Files: `EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)`.

## Row count behaviour
One staging row per Beneficiaries row of an in-scope client. No DISTINCT, no join, so staging count = source count after the scope filter.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Beneficiaries | Every beneficiary row of an in-scope client. No extraction filter other than the client scope. | `FROM Beneficiaries WHERE EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1)` | Bring over the beneficiary details of in-scope Client Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- EntCode -> [Client No]; Beneficiary -> [Entity No]; BenfLevel -> [Order]; Benefits -> [Entitlement Details]; DateAppoint -> [Effective Date]; Note -> [Condtions]; BenfType -> [Capital_Income]
- [Type of Beneficiary] = constant 0; [NAV_Entry No] = ROW_NUMBER() OVER (ORDER BY EntCode)

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtBeneficiaryDetails'
GO

INSERT INTO [MT Beneficiary Details]
(
    [Client No]
    , [Entity No]
    , [Order]
    , [Guardian Code]
    , [Entitlement Details]
    , [Effective Date]
    , [Condtions]
    , [Beneficiary Classif_ Code]
    , [Kind of Distribution]
    , [Description of Distribution]
    , [Comments]
    , [Percentage Of Membership]
    , [Membership Certificate No_]
    , [Date Of Issue]
    , [Certificate of Formation]
    , [Partnersh__Operating Agreement]
    , [Partnership Type]
    , [Amount Committed]
    , [Commitment Currency]
    , [Date Registered]
    , [Transfer Out Date]
    , [Nature Of Interest]
    , [Limit Of Interest]
    , [Capital_Income]
    , [Date Of Majority For Minors]
    , [Type of Deed]
    , [Type of Beneficiary]
    , [_ Share of Fund]
    , [Gross or Net]
    , [Entitlement to Capital]
    , [Entitlement to Income]
    , [NAV_Entry No]
)
SELECT
    EntCode AS [Client No]
    , Beneficiary AS [Entity No]
    , BenfLevel AS [Order]
    , NULL AS [Guardian Code]
    , Benefits AS [Entitlement Details]
    , DateAppoint AS [Effective Date]
    , Note AS [Condtions]
    , NULL AS [Beneficiary Classif_ Code]
    , NULL AS [Kind of Distribution]
    , NULL AS [Description of Distribution]
    , NULL AS [Comments]
    , NULL AS [Percentage Of Membership]
    , NULL AS [Membership Certificate No_]
    , NULL AS [Date Of Issue]
    , NULL AS [Certificate of Formation]
    , NULL AS [Partnersh__Operating Agreement]
    , NULL AS [Partnership Type]
    , NULL AS [Amount Committed]
    , NULL AS [Commitment Currency]
    , NULL AS [Date Registered]
    , NULL AS [Transfer Out Date]
    , NULL AS [Nature Of Interest]
    , NULL AS [Limit Of Interest]
    , BenfType AS [Capital_Income]
    , NULL AS [Date Of Majority For Minors]
    , NULL AS [Type of Deed]
    , 0 AS [Type of Beneficiary]
    , NULL AS [_ Share of Fund]
    , NULL AS [Gross or Net]
    , NULL AS [Entitlement to Capital]
    , NULL AS [Entitlement to Income]
    , ROW_NUMBER() OVER(ORDER BY EntCode) AS [NAV_Entry No]
FROM Beneficiaries
WHERE
    EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )

GO
```
