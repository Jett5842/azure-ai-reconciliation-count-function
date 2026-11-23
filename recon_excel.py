"""Builds the reconciliation Excel report: one "Detail" worksheet, one block of rows per MIG_STAGING table,
grouped by migration module (Module is column A)."""
import math
from io import BytesIO

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# (header, row key, width)
COLUMNS = [
    ("Module", "module", 20),                                          # A  merged per staging table, like E..L
    ("Source Table Name", "source_table", 38),                         # B
    ("Source Table Type", "source_type", 11),                          # C
    ("Source Record Count", "source_count", 12),                       # D
    ("Source Total Record Count", "source_total", 14),                 # E  merged per staging table
    ("MIG_STAGING Table Name", "mig_table", 30),                       # F  merged
    ("MIG_STAGING Table Record Count", "mig_count", 14),               # G  merged
    ("Qcore Table Name", "qcore_table", 30),                           # H  merged
    ("No of Records Migrated Successfully", "success", 14),            # I  merged
    ("No of Records Migrated Failed", "failed", 13),                   # J  merged
    ("Fail %", None, 9),                                               # K  merged, formula
    ("Status", None, 14),                                              # L  merged, formula
    ("Extract Script Condition Applied", "condition", 70),             # M
    ("Scope", "scope", 45),                                            # N
    ("Remark", "remark", 22),                                          # O
]
KEYS = [key for _, key, _ in COLUMNS]
COL = {title: i for i, (title, _, _) in enumerate(COLUMNS, start=1)}
C_MODULE, C_SOURCE, C_TYPE, C_COUNT = 1, 2, 3, 4
C_TOTAL, C_MIG, C_MIGCOUNT, C_QCORE, C_OK, C_FAIL, C_FAILPCT, C_STATUS = 5, 6, 7, 8, 9, 10, 11, 12
MERGE_FIRST_COL, MERGE_LAST_COL = C_TOTAL, C_STATUS   # E..L merged per staging table
LEFT_COLS, BOLD_COLS = {C_MODULE, C_MIG, C_QCORE}, {C_MODULE, C_MIG, C_QCORE, C_STATUS}

# Module order in the report; any other module name is listed last as "Other Modules"
MODULE_ORDER = ["EA Migration", "CA Migration", "Share Migration", "TRB/Finance Migration", "Setup"]
OTHER_MODULE = "Other Modules"

FONT = "Arial"
NAVY = "1F3864"
FILL_A = PatternFill("solid", fgColor="EAF1FB")
FILL_B = PatternFill("solid", fgColor="FFFFFF")
FILL_LOOKUP = PatternFill("solid", fgColor="F2F2F2")
MISMATCH_FILL = PatternFill("solid", fgColor="F8CBAD")
THIN = Side(style="thin", color="BFBFBF")
MEDIUM = Side(style="medium", color="808080")


def _lines(text, chars_per_line: int) -> int:
    text = str(text or "")
    return sum(max(1, math.ceil(len(part) / chars_per_line)) for part in text.split("\n"))


def _module_of(row: dict) -> str:
    """Canonical module name; tolerant of case, spacing and "/" vs "-" (e.g. "TRB-Finance Migration")."""
    def key(text):
        return "".join(ch for ch in str(text).lower() if ch.isalnum())
    wanted = key(row.get("module") or "")
    for module in MODULE_ORDER:
        if key(module) == wanted:
            return module
    return OTHER_MODULE


