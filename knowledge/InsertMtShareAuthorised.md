---
staging_table: MT Share Authorised
etl_script: InsertMtShareAuthorised.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Share_Capital.EntCode) and RefMaster.Status = '0'
exact_sources: [Share_Transactions (AU, first per class)]
lookup_sources: [Share_Capital (lookup)]
---
# MT Share Authorised

## Overview
Migrates the INITIAL authorised share capital of each share class (class, currency, par value, authorised shares and date, authorised share limits, votes per share) for active in-scope Clients. Later increases / decreases of authorised capital are migrated through MT Share Transaction.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtShareAuthorised.sql` into staging table `[MT Share Authorised]`.

## Scope filter
`SC.EntCode IN (SELECT RefCode FROM fnGetInScopeClients() WHERE IsClient = 1)` and the client's RefMaster.Status = '0' (active). No hard-coded client exclusion exists in this version.

## Row count behaviour
One staging row per (EntCode, ShareClass) first 'AU' transaction joined to Share_Capital. Multiple Share_Capital rows for the same EntCode + ShareClass would produce multiple rows.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Share_Transactions (AU, first per class) | The first 'AU' (authorisation) transaction per client + share class (lowest IssueNr), for active in-scope clients, joined to Share_Capital; General Partner / Limited Partner share types excluded. | `FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY EntCode, ShareClass ORDER BY IssueNr) AS AuthRN FROM Share_Transactions WHERE TransType = 'AU') AS ST INNER JOIN Share_Capital AS SC ON ST.EntCode = SC.EntCode AND ST.ShareClass = SC.ShareClass INNER JOIN RefMaster AS RM ON SC.EntCode = RM.RefCode AND RM.Status = '0' AND SC.ShareTypeCode NOT IN ('/G','/L') AND SC.EntCode IN (SELECT RefCode FROM fnGetInScopeClients() WHERE IsClient = 1) WHERE ST.AuthRN = 1` | Bring over the initial authorisation of each share class for active in-scope clients. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Share_Capital (lookup) | INNER JOIN Share_Capital ON EntCode + ShareClass of the initial AU transaction (ShareTypeCode NOT IN ('/G','/L')) | [Class of Share], [Currency Code], [Par Value], [Class Type], [Authorised Share Limits], [Votes Per Share] |

## Column mapping highlights
- [Class Type] = 1 for OwnType SA/SS/XS, 2 for SB/SN/XB, otherwise 0
- [Authorised Share Limits] = '1' / '3' / '99' / 'DUMMY' derived from OwnType and the sign of Share_Capital.NrShare
- ST.NrShare -> [Authorised Shares]; ST.TransferDate -> [Authorised Date]

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtShareAuthorised'
GO

INSERT INTO [MT Share Authorised]
(
    [Entry No_]
    , [Ext_ Client Code]
    , [Class of Share]
    , [Currency Code]
    , [Par Value]
    , [Class Type]
    , [Authorised Shares]
    , [Authorised Date]
    , [Authorised Share Limits]
    , [Printed Certificate No_ Series]
    , [Transaction Processed]
    , [Amount Rnd_ Precision]
    , [Amount Dec_ Places]
    , [Units Rnd_ Precision]
    , [Units Dec_ Places]
    , [Uncertificated]
    , [Votes Per Share]
)
SELECT
    ROW_NUMBER() OVER(ORDER BY(SELECT NULL)) AS [Entry No_] -- Auto-incrementing row number. Logic yet to be dicussed
    , SC.EntCode AS [Ext_ Client Code]
    , SC.ShareClassName AS [Class of Share]
    , SC.Currency AS [Currency Code]
    , SC.NomValShare AS [Par Value]

    , CASE
        WHEN SC.OwnType IN('SA', 'SS', 'XS') THEN 1
        WHEN SC.OwnType IN('SB', 'SN', 'XB') THEN 2
        ELSE 0
    END AS [Class Type]

    , ST.NrShare AS [Authorised Shares]
    , ST.TransferDate AS [Authorised Date]

    , CASE
        WHEN SC.OwnType = 'SA' THEN '1'
        WHEN SC.OwnType = 'SB' THEN '1'
        WHEN SC.OwnType = 'SN' THEN '3'
        WHEN SC.OwnType = 'SS' THEN '3'
        WHEN SC.OwnType = 'XA' THEN '1'
        WHEN SC.OwnType = 'XB' AND Sc.NrShare > 0 THEN '1'
        WHEN SC.OwnType = 'XB' AND Sc.NrShare < 0 THEN '3'
        WHEN SC.OwnType = 'XC' AND Sc.NrShare > 0 THEN '1'
        WHEN SC.OwnType = 'XC' AND Sc.NrShare < 0 THEN '3'
        WHEN SC.OwnType = 'XN' THEN '3'
        WHEN SC.OwnType = 'XS' AND Sc.NrShare > 0 THEN '1'
        WHEN SC.OwnType = 'XS' AND Sc.NrShare < 0 THEN '3'
        WHEN SC.OwnType IS NULL THEN '99' -- No Ownership Structure found
        ELSE 'DUMMY'
    END AS [Authorised Share Limits]

    , 'SHR' AS [Printed Certificate No_ Series]
    , '1' AS [Transaction Processed]
    , '1' AS [Amount Rnd_ Precision]
    , '3' AS [Amount Dec_ Places]
    , '1' AS [Units Rnd_ Precision]
    , '1' AS [Units Dec_ Places]
    , 1 AS [Uncertificated]
    , SC.VotesPerShare AS [Votes Per Share]
FROM(
    -- Keep only the INITIAL authorisation per Entity + Share Class (lowest IssueNr).
    -- Excludes subsequent increase/decrease authorisations.
    SELECT
        *
        , ROW_NUMBER() OVER(PARTITION BY EntCode, ShareClass ORDER BY IssueNr) AS AuthRN
    FROM Share_Transactions
    WHERE TransType = 'AU'
) AS ST
INNER JOIN Share_Capital AS SC ON ST.EntCode = SC.EntCode AND ST.ShareClass = SC.ShareClass
INNER JOIN RefMaster AS RM
    ON
        SC.EntCode = RM.RefCode AND RM.Status = '0' AND SC.ShareTypeCode NOT IN('/G', '/L')
        AND SC.EntCode IN(
            SELECT RefCode FROM fnGetInScopeClients()
            WHERE IsClient = 1
        )
WHERE ST.AuthRN = 1

GO
```
