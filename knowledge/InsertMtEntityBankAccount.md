---
staging_table: MT Entity Bank Account
etl_script: InsertMtEntityBankAccount.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: Beneficiary IsEntity = 1 AND EntCode IsClient = 1
exact_sources: [Beneficiaries (DISTINCT)]
lookup_sources: []
---
# MT Entity Bank Account

## Overview
Migrates bank accounts that belong to beneficiary entities (account holder, bank code, account number) between in-scope Client and Entity Master Files.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtEntityBankAccount.sql` into staging table `[MT Entity Bank Account]`.

## Scope filter
Dual scope: `Beneficiary IN (... IsEntity = 1)` AND `EntCode IN (... IsClient = 1)` from dbo.fnGetInScopeClients().

## Row count behaviour
SELECT DISTINCT over the selected columns, so identical bank account rows collapse into one. Staging count <= number of Beneficiaries rows that pass the filters.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Beneficiaries (DISTINCT) | Beneficiary rows that have a bank address code, where the beneficiary is an in-scope entity and the client is in scope. Duplicate account rows are removed. | `SELECT DISTINCT ... FROM Beneficiaries WHERE Beneficiary IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1) AND EntCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsClient = 1) AND BAddrCode IS NOT NULL` | Bring over bank account holder relations between in-scope Client and Entity Master Files. |

## Lookup sources (values only, no staging rows)
None - this script reads only the exact source(s) above.

## Column mapping highlights
- Beneficiary -> [Entity No_]; BAddrCode -> [System Bank Code]; BaNumber -> [Bank Account Number]; AccountHolder -> [Account Name]
- [Blocked], [Closed], [Default Distribution Account], [Default Payment Account] = constant 0

## Notes for reconciliation
- DISTINCT includes only the selected columns, so a repeated bank/account for the same beneficiary under several clients counts once.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtEntityBankAccount'
GO

INSERT INTO [MT Entity Bank Account]
(
    [Entity No_]
    , [Bank ID]
    , [System Bank Code]
    , [Account Currency]
    , [Primary Bank]
    , [Last Date Modified]
    , [Bank Account IBAN]
    , [Bank Account Number]
    , [Blocked]
    , [Account Name]
    , [Account Description]
    , [Default Distribution Account]
    , [Default Payment Account]
    , [External Payment Type]
    , [Default Customer Reference]
    , [Closed]
    , [Date_Time Last Validated]
    , [Validating User ID]
    , [NAV_Entry No]
)
SELECT DISTINCT
    Beneficiary AS [Entity No_]
    , NULL AS [Bank ID]
    , BAddrCode AS [System Bank Code]
    , NULL AS [Account Currency]
    , NULL AS [Primary Bank]
    , NULL AS [Last Date Modified]
    , NULL AS [Bank Account IBAN]
    , BaNumber AS [Bank Account Number]
    , 0 AS [Blocked]
    , AccountHolder AS [Account Name]
    , NULL AS [Account Description]
    , 0 AS [Default Distribution Account]
    , 0 AS [Default Payment Account]
    , NULL AS [External Payment Type]
    , NULL AS [Default Customer Reference]
    , 0 AS [Closed]
    , NULL AS [Date_Time Last Validated]
    , NULL AS [Validating User ID]
    , ROW_NUMBER() OVER(ORDER BY Beneficiary) AS [NAV_Entry No]
FROM Beneficiaries
WHERE
    Beneficiary IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsEntity = 1
    )
    AND EntCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsClient = 1
    )
    AND BAddrCode IS NOT NULL

GO
```
