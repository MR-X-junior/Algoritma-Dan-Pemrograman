"""
utils.py
Konstanta aplikasi, fungsi format tampilan, validasi input pengguna,
dan helper baca/tulis file JSON yang dipakai oleh modul lain.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ===== PATHS =====
# Path dihitung dari lokasi proyek (bukan folder terminal), jadi program
# tetap berjalan benar walau dijalankan dari folder lain.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORT_DIR = os.path.join(BASE_DIR, "export")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.json")

# ===== STORE & PRICING RULES =====
STORE_NAME = "Rahmat Store"          # nama toko, dicetak di struk dan laporan
TAX_RATE = 11                    # persen PPN, dihitung dari nilai setelah diskon
LOW_STOCK_THRESHOLD = 5          # stok <= angka ini dianggap menipis
# (minimal belanja, persen diskon), diurutkan dari yang terbesar
DISCOUNT_TIERS = [(500_000, 15), (250_000, 10), (100_000, 5)]

# ===== FORMATS =====
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LINE_WIDTH = 53                  # lebar garis, judul, tabel, dan struk (disamakan)
CSV_DELIMITER = ";"              # ganti "," jika Excel memakai pengaturan regional English

# Bilangan bulat valid: "15000" atau memakai titik ribuan "15.000"
_INT_PATTERN = re.compile(r"\d+|\d{1,3}(\.\d{3})+")


# ===== DISPLAY HELPERS =====
def format_rupiah(amount: int) -> str:
    """Mengubah angka menjadi teks rupiah, contoh: 15000 -> 'Rp15.000'."""
    return "Rp" + f"{amount:,}".replace(",", ".")


def divider(char: str = "-", width: int = LINE_WIDTH) -> str:
    """Mengembalikan garis pemisah dari karakter yang diulang sepanjang width."""
    return char * width


def print_title(text: str) -> None:
    """Mencetak judul bagian, diapit garis di atas dan bawahnya."""
    print(f"\n{divider('=')}\n{text.center(LINE_WIDTH)}\n{divider('=')}")


def align_row(left: str, right: str, width: int = LINE_WIDTH) -> str:
    """Menyusun satu baris: teks kiri rata kiri dan teks kanan rata kanan."""
    return left + " " * max(1, width - len(left) - len(right)) + right


def normalize_code(code: str) -> str:
    """Menyeragamkan kode barang: spasi dan tanda '-' dibuang, huruf jadi kapital,
    sehingga 'b-001', 'B 001', dan 'B001' dianggap sama."""
    return re.sub(r"[\s-]", "", str(code)).upper()


def escape_formula(text: str) -> str:
    """Mencegah 'formula injection' di Excel/CSV: teks yang diawali = + - @ diberi
    tanda petik di depan supaya dibaca sebagai teks biasa, bukan rumus."""
    text = str(text)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def today() -> str:
    """Mengembalikan tanggal hari ini berformat YYYY-MM-DD."""
    return datetime.now().strftime(DATE_FORMAT)


# ===== INPUT VALIDATION =====
def prompt_text(prompt: str, allow_empty: bool = False) -> str:
    """Meminta input teks. Diulang sampai tidak kosong (kecuali allow_empty=True)."""
    while True:
        value = input(prompt).strip()
        if value or allow_empty:
            return value
        print("  [!] Input tidak boleh kosong.")


def prompt_int(prompt: str, minimum: Optional[int] = None, maximum: Optional[int] = None,
               allow_empty: bool = False) -> Optional[int]:
    """Meminta bilangan bulat dan memvalidasinya (bukan angka, negatif, di luar
    batas minimum/maksimum akan ditolak lalu ditanya ulang). Jika allow_empty=True
    dan pengguna hanya menekan Enter, mengembalikan None."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            if allow_empty:
                return None
            print("  [!] Input tidak boleh kosong.")
            continue
        cleaned = raw.lower().replace("rp", "").replace(" ", "")
        if cleaned.startswith("-") and cleaned[1:].isdigit():
            print("  [!] Angka tidak boleh negatif.")
        elif not _INT_PATTERN.fullmatch(cleaned):
            print("  [!] Input harus berupa angka bulat, contoh: 15000 atau 15.000.")
        else:
            value = int(cleaned.replace(".", ""))
            if minimum is not None and value < minimum:
                print(f"  [!] Nilai minimal adalah {minimum}.")
            elif maximum is not None and value > maximum:
                print(f"  [!] Nilai maksimal adalah {maximum}.")
            else:
                return value


def prompt_choice(prompt: str, valid_choices: List[str]) -> str:
    """Meminta pilihan menu. Hanya menerima salah satu dari valid_choices,
    selain itu menampilkan pesan error dan bertanya ulang."""
    while True:
        value = input(prompt).strip().lower()
        if value in valid_choices:
            return value
        print("  [!] Pilihan tidak valid. Pilih salah satu dari: " + ", ".join(valid_choices) + ".")


def prompt_yes_no(prompt: str) -> bool:
    """Meminta konfirmasi y/t. Mengembalikan True untuk ya, False untuk tidak."""
    while True:
        value = input(f"{prompt} (y/t): ").strip().lower()
        if value in ("y", "ya"):
            return True
        if value in ("t", "tidak", "n"):
            return False
        print("  [!] Jawab dengan 'y' (ya) atau 't' (tidak).")


def prompt_date(prompt: str) -> str:
    """Meminta tanggal berformat YYYY-MM-DD. Enter = hari ini. Format salah
    atau tanggal yang tidak ada (misal bulan 13) ditolak lalu ditanya ulang."""
    while True:
        value = prompt_text(prompt, allow_empty=True)
        if not value:
            return today()
        try:
            return datetime.strptime(value, DATE_FORMAT).strftime(DATE_FORMAT)
        except ValueError:
            print("  [!] Format tanggal salah. Contoh yang benar: 2026-12-01.")


def pause() -> None:
    """Menahan tampilan sampai pengguna menekan Enter."""
    input("\nTekan Enter untuk melanjutkan...")


# ===== FOLDER CHECK =====
def ensure_directories(paths: Tuple[str, ...] = (DATA_DIR, EXPORT_DIR)) -> Dict[str, bool]:
    """Memastikan folder yang dibutuhkan program ada. Folder yang belum ada dibuat,
    yang sudah ada dibiarkan. Mengembalikan {nama_folder: True jika baru dibuat}."""
    status = {}
    for path in paths:
        created = not os.path.isdir(path)
        if created:
            os.makedirs(path)
        status[os.path.basename(path)] = created
    return status


# ===== JSON STORAGE =====
def load_json(path: str, default: Any) -> Any:
    """Membaca file JSON. Jika file belum ada, mengembalikan default. Jika isinya
    rusak, file diganti nama menjadi *.rusak lalu mengembalikan default
    supaya program tidak crash."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        os.replace(path, path + ".rusak")
        print(f"  [!] File {os.path.basename(path)} rusak, disimpan sebagai *.rusak "
              "dan data dimulai dari awal.")
        return default


def save_json(path: str, data: Any) -> None:
    """Menulis data ke file JSON dengan aman: tulis ke file sementara dulu lalu
    ganti file asli, supaya data tidak rusak jika program terhenti di tengah jalan."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)