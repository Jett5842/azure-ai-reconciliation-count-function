"""Builds the reconciliation Excel report (single "Detail" worksheet, one block of rows per MIG_STAGING table)."""
import math
from io import BytesIO

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# (header, row key, width)
COLUMNS = [
    ("Source Table Name", "source_table", 38),                         # A
    ("Source Table Type", "source_type", 11),                          # B
    ("Source Record Count", "source_count", 12),                       # C
    ("Source Total Record Count", "source_total", 14),                 # D  merged per staging table
    ("MIG_STAGING Table Name", "mig_table", 30),                       # E  merged
    ("MIG_STAGING Table Record Count", "mig_count", 14),               # F  merged
    ("Qcore Table Name", "qcore_table", 30),                           # G  merged
    ("No of Records Migrated Successfully", "success", 14),            # H  merged
    ("No of Records Migrated Failed", "failed", 13),                   # I  merged
    ("Fail %", None, 9),                                               # J  merged, formula
    ("Status", None, 14),                                              # K  merged, formula
    ("Extract Script Condition Applied", "condition", 70),             # L
    ("Scope", "scope", 45),                                            # M
    ("Remark", "remark", 22),                                          # N
]
MERGE_FIRST_COL, MERGE_LAST_COL = 4, 11  # D..K
BOLD_COLS = {5, 7, 11}                   # E, G, K

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


def build_workbook(rows: list) -> bytes:
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
    group_start = 2
    group_index = -1
    previous_table = None
    for r, row in enumerate(rows, start=2):
        if row["mig_table"] != previous_table:
            group_start, group_index, previous_table = r, group_index + 1, row["mig_table"]
        first_in_group = r == group_start
        is_lookup = row["source_type"].lower() == "lookup"
        fill = FILL_LOOKUP if is_lookup else (FILL_A if group_index % 2 == 0 else FILL_B)
        font = Font(name=FONT, size=9, italic=True, color="7F7F7F") if is_lookup else Font(name=FONT, size=10)
        border = Border(top=MEDIUM if first_in_group else THIN, bottom=THIN, left=THIN, right=THIN)

        for c, (_, key, _) in enumerate(COLUMNS, start=1):
            if key is None:  # Fail % / Status are formulas, written on the first row of the block
                value = None
            else:
                value = row[key]
            cell = ws.cell(row=r, column=c, value=value)
            cell.fill = FILL_A if (MERGE_FIRST_COL <= c <= MERGE_LAST_COL and group_index % 2 == 0) else (
                FILL_B if MERGE_FIRST_COL <= c <= MERGE_LAST_COL else fill)
            cell.font = font
            cell.border = border
            if c <= 3:
                cell.alignment = Alignment(wrap_text=(c == 1), vertical="top", horizontal=None if c == 1 else "center")
            elif c > MERGE_LAST_COL:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c in (3, 4, 6, 8, 9):
                cell.number_format = "#,##0;-#,##0;0" if c == 3 else "#,##0"

        # row height from the longest wrapped text (A 38, L 70, M 45 characters wide)
        size_factor = 12 if is_lookup else 13.5
        lines = max(_lines(row["source_table"], 38), _lines(row["condition"], 72), _lines(row["scope"], 46), 1)
        ws.row_dimensions[r].height = max(30, lines * size_factor + 4) if not is_lookup else max(16.5, lines * size_factor + 4)

    # ---- merge D..K per block, centre, add Fail % / Status formulas -----------------------------------------
    last_row = len(rows) + 1
    start = 2
    for r in range(2, last_row + 2):  # one extra pass closes the last block
        if r <= last_row and rows[r - 2]["mig_table"] == rows[start - 2]["mig_table"]:
            continue
        end = r - 1
        ws.cell(row=start, column=10, value=f"=IF(N(F{start})=0,0,N(I{start})/F{start})")
        ws.cell(row=start, column=11, value=(
            f'=IF(N(F{start})=0,"No data",IF(G{start}="","Not loaded",'
            f'IF(N(I{start})>0,"Has failures",IF(N(H{start})+N(I{start})<>N(F{start}),"Check","OK"))))'))
        for c in range(MERGE_FIRST_COL, MERGE_LAST_COL + 1):
            top = ws.cell(row=start, column=c)
            top.font = Font(name=FONT, size=10, bold=c in BOLD_COLS)
            top.alignment = Alignment(
                horizontal="left" if c in (5, 7) else "center", vertical="center", wrap_text=True)
            if c == 10:
                top.number_format = "0.0%"
            if end > start:
                ws.merge_cells(start_row=start, start_column=c, end_row=end, end_column=c)
        # Exact source total should equal the MIG_STAGING record count
        if rows[start - 2]["source_total"] != rows[start - 2]["mig_count"]:
            ws.cell(row=start, column=4).fill = MISMATCH_FILL
            ws.cell(row=start, column=6).fill = MISMATCH_FILL
        start = r

    # ---- conditional formats ---------------------------------------------------------------------------------
    body = f"{{}}2:{{}}{max(last_row, 2)}"
    ws.conditional_formatting.add(body.format("I", "J"), FormulaRule(formula=["$I2>0"], font=Font(color="C00000")))
    status_rng = body.format("K", "K")
    for text, bg, fg in (("Has failures", "F8CBAD", "9C0006"), ("Not loaded", "FFE699", "7F6000"),
                         ("OK", "C6E0B4", "375623"), ("No data", "D9D9D9", "595959"), ("Check", "F8CBAD", "9C0006")):
        ws.conditional_formatting.add(status_rng, CellIsRule(
            operator="equal", formula=[f'"{text}"'], font=Font(color=fg),
            fill=PatternFill(start_color=bg, end_color=bg, fill_type="solid")))

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(last_row, 2)}"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
