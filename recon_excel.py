"""Builds the reconciliation Excel report."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

COLUMNS = [
    ("Source Table Name", "source_table", 40),
    ("Source Table Type", "source_type", 14),
    ("Source Record Count", "source_count", 16),
    ("Source Total Record Count", "source_total", 18),
    ("MIG_STAGING Table Name", "mig_table", 34),
    ("MIG_STAGING Table Record Count", "mig_count", 18),
    ("Qcore Table Name", "qcore_table", 34),
    ("No of Records Migrated Successfully", "success", 18),
    ("No of Records Migrated Failed", "failed", 18),
    ("Extract Script Condition Applied", "condition", 70),
    ("Scope", "scope", 55),
    ("Remark", "remark", 25),
]


def build_workbook(rows: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reconciliation"

    header_fill = PatternFill("solid", fgColor="1F3864")
    for c, (title, _, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[1].height = 32

    mismatch_fill = PatternFill("solid", fgColor="F8CBAD")
    lookup_font = Font(italic=True, color="7F7F7F")
    group_border = Border(top=Side(style="thin", color="808080"))
    int_cols = {"source_count", "source_total", "mig_count", "success", "failed"}

    previous_table = None
    for r, row in enumerate(rows, start=2):
        is_lookup = row["source_type"].lower() == "lookup"
        new_group = row["mig_table"] != previous_table
        previous_table = row["mig_table"]
        for c, (_, key, _) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=r, column=c, value=row[key])
            cell.alignment = Alignment(wrap_text=key in ("condition", "scope"), vertical="top")
            if key in int_cols:
                cell.number_format = "#,##0;-#,##0;0"
            if is_lookup:
                cell.font = lookup_font
            if new_group:
                cell.border = group_border
        # Exact source total must equal the MIG_STAGING record count
        if row["source_total"] != row["mig_count"]:
            ws.cell(row=r, column=4).fill = mismatch_fill
            ws.cell(row=r, column=6).fill = mismatch_fill

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(len(rows) + 1, 2)}"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
