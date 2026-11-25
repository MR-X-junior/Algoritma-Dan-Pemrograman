"""
Paket lib: logika bisnis aplikasi Smart-POS.

Modul:
    utils         konstanta, format tampilan, validasi input, cek folder, helper JSON
    models        class Product dan Transaction
    inventory     class Inventory (kelola barang)
    report        class DailyReport (laporan harian, export CSV)
    excel_export  pembuat file Excel laporan (4 sheet, butuh openpyxl)
    live_input    input real-time: rupiah berpemisah ribuan dan saran kode barang

Class publik diekspor di sini, sehingga cukup menulis
`from lib import Inventory, Product, Transaction, DailyReport`.
"""

from lib.inventory import Inventory
from lib.models import Product, Transaction
from lib.report import DailyReport

__version__ = "1.0.0"
__all__ = ["Product", "Transaction", "Inventory", "DailyReport"]