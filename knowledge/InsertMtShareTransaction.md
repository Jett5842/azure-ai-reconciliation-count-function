---
staging_table: MT Share Transaction
etl_script: InsertMtShareTransaction.sql
vpoint_module: Entity Administration
vpoint_menu_path: vPoint > Standard > 2. Migration > 1. Entity Administration
source_system: Vpoint (read through synonym; scope helper dbo.fnGetInScopeClients())
scope_filter: IsClient = 1 (Share_Transactions.EntCode); needs [MT Share Authorised] to be loaded first
exact_sources: [Share_Transactions (AL), Share_Transactions (AU, 2nd+ per class), Share_Transactions (CP), Share_Transactions (TR, Transfer To row), Share_Transactions (RC/RF), Share_Transactions (RD), Lot-ledger rows (TR Transfered-From + extra RC/RD lot splits) - derived from staging]
lookup_sources: [Share_Transactions (NC) (lookup), Share_Capital (lookup)]
---
# MT Share Transaction

## Overview
Migrates the share transaction history of in-scope Clients (allotments, transfers, cancellations, redemptions, calls paid and later authorised-capital changes) with certificate numbers, balancing certificates, nominal / added value paid and shareholder type. The script is cursor-driven: a lot ledger first works out which share lots each transfer / redemption draws from, then a second cursor writes the staging rows. The staging table is truncated at the start.

## Module
Vpoint - Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). Loaded by `InsertMtShareTransaction.sql` into staging table `[MT Share Transaction]`.

## Scope filter
Cursor source: `ST.EntCode IN (SELECT RefCode FROM #InScopeClients WHERE IsClient = 1)` (a temp copy of fnGetInScopeClients() with IsClient = 1), posted transactions only, and only share classes that match a row of [MT Share Authorised].

## Row count behaviour
One staging row per cursor transaction for AL, AU (2nd+), CP, RC; one 'Transfer To' row per TR plus one or more 'Transfered From' rows per TR (one per lot drawn); RD and RC rows can be split over several lots; NC (balancing certificate) transactions create no row, they only update the balancing certificate of the related row. The Transfered-From and extra lot-split rows cannot be derived from Vpoint row counts.

## Exact sources (rows taken into the staging table)
Use the label in the first column exactly as written when you report on a source.

| Source label | Extraction condition (plain language) | Technical SQL condition | Business scope |
|---|---|---|---|
| Share_Transactions (AL) | Allotment transactions that pass the cursor filters; 1 row each, Issue Type 0. | `Cursor source: FROM Share_Transactions AS ST INNER JOIN Share_Capital AS SC ON ST.EntCode = SC.EntCode AND ST.ShareClass = SC.ShareClass INNER JOIN ShareAuthorised AS SA ON ST.EntCode = SA.[Ext_ Client Code] AND ST.NomValShare = SA.[Par Value] AND SC.ShareClassName = SA.[Class of Share] AND ST.Currency = SA.[Currency Code] WHERE ST.ShareClass NOT LIKE '%/G%' AND ST.ShareClass NOT LIKE '%/L%' AND ST.Posted = 1 AND ST.EntCode IN (in-scope clients) AND TransType = 'AL'` | Bring over share allotments of in-scope client master files. |
| Share_Transactions (AU, 2nd+ per class) | Authorised-capital changes after the first authorisation of the class (IssueNr greater than the smallest posted AU of the same client and class); Issue Type 7. The first AU is migrated in MT Share Authorised. | `Same cursor source AND ST.TransType = 'AU' AND ST.IssueNr > (SELECT MIN(AU0.IssueNr) FROM Share_Transactions AS AU0 WHERE AU0.EntCode = ST.EntCode AND AU0.ShareClass = ST.ShareClass AND AU0.TransType = 'AU' AND AU0.Posted = 1)` | Bring over later increases / decreases of authorised capital. |
| Share_Transactions (CP) | Calls-paid transactions; 1 row each, Issue Type 6. The amount paid is the difference to the previous certificate's paid amount. | `Same cursor source AND ST.TransType = 'CP'` | Bring over capital payments (calls paid). |
| Share_Transactions (TR, Transfer To row) | Transfer transactions: exactly 1 'Transfer To' row each (Issue Type 2, shareholder = AddrCode, the receiving holder). | `Same cursor source AND ST.TransType = 'TR' (Transfer To row = one per TR)` | Bring over the receiving side of share transfers. |
| Share_Transactions (RC/RF) | Cancellation transactions: at least 1 row each, Issue Type 3 (RC maps to Issue Type 3 in the script; RF has no explicit mapping). | `Same cursor source AND ST.TransType IN ('RC','RF')` | Bring over share cancellations. |
| Share_Transactions (RD) | Redemption transactions: at least 1 row each, Issue Type 4; a redemption drawing on several lots is split into one row per lot. | `Same cursor source AND ST.TransType = 'RD'` | Bring over share redemptions. |
| Lot-ledger rows (TR Transfered-From + extra RC/RD lot splits) - derived from staging | Rows created by the lot ledger: Issue Type 1 (Transfered From, one per lot drawn) plus the extra Issue Type 3 / 4 rows beyond one per RC / RD. Taken from staging, not from Vpoint. | `Counted in [MT Share Transaction]: COUNT(Issue Type = 1) + (COUNT(Issue Type = 3) - cursor RC/RF rows) + (COUNT(Issue Type = 4) - cursor RD rows)` | Rows created by the lot-ledger logic; cannot be derived from Vpoint row counts. |

## Lookup sources (values only, no staging rows)

| Source label | Join / lookup condition | MT columns populated |
|---|---|---|
| Share_Transactions (NC) (lookup) | Cursor rows with TransType = 'NC' (re-certification, Issue Type code 9999 inside the script) | [Balancing Certificate No_] on the related transfer / cancellation / redemption rows; NC rows themselves create no staging row |
| Share_Capital (lookup) | INNER JOIN Share_Capital ON EntCode + ShareClass of the cursor rows | [Class of Share] (class name used to match [MT Share Authorised]) |

## Column mapping highlights
- Issue Type codes: 0 AL (allotment), 1 Transfered From, 2 Transfer To, 3 RC (cancellation), 4 RD (redemption), 6 CP (calls paid), 7 AU (authorised change), 9999 NC (internal marker, no row)
- [Shareholder No_]: AddrCode for AL / RD / RC, PrevOwner for the Transfered-From side, AddrCode for the Transfer-To side
- [Payment Type] = 1 nothing paid, 2 partly paid, 3 fully paid (from Paid vs nominal value + added value); [Authorised Type] = 2 when TransCode 'AU', 3 when 'CR', else 1
- [Entry No_] and [Transaction ID] are generated counters (ROW_NUMBER per client by TransDate)

## Post-insert updates
- UPDATE [ShareHolder Type] = 1 when the shareholder is an in-scope Client, otherwise 0 (join on fnGetInScopeClients())
- Balancing certificate numbers are stamped by NC rows while the cursor runs