def build_workbook(rows: list) -> bytes:
    # Group by module in the fixed order; a stable sort keeps the staging tables in payload order inside a module
    order = {m: i for i, m in enumerate(MODULE_ORDER + [OTHER_MODULE])}
    rows = sorted(({**r, "module": _module_of(r)} for r in rows), key=lambda r: order[r["module"]])

    wb = Workbook()
    ws = wb.active
    ws.title = "Detail"
    ws.sheet_view.zoomScale = 90

    header_fill = PatternFill("solid", fgColor=NAVY)
    for c, (title, _, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=title)
        cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[1].height = 42

    # ---- body: one block per MIG_STAGING table, fill alternates between blocks ------------------------------
    group_start, group_index, previous_table = 2, -1, None
    for r, row in enumerate(rows, start=2):
        if row["mig_table"] != previous_table:
            group_start, group_index, previous_table = r, group_index + 1, row["mig_table"]
        first_in_group = r == group_start
        is_lookup = row["source_type"].lower() == "lookup"
        block_fill = FILL_A if group_index % 2 == 0 else FILL_B
        font = Font(name=FONT, size=9, italic=True, color="7F7F7F") if is_lookup else Font(name=FONT, size=10)
        border = Border(top=MEDIUM if first_in_group else THIN, bottom=THIN, left=THIN, right=THIN)

        for c, key in enumerate(KEYS, start=1):
            cell = ws.cell(row=r, column=c, value=None if key is None else row[key])
            merged_col = c == C_MODULE or MERGE_FIRST_COL <= c <= MERGE_LAST_COL
            cell.fill = block_fill if merged_col else (FILL_LOOKUP if is_lookup else block_fill)
            cell.font = font
            cell.border = border
            if c in (C_SOURCE, C_TYPE, C_COUNT):
                cell.alignment = Alignment(wrap_text=(c == C_SOURCE), vertical="top",
                                           horizontal=None if c == C_SOURCE else "center")
            elif c > MERGE_LAST_COL:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c == C_COUNT:
                cell.number_format = "#,##0;-#,##0;0"
            elif c in (C_TOTAL, C_MIGCOUNT, C_OK, C_FAIL):
                cell.number_format = "#,##0"

        # row height from the longest wrapped text (B 38, M 70, N 45 characters wide)
        size_factor = 12 if is_lookup else 13.5
        lines = max(_lines(row["source_table"], 38), _lines(row["condition"], 72), _lines(row["scope"], 46), 1)
        ws.row_dimensions[r].height = max(16.5 if is_lookup else 30, lines * size_factor + 4)

    last_row = len(rows) + 1
    if rows:
        # ---- merge A and E..L per staging table, centre, add Fail % / Status formulas --------------------------------
        start = 2
        for r in range(2, last_row + 2):  # one extra pass closes the last block
            if r <= last_row and rows[r - 2]["mig_table"] == rows[start - 2]["mig_table"]:
                continue
            end = r - 1
            g, i, j, h, f = (f"{get_column_letter(c)}{start}" for c in (C_MIGCOUNT, C_FAIL, C_OK, C_QCORE, C_FAILPCT))
            ws.cell(row=start, column=C_FAILPCT, value=f"=IF(N({g})=0,0,N({i})/{g})")
            ws.cell(row=start, column=C_STATUS, value=(
                f'=IF(N({g})=0,"No data",IF({h}="","Not loaded",'
                f'IF(N({i})>0,"Has failures",IF(N({j})+N({i})<>N({g}),"Check","OK"))))'))
            for c in (C_MODULE, *range(MERGE_FIRST_COL, MERGE_LAST_COL + 1)):
                top = ws.cell(row=start, column=c)
                top.font = Font(name=FONT, size=10, bold=c in BOLD_COLS)
                top.alignment = Alignment(horizontal="left" if c in LEFT_COLS else "center",
                                          vertical="center", wrap_text=True)
                if c == C_FAILPCT:
                    top.number_format = "0.0%"
                if end > start:
                    ws.merge_cells(start_row=start, start_column=c, end_row=end, end_column=c)
            # Exact source total should equal the MIG_STAGING record count
            if rows[start - 2]["source_total"] != rows[start - 2]["mig_count"]:
                ws.cell(row=start, column=C_TOTAL).fill = MISMATCH_FILL
                ws.cell(row=start, column=C_MIGCOUNT).fill = MISMATCH_FILL
            start = r

    # ---- conditional formats ---------------------------------------------------------------------------------
    body = f"{{}}2:{{}}{max(last_row, 2)}"
    fail_cols = (get_column_letter(C_FAIL), get_column_letter(C_FAILPCT))
    ws.conditional_formatting.add(body.format(*fail_cols), FormulaRule(
        formula=[f"${fail_cols[0]}2>0"], font=Font(color="C00000")))
    status_col = get_column_letter(C_STATUS)
    for text, bg, fg in (("Has failures", "F8CBAD", "9C0006"), ("Not loaded", "FFE699", "7F6000"),
                         ("OK", "C6E0B4", "375623"), ("No data", "D9D9D9", "595959"), ("Check", "F8CBAD", "9C0006")):
        ws.conditional_formatting.add(body.format(status_col, status_col), CellIsRule(
            operator="equal", formula=[f'"{text}"'], font=Font(color=fg),
            fill=PatternFill(start_color=bg, end_color=bg, fill_type="solid")))

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(last_row, 2)}"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
