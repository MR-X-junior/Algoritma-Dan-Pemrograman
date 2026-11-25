"""
main.py
Titik masuk aplikasi Smart-POS (Sistem Manajemen Kasir & Inventaris Toko Ritel).
Berisi menu dan alur interaksi dengan pengguna. Logika bisnis ada di paket lib
(models, inventory, report).

Cara menjalankan:  python main.py
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional, Tuple

from lib import DailyReport, Inventory, Product, Transaction
from lib.live_input import prompt_lookup, prompt_rupiah
from lib.models import load_transactions, next_transaction_id, save_transactions
from lib.utils import (
    DISCOUNT_TIERS, LOW_STOCK_THRESHOLD, PRODUCTS_FILE, STORE_NAME, TAX_RATE, TRANSACTIONS_FILE,
    divider, ensure_directories, format_rupiah, pause, print_title, prompt_choice, prompt_date,
    prompt_int, prompt_text, prompt_yes_no, today,
)

# Satu opsi menu: (tombol, label, handler). Handler yang mengembalikan True menutup menu.
MenuOption = Tuple[str, str, Callable[[], Optional[bool]]]
BACK: MenuOption = ("0", "Kembali", lambda: True)


# ===== MENU & DISPLAY HELPERS =====
def run_menu(title: str, options: List[MenuOption], pause_after: bool = False,
             header: Optional[Callable[[], None]] = None) -> None:
    """Menampilkan menu berulang sampai salah satu handler mengembalikan True.
    header (opsional) dipanggil tiap kali menu digambar, pause_after menahan
    layar setelah handler selesai."""
    handlers = {key: handler for key, _, handler in options}
    while True:
        print_title(title)
        if header:
            header()
        for key, label, _ in options:
            print(f"{key}. {label}")
        if handlers[prompt_choice("Pilih menu: ", list(handlers))]():
            return
        if pause_after:
            pause()


def print_product_table(products: List[Product],
                        stock_of: Optional[Callable[[Product], int]] = None) -> None:
    """Mencetak tabel barang (kode, nama, harga, stok); stok menipis diberi tanda.
    stock_of (opsional) menentukan stok yang ditampilkan, bawaannya stok asli."""
    if not products:
        print("  (tidak ada barang)")
        return
    print(f"{'Kode':<8}{'Nama Barang':<26}{'Harga':>12}{'Stok':>7}\n{divider()}")
    for product in products:
        stock = stock_of(product) if stock_of else product.stock
        flag = "  <- menipis" if stock <= LOW_STOCK_THRESHOLD else ""
        print(f"{product.code:<8}{product.name[:25]:<26}"
              f"{format_rupiah(product.price):>12}{stock:>7}{flag}")


def print_cart(transaction: Transaction) -> None:
    """Mencetak isi keranjang belanja beserta subtotal sementara."""
    print(f"\n{divider()}")
    if transaction.is_empty():
        print("Keranjang masih kosong.")
    else:
        print(f"{'No':<4}{'Barang':<24}{'Qty':>5}{'Harga':>10}{'Jumlah':>10}")
        for number, item in enumerate(transaction.items, start=1):
            print(f"{number:<4}{item['name'][:23]:<24}{item['qty']:>5}"
                  f"{format_rupiah(item['price']):>10}"
                  f"{format_rupiah(item['price'] * item['qty']):>10}")
        print(f"Subtotal sementara: {format_rupiah(transaction.subtotal())}")
    print(divider())


def show_products(inventory: Inventory, wait: bool = False,
                  transaction: Optional[Transaction] = None) -> None:
    """Mencetak tabel seluruh barang. wait=True menahan layar sampai Enter.
    Jika transaction diberikan, stok yang tampil sudah dikurangi isi keranjang."""
    print()
    print_product_table(inventory.all(), transaction.available_stock if transaction else None)
    if wait:
        pause()


def ask_product(inventory: Inventory, prompt: str = "Kode barang (Enter = batal): ",
                transaction: Optional[Transaction] = None) -> Optional[Product]:
    """Meminta kode barang dengan saran real-time (bisa mengetik kode atau nama).
    Diulang sampai ditemukan. Enter kosong = batal (mengembalikan None).
    Jika transaction diberikan, stok pada saran sudah dikurangi isi keranjang."""
    stock_of = transaction.available_stock if transaction else None
    while True:
        code = prompt_lookup(inventory.search, prompt, stock_of)
        if not code:
            return None
        product = inventory.find(code)
        if product:
            return product
        print(f"  [!] Barang dengan kode '{code.upper()}' tidak ditemukan.")


# ===== PRODUCT MANAGEMENT =====
def manage_products(inventory: Inventory) -> None:
    """Submenu pengelolaan barang: lihat, tambah, ubah, hapus, cari, restock."""
    run_menu("KELOLA BARANG", [
        ("1", "Lihat semua barang", lambda: show_products(inventory)),
        ("2", "Tambah barang baru", lambda: add_product(inventory)),
        ("3", "Ubah data barang", lambda: edit_product(inventory)),
        ("4", "Hapus barang", lambda: delete_product(inventory)),
        ("5", "Cari barang (nama)", lambda: search_products(inventory)),
        ("6", "Tambah stok (restock)", lambda: restock_product(inventory)),
        BACK,
    ], pause_after=True)


def add_product(inventory: Inventory) -> None:
    """Meminta data barang baru lalu menambahkannya. Kode duplikat ditolak."""
    print("\n-- Tambah Barang Baru --")
    code = prompt_text("Kode barang (contoh: B011): ").upper()
    while inventory.find(code) or " " in code:
        print(f"  [!] Kode '{code}' tidak valid atau sudah dipakai. Gunakan kode lain.")
        code = prompt_text("Kode barang (contoh: B011): ").upper()
    name = prompt_text("Nama barang: ")
    price = prompt_rupiah("Harga satuan: Rp")
    stock = prompt_int("Stok awal: ", minimum=0)
    inventory.add(Product(code, name, price, stock))
    print(f"  [OK] Barang {code} - {name} berhasil ditambahkan.")


def edit_product(inventory: Inventory) -> None:
    """Mengubah nama, harga, atau stok barang. Enter kosong = tidak diubah."""
    print("\n-- Ubah Data Barang --")
    product = ask_product(inventory)
    if not product:
        return
    print(f"Data saat ini: {product.name} | {format_rupiah(product.price)} | stok {product.stock}")
    print("(Kosongkan lalu Enter untuk tidak mengubah)")
    changes = {
        "name": prompt_text("Nama baru: ", allow_empty=True) or None,
        "price": prompt_rupiah("Harga baru (Enter = tidak diubah): Rp", allow_empty=True),
        "stock": prompt_int("Stok baru: ", minimum=0, allow_empty=True),
    }
    changes = {field: value for field, value in changes.items() if value is not None}
    if changes:
        inventory.update(product.code, **changes)
        print(f"  [OK] Data {product.code} berhasil diubah.")
    else:
        print("  Tidak ada perubahan.")


def delete_product(inventory: Inventory) -> None:
    """Menghapus barang setelah pengguna mengonfirmasi."""
    print("\n-- Hapus Barang --")
    product = ask_product(inventory)
    if product and prompt_yes_no(f"Yakin hapus {product.code} - {product.name}?"):
        inventory.remove(product.code)
        print(f"  [OK] Barang {product.code} dihapus.")
    elif product:
        print("  Penghapusan dibatalkan.")


def search_products(inventory: Inventory) -> None:
    """Mencari barang berdasarkan kode atau nama (dengan saran real-time),
    lalu menampilkan hasilnya. Enter kosong = batal."""
    keyword = prompt_lookup(inventory.search, "Cari kode/nama barang (Enter = batal): ")
    if not keyword:
        return
    results = inventory.search(keyword)
    print()
    if results:
        print_product_table(results)
    else:
        print(f"  Tidak ada barang untuk '{keyword}'.")


def restock_product(inventory: Inventory) -> None:
    """Menambah stok barang yang sudah ada."""
    print("\n-- Tambah Stok --")
    product = ask_product(inventory)
    if product:
        quantity = prompt_int(f"Jumlah stok masuk untuk {product.name}: ", minimum=1)
        inventory.restock(product.code, quantity)
        print(f"  [OK] Stok {product.name} sekarang {product.stock}.")


# ===== SALES TRANSACTION =====
def new_transaction(inventory: Inventory, transactions: List[Transaction]) -> None:
    """Alur transaksi: isi keranjang -> hapus item (opsional) -> bayar -> struk.
    Stok baru berkurang saat pembayaran berhasil."""
    transaction = Transaction(next_transaction_id(transactions, today()))

    def cancel() -> bool:
        """Membatalkan transaksi (dengan konfirmasi jika keranjang sudah terisi)."""
        if transaction.is_empty() or prompt_yes_no("Keranjang akan dikosongkan. Batalkan transaksi?"):
            print("  Transaksi dibatalkan.")
            return True
        return False

    run_menu(f"TRANSAKSI BARU - {transaction.id}", [
        ("1", "Tambah barang ke keranjang", lambda: add_to_cart(inventory, transaction)),
        ("2", "Lihat daftar barang", lambda: show_products(inventory, wait=True, transaction=transaction)),
        ("3", "Hapus barang dari keranjang", lambda: remove_from_cart(transaction)),
        ("4", "Bayar / Checkout", lambda: checkout(inventory, transactions, transaction)),
        ("0", "Batalkan transaksi", cancel),
    ], header=lambda: print_cart(transaction))


def add_to_cart(inventory: Inventory, transaction: Transaction) -> None:
    """Memilih barang dan jumlahnya lalu memasukkannya ke keranjang.
    Kode tidak ditemukan atau stok tidak cukup akan ditolak."""
    product = ask_product(inventory, transaction=transaction)
    if not product:
        return
    print(f"  {product.name} - {format_rupiah(product.price)} "
          f"(stok tersedia {transaction.available_stock(product)})")
    quantity = prompt_int("Jumlah: ", minimum=1)
    try:
        transaction.add_item(product, quantity)
        print(f"  [OK] {quantity} x {product.name} masuk keranjang.")
    except ValueError as error:
        print(f"  [!] {error}")


def remove_from_cart(transaction: Transaction) -> None:
    """Menghapus satu barang dari keranjang berdasarkan nomor urut."""
    if transaction.is_empty():
        print("  [!] Keranjang masih kosong.")
        return
    number = prompt_int("Nomor item yang dihapus: ", minimum=1, maximum=len(transaction.items))
    item = transaction.items[number - 1]
    transaction.remove_item(item["code"])
    print(f"  [OK] {item['name']} dihapus dari keranjang.")


def checkout(inventory: Inventory, transactions: List[Transaction], transaction: Transaction) -> bool:
    """Menampilkan rincian biaya, meminta uang bayar, lalu menyelesaikan transaksi
    (kurangi stok, simpan riwayat, cetak struk). Mengembalikan True jika transaksi
    selesai, False jika pengguna kembali ke keranjang."""
    if transaction.is_empty():
        print("  [!] Keranjang masih kosong, tidak bisa checkout.")
        return False
    print(f"\n{divider('=')}")
    print("\n".join(transaction.summary_lines()))
    print(divider("="))
    while True:
        cash = prompt_rupiah("Uang dibayar (Enter = kembali): Rp", allow_empty=True)
        if cash is None:
            return False
        try:
            transaction.pay(cash)
            break
        except ValueError as error:
            print(f"  [!] {error}")
    try:
        inventory.commit_sale(transaction)
    except ValueError as error:
        print(f"  [!] Transaksi gagal: {error}")
        return False
    transactions.append(transaction)
    save_transactions(transactions)
    print(f"\n{transaction.receipt()}")
    pause()
    return True


# ===== REPORTS & INFO =====
def show_reports(transactions: List[Transaction]) -> None:
    """Memilih tanggal laporan, lalu submenu: tampil di layar / export CSV / export Excel."""
    report = DailyReport(transactions, prompt_date(f"Tanggal laporan YYYY-MM-DD (Enter = {today()}): "))

    def export(exporter: Callable[[], List[str]]) -> None:
        """Menjalankan satu fungsi export dan menampilkan lokasi file hasilnya.
        Gagal menyimpan (misalnya file sedang dibuka di Excel) ditampilkan sebagai pesan."""
        if not report.has_data():
            print(f"  [!] Tidak ada transaksi pada {report.date}, tidak ada yang di-export.")
            return
        try:
            for path in exporter():
                print(f"  [OK] File tersimpan: {path}")
        except RuntimeError as error:
            print(f"  [!] {error}")
        except OSError as error:
            print(f"  [!] Gagal menyimpan file: {error}")
            print("      Pastikan file laporan tidak sedang dibuka di program lain (Excel, VS Code).")

    run_menu(f"LAPORAN PENJUALAN {report.date}", [
        ("a", "Tampilkan di layar", report.show),
        ("b", "Export ke CSV", lambda: export(report.export_csv)),
        ("c", "Export ke Excel (.xlsx)", lambda: export(report.export_excel)),
        BACK,
    ], pause_after=True)


def show_low_stock(inventory: Inventory) -> None:
    """Menampilkan barang yang stoknya sudah menipis atau habis."""
    print_title("CEK STOK MENIPIS")
    low_stock = inventory.low_stock()
    if low_stock:
        print(f"Barang dengan stok <= {LOW_STOCK_THRESHOLD}:\n")
        print_product_table(low_stock)
    else:
        print(f"Semua stok aman (di atas {LOW_STOCK_THRESHOLD}).")
    pause()


def show_rules() -> None:
    """Menampilkan aturan diskon dan pajak yang berlaku."""
    print_title("ATURAN DISKON & PAJAK")
    for minimum, percent in sorted(DISCOUNT_TIERS):
        print(f"Belanja >= {format_rupiah(minimum)}: diskon {percent}%")
    print(f"PPN {TAX_RATE}% dihitung dari total setelah diskon.")
    pause()


def main() -> None:
    """Memuat data, lalu menjalankan menu utama sampai pengguna
    memilih keluar. Ctrl+C atau akhir input ditutup dengan rapi; data yang sudah
    diproses tetap tersimpan."""

    inventory = Inventory()
    transactions = load_transactions()

    def exit_app() -> bool:
        """Menampilkan pesan perpisahan lalu menutup menu utama."""
        print("\nTerima kasih. Data sudah tersimpan. Sampai jumpa!")
        return True

    try:
        run_menu(f"SMART-POS | {STORE_NAME}", [
            ("1", "Kelola Barang", lambda: manage_products(inventory)),
            ("2", "Transaksi Baru", lambda: new_transaction(inventory, transactions)),
            ("3", "Laporan Penjualan Harian", lambda: show_reports(transactions)),
            ("4", "Cek Stok Menipis", lambda: show_low_stock(inventory)),
            ("5", "Lihat Aturan Diskon & Pajak", show_rules),
            ("0", "Keluar", exit_app),
        ])
    except (KeyboardInterrupt, EOFError):
        print("\n\nProgram dihentikan. Data yang sudah diproses tetap tersimpan.")


if __name__ == "__main__":
    main()