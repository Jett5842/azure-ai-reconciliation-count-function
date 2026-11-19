# Vpoint Entity Administration - shared glossary
Applies to every ETL knowledge document of module **Entity Administration** (vPoint > Standard > 2. Migration > 1. Entity Administration). Meanings are taken from how the ETL scripts use the codes.

## Exact vs Lookup
- **Exact** source: Vpoint rows that are counted into the MT staging table. The sum of the Exact counts of a table (including the negative 'Duplicates removed across UNION branches' adjustment row, when present) is expected to equal the staging record count.
- **Lookup** source: a Vpoint table read only to fill MT columns (LEFT JOIN, sub-query, post-insert UPDATE). It creates no staging rows and is not part of the total.

## Scope helper
`dbo.fnGetInScopeClients()` returns one row per in-scope master file with the flags **IsClient, IsEntity, IsOwner, IsResource** and the key **RefCode**. Filtering `IsClient = 1` means "in-scope Client Master File". The function is the scope definition of the migration, it is not a business table and is never listed as a source.
- Type codes written by the ETL for a related master file: 1 = Client, 0 = Entity, 2 = Resource (some tables use 3 / 4 for Entity / Resource).

## Common patterns
- `[NAV_Entry No]` is a generated sequence (`ROW_NUMBER() OVER (...)`), not a Vpoint value.
- `UNION` removes identical rows; `UNION ALL` keeps them; `SELECT DISTINCT` removes identical output rows. Tables built with an untagged UNION have a 'Duplicates removed across UNION branches' adjustment row in the reconciliation.
- Staging table names replace characters that are not allowed with `_` (for example `MT Rel_ Mgt_ Comment Line`, `MT Principals _ Entities`); the Business Central table names use the real characters (`.` and `/`).
- Long texts are split into pieces (Comments: 250 characters; Safe Custody: 150 + remainder; Client Entity notes: 50 + remainder).

## Officers.OfficerType codes used
DAL Alternate Director; POA Power of Attorney agent; CNP Controlling Person; SOW Substantial Owner; ADM used as an Owner source; EMR employer relation (employer name lookup); PRO Protector; COT Co Trustee. Officers.RelClass M / I = master-file / internal relation. A relation is active when DateResign is empty and Status is not 'R'.

## Share_Interests.IntType codes used
BEO Beneficial Owner; UBO Ultimate Beneficial Owner; MST Settlor (only used for Owner links). A relation has ended when DateEnd is populated.

## Share types and share transaction codes
- ShareTypeCode '/G' = General Partner, '/L' = Limited Partner (excluded from normal share class tables, reported as GPA / LIP relations).
- Share_Transactions.TransType: AL allotment, AU authorisation (first AU = initial authorised capital, later AU = capital change), CP calls paid, TR transfer, RC cancellation, RD redemption, NC balancing / re-certification (no row of its own), RF handled like RC in the reconciliation.

## IdentityRegister.IdType codes used
FSPR FATCA sponsoring entity; FPTFI FATCA reporting through FI; CPTFI CRS reporting through FI; FRFI FATCA reporting financial institution; CRFI CRS reporting financial institution; CTDT CRS record used for CRS_RFI tax details; FCSC FATCA classification; FCRS CRS classification; GIIN / GIINSP FATCA identification number of the entity / of its sponsor; FIC and FIN tax identification numbers; LEI legal entity identifier; PEPT / PEPC politically exposed person; BCT country of birth; INC incorporation; REG regulatory licence; IDC ID card; PSP passport; CTZ second citizenship. Active records have `Active = 1`.

## RefAddress / CR_RefAddresses AddrType codes used
BI billing; RO registered office of the master file; SR registered office of the company; RA residential; MA mailing; BA business; RS address used as administrative office (flagged as service address in MT Address); SS company seal; S% statutory.

## RefContacts.cType codes used
TB business phone; FB business fax; EB business e-mail; WB web page; TM mobile / phone of an individual; FH fax of an individual; EP e-mail of an individual; TH home phone; TD direct phone; EI e-mail (contacts).

## Alerts
RefAlerts with `AlertActive = 1` are warnings. Their code goes to MT Warning Register, their note text to MT Comments (Client / Entity) or MT Rel_ Mgt_ Comment Line (Owner), prefixed with the alert type name from qLvALTC.
