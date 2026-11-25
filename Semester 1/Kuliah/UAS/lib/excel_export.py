"""
excel_export.py
Membuat file Excel laporan harian (4 sheet) dari objek DailyReport:
    Ringkasan          angka penting, barang terlaris, penjualan per jam
    Daftar Transaksi   satu baris per transaksi, lengkap dengan baris TOTAL
    Rincian Transaksi  blok per transaksi seperti struk (daftar barang, diskon, PPN, bayar)
    Barang Terjual     rekap per barang

Modul ini membutuhkan library openpyxl (pip install openpyxl).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from lib.report import TRANSACTION_COLUMNS
from lib.utils import STORE_NAME, TAX_RATE, escape_formula

if TYPE_CHECKING:
    from lib.report import DailyReport

MONEY_FORMAT = '"Rp"#,##0'
NAVY = "1F4E78"
BOLD = Font(bold=True)
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HIGHLIGHT_FILL = PatternFill("solid", fgColor="DDEBF7")
STRIPE_FILL = PatternFill("solid", fgColor="F2F2F2")
GRID = Side(style="thin", color="BFBFBF")
BOX = Border(left=GRID, right=GRID, top=GRID, bottom=GRID)
TOTAL_LINE = Border(top=Side(style="medium", color=NAVY))
CENTER = Alignment(horizontal="center")
RIGHT = Alignment(horizontal="right")


# ===== STYLE HELPERS =====
def write_header(ws: Worksheet, row: int, titles: List[str], tall: bool = False) -> None:
    """Menulis baris judul kolom bergaya (latar biru, teks putih, rata tengah).
    tall=True memperbesar tinggi baris, untuk judul kolom yang bisa terbagi dua baris."""
    for column, title in enumerate(titles, start=1):
        cell = ws.cell(row=row, column=column, value=title)
        cell.font, cell.fill, cell.border = HEADER_FONT, HEADER_FILL, BOX
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if tall:
        ws.row_dimensions[row].height = 32


def write_section(ws: Worksheet, row: int, text: str, span: int) -> None:
    """Menulis judul bagian dengan garis bawah selebar span kolom."""
    ws.cell(row=row, column=1, value=text).font = Font(bold=True, color=NAVY, size=12)
    for column in range(1, span + 1):
        ws.cell(row=row, column=column).border = Border(bottom=Side(style="medium", color=NAVY))


def set_widths(ws: Worksheet, widths: List[int]) -> None:
    """Mengatur lebar kolom A, B, C, ... sesuai daftar widths."""
    for column, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(column)].width = width


def write_total_row(ws: Worksheet, row: int, label_column: int, sum_columns: List[int],
                    first_row: int, last_row: int, last_column: int, money_from: int) -> None:
    """Menulis baris TOTAL berisi rumus SUM untuk kolom-kolom tertentu. Kolom mulai
    nomor money_from diberi format rupiah, sisanya rata tengah."""
    ws.cell(row=row, column=label_column, value="TOTAL").font = BOLD
    for column in sum_columns:
        letter = get_column_letter(column)
        cell = ws.cell(row=row, column=column, value=f"=SUM({letter}{first_row}:{letter}{last_row})")
        cell.font = BOLD
        if column >= money_from:
            cell.number_format = MONEY_FORMAT
        else:
            cell.alignment = CENTER
    for column in range(1, last_column + 1):
        ws.cell(row=row, column=column).border = TOTAL_LINE


# ===== SHEETS =====
def build_summary_sheet(ws: Worksheet, report: DailyReport) -> None:
    """Sheet 'Ringkasan': info laporan, angka penting, Top 5 barang terlaris, penjualan per jam."""
    ws.title = "Ringkasan"
    ws.sheet_view.showGridLines = False
    ws["A1"] = "LAPORAN PENJUALAN HARIAN"
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws["A2"] = STORE_NAME
    ws["A2"].font = Font(bold=True, size=12)

    times = sorted(t.timestamp[11:] for t in report.transactions)
    info = [("Tanggal laporan", report.date), ("Dicetak pada", report.printed_at),
            ("Transaksi pertama", times[0]), ("Transaksi terakhir", times[-1])]
    for row, (label, value) in enumerate(info, start=4):
        ws.cell(row=row, column=1, value=label).font = BOLD
        ws.cell(row=row, column=2, value=value).alignment = RIGHT

    row = 9
    write_section(ws, row, "RINGKASAN PENJUALAN", 4)
    summary = report.summary_rows()
    for row, (label, value, is_money) in enumerate(summary, start=row + 1):
        ws.cell(row=row, column=1, value=label).font = BOLD
        cell = ws.cell(row=row, column=2, value=value)
        cell.alignment = RIGHT
        if is_money:
            cell.number_format = MONEY_FORMAT
        if label.startswith("Pendapatan bersih"):
            ws.cell(row=row, column=1).fill = ws.cell(row=row, column=2).fill = HIGHLIGHT_FILL

    row += 2
    write_section(ws, row, "BARANG TERLARIS (TOP 5)", 4)
    write_header(ws, row + 1, ["Peringkat", "Nama Barang", "Qty Terjual", "Omzet (sebelum diskon)"])
    for rank, product in enumerate(report.product_totals()[:5], start=1):
        values = [rank, product["name"], product["qty"], product["revenue"]]
        for column, value in enumerate(values, start=1):
            cell = ws.cell(row=row + 1 + rank, column=column, value=value)
            cell.border = BOX
            if column == 1:
                cell.alignment = CENTER
            if column == 4:
                cell.number_format = MONEY_FORMAT

    row += 8
    write_section(ws, row, "PENJUALAN PER JAM", 4)
    write_header(ws, row + 1, ["Jam", "Jumlah Transaksi", "Pendapatan (diterima)"])
    for offset, (hour, count, amount) in enumerate(report.hourly_sales(), start=row + 2):
        for column, value in enumerate([f"{hour}:00 - {hour}:59", count, amount], start=1):
            cell = ws.cell(row=offset, column=column, value=value)
            cell.border = BOX
            cell.alignment = CENTER if column < 3 else Alignment()
            if column == 3:
                cell.number_format = MONEY_FORMAT
    set_widths(ws, [46, 24, 24, 26])


def build_transactions_sheet(ws: Worksheet, report: DailyReport) -> None:
    """Sheet 'Daftar Transaksi': satu baris per transaksi, filter, dan baris TOTAL."""
    ws.title = "Daftar Transaksi"
    columns = ["No"] + TRANSACTION_COLUMNS
    write_header(ws, 1, columns, tall=True)
    for number, values in enumerate(report.transaction_rows(), start=1):
        for column, value in enumerate([number] + values, start=1):
            cell = ws.cell(row=number + 1, column=column, value=value)
            cell.border = BOX
            if column in (7, 9, 10, 11, 12, 13, 14):
                cell.number_format = MONEY_FORMAT
            if column == 8:
                cell.number_format = '0"%"'
            if column in (1, 3, 4, 5, 6, 8):
                cell.alignment = CENTER
            if number % 2 == 0:
                cell.fill = STRIPE_FILL
    last_row = len(report.transactions) + 1
    write_total_row(ws, last_row + 1, label_column=2, sum_columns=[6, 7, 9, 10, 11, 12, 13, 14],
                    first_row=2, last_row=last_row, last_column=len(columns), money_from=7)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{last_row}"
    set_widths(ws, [5, 20, 12, 10, 12, 10, 14, 10, 13, 18, 12, 14, 14, 13])


def build_receipts_sheet(ws: Worksheet, report: DailyReport) -> None:
    """Sheet 'Rincian Transaksi': satu blok per transaksi seperti struk, berisi daftar
    barang, subtotal, diskon, DPP, PPN, total, uang dibayar, dan kembalian."""
    ws.title = "Rincian Transaksi"
    ws.sheet_view.showGridLines = False
    write_header(ws, 1, ["ID / Kode", "Waktu / Nama Barang", "Harga Satuan", "Qty", "Jumlah"])
    row = 2
    for transaction in report.transactions:
        for column, value in enumerate([transaction.id, transaction.timestamp, None, None,
                                        transaction.total()], start=1):
            cell = ws.cell(row=row, column=column, value=value)
            cell.fill, cell.font = HIGHLIGHT_FILL, BOLD
            if column == 5:
                cell.number_format = MONEY_FORMAT
        row += 1
        for item in transaction.items:
            ws.cell(row=row, column=1, value=item["code"]).alignment = Alignment(horizontal="left", indent=1)
            ws.cell(row=row, column=2, value=escape_formula(item["name"]))
            ws.cell(row=row, column=3, value=item["price"]).number_format = MONEY_FORMAT
            ws.cell(row=row, column=4, value=item["qty"]).alignment = CENTER
            ws.cell(row=row, column=5, value=item["price"] * item["qty"]).number_format = MONEY_FORMAT
            row += 1
        percent = transaction.discount_percent()
        footer = [
            ("Subtotal", transaction.subtotal(), False),
            (f"Diskon ({percent}%)" if percent else "Diskon", -transaction.discount() if percent else 0, False),
            ("Setelah diskon (DPP)", transaction.taxable_amount(), False),
            (f"PPN ({TAX_RATE}%)", transaction.tax(), False),
            ("TOTAL", transaction.total(), True),
            ("Uang dibayar", transaction.paid, False),
            ("Kembalian", transaction.change, False),
        ]
        for label, value, strong in footer:
            label_cell = ws.cell(row=row, column=4, value=label)
            label_cell.alignment = RIGHT
            value_cell = ws.cell(row=row, column=5, value=value)
            value_cell.number_format = MONEY_FORMAT
            if strong:
                label_cell.font = value_cell.font = BOLD
                label_cell.border = value_cell.border = TOTAL_LINE
            row += 1
        row += 1                                        # baris kosong antar transaksi
    set_widths(ws, [22, 34, 16, 24, 16])


def build_products_sheet(ws: Worksheet, report: DailyReport) -> None:
    """Sheet 'Barang Terjual': rekap per barang (terlaris di atas) dengan baris TOTAL."""
    ws.title = "Barang Terjual"
    columns = ["No", "Kode", "Nama Barang", "Harga Satuan", "Qty Terjual",
               "Muncul di (transaksi)", "Omzet (sebelum diskon)"]
    write_header(ws, 1, columns, tall=True)
    products = report.product_totals()
    for number, product in enumerate(products, start=1):
        values = [number, product["code"], escape_formula(product["name"]), product["price"],
                  product["qty"], product["transactions"], product["revenue"]]
        for column, value in enumerate(values, start=1):
            cell = ws.cell(row=number + 1, column=column, value=value)
            cell.border = BOX
            if column in (4, 7):
                cell.number_format = MONEY_FORMAT
            if column in (1, 2, 5, 6):
                cell.alignment = CENTER
            if number % 2 == 0:
                cell.fill = STRIPE_FILL
    last_row = len(products) + 1
    write_total_row(ws, last_row + 1, label_column=3, sum_columns=[5, 7], first_row=2,
                    last_row=last_row, last_column=len(columns), money_from=7)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{last_row}"
    set_widths(ws, [5, 9, 26, 15, 12, 14, 20])


def build_workbook(report: DailyReport) -> Workbook:
    """Menyusun seluruh workbook laporan harian (4 sheet) dengan pengaturan cetak
    A4 landscape yang muat satu halaman lebar. Mengembalikan objek Workbook (belum disimpan)."""
    workbook = Workbook()
    summary = workbook.active
    build_summary_sheet(summary, report)
    build_transactions_sheet(workbook.create_sheet(), report)
    build_receipts_sheet(workbook.create_sheet(), report)
    build_products_sheet(workbook.create_sheet(), report)
    for sheet in workbook.worksheets:
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 1 if sheet is summary else 0
        sheet.print_options.horizontalCentered = True
        if sheet is not summary:
            sheet.print_title_rows = "1:1"
    return workbook