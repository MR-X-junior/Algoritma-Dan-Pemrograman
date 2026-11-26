"""
report.py
Class DailyReport: merangkum transaksi pada satu tanggal, menampilkannya di
layar, dan mengekspornya ke CSV (2 file tabel) atau Excel (4 sheet).
"""

from __future__ import annotations

import csv
import os
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from lib.models import Transaction
from lib.utils import (
    CSV_DELIMITER, DATETIME_FORMAT, EXPORT_DIR, LINE_WIDTH, STORE_NAME, TAX_RATE,
    align_row, divider, escape_formula, format_rupiah,
)

# Judul kolom tabel transaksi (satu baris per transaksi) dan tabel detail barang
TRANSACTION_COLUMNS = ["ID Transaksi", "Tanggal", "Jam", "Jenis Barang", "Total Qty", "Subtotal",
                       "Diskon (%)", "Diskon (Rp)", "Setelah Diskon (DPP)", f"PPN {TAX_RATE}%",
                       "Total Bayar", "Uang Dibayar", "Kembalian"]
DETAIL_COLUMNS = ["ID Transaksi", "Tanggal", "Jam", "Kode", "Nama Barang", "Harga Satuan",
                  "Qty", "Subtotal Item"]

# Muat openpyxl dan siapkan gaya Excel. Jika belum terpasang, EXCEL_AVAILABLE = False
# dan export Excel menampilkan petunjuk instalasi (lihat DailyReport.export_excel).
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.worksheet import Worksheet

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
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


