---
staging_table: MT Entity Contact
etl_script: InsertMtEntityContact.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: RefMaster.RefCode IsEntity = 1 (non-individual)
exact_sources: [RefMaster self-join (EmployerMf)]
lookup_sources: [Compliance (lookup), RefContacts (lookup)]
---
# MT Entity Contact

## Overview
Migrates the contact person (employer link) of each in-scope non-individual Entity Master File: contact name, title, job title, phone numbers, e-mail and date of birth.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtEntityContact.sql` into staging table `[MT Entity Contact]`.

## Scope filter
Only in-scope Entities: `RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1)` and non-individual (`RM.RefType <> 'I'`).

## Row count behaviour
SELECT DISTINCT of one row per entity RefCode + its contact person (RefMaster self-join on EmployerMf).

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| RefMaster self-join (EmployerMf) | Non-individual in-scope entities that have an employer/contact link to another master file record. | `FROM RefMaster AS RM INNER JOIN RefMaster AS CP ON RM.EmployerMf = CP.RefCode WHERE RM.RefCode IN (SELECT RefCode FROM dbo.fnGetInScopeClients() WHERE IsEntity = 1) AND RM.RefType <> 'I'` | Bring over the contact person (employer) relations of in-scope Entity Master Files. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Compliance (lookup) | LEFT JOIN Compliance ON AddrCode = CP.RefCode (contact person) | [Job Title], [Date of Birth] |
| RefContacts (lookup) | Scalar sub-queries on RefContacts WHERE RefCode = CP.RefCode AND cType = 'TD' / 'FB' / 'TM' / 'TH' / 'EB' | [Direct Phone No_], [Direct Fax No_], [Mobile Phone No_], [Home Phone No_], [E-Mail] |

## Column mapping highlights
- CP.Title -> [Title]; CP.Name -> [Surname]; CP.SearchName -> [Search Name]; CP.Initials -> [Forename(s)]
- [Primary Contact] = 1 and [Include in Campaigns] = 1 (constants)

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtEntityContact'
GO

INSERT INTO [MT Entity Contact]
(
    [Entity No_]
    , [No_]
    , [Title]
    , [Surname]
    , [Search Name]
    , [Job Title]
    , [Primary Contact]
    , [Direct Phone No_]
    , [Direct Fax No_]
    , [Mobile Phone No_]
    , [Home Phone No_]
    , [Include in Campaigns]
    , [E-Mail]
    , [Forename(s)]
    , [Date of Birth]
    , [NAV_Entry No]
)
SELECT
    EntityContact.*
    , ROW_NUMBER() OVER(ORDER BY EntityContact.[Entity No_]) AS [NAV_Entry No]
FROM(
    SELECT DISTINCT
        RM.RefCode AS [Entity No_]
        , NULL AS [No_]
        , CP.Title AS [Title]
        , CP.Name AS [Surname]
        , CP.SearchName AS [Search Name]
        , C.Occupation AS [Job Title]
        , 1 AS [Primary Contact]
        ,(
            SELECT cText FROM RefContacts AS RC
            WHERE RC.RefCode = CP.RefCode AND cType = 'TD'
        ) AS [Direct Phone No_]
        ,(
            SELECT cText FROM RefContacts AS RC
            WHERE RC.RefCode = CP.RefCode AND cType = 'FB'
        ) AS [Direct Fax No_]
        ,(
            SELECT cText FROM RefContacts AS RC
            WHERE RC.RefCode = CP.RefCode AND cType = 'TM'
        ) AS [Mobile Phone No_]
        ,(
            SELECT cText FROM RefContacts AS RC
            WHERE RC.RefCode = CP.RefCode AND cType = 'TH'
        ) AS [Home Phone No_]
        , 1 AS [Include in Campaigns]
        ,(
            SELECT cText FROM RefContacts AS RC
            WHERE RC.RefCode = CP.RefCode AND cType = 'EB'
        ) AS [E-Mail]
        , CP.Initials AS [Forename(s)]
        , C.BirthDate AS [Date of Birth]
    FROM RefMaster AS RM
    INNER JOIN RefMaster AS CP ON RM.EmployerMf = CP.RefCode
    LEFT JOIN Compliance AS C ON CP.RefCode = C.AddrCode
    WHERE RM.RefCode IN(
        SELECT RefCode FROM dbo.fnGetInScopeClients()
        WHERE IsEntity = 1
    ) AND RM.RefType <> 'I'
) AS EntityContact

GO
```
