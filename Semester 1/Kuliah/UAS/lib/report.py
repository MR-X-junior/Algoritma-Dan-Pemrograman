"""
report.py
Class DailyReport: merangkum transaksi pada satu tanggal, menampilkannya di
layar, dan mengekspornya ke CSV (2 file tabel) atau Excel (4 sheet).
Pembuatan file Excel ada di excel_export.py.
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
        try:
            from lib.excel_export import build_workbook
        except ImportError as error:
            raise RuntimeError("Export Excel membutuhkan library openpyxl. "
                               "Pasang dengan: pip install openpyxl") from error
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"laporan_{self.date}.xlsx")
        build_workbook(self).save(path)
        return [path]