## Notes for reconciliation
- Dependency: run InsertMtShareAuthorised first - the cursor INNER JOINs [MT Share Authorised] on client, par value, class name and currency.
- Transaction types that are not mapped to an Issue Type (for example RF) get a NULL Issue Type but still enter the 'other transaction types' branch of the second cursor and insert one row.
- Staging count = AL + AU(2nd+) + CP + TR(to) + RC + RD + lot-ledger extra rows, so it is not a direct count of Vpoint rows.

## Original ETL script (reference - the sections above summarise it)
```sql
PRINT CONVERT(VARCHAR, GETDATE(), 108) + ' >>> InsertMtShareTransaction'
GO

-- FIX: For RC/RD transactions where PrevCertificateNr = CertificateNr,
-- use CertificateNr directly without tracing. This handles the case where
-- a certificate is being cancelled with the same certificate number.

SET NOCOUNT ON
GO

TRUNCATE TABLE [MT Share Transaction]
GO

-- Pre-calculate values to avoid repeated function calls in cursor
IF OBJECT_ID('tempdb..#InScopeClients') IS NOT NULL DROP TABLE #InScopeClients
SELECT
    RefCode
    , IsClient
    , IsEntity
INTO #InScopeClients
FROM fnGetInScopeClients()
WHERE IsClient = 1
CREATE CLUSTERED INDEX IX_Clients ON #InScopeClients(RefCode)

-- Pre-calculate paid amounts for CP transactions to avoid lookups in loop
IF OBJECT_ID('tempdb..#PaidLookup') IS NOT NULL DROP TABLE #PaidLookup
SELECT
    ST.CertificateNr
    , ST.EntCode
    , ST.NrShare
    , ST.Currency
    , ST.PrevCertificateNr
    , ST.IssueNr
    , ST.Paid - COALESCE(PREV.Paid, 0) AS PaidAmount
INTO #PaidLookup
FROM Share_Transactions AS ST WITH(NOLOCK)
LEFT JOIN Share_Transactions AS PREV WITH(NOLOCK)
    ON
        ST.EntCode = PREV.EntCode
        AND ST.NrShare = PREV.NrShare
        AND ST.Currency = PREV.Currency
        AND ST.PrevCertificateNr = PREV.CertificateNr
        AND ST.IssueNr > PREV.IssueNr  -- Ensure we get the chronologically previous transaction
WHERE ST.TransType = 'CP'

CREATE CLUSTERED INDEX IX_Paid ON #PaidLookup(CertificateNr, EntCode, NrShare, Currency)

------------------------------------------------------------------------------
-- LOT-LEDGER PRE-PASS (drives the "Transfered From" side for ALL transfers)
--
-- Each holder's shares are tracked as individual lots, every lot carrying its
-- own remaining balance and its CURRENT certificate (which evolves as partial
-- transfers reduce it and NCs re-certificate the reduced lot). For every
-- outbound TR this produces a breakdown (#TransferFrom) of how the quantity is
-- drawn from the holder's lots:
--   * draw from the OLDEST single lot that can cover the quantity (one row); if
--     none can, draw across lots oldest-first (many-to-one split rows).
--   * each row carries the cert of the lot it drew from.
--   * an NC re-certificates the lot just partially reduced, and that NC cert
--     becomes the balancing cert on the corresponding "from" row.
-- The main cursor below simply reads this breakdown, so CP / AL / RC / RD / NC
-- handling and the overall structure are unchanged.
------------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#Lots') IS NOT NULL DROP TABLE #Lots
CREATE TABLE #Lots
(
    LotId INT IDENTITY(1, 1) PRIMARY KEY
    , EntCode VARCHAR(50)
    , ShareClass VARCHAR(50)
    , Holder VARCHAR(50)
    , OriginIssueNr INT
    , Balance DECIMAL(38, 12)
    , CurrentCert VARCHAR(50)
)

IF OBJECT_ID('tempdb..#TransferFrom') IS NOT NULL DROP TABLE #TransferFrom
CREATE TABLE #TransferFrom
(
    EntCode VARCHAR(50)
    , IssueNr INT
    , LotId INT
    , FromShares DECIMAL(38, 12)
    , FromCert VARCHAR(50)
    , BalancingCert VARCHAR(50)
    , OrderCert INT          -- numeric form of FromCert for deterministic ordering
    , OriginIssueNr INT      -- tie-break for the standardized ordering
)

DECLARE
    @pp_EntCode VARCHAR(50), @pp_ShareClass VARCHAR(50), @pp_IssueNr INT
    , @pp_TransType VARCHAR(2), @pp_AddrCode VARCHAR(50), @pp_PrevOwner VARCHAR(50)
    , @pp_NrShare DECIMAL(38, 12), @pp_Cert VARCHAR(50), @pp_PrevCert VARCHAR(50)
    , @pp_LotId INT, @pp_LotBal DECIMAL(38, 12), @pp_LotCert VARCHAR(50)
    , @pp_LotOrigin INT, @pp_Take DECIMAL(38, 12), @pp_Remaining DECIMAL(38, 12)
    , @pp_Holder VARCHAR(50), @pp_Q DECIMAL(38, 12)
    , @pp_PendLotId INT, @pp_PendHolder VARCHAR(50), @pp_PendEnt VARCHAR(50)
    , @pp_PendClass VARCHAR(50), @pp_PendIssueNr INT

SET @pp_PendLotId = NULL
SET @pp_PendHolder = NULL

DECLARE ledger_cursor CURSOR FOR
SELECT
    ST.EntCode
    , ST.ShareClass
    , ST.IssueNr
    , ST.TransType
    , ST.AddrCode
    , ST.PrevOwner
    , ST.NrShare
    , CONVERT (VARCHAR(50), ST.CertificateNr)
    , CONVERT (VARCHAR(50), ST.PrevCertificateNr)
FROM Share_Transactions AS ST WITH(NOLOCK)
WHERE
    ST.TransType IN('AL', 'TR', 'NC', 'RD')
    AND ST.ShareClass NOT LIKE('%/G%')
    AND ST.ShareClass NOT LIKE('%/L%')
    AND ST.Posted = 1
    AND ST.EntCode IN(
        SELECT RefCode FROM #InScopeClients
        WHERE IsClient = 1
    )
ORDER BY ST.EntCode, ST.ShareClass, ST.IssueNr

OPEN ledger_cursor
FETCH NEXT FROM ledger_cursor INTO
@pp_EntCode, @pp_ShareClass, @pp_IssueNr, @pp_TransType
, @pp_AddrCode, @pp_PrevOwner, @pp_NrShare, @pp_Cert, @pp_PrevCert

WHILE @@FETCH_STATUS = 0
    BEGIN
        IF @pp_TransType = 'AL'
            BEGIN
                INSERT INTO #Lots(EntCode, ShareClass, Holder, OriginIssueNr, Balance, CurrentCert)
                VALUES(@pp_EntCode, @pp_ShareClass, @pp_AddrCode, @pp_IssueNr, @pp_NrShare, @pp_Cert)
            END
        ELSE IF @pp_TransType IN('TR', 'RD')
            BEGIN
                SET @pp_PendLotId = NULL  -- reset pending; a new reduction may set it

                -- Holder whose lots are consumed, and the quantity drawn down:
                --   TR -> the seller (PrevOwner) gives up @NrShare
                --   RD -> the redeemed shareholder (AddrCode) gives up ABS(@NrShare)
                IF @pp_TransType = 'TR'
                    BEGIN SET @pp_Holder = @pp_PrevOwner; SET @pp_Q = @pp_NrShare END
                ELSE
                    BEGIN SET @pp_Holder = @pp_AddrCode; SET @pp_Q = ABS(@pp_NrShare) END

                -- (1) Prefer the oldest single lot that can cover the whole quantity
                SET @pp_LotId = NULL
                SELECT TOP 1
                    @pp_LotId = LotId
                    , @pp_LotBal = Balance
                    , @pp_LotCert = CurrentCert
                    , @pp_LotOrigin = OriginIssueNr
                FROM #Lots
                WHERE
                    EntCode = @pp_EntCode AND ShareClass = @pp_ShareClass
                    AND Holder = @pp_Holder AND Balance >= @pp_Q
                ORDER BY OriginIssueNr ASC, LotId ASC

                IF @pp_LotId IS NOT NULL
                    BEGIN
                        INSERT INTO #TransferFrom(EntCode, IssueNr, LotId, FromShares, FromCert, BalancingCert, OrderCert, OriginIssueNr)
                        VALUES(
                            @pp_EntCode, @pp_IssueNr, @pp_LotId, @pp_Q, @pp_LotCert, NULL
                            , ISNULL(TRY_CAST(@pp_LotCert AS INT), 0), @pp_LotOrigin
                        )
                        UPDATE #Lots SET Balance = Balance - @pp_Q
                        WHERE LotId = @pp_LotId
                        IF(@pp_LotBal - @pp_Q) > 0
                            BEGIN
                                SET @pp_PendLotId = @pp_LotId
                                SET @pp_PendHolder = @pp_Holder
                                SET @pp_PendEnt = @pp_EntCode
                                SET @pp_PendClass = @pp_ShareClass
                                SET @pp_PendIssueNr = @pp_IssueNr
                            END
                    END
                ELSE
                    BEGIN
                        -- (2) No single lot suffices: draw across lots oldest-first
                        SET @pp_Remaining = @pp_Q
                        WHILE @pp_Remaining > 0
                            BEGIN
                                SET @pp_LotId = NULL
                                SELECT TOP 1
                                    @pp_LotId = LotId
                                    , @pp_LotBal = Balance
                                    , @pp_LotCert = CurrentCert
                                    , @pp_LotOrigin = OriginIssueNr
                                FROM #Lots
                                WHERE
                                    EntCode = @pp_EntCode AND ShareClass = @pp_ShareClass
                                    AND Holder = @pp_Holder AND Balance > 0
                                ORDER BY OriginIssueNr ASC, LotId ASC

                                IF @pp_LotId IS NULL BREAK  -- insufficient lots (defensive)

                                SET @pp_Take = CASE WHEN @pp_LotBal <= @pp_Remaining THEN @pp_LotBal ELSE @pp_Remaining END
                                INSERT INTO #TransferFrom(EntCode, IssueNr, LotId, FromShares, FromCert, BalancingCert, OrderCert, OriginIssueNr)
                                VALUES(
                                    @pp_EntCode, @pp_IssueNr, @pp_LotId, @pp_Take, @pp_LotCert, NULL
                                    , ISNULL(TRY_CAST(@pp_LotCert AS INT), 0), @pp_LotOrigin
                                )
                                UPDATE #Lots SET Balance = Balance - @pp_Take
                                WHERE LotId = @pp_LotId
                                SET @pp_Remaining = @pp_Remaining - @pp_Take

                                -- if the final lot is left with a remainder, it is the boundary/pending lot
                                IF @pp_Remaining = 0 AND(@pp_LotBal - @pp_Take) > 0
                                    BEGIN
                                        SET @pp_PendLotId = @pp_LotId
                                        SET @pp_PendHolder = @pp_Holder
                                        SET @pp_PendEnt = @pp_EntCode
                                        SET @pp_PendClass = @pp_ShareClass
                                        SET @pp_PendIssueNr = @pp_IssueNr
                                    END
                            END
                    END

                -- (3) TR only: the receiving holder gains a new lot at the transfer's cert.
                --     RD removes shares from circulation, so no new lot is created.
                IF @pp_TransType = 'TR'
                    INSERT INTO #Lots(EntCode, ShareClass, Holder, OriginIssueNr, Balance, CurrentCert)
                    VALUES(@pp_EntCode, @pp_ShareClass, @pp_AddrCode, @pp_IssueNr, @pp_NrShare, @pp_Cert)
            END
        ELSE IF @pp_TransType = 'NC'
            BEGIN
                -- Re-certificate the lot just reduced and stamp the balancing cert on its row
                IF
                    @pp_PendLotId IS NOT NULL
                    AND @pp_PendHolder = @pp_PrevOwner
                    AND @pp_PendEnt = @pp_EntCode
                    AND @pp_PendClass = @pp_ShareClass
                    BEGIN
                        UPDATE #Lots SET CurrentCert = @pp_Cert
                        WHERE LotId = @pp_PendLotId
                        UPDATE #TransferFrom SET BalancingCert = @pp_Cert
                        WHERE LotId = @pp_PendLotId AND IssueNr = @pp_PendIssueNr AND EntCode = @pp_PendEnt
                        SET @pp_PendLotId = NULL
                        SET @pp_PendHolder = NULL
                    END
            END

        FETCH NEXT FROM ledger_cursor INTO
        @pp_EntCode, @pp_ShareClass, @pp_IssueNr, @pp_TransType
        , @pp_AddrCode, @pp_PrevOwner, @pp_NrShare, @pp_Cert, @pp_PrevCert
    END

CLOSE ledger_cursor
DEALLOCATE ledger_cursor

CREATE CLUSTERED INDEX IX_TF ON #TransferFrom(EntCode, IssueNr)

-- Declare necessary variables
DECLARE
    @EntryNo INT
    , @ExtClientCode VARCHAR(50)
    , @ClassofShare VARCHAR(50)
    , @CurrencyCode VARCHAR(10)
    , @TransactionID INT
    , @TransactionDate DATE
    , @NoofShares INT
    , @ParValue DECIMAL(38, 20)
    , @ShareholderNo VARCHAR(50)
    , @CertificateNo VARCHAR(50)
    , @BalancingCertificateNo VARCHAR(50)
    , @IssueType INT
    , @CertificateDate DATE
    , @ShareHolderType VARCHAR(50)
    , @PrevOwner VARCHAR(50)
    , @AddrCode VARCHAR(50)
    , @PrevCertificateNr VARCHAR(50)
    , @NominalPaid DECIMAL(18, 2)
    , @TransCode NVARCHAR(8)
    , @IssuePrice DECIMAL(18, 2)
    , @LastBalancingEntryNo INT --Track Entry No that needs balancing cert
    , @LastBalancingShareholder VARCHAR(50) --Track shareholder who needs balancing cert

    , @AddValue DECIMAL(18, 2) -- Add Value per Share
    , @AddValuePaid DECIMAL(18, 2) -- Add Value paid per share
    , @TotalPaid DECIMAL(18, 2) -- Total Amount Paid (Par Value + Add Value)
    , @PaidAmount DECIMAL(18, 2) -- To compute amount Paid
    , @IssueNr INT -- Track the IssueNr for proper lookup


DECLARE @OriginCertificateNo VARCHAR(50)
DECLARE @LoopCounter INT = 0
-- Safety counter for certificate tracing


-- Loop through each Share_Transaction
DECLARE transaction_cursor CURSOR FOR

WITH
ShareAuthorised AS(
    SELECT DISTINCT
        [Ext_ Client Code]
        , [Class of Share]
        , [Currency Code]
        , [Par Value]
    FROM [MT Share Authorised]
)

SELECT
    ST.EntCode
    , SC.ShareClassName AS ClassOf_Share
    , ST.Currency
    , ROW_NUMBER() OVER(PARTITION BY ST.EntCode ORDER BY ST.TransDate) AS TransactionID
    , ST.TransferDate
    , ST.NrShare
    , ST.NomValShare
    , CASE
        WHEN ST.TransType IN('AL', 'RD', 'RC') THEN ST.AddrCode ELSE ST.PrevOwner
    END AS ShareholderNo

    , ST.CertificateNr
    , NULL AS BalancingCertificateNo

    , CASE
        WHEN ST.TransType = 'AL' THEN '0'
        WHEN ST.TransType = 'RD' THEN '4'
        WHEN ST.TransType = 'RC' THEN '3'
        WHEN ST.TransType = 'TR' THEN '1' -- Transfer logic
        WHEN ST.TransType = 'NC' THEN '9999' -- Unique code for NC as part of loop logic
        WHEN ST.TransType = 'CP' THEN '6'
        WHEN ST.TransType = 'AU' THEN '7' -- Authorised increase/decrease (2nd+ AU only)
        ELSE NULL -- Ensure other transaction types don't interfere with basic logic. Need to remove at final product
    END AS IssueType

    , ST.TransferDate AS CertificateDate

    , CASE
        --WHEN RM.RefType = 'I' THEN '0'
        --WHEN RM.RefType = 'C' THEN '1'
        WHEN fn.IsEntity = 1 THEN 0
        WHEN fn.IsClient = 1 THEN 1
    END AS ShareHolderType

    , ST.PrevOwner
    , ST.AddrCode
    , ST.PrevCertificateNr -- Add previous certificate number for Transfer From
    , CASE
        WHEN ST.Paid = 0 THEN 0
        WHEN ST.Paid < ST.NomValShare THEN ST.Paid
        WHEN ST.Paid >= ST.NomValShare THEN ST.NomValShare
    END -- This should be nominal Value being paid when share is issued
    , ST.TransCode
    , ST.IssuePrice
    , ST.IssuePrice - ST.NomValShare -- @AddValue
    , CASE
        WHEN ST.NomValShare = 0 THEN ST.Paid
        WHEN ST.Paid > ST.NomValShare THEN ST.Paid - ST.NomValShare
        WHEN ST.Paid <= ST.NomValShare THEN 0
    END -- @AddValuePaid
    , ST.Paid
    , ST.IssueNr -- Add IssueNr for proper lookup
--- Total Amount Paid for Transaction in @Paid
FROM Share_Transactions AS ST
INNER JOIN Share_Capital AS SC ON ST.EntCode = SC.EntCode AND ST.ShareClass = SC.ShareClass
LEFT JOIN RefMaster AS RM ON ST.AddrCode = RM.RefCode
LEFT JOIN fnGetInScopeClients() AS fn ON ST.AddrCode = fn.RefCode
INNER JOIN ShareAuthorised AS SA
    ON
        ST.EntCode = SA.[Ext_ Client Code] AND ST.NomValShare = SA.[Par Value] AND SC.ShareClassName = SA.[Class of Share]
        AND ST.Currency = SA.[Currency Code]
WHERE
    -- AU is IN scope; only the initial (first) authorisation per share class is removed.
    -- For an AU row: keep it only when its IssueNr is greater than the smallest AU
    -- IssueNr for the same EntCode + ShareClass (that smallest one is the initial auth).
    -- For any non-AU row: CASE returns -1 so the row always passes (IssueNr is always >= 1).
    ST.IssueNr
    > CASE
        WHEN ST.TransType = 'AU'
            THEN(
                SELECT MIN(AU0.IssueNr)
                FROM Share_Transactions AS AU0 WITH(NOLOCK)
                WHERE
                    AU0.EntCode = ST.EntCode
                    AND AU0.ShareClass = ST.ShareClass
                    AND AU0.TransType = 'AU'
                    AND AU0.Posted = 1
            )
        ELSE -1
    END
    AND ST.ShareClass NOT LIKE('%/G%')
    AND ST.ShareClass NOT LIKE('%/L%')
    AND ST.Posted = 1
    AND ST.EntCode IN(
        SELECT RefCode
        FROM #InScopeClients
        WHERE IsClient = 1
    )
ORDER BY ST.EntCode, st.TransferDate, ST.IssueNr


OPEN transaction_cursor

FETCH NEXT FROM transaction_cursor INTO
@ExtClientCode
, @ClassofShare
, @CurrencyCode
, @TransactionID
, @TransactionDate
, @NoofShares
, @ParValue
, @ShareholderNo
, @CertificateNo
, @BalancingCertificateNo
, @IssueType
, @CertificateDate
, @ShareHolderType
, @PrevOwner
, @AddrCode
, @PrevCertificateNr
, @NominalPaid
, @TransCode
, @IssuePrice
, @AddValue
, @AddValuePaid
, @TotalPaid
, @IssueNr


SET @EntryNo = 0;
SET @LastBalancingEntryNo = NULL
SET @LastBalancingShareholder = NULL

WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @EntryNo = @EntryNo + 1

        -- CP (Calls Paid)
        IF @IssueType = 6
            BEGIN
                SET @OriginCertificateNo = @PrevCertificateNr
                SET @LoopCounter = 0

                IF @PrevCertificateNr = @CertificateNo
                    BEGIN
                        DECLARE @TempOriginCert VARCHAR(50), @TempTransType VARCHAR(2)
                        SELECT TOP 1
                            @TempOriginCert = PrevCertificateNr
                            , @TempTransType = TransType
                        FROM Share_Transactions WITH(NOLOCK)
                        WHERE
                            CertificateNr = @CertificateNo
                            AND EntCode = @ExtClientCode
                            AND Currency = @CurrencyCode
                            AND AddrCode = @ShareholderNo
                            AND IssueNr < @IssueNr
                            AND PrevCertificateNr <> @CertificateNo
                        ORDER BY IssueNr DESC

                        -- FIX: If the transaction that created this cert is NC, stop here
                        IF @TempTransType = 'NC'
                            BEGIN
                                SET @OriginCertificateNo = @CertificateNo
                            END
                        ELSE IF
                            @TempOriginCert IS NOT NULL AND EXISTS(
                                SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                WHERE
                                    CertificateNr = @TempOriginCert AND EntCode = @ExtClientCode
                                    AND Currency = @CurrencyCode
                                    AND AddrCode = @ShareholderNo
                                    AND IssueNr < @IssueNr
                            )
                            BEGIN
                                SET @OriginCertificateNo = @TempOriginCert
                            END
                    END

                WHILE EXISTS(
                    SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                    WHERE
                        CertificateNr = @OriginCertificateNo AND EntCode = @ExtClientCode
                        AND Currency = @CurrencyCode
                        AND ISNULL(PrevCertificateNr, '0') <> '0'
                        AND PrevCertificateNr IS NOT NULL
                        AND AddrCode = @ShareholderNo
                        AND IssueNr < @IssueNr AND TransType <> 'NC'
                ) AND @LoopCounter < 100
                    BEGIN
                        DECLARE @NextCert VARCHAR(50)
                        SELECT TOP 1 @NextCert = PrevCertificateNr
                        FROM Share_Transactions WITH(NOLOCK)
                        WHERE
                            CertificateNr = @OriginCertificateNo AND EntCode = @ExtClientCode
                            AND Currency = @CurrencyCode
                            AND AddrCode = @ShareholderNo
                            AND IssueNr < @IssueNr
                            AND ISNULL(PrevCertificateNr, '0') <> '0'
                            AND PrevCertificateNr IS NOT NULL
                        ORDER BY IssueNr DESC

                        IF
                            EXISTS(
                                SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                WHERE
                                    CertificateNr = @NextCert
                                    AND EntCode = @ExtClientCode
                                    AND Currency = @CurrencyCode
                                    AND AddrCode = @ShareholderNo
                                    AND IssueNr < @IssueNr
                            )
                            BEGIN
                                SET @OriginCertificateNo = @NextCert
                            END
                        ELSE BREAK
                        SET @LoopCounter = @LoopCounter + 1
                    END

                SELECT @PaidAmount = PaidAmount FROM #PaidLookup
                WHERE
                    CertificateNr = @CertificateNo
                    AND EntCode = @ExtClientCode
                    AND NrShare = @NoofShares
                    AND Currency = @CurrencyCode
                    AND IssueNr = @IssueNr

                INSERT INTO [MT Share Transaction]
                (
                    [Entry No_]
                    , [Ext_ Client Code]
                    , [Class of Share]
                    , [Currency Code]
                    , [Transaction ID]
                    , [Transaction Date]
                    , [No_ of Shares]
                    , [Par Value]
                    , [Shareholder No_]
                    , [Certificate No_]
                    , [Balancing Certificate No_]
                    , [Issue Type]
                    , [Certificate Date]
                    , [ShareHolder Type]
                    , [Payment Type]
                    , [Authorised Type]
                    , [Amount Paid Per Share]
                    , [Add_ Value per share]
                    , [Add_ Value Paid per share]
                )
                VALUES
                (
                    @EntryNo
                    , @ExtClientCode
                    , @ClassofShare
                    , @CurrencyCode
                    , @TransactionID
                    , @TransactionDate
                    , @NoofShares
                    , @ParValue
                    , @ShareholderNo
                    , @OriginCertificateNo  -- To obtain the original certificate
                    , @BalancingCertificateNo
                    , @IssueType
                    , @CertificateDate
                    , @ShareHolderType
                    , CASE
                        WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                        WHEN(@TotalPaid <>(@ParValue + @AddValue)) THEN 2
                        WHEN(@TotalPaid = @ParValue + @AddValue) THEN 3
                        ELSE 0
                    END
                    , CASE
                        WHEN @TransCode = 'AU' THEN 2
                        WHEN @TransCode = 'CR' THEN 3
                        ELSE 1
                    END
                    , CASE
                        WHEN @ParValue = 0 THEN 0
                        WHEN @AddValue = 0 AND @TotalPaid <= @ParValue THEN @PaidAmount
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid <= @ParValue) THEN @PaidAmount
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid > @ParValue) AND(@ParValue -(@TotalPaid - @PaidAmount) > 0) THEN @ParValue -(@TotalPaid - @PaidAmount)
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid > @ParValue) AND(@ParValue -(@TotalPaid - @PaidAmount) <= 0) THEN 0
                        ELSE 0
                    END
                    , @AddValue
                    , CASE
                        WHEN @AddValue = 0 THEN 0
                        WHEN @ParValue = 0 THEN @PaidAmount
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid <= @ParValue) THEN 0
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid > @ParValue) AND(@ParValue -(@TotalPaid - @PaidAmount) > 0) THEN @TotalPaid - @ParValue
                        WHEN @AddValue <> 0 AND @ParValue <> 0 AND(@TotalPaid > @ParValue) AND(@ParValue -(@TotalPaid - @PaidAmount) <= 0) THEN @PaidAmount
                        ELSE 0
                    END
                )
            END

        -- Other transaction types (AL, RC, RD)
        IF @IssueType IS NULL OR @IssueType NOT IN(1, 9999, 6, 7)
            BEGIN
                DECLARE @RdRowCount INT = 0
                IF @IssueType = 4
                    SELECT @RdRowCount = COUNT(*) FROM #TransferFrom
                    WHERE EntCode = @ExtClientCode AND IssueNr = @IssueNr

                ----------------------------------------------------------------
                -- Multi-lot REDEMPTION (RD): when the redeemed holding was
                -- accumulated from several parcels, the lot ledger breaks the
                -- redemption into one row per lot (mirrors the many-to-one
                -- transfer split). The partially-redeemed boundary lot carries
                -- the follow-up NC as its balancing cert; the rest are blank.
                -- Single-lot redemptions (and RC / AL) keep the original logic.
                ----------------------------------------------------------------
                IF @IssueType = 4 AND @RdRowCount > 1
                    BEGIN
                        ; WITH B AS(
                            SELECT
                                FromShares
                                , FromCert
                                , BalancingCert
                                , ROW_NUMBER() OVER(ORDER BY OrderCert ASC, OriginIssueNr ASC, LotId ASC) AS rn
                            FROM #TransferFrom
                            WHERE EntCode = @ExtClientCode AND IssueNr = @IssueNr
                        )

                        INSERT INTO [MT Share Transaction]
                        (
                            [Entry No_]
                            , [Ext_ Client Code]
                            , [Class of Share]
                            , [Currency Code]
                            , [Transaction ID]
                            , [Transaction Date]
                            , [No_ of Shares]
                            , [Par Value]
                            , [Shareholder No_]
                            , [Certificate No_]
                            , [Balancing Certificate No_]
                            , [Issue Type]
                            , [Certificate Date]
                            , [ShareHolder Type]
                            , [Payment Type]
                            , [Authorised Type]
                            , [Amount Paid Per Share]
                            , [Add_ Value per share]
                            , [Add_ Value Paid per share]
                        )
                        SELECT
                            @EntryNo +(rn - 1)  -- distinct Entry No_ per redemption lot ([Entry No_] is the PK)
                            , @ExtClientCode
                            , @ClassofShare
                            , @CurrencyCode
                            , @TransactionID
                            , @TransactionDate
                            ,(-FromShares)
                            , @ParValue
                            , @ShareholderNo
                            , FromCert
                            , BalancingCert  -- NC cert on the partially-redeemed boundary lot (else NULL)
                            , @IssueType
                            , @CertificateDate
                            , @ShareHolderType
                            , CASE
                                WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                                WHEN(@NominalPaid < @ParValue) OR(@AddValuePaid < @AddValue) THEN 2
                                WHEN(@NominalPaid = @ParValue) AND(@AddValuePaid = @AddValue) THEN 3
                                ELSE 0
                            END
                            , CASE
                                WHEN @TransCode = 'AU' THEN 2
                                WHEN @TransCode = 'CR' THEN 3
                                ELSE 1
                            END
                            , @NominalPaid
                            , @AddValue
                            , @AddValuePaid
                        FROM B

                        -- Advance Entry No_ by the extra rows; balancing is from the
                        -- ledger, so suppress the deferred NC update.
                        SET @EntryNo = @EntryNo +(@RdRowCount - 1)
                        SET @LastBalancingEntryNo = NULL
                        SET @LastBalancingShareholder = NULL
                    END
                ELSE
                    BEGIN
                        DECLARE @FinalCertificateNo VARCHAR(50)
                        SET @FinalCertificateNo = @CertificateNo

                        -- For RC/RD: Trace back through certificate chain to find origin
                        IF @IssueType IN(3, 4)
                            BEGIN
                                DECLARE @RCRDOriginCert VARCHAR(50)
                                -- Start tracing from PrevCertificateNr (which may equal CertificateNr)
                                SET @RCRDOriginCert = @PrevCertificateNr
                                SET @LoopCounter = 0

                                -- Trace backwards through the certificate chain
                                WHILE EXISTS(
                                    SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                    WHERE
                                        CertificateNr = @RCRDOriginCert
                                        AND EntCode = @ExtClientCode
                                        AND Currency = @CurrencyCode
                                        AND ISNULL(PrevCertificateNr, '0') <> '0'
                                        AND PrevCertificateNr IS NOT NULL
                                        AND AddrCode = @ShareholderNo
                                        AND IssueNr < @IssueNr
                                        AND TransType <> 'NC'
                                        AND PrevCertificateNr <> @RCRDOriginCert  -- skip no-op calls-paid rows (PrevCert = Cert); follow only real cert changes
                                ) AND @LoopCounter < 100
                                    BEGIN
                                        DECLARE @NextRCRDCert VARCHAR(50)
                                        SELECT TOP 1 @NextRCRDCert = PrevCertificateNr
                                        FROM Share_Transactions WITH(NOLOCK)
                                        WHERE
                                            CertificateNr = @RCRDOriginCert
                                            AND EntCode = @ExtClientCode
                                            AND Currency = @CurrencyCode
                                            AND AddrCode = @ShareholderNo
                                            AND IssueNr < @IssueNr
                                            AND ISNULL(PrevCertificateNr, '0') <> '0'
                                            AND PrevCertificateNr IS NOT NULL
                                            AND PrevCertificateNr <> @RCRDOriginCert  -- skip no-op calls-paid rows; trace to the real origin cert
                                        ORDER BY IssueNr DESC

                                        IF
                                            EXISTS(
                                                SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                                WHERE
                                                    CertificateNr = @NextRCRDCert
                                                    AND EntCode = @ExtClientCode
                                                    AND Currency = @CurrencyCode
                                                    AND AddrCode = @ShareholderNo
                                                    AND IssueNr < @IssueNr
                                            )
                                            BEGIN
                                                SET @RCRDOriginCert = @NextRCRDCert
                                            END
                                        ELSE BREAK
                                        SET @LoopCounter = @LoopCounter + 1
                                    END
                                SET @FinalCertificateNo = @RCRDOriginCert
                            END

                        INSERT INTO [MT Share Transaction]
                        (
                            [Entry No_]
                            , [Ext_ Client Code]
                            , [Class of Share]
                            , [Currency Code]
                            , [Transaction ID]
                            , [Transaction Date]
                            , [No_ of Shares]
                            , [Par Value]
                            , [Shareholder No_]
                            , [Certificate No_]
                            , [Balancing Certificate No_]
                            , [Issue Type]
                            , [Certificate Date]
                            , [ShareHolder Type]
                            , [Payment Type]
                            , [Authorised Type]
                            , [Amount Paid Per Share]
                            , [Add_ Value per share]
                            , [Add_ Value Paid per share]
                        )
                        VALUES
                        (
                            @EntryNo
                            , @ExtClientCode
                            , @ClassofShare
                            , @CurrencyCode
                            , @TransactionID
                            , @TransactionDate
                            , @NoofShares
                            , @ParValue
                            , @ShareholderNo
                            , @FinalCertificateNo
                            , @BalancingCertificateNo
                            , @IssueType
                            , @CertificateDate
                            , @ShareHolderType
                            , CASE
                                WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                                WHEN(@NominalPaid < @ParValue) OR(@AddValuePaid < @AddValue) THEN 2
                                WHEN(@NominalPaid = @ParValue) AND(@AddValuePaid = @AddValue) THEN 3
                                ELSE 0
                            END
                            , CASE
                                WHEN @TransCode = 'AU' THEN 2
                                WHEN @TransCode = 'CR' THEN 3
                                ELSE 1
                            END
                            , @NominalPaid
                            , @AddValue
                            , @AddValuePaid
                        )

                        IF @IssueType IN(3, 4)
                            BEGIN
                                SET @LastBalancingEntryNo = @EntryNo
                                SET @LastBalancingShareholder = @ShareholderNo
                            END
                    END
            END

        -- AU (Authorised increase/decrease) -- 2nd and subsequent authorisations only.
        -- Single row per AU. Direction is taken from the sign of the share count:
        --   Authorised Type 2 = Increase (NrShare > 0), 3 = Decrease (NrShare < 0).
        -- An authorised change is not a payment/premium event, so Payment Type is
        -- Nil (1) and the paid / add-value fields are 0. Shareholder is 'ISSUE'.
        IF @IssueType = 7
            BEGIN
                INSERT INTO [MT Share Transaction]
                (
                    [Entry No_]
                    , [Ext_ Client Code]
                    , [Class of Share]
                    , [Currency Code]
                    , [Transaction ID]
                    , [Transaction Date]
                    , [No_ of Shares]
                    , [Par Value]
                    , [Shareholder No_]
                    , [Certificate No_]
                    , [Balancing Certificate No_]
                    , [Issue Type]
                    , [Certificate Date]
                    , [ShareHolder Type]
                    , [Payment Type]
                    , [Authorised Type]
                    , [Amount Paid Per Share]
                    , [Add_ Value per share]
                    , [Add_ Value Paid per share]
                )
                VALUES
                (
                    @EntryNo
                    , @ExtClientCode
                    , @ClassofShare
                    , @CurrencyCode
                    , @TransactionID
                    , @TransactionDate
                    , @NoofShares                 -- signed: positive = increase, negative = decrease
                    , @ParValue
                    , @ShareholderNo              -- 'ISSUE'
                    , @CertificateNo              -- 0 for authorised rows
                    , @BalancingCertificateNo
                    , @IssueType                  -- 7 = Authorised increase/decrease
                    , @CertificateDate
                    , @ShareHolderType
                    , 1                            -- Payment Type: Nil (not a payment event)
                    , CASE WHEN @NoofShares < 0 THEN 3 ELSE 2 END  -- Authorised Type: 3 = Decrease, 2 = Increase
                    , 0                            -- Amount Paid Per Share
                    , 0                            -- Add_ Value per share
                    , 0                            -- Add_ Value Paid per share
                )
            END

        -- Transfer
        IF @IssueType = 1
            BEGIN
                SET @LastBalancingEntryNo = @EntryNo
                SET @LastBalancingShareholder = @PrevOwner

                DECLARE @TransferOriginCert VARCHAR(50)
                DECLARE @PreviousTransTypeForTransfer VARCHAR(2)

                -- Check if the previous transaction was CP																				  
                SELECT TOP 1 @PreviousTransTypeForTransfer = TransType
                FROM Share_Transactions WITH(NOLOCK)
                WHERE
                    CertificateNr = @PrevCertificateNr
                    AND EntCode = @ExtClientCode
                    AND Currency = @CurrencyCode
                    AND AddrCode = @PrevOwner
                    AND IssueNr < @IssueNr

                ORDER BY IssueNr DESC

                -- Only trace if previous transaction was CP
                IF @PreviousTransTypeForTransfer = 'CP'
                    BEGIN
                        SET @TransferOriginCert = @PrevCertificateNr
                        SET @LoopCounter = 0
                        IF @PrevCertificateNr = @CertificateNo
                            BEGIN
                                DECLARE @TempTransferOriginCert VARCHAR(50), @TempTransferTransType VARCHAR(2)

                                SELECT TOP 1
                                    @TempTransferOriginCert = PrevCertificateNr
                                    , @TempTransferTransType = TransType
                                FROM Share_Transactions WITH(NOLOCK)
                                WHERE
                                    CertificateNr = @CertificateNo
                                    AND EntCode = @ExtClientCode
                                    AND Currency = @CurrencyCode
                                    AND AddrCode = @PrevOwner
                                    AND IssueNr < @IssueNr
                                    AND PrevCertificateNr <> @CertificateNo
                                ORDER BY IssueNr DESC

                                -- FIX: If the transaction that created this cert is NC, stop here
                                IF @TempTransferTransType = 'NC'
                                    BEGIN
                                        SET @TransferOriginCert = @CertificateNo
                                    END
                                ELSE IF
                                    @TempTransferOriginCert IS NOT NULL AND EXISTS(
                                        SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                        WHERE
                                            CertificateNr = @TempTransferOriginCert AND EntCode = @ExtClientCode
                                            AND Currency = @CurrencyCode
                                            AND AddrCode = @PrevOwner
                                            AND IssueNr < @IssueNr
                                    )
                                    BEGIN
                                        SET @TransferOriginCert = @TempTransferOriginCert
                                    END
                            END

                        WHILE EXISTS(
                            SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                            WHERE
                                CertificateNr = @TransferOriginCert AND EntCode = @ExtClientCode
                                AND Currency = @CurrencyCode AND ISNULL(PrevCertificateNr, '0') <> '0'
                                AND PrevCertificateNr IS NOT NULL
                                AND AddrCode = @PrevOwner
                                AND IssueNr < @IssueNr AND TransType <> 'NC'
                        ) AND @LoopCounter < 100
                            BEGIN
                                DECLARE @NextTransferCert VARCHAR(50)
                                SELECT TOP 1 @NextTransferCert = PrevCertificateNr
                                FROM Share_Transactions WITH(NOLOCK)
                                WHERE
                                    CertificateNr = @TransferOriginCert AND EntCode = @ExtClientCode
                                    AND Currency = @CurrencyCode AND AddrCode = @PrevOwner
                                    AND IssueNr < @IssueNr AND ISNULL(PrevCertificateNr, '0') <> '0'
                                    AND PrevCertificateNr IS NOT NULL
                                ORDER BY IssueNr DESC

                                IF
                                    EXISTS(
                                        SELECT 1 FROM Share_Transactions WITH(NOLOCK)
                                        WHERE
                                            CertificateNr = @NextTransferCert
                                            AND EntCode = @ExtClientCode
                                            AND Currency = @CurrencyCode
                                            AND AddrCode = @PrevOwner
                                            AND IssueNr < @IssueNr
                                    )
                                    BEGIN
                                        SET @TransferOriginCert = @NextTransferCert
                                    END
                                ELSE BREAK
                                SET @LoopCounter = @LoopCounter + 1
                            END
                    END
                ELSE
                    BEGIN
                        -- Previous transaction is NOT CP, use PrevCertificateNr directly
                        SET @TransferOriginCert = @PrevCertificateNr
                    END

                ------------------------------------------------------------------
                -- "Transfered From" side, driven by the lot-ledger breakdown
                -- (#TransferFrom) built in the pre-pass. One row per lot the
                -- quantity was drawn from, ordered by current certificate
                -- ascending (tie-break oldest lot first), each on its own
                -- Entry No_. Many-to-one (full or partial) therefore emits
                -- multiple rows; a one-to-one transfer emits a single row.
                -- Falls back to the original single-row insert (using the
                -- traced origin cert) if no breakdown exists for this transfer.
                ------------------------------------------------------------------
                DECLARE @FromRowCount INT
                SELECT @FromRowCount = COUNT(*)
                FROM #TransferFrom
                WHERE EntCode = @ExtClientCode AND IssueNr = @IssueNr

                IF @FromRowCount > 0
                    BEGIN
                        ; WITH B AS(
                            SELECT
                                FromShares
                                , FromCert
                                , BalancingCert
                                , ROW_NUMBER() OVER(ORDER BY OrderCert ASC, OriginIssueNr ASC, LotId ASC) AS rn
                            FROM #TransferFrom
                            WHERE EntCode = @ExtClientCode AND IssueNr = @IssueNr
                        )

                        INSERT INTO [MT Share Transaction]
                        (
                            [Entry No_]
                            , [Ext_ Client Code]
                            , [Class of Share]
                            , [Currency Code]
                            , [Transaction ID]
                            , [Transaction Date]
                            , [No_ of Shares]
                            , [Par Value]
                            , [Shareholder No_]
                            , [Certificate No_]
                            , [Balancing Certificate No_]
                            , [Issue Type]
                            , [Certificate Date]
                            , [ShareHolder Type]
                            , [Payment Type]
                            , [Authorised Type]
                            , [Amount Paid Per Share]
                            , [Add_ Value per share]
                            , [Add_ Value Paid per share]
                        )
                        SELECT
                            @EntryNo +(rn - 1)  -- distinct Entry No_ per split row ([Entry No_] is the PK)
                            , @ExtClientCode
                            , @ClassofShare
                            , @CurrencyCode
                            , @TransactionID
                            , @TransactionDate
                            ,(-FromShares)
                            , @ParValue
                            , @PrevOwner
                            , FromCert            -- current cert of the lot the shares were drawn from
                            , BalancingCert       -- NC cert for the partially-consumed lot (else NULL)
                            , 1
                            , @CertificateDate
                            , @ShareHolderType
                            , CASE
                                WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                                WHEN(@NominalPaid < @ParValue) OR(@AddValuePaid < @AddValue) THEN 2
                                WHEN(@NominalPaid = @ParValue) AND(@AddValuePaid = @AddValue) THEN 3
                                ELSE 0
                            END
                            , CASE
                                WHEN @TransCode = 'AU' THEN 2
                                WHEN @TransCode = 'CR' THEN 3
                                ELSE 1
                            END
                            , @NominalPaid
                            , @AddValue
                            , @AddValuePaid
                        FROM B

                        -- Advance Entry No_ by the extra rows produced
                        SET @EntryNo = @EntryNo +(@FromRowCount - 1)

                        -- Balancing is supplied by the ledger; suppress the deferred NC update.
                        SET @LastBalancingEntryNo = NULL
                        SET @LastBalancingShareholder = NULL
                    END
                ELSE
                    BEGIN
                        -- Fallback (no breakdown): original single-row "Transfered From".
                        INSERT INTO [MT Share Transaction]
                        (
                            [Entry No_]
                            , [Ext_ Client Code]
                            , [Class of Share]
                            , [Currency Code]
                            , [Transaction ID]
                            , [Transaction Date]
                            , [No_ of Shares]
                            , [Par Value]
                            , [Shareholder No_]
                            , [Certificate No_]
                            , [Balancing Certificate No_]
                            , [Issue Type]
                            , [Certificate Date]
                            , [ShareHolder Type]
                            , [Payment Type]
                            , [Authorised Type]
                            , [Amount Paid Per Share]
                            , [Add_ Value per share]
                            , [Add_ Value Paid per share]
                        )
                        VALUES
                        (
                            @EntryNo
                            , @ExtClientCode
                            , @ClassofShare
                            , @CurrencyCode
                            , @TransactionID
                            , @TransactionDate
                            ,(-@NoofShares)
                            , @ParValue
                            , @PrevOwner
                            , @TransferOriginCert
                            , @BalancingCertificateNo
                            , 1
                            , @CertificateDate
                            , @ShareHolderType
                            , CASE
                                WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                                WHEN(@NominalPaid < @ParValue) OR(@AddValuePaid < @AddValue) THEN 2
                                WHEN(@NominalPaid = @ParValue) AND(@AddValuePaid = @AddValue) THEN 3
                                ELSE 0
                            END
                            , CASE
                                WHEN @TransCode = 'AU' THEN 2
                                WHEN @TransCode = 'CR' THEN 3
                                ELSE 1
                            END
                            , @NominalPaid
                            , @AddValue
                            , @AddValuePaid
                        )
                    END

                -- Insert Transfer To (using AddrCode for Transfer To) -- single row in all cases
                SET @EntryNo = @EntryNo + 1
                INSERT INTO [MT Share Transaction]
                (
                    [Entry No_]
                    , [Ext_ Client Code]
                    , [Class of Share]
                    , [Currency Code]
                    , [Transaction ID]
                    , [Transaction Date]
                    , [No_ of Shares]
                    , [Par Value]
                    , [Shareholder No_]
                    , [Certificate No_]
                    , [Balancing Certificate No_]
                    , [Issue Type]
                    , [Certificate Date]
                    , [ShareHolder Type]
                    , [Payment Type]
                    , [Authorised Type]
                    , [Amount Paid Per Share]
                    , [Add_ Value per share]
                    , [Add_ Value Paid per share]
                )
                VALUES
                (
                    @EntryNo
                    , @ExtClientCode
                    , @ClassofShare
                    , @CurrencyCode
                    , @TransactionID
                    , @TransactionDate
                    , @NoofShares
                    , @ParValue
                    , @AddrCode
                    , @CertificateNo
                    , @BalancingCertificateNo
                    , 2
                    , @CertificateDate
                    , @ShareHolderType
                    , CASE
                        WHEN @NominalPaid = 0 AND @AddValuePaid = 0 THEN 1
                        WHEN(@NominalPaid < @ParValue) OR(@AddValuePaid < @AddValue) THEN 2
                        WHEN(@NominalPaid = @ParValue) AND(@AddValuePaid = @AddValue) THEN 3
                        ELSE 0
                    END
                    , CASE
                        WHEN @TransCode = 'AU' THEN 2
                        WHEN @TransCode = 'CR' THEN 3 ELSE 1
                    END
                    , @NominalPaid
                    , @AddValue
                    , @AddValuePaid
                )
            END

        -- Balancing Certificate (NC)
        IF @IssueType = 9999
            BEGIN
                SET @EntryNo = @EntryNo - 1
                IF @LastBalancingEntryNo IS NOT NULL AND @ShareholderNo = @LastBalancingShareholder
                    BEGIN
                        UPDATE [MT Share Transaction]
                        SET [Balancing Certificate No_] = ISNULL(@CertificateNo, '0')
                        WHERE [Entry No_] = @LastBalancingEntryNo AND [Ext_ Client Code] = @ExtClientCode
                        SET @LastBalancingEntryNo = NULL
                        SET @LastBalancingShareholder = NULL
                    END
            END

        FETCH NEXT FROM transaction_cursor INTO
        @ExtClientCode
        , @ClassofShare
        , @CurrencyCode
        , @TransactionID
        , @TransactionDate
        , @NoofShares
        , @ParValue
        , @ShareholderNo
        , @CertificateNo
        , @BalancingCertificateNo
        , @IssueType
        , @CertificateDate
        , @ShareHolderType
        , @PrevOwner
        , @AddrCode
        , @PrevCertificateNr
        , @NominalPaid
        , @TransCode
        , @IssuePrice
        , @AddValue
        , @AddValuePaid
        , @TotalPaid
        , @IssueNr
    END

CLOSE transaction_cursor
DEALLOCATE transaction_cursor

UPDATE M SET M.[ShareHolder Type] = CASE WHEN F.IsClient = 1 THEN '1' ELSE '0' END
FROM [MT Share Transaction] AS M
INNER JOIN dbo.fnGetInScopeClients() AS F
    ON M.[Shareholder No_] COLLATE DATABASE_DEFAULT = F.RefCode COLLATE DATABASE_DEFAULT
```
