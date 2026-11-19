# Vpoint Entity Administration - ETL knowledge index

Module: Entity Administration (vPoint > Standard > 2. Migration > 1. Entity Administration). One document per staging table; shared codes are in `_Glossary.md`.

| MT staging table | Document | Exact sources | Lookup sources | Scope filter |
|---|---|---|---|---|
| MT Address | InsertMtAddress.md | CR_RefAddresses (MAILING), CR_RefAddresses (nonMAILING, DISTINCT), RefContacts (nonMCONTACT) | qLvCNTR (lookup), RefMaster (lookup), RefContacts (lookup) | IsEntity = 1 (RefCode of addresses and contacts) |
| MT Beneficiary Details | InsertMtBeneficiaryDetails.md | Beneficiaries | - | IsClient = 1 (EntCode) |
| MT Client | InsertMtClient.md | RefMaster | Entity (lookup), EntityAccount (lookup), IdentityRegister (lookup), EntityTypes (lookup), RefAddress (lookup) | IsClient = 1 (RefMaster.RefCode), non-individual |
| MT Client Alternate Directors | InsertMtClientAlternateDirectors.md | Officers | RefMaster (lookup) | IsClient = 1 (Officers.EntCode) |
| MT Client Entity | InsertMtClientEntity.md | Officers, Share_Interests (UBO), Share_Interests (BEO), Beneficiaries, CR_Shareholders (SHR/etc), CR_Shareholders (LIP), CR_Shareholders (GPA), Entity, IdentityRegister (FSPR), IdentityRegister (FPTFI/CPTFI) | Entity (lookup), IdentityRegister (lookup), Share_Interests (lookup), Officers (lookup) | IsClient = 1 (Client No_) |
| MT Client Entity History | InsertMtClientEntityHistory.md | Officers, Share_Interests (UBO), Share_Interests (BEO), Beneficiaries, CR_Shareholders (SHR/etc), CR_Shareholders (LIP), CR_Shareholders (GPA) | Share_Interests (lookup), Officers (lookup) | IsClient = 1 (Client No_) |
| MT Client POA Agent | InsertMtClientPoaAgent.md | Officers | RefMaster (lookup) | IsClient = 1 (Officers.EntCode) |
| MT Client POA Agent History | InsertMtClientPoaAgentHistory.md | Officers | RefMaster (lookup) | IsClient = 1 (Officers.EntCode) |
| MT CM Address | InsertMtCmAddress.md | RefAddress + Addresses | Addresses (lookup), AddrRegion (lookup) | IsClient = 1 (RefAddress.RefCode) |
| MT Comments | InsertMtComments.md | RefAlerts | qLvALTC (lookup) | IsClient = 1 OR IsEntity = 1 (RefAlerts.RefCode) |
| MT Entity | InsertMtEntity.md | RefMaster | Entity (lookup), Compliance (lookup), RefLabels (lookup), LookComboSave (lookup), qLvCNTR (lookup), IdentityRegister (lookup), CR_RefAddresses (lookup), RefStatus (lookup), BankAccounts (lookup), Officers (lookup) | IsEntity = 1 (RefMaster.RefCode) |
| MT Entity Bank Account | InsertMtEntityBankAccount.md | Beneficiaries (DISTINCT) | - | Beneficiary IsEntity = 1 AND EntCode IsClient = 1 |
| MT Entity Contact | InsertMtEntityContact.md | RefMaster self-join (EmployerMf) | Compliance (lookup), RefContacts (lookup) | RefMaster.RefCode IsEntity = 1 (non-individual) |
| MT Office Address | InsertMtOfficeAddress.md | RefAddress + Addresses (DISTINCT address + contacts + Temp key) | Addresses (lookup), RefContacts (lookup) | Embedded: Client IsClient = 1 OR Owner sources OR VpUser.RelMfCode |
| MT Owner | InsertMtOwner.md | 1) EntityOwners, 2) EntityOwners + Officers, 3) EntityOwners + Share_Interests, 4) Share_Interests, 5) Share_Interests + Officers, 6) Officers, 7) EntityOwners + Share_Interests + Officers | Entity (lookup), Compliance (lookup), LookComboSave (lookup), IdentityRegister (lookup), RefAddress (lookup), Officers (lookup) | Owner linked to a client with IsClient = 1 |
| MT Owner Clients | InsertMtOwnerClients.md | 1) EntityOwners, 2) EntityOwners + Officers, 3) EntityOwners + Share_Interests, 4) Share_Interests, 5) Share_Interests + Officers, 6) Officers, 7) EntityOwners + Share_Interests + Officers | - | IsClient = 1 (Client No_) |
| MT Particulars History | InsertMtParticularsHistory.md | EntNameChanges | - | IsClient = 1 (EntNameChanges.EntCode) |
| MT Power Of Attorney Register | InsertMtPowerOfAttorneyRegister.md | Officers | - | IsClient = 1 (Officers.EntCode) |
| MT Principals _ Entities | InsertMtPrincipalsEntities.md | Officers (RelClass M/I), Share_Interests | Share_Interests (lookup), Officers (lookup) | IsEntity = 1 (Linked To No_ / EntCode) |
| MT Rel_ Mgt_ Comment Line | InsertMtRelMgtCommentLine.md | RefAlerts (Owner, 250-char chunks) | qLvALTC (lookup) | IsOwner = 1 (RefAlerts.RefCode) |
| MT Resource | InsertMtResource.md | VpUser | RefMaster (lookup), Compliance (lookup), LookComboSave (lookup), Administrators (lookup), CR_RefAddresses (lookup), IdentityRegister (lookup), RefContacts (lookup), ServiceRates (lookup) | No client scope; users selected by activity / link rules |
| MT Risk Assessment | InsertMtRiskAssessment.md | RefMaster (Client, Type=0), RefMaster (non-Client, one row per Owner/Entity tag) | RefStatus (lookup), Entity (lookup) | Any in-scope RefCode (fnGetInScopeClients), Client = Type 0 |
| MT Safe Custody Ledger Entry | InsertMtSafeCustodyLedgerEntry.md | DocuIndexMoves | RefMaster (lookup) | IsClient = 1 (DocuIndexMoves.EntCode) |
| MT Safe Custody Records | InsertMtSafeCustodyRecords.md | DocuIndex | - | IsClient = 1 (DocuIndex.EntCode) |
| MT Share Authorised | InsertMtShareAuthorised.md | Share_Transactions (AU, first per class) | Share_Capital (lookup) | IsClient = 1 (Share_Capital.EntCode) and RefMaster.Status = '0' |
| MT Share Class RnC | InsertMtShareClassRnC.md | Share_Capital | - | IsClient = 1 (Share_Capital.EntCode) |
| MT Share Transaction | InsertMtShareTransaction.md | Share_Transactions (AL), Share_Transactions (AU, 2nd+ per class), Share_Transactions (CP), Share_Transactions (TR, Transfer To row), Share_Transactions (RC/RF), Share_Transactions (RD), Lot-ledger rows (TR Transfered-From + extra RC/RD lot splits) - derived from staging | Share_Transactions (NC) (lookup), Share_Capital (lookup) | IsClient = 1 (Share_Transactions.EntCode); needs [MT Share Authorised] to be loaded first |
| MT Tax Details | InsertMtTaxDetails.md | RefMaster + IdentityRegister (TaxDetails), RefMaster + IdentityRegister/ReportAccounts (TIN, NOT EXISTS dedup) | IdentityRegister (lookup), ReportAccounts (lookup) | Record No_ in-scope (fnGetInScopeClients); TaxDetails branch IsClient = 1 |
| MT Warning Register | InsertMtWarningRegister.md | RefAlerts (any active alert), RefAlerts (Owner) | - | No client/entity scope filter (any active alert); Owner branch uses IsOwner = 1 |