class DailyReport:
    """Ringkasan penjualan untuk satu tanggal tertentu."""

    def __init__(self, transactions: List[Transaction], date: str) -> None:
        """Menyaring riwayat transaksi menjadi hanya yang terjadi pada tanggal tersebut."""
        self.date = date
        self.transactions = [t for t in transactions if t.date() == date]
        self.printed_at = datetime.now().strftime(DATETIME_FORMAT)

    def has_data(self) -> bool:
        """True jika ada minimal satu transaksi pada tanggal ini."""
        return bool(self.transactions)

    def _require_data(self) -> None:
        """Memunculkan ValueError jika tidak ada transaksi (tidak ada yang bisa di-export)."""
        if not self.has_data():
            raise ValueError(f"Tidak ada transaksi pada {self.date}.")

    # ----- calculations -----
    def summary_rows(self) -> List[Tuple[str, int, bool]]:
        """Ringkasan sebagai daftar (label, nilai, apakah_rupiah). Nilai berupa angka
        mentah; tampilan layar dan file export memformatnya sendiri."""
        txs = self.transactions
        biggest = max(txs, key=lambda t: t.total())
        smallest = min(txs, key=lambda t: t.total())
        return [
            ("Jumlah transaksi", len(txs), False),
            ("Total item terjual (qty)", sum(t.total_quantity() for t in txs), False),
            ("Jenis barang terjual", len({item["code"] for t in txs for item in t.items}), False),
            ("Pendapatan kotor (subtotal)", sum(t.subtotal() for t in txs), True),
            ("Total diskon", sum(t.discount() for t in txs), True),
            ("Pendapatan setelah diskon (DPP)", sum(t.taxable_amount() for t in txs), True),
            (f"Total pajak (PPN {TAX_RATE}%)", sum(t.tax() for t in txs), True),
            ("Pendapatan bersih (diterima)", sum(t.total() for t in txs), True),
            ("Total uang dibayar pelanggan", sum(t.paid for t in txs), True),
            ("Total kembalian", sum(t.change for t in txs), True),
            ("Rata-rata nilai per transaksi", round(sum(t.total() for t in txs) / len(txs)), True),
            (f"Transaksi terbesar ({biggest.id})", biggest.total(), True),
            (f"Transaksi terkecil ({smallest.id})", smallest.total(), True),
        ]

    def product_totals(self) -> List[Dict[str, Any]]:
        """Rekap penjualan per barang, diurutkan dari qty terbanyak (jika sama,
        berdasarkan nama). Tiap elemen: code, name, price, qty, transactions, revenue."""
        totals: Dict[str, Dict[str, Any]] = {}
        for transaction in self.transactions:
            for item in transaction.items:
                row = totals.setdefault(item["code"], {"code": item["code"], "name": item["name"],
                                                       "price": item["price"], "qty": 0,
                                                       "transactions": 0, "revenue": 0})
                row["price"] = item["price"]                  # harga terakhir yang tercatat
                row["qty"] += item["qty"]
                row["transactions"] += 1
                row["revenue"] += item["price"] * item["qty"]
        return sorted(totals.values(), key=lambda row: (-row["qty"], row["name"]))

    def top_products(self, limit: int = 3) -> List[Tuple[str, int]]:
        """Barang terlaris sebagai daftar (nama, qty terjual)."""
        return [(row["name"], row["qty"]) for row in self.product_totals()[:limit]]

    def hourly_sales(self) -> List[Tuple[str, int, int]]:
        """Penjualan per jam sebagai daftar (jam 'HH', jumlah transaksi, pendapatan diterima)."""
        hours: Dict[str, List[int]] = OrderedDict()
        for transaction in sorted(self.transactions, key=lambda t: t.timestamp):
            count_and_amount = hours.setdefault(transaction.timestamp[11:13], [0, 0])
            count_and_amount[0] += 1
            count_and_amount[1] += transaction.total()
        return [(hour, count, amount) for hour, (count, amount) in hours.items()]

    def transaction_rows(self) -> List[list]:
        """Tabel transaksi untuk export: satu baris per transaksi (urutan = TRANSACTION_COLUMNS)."""
        return [[t.id, t.date(), t.timestamp[11:], len(t.items), t.total_quantity(), t.subtotal(),
                 t.discount_percent(), t.discount(), t.taxable_amount(), t.tax(), t.total(),
                 t.paid, t.change] for t in self.transactions]

    def detail_rows(self) -> List[list]:
        """Tabel detail untuk export: satu baris per barang pada tiap transaksi (urutan = DETAIL_COLUMNS)."""
        return [[t.id, t.date(), t.timestamp[11:], item["code"], escape_formula(item["name"]),
                 item["price"], item["qty"], item["price"] * item["qty"]]
                for t in self.transactions for item in t.items]

    # ----- screen output -----
    def show(self) -> None:
        """Mencetak laporan di layar: ringkasan, barang terlaris, dan rincian
        setiap transaksi beserta barangnya."""
        print(f"\n{divider('=')}")
        print(f"LAPORAN PENJUALAN - {STORE_NAME}".center(LINE_WIDTH))
        print(f"Tanggal: {self.date}".center(LINE_WIDTH))
        print(divider("="))
        if not self.has_data():
            print("Belum ada transaksi pada tanggal ini.".center(LINE_WIDTH))
            print(divider("="))
            return
        for label, value, is_money in self.summary_rows():
            print(align_row(label, format_rupiah(value) if is_money else str(value)))
        print(divider())
        print("Barang terlaris:")
        for rank, (name, quantity) in enumerate(self.top_products(), start=1):
            print(f"  {rank}. {name} ({quantity} terjual)")
        print(divider())
        print("Rincian transaksi:")
        for transaction in self.transactions:
            print(align_row(f"{transaction.id}  {transaction.timestamp[11:]}",
                            format_rupiah(transaction.total())))
            for item in transaction.items:
                print(align_row(f"    {item['qty']} x {item['name'][:30]}",
                                format_rupiah(item["price"] * item["qty"])))
        print(divider("="))

    # ----- export -----
    def export_csv(self, folder: str = EXPORT_DIR) -> List[str]:
        """Mengekspor laporan ke dua file CSV: tabel transaksi dan tabel detail barang.
        Memakai utf-8-sig supaya terbaca benar di Excel. Mengembalikan daftar path file."""
        self._require_data()
        os.makedirs(folder, exist_ok=True)
        tables = [("transaksi", TRANSACTION_COLUMNS, self.transaction_rows()),
                  ("detail_barang", DETAIL_COLUMNS, self.detail_rows())]
        paths = []
        for suffix, columns, rows in tables:
            path = os.path.join(folder, f"laporan_{self.date}_{suffix}.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file, delimiter=CSV_DELIMITER)
                writer.writerow(columns)
                writer.writerows(rows)
            paths.append(path)
        return paths

    def export_excel(self, folder: str = EXPORT_DIR) -> List[str]:
        """Mengekspor laporan ke Excel (.xlsx) dengan 4 sheet: Ringkasan, Daftar
        Transaksi, Rincian Transaksi, Barang Terjual. Membutuhkan openpyxl; jika belum
        terpasang, memunculkan RuntimeError berisi petunjuk instalasi.
        Mengembalikan daftar berisi satu path file."""
        self._require_data()
        if not EXCEL_AVAILABLE:
            raise RuntimeError("Export Excel membutuhkan library openpyxl. "
                               "Pasang dengan: pip install openpyxl")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"laporan_{self.date}.xlsx")
        build_workbook(self).save(path)
        return [path]


# ===== EXCEL BUILDER =====
# ----- style helpers -----
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


# ----- sheets -----
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
        workbook.properties.title = f"Laporan Penjualan {report.date}"
        workbook.properties.creator = STORE_NAME
        workbook.properties.subject = "Laporan penjualan harian Smart-POS"
        if sheet is not summary:
            sheet.print_title_rows = "1:1"
    return workbook