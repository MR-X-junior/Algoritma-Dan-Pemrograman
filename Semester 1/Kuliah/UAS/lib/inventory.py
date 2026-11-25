"""
inventory.py
Class Inventory: mengelola kumpulan barang (tambah, ubah, hapus, cari,
restock, stok menipis) dan menyimpannya ke file JSON.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from lib.models import Product, Transaction
from lib.utils import LOW_STOCK_THRESHOLD, PRODUCTS_FILE, load_json, normalize_code, save_json


class Inventory:
    """Seluruh barang di toko, disimpan sebagai dictionary {kode: Product}."""

    def __init__(self, path: str = PRODUCTS_FILE) -> None:
        """Membuat inventory lalu langsung memuat data dari file JSON."""
        self.path = path
        self.products: Dict[str, Product] = {}
        self.load()

    # ----- storage -----
    def load(self) -> None:
        """Memuat barang dari file JSON. Data yang tidak valid dilewati dengan
        peringatan, bukan membuat program crash."""
        self.products = {}
        for data in load_json(self.path, []):
            try:
                product = Product(**data)
            except (ValueError, TypeError) as error:
                print(f"  [!] Satu data barang dilewati karena tidak valid: {error}")
                continue
            self.products[product.code] = product

    def save(self) -> None:
        """Menyimpan seluruh barang ke file JSON."""
        save_json(self.path, [product.to_dict() for product in self.all()])

    # ----- queries -----
    def all(self) -> List[Product]:
        """Seluruh barang, terurut berdasarkan kode."""
        return sorted(self.products.values(), key=lambda product: product.code)

    def find(self, code: str) -> Optional[Product]:
        """Mencari barang berdasarkan kode (tidak peka huruf besar/kecil, tanda '-'
        dan spasi diabaikan). Mengembalikan Product, atau None jika tidak ada."""
        wanted = normalize_code(code)
        if not wanted:
            return None
        return next((product for product in self.products.values()
                     if normalize_code(product.code) == wanted), None)

    def search(self, keyword: str) -> List[Product]:
        """Mencari barang: kode yang diawali keyword lebih dulu, lalu nama yang
        mengandung keyword (tidak peka huruf besar/kecil). Keyword kosong = semua barang."""
        keyword = keyword.strip().lower()
        wanted = normalize_code(keyword)
        by_code = [product for product in self.all()
                   if wanted and normalize_code(product.code).startswith(wanted)]
        by_name = [product for product in self.all()
                   if keyword in product.name.lower() and product not in by_code]
        return by_code + by_name

    def low_stock(self, threshold: int = LOW_STOCK_THRESHOLD) -> List[Product]:
        """Barang dengan stok <= threshold, dari yang paling sedikit."""
        return sorted((p for p in self.all() if p.is_low_stock(threshold)),
                      key=lambda product: product.stock)

    # ----- mutations -----
    def _require(self, code: str) -> Product:
        """Mengambil barang berdasarkan kode, atau ValueError jika tidak ditemukan."""
        product = self.find(code)
        if product is None:
            raise ValueError(f"Barang dengan kode '{str(code).strip().upper()}' tidak ditemukan.")
        return product

    def add(self, product: Product) -> None:
        """Menambah barang baru. Ditolak jika kodenya sudah dipakai."""
        if product.code in self.products:
            raise ValueError(f"Kode '{product.code}' sudah dipakai oleh barang lain.")
        self.products[product.code] = product
        self.save()

    def update(self, code: str, **changes) -> None:
        """Mengubah data barang. changes berisi name/price/stock yang ingin diganti."""
        self._require(code).update(**changes)
        self.save()

    def remove(self, code: str) -> None:
        """Menghapus barang berdasarkan kode."""
        del self.products[self._require(code).code]
        self.save()

    def restock(self, code: str, quantity: int) -> None:
        """Menambah stok barang yang sudah ada lalu menyimpannya."""
        self._require(code).add_stock(quantity)
        self.save()

    def commit_sale(self, transaction: Transaction) -> None:
        """Mengurangi stok sesuai isi transaksi yang sudah dibayar. Semua item
        diperiksa dulu; jika ada yang bermasalah, tidak ada stok yang berubah."""
        for item in transaction.items:
            product = self._require(item["code"])
            if item["qty"] > product.stock:
                raise ValueError(f"Stok {product.name} tidak cukup (tersisa {product.stock}).")
        for item in transaction.items:
            self.products[item["code"]].reduce_stock(item["qty"])
        self.save()