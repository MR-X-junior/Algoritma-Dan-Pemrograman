"""
models.py
Class Product dan Transaction (model data inti Smart-POS), serta fungsi
untuk menyimpan dan memuat riwayat transaksi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from lib.utils import (
    DATETIME_FORMAT, DISCOUNT_TIERS, LINE_WIDTH, LOW_STOCK_THRESHOLD, STORE_NAME,
    TAX_RATE, TRANSACTIONS_FILE, align_row, divider, format_rupiah, load_json, save_json,
)


class Product:
    """Satu jenis barang di toko: kode, nama, harga satuan, dan stok."""

    def __init__(self, code: str, name: str, price: int, stock: int) -> None:
        """Membuat objek Product. Memunculkan ValueError jika data tidak valid."""
        code = str(code).strip().upper()
        if not code or " " in code:
            raise ValueError("Kode barang tidak boleh kosong atau mengandung spasi.")
        self.code = code
        self.name = ""
        self.price = 0
        self.stock = 0
        self.update(name=name, price=price, stock=stock)

    def update(self, name: Optional[str] = None, price: Optional[int] = None,
               stock: Optional[int] = None) -> None:
        """Mengubah nama/harga/stok (None = tidak diubah). Semua nilai divalidasi
        dulu sebelum disimpan, jadi tidak ada perubahan setengah jalan."""
        if name is not None and not str(name).strip():
            raise ValueError("Nama barang tidak boleh kosong.")
        if price is not None and price <= 0:
            raise ValueError("Harga harus lebih dari 0.")
        if stock is not None and stock < 0:
            raise ValueError("Stok tidak boleh negatif.")
        if name is not None:
            self.name = str(name).strip()
        if price is not None:
            self.price = price
        if stock is not None:
            self.stock = stock

    def reduce_stock(self, quantity: int) -> None:
        """Mengurangi stok karena terjual. Ditolak jika quantity <= 0 atau melebihi stok."""
        if quantity <= 0:
            raise ValueError("Jumlah pengurangan stok harus lebih dari 0.")
        if quantity > self.stock:
            raise ValueError(f"Stok {self.name} tidak cukup (tersisa {self.stock}).")
        self.stock -= quantity

    def add_stock(self, quantity: int) -> None:
        """Menambah stok (restock). Ditolak jika quantity <= 0."""
        if quantity <= 0:
            raise ValueError("Jumlah penambahan stok harus lebih dari 0.")
        self.stock += quantity

    def is_low_stock(self, threshold: int = LOW_STOCK_THRESHOLD) -> bool:
        """True jika stok sudah sama dengan atau di bawah threshold."""
        return self.stock <= threshold

    def to_dict(self) -> Dict[str, Any]:
        """Mengubah objek menjadi dictionary (untuk disimpan ke JSON)."""
        return {"code": self.code, "name": self.name, "price": self.price, "stock": self.stock}


class Transaction:
    """Satu transaksi penjualan: keranjang belanja, perhitungan diskon dan
    pajak, serta data pembayaran."""

    def __init__(self, transaction_id: str, timestamp: Optional[str] = None) -> None:
        """Membuat transaksi dengan keranjang kosong. Tanpa timestamp, dipakai waktu saat ini."""
        self.id = transaction_id
        self.timestamp = timestamp or datetime.now().strftime(DATETIME_FORMAT)
        self.items: List[Dict[str, Any]] = []   # tiap item: {"code", "name", "price", "qty"}
        self.paid = 0
        self.change = 0

    def date(self) -> str:
        """Mengembalikan bagian tanggal (YYYY-MM-DD) dari timestamp."""
        return self.timestamp[:10]

    # ----- cart -----
    def cart_quantity(self, code: str) -> int:
        """Jumlah barang berkode tertentu yang sudah ada di keranjang."""
        return sum(item["qty"] for item in self.items if item["code"] == code)

    def available_stock(self, product: Product) -> int:
        """Stok yang masih bisa dibeli pada transaksi ini: stok asli dikurangi isi
        keranjang. Ini stok sementara; stok asli baru berkurang setelah pembayaran
        berhasil, dan tidak berubah jika transaksi dibatalkan."""
        return product.stock - self.cart_quantity(product.code)

    def add_item(self, product: Product, quantity: int) -> None:
        """Menambah barang ke keranjang. Ditolak jika quantity <= 0 atau melebihi
        stok tersedia (stok dikurangi isi keranjang). Barang yang sama digabung."""
        if quantity <= 0:
            raise ValueError("Jumlah harus lebih dari 0.")
        available = self.available_stock(product)
        if available <= 0:
            raise ValueError(f"Stok {product.name} habis atau seluruhnya sudah ada di keranjang.")
        if quantity > available:
            raise ValueError(f"Stok tidak cukup. {product.name} tersedia {available}, diminta {quantity}.")
        for item in self.items:
            if item["code"] == product.code:
                item["qty"] += quantity
                return
        self.items.append({"code": product.code, "name": product.name,
                           "price": product.price, "qty": quantity})

    def remove_item(self, code: str) -> None:
        """Menghapus satu jenis barang dari keranjang berdasarkan kode."""
        self.items = [item for item in self.items if item["code"] != code]

    def is_empty(self) -> bool:
        """True jika keranjang belum berisi apa pun."""
        return not self.items

    # ----- calculations -----
    def total_quantity(self) -> int:
        """Total jumlah satuan barang di keranjang."""
        return sum(item["qty"] for item in self.items)

    def subtotal(self) -> int:
        """Total harga seluruh barang sebelum diskon dan pajak."""
        return sum(item["price"] * item["qty"] for item in self.items)

    def discount_percent(self) -> int:
        """Persen diskon berdasarkan subtotal dan DISCOUNT_TIERS (0 jika tidak ada)."""
        subtotal = self.subtotal()
        return next((percent for minimum, percent in DISCOUNT_TIERS if subtotal >= minimum), 0)

    def discount(self) -> int:
        """Nominal diskon, dibulatkan ke rupiah terdekat."""
        return (self.subtotal() * self.discount_percent() + 50) // 100

    def taxable_amount(self) -> int:
        """Nilai setelah diskon (Dasar Pengenaan Pajak)."""
        return self.subtotal() - self.discount()

    def tax(self) -> int:
        """PPN dari nilai setelah diskon, dibulatkan ke rupiah terdekat."""
        return (self.taxable_amount() * TAX_RATE + 50) // 100

    def total(self) -> int:
        """Total yang harus dibayar pelanggan (setelah diskon dan pajak)."""
        return self.taxable_amount() + self.tax()

    def pay(self, cash: int) -> None:
        """Mencatat pembayaran tunai dan menghitung kembalian. Ditolak jika
        keranjang kosong atau uang kurang dari total."""
        if self.is_empty():
            raise ValueError("Keranjang masih kosong, tidak bisa checkout.")
        if cash < self.total():
            raise ValueError(f"Uang kurang {format_rupiah(self.total() - cash)} "
                             f"dari total {format_rupiah(self.total())}.")
        self.paid = cash
        self.change = cash - self.total()

    # ----- output -----
    def summary_lines(self) -> List[str]:
        """Baris rincian biaya: subtotal, diskon, nilai setelah diskon, PPN, total."""
        percent = self.discount_percent()
        discount_label = f"Diskon ({percent}%)" if percent else "Diskon"
        discount_text = ("-" if percent else "") + format_rupiah(self.discount())
        return [
            align_row("Subtotal", format_rupiah(self.subtotal())),
            align_row(discount_label, discount_text),
            align_row("Setelah diskon (DPP)", format_rupiah(self.taxable_amount())),
            align_row(f"PPN ({TAX_RATE}%)", format_rupiah(self.tax())),
            divider(),
            align_row("TOTAL", format_rupiah(self.total())),
        ]

    def receipt(self) -> str:
        """Menyusun teks struk lengkap (item, rincian biaya, bayar, kembalian)."""
        lines = [divider("="), STORE_NAME.center(LINE_WIDTH), divider("="),
                 f"No    : {self.id}", f"Waktu : {self.timestamp}", divider()]
        for item in self.items:
            lines.append(item["name"][:LINE_WIDTH])
            lines.append(align_row(f"  {item['qty']} x {format_rupiah(item['price'])}",
                                   format_rupiah(item["price"] * item["qty"])))
        lines.append(divider())
        lines.extend(self.summary_lines())
        lines.append(align_row("Bayar", format_rupiah(self.paid)))
        lines.append(align_row("Kembalian", format_rupiah(self.change)))
        lines.extend([divider("="), "Terima kasih, selamat belanja lagi!".center(LINE_WIDTH),
                      divider("=")])
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Mengubah transaksi menjadi dictionary (untuk JSON). Nilai diskon,
        pajak, dan total ikut disimpan sebagai catatan transaksi."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "items": [dict(item) for item in self.items],
            "subtotal": self.subtotal(),
            "discount_percent": self.discount_percent(),
            "discount": self.discount(),
            "taxable_amount": self.taxable_amount(),
            "tax": self.tax(),
            "total": self.total(),
            "paid": self.paid,
            "change": self.change,
        }


# ===== TRANSACTION HISTORY =====
def load_transactions(path: str = TRANSACTIONS_FILE) -> List[Transaction]:
    """Membaca seluruh riwayat transaksi dari file JSON menjadi list Transaction."""
    transactions = []
    for data in load_json(path, []):
        transaction = Transaction(data["id"], data["timestamp"])
        transaction.items = data["items"]
        transaction.paid = data["paid"]
        transaction.change = data["change"]
        transactions.append(transaction)
    return transactions


def save_transactions(transactions: List[Transaction], path: str = TRANSACTIONS_FILE) -> None:
    """Menyimpan seluruh riwayat transaksi ke file JSON."""
    save_json(path, [transaction.to_dict() for transaction in transactions])


def next_transaction_id(transactions: List[Transaction], date: str) -> str:
    """Membuat ID transaksi berurutan per hari, contoh: TRX-20261124-001."""
    sequence = sum(1 for transaction in transactions if transaction.date() == date) + 1
    return f"TRX-{date.replace('-', '')}-{sequence:03d}"