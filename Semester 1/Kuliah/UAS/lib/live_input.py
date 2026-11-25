"""
live_input.py
Input interaktif real-time di terminal:
    - prompt_rupiah  : nominal rupiah dengan pemisah ribuan yang muncul saat mengetik
    - prompt_lookup  : kode/nama barang dengan daftar saran yang diperbarui tiap ketikan

Jika input bukan terminal interaktif (misalnya dijalankan lewat pipe atau
beberapa IDE), kedua fungsi otomatis memakai input() biasa dengan validasi yang sama.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Callable, Iterator, List, Optional

from lib.models import Product
from lib.utils import prompt_int, prompt_text

if os.name == "nt":
    import msvcrt

    os.system("")  # mengaktifkan dukungan ANSI escape di Windows 10+ (hapus baris, geser kursor)

MAX_RUPIAH_DIGITS = 12
MAX_LOOKUP_LENGTH = 40
MAX_SUGGESTIONS = 5
ENTER_KEYS = ("\r", "\n")
BACKSPACE_KEYS = ("\x08", "\x7f")


# ===== LOW-LEVEL TERMINAL HELPERS =====
def is_interactive() -> bool:
    """True jika input dan output terhubung ke terminal sungguhan (bukan pipe/file)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


@contextmanager
def keypress_mode() -> Iterator[None]:
    """Mengaktifkan pembacaan tombol satu per satu (tanpa Enter dan tanpa echo)
    selama blok `with`, lalu mengembalikan pengaturan terminal seperti semula
    meskipun terjadi error. Ctrl+C tetap berfungsi. Di Windows tidak perlu pengaturan."""
    if os.name == "nt":
        yield
        return
    # Modul Unix diimpor di sini agar tidak menyebabkan error saat dijalankan di Windows
    import termios
    import tty

    fd = sys.stdin.fileno()
    saved_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved_settings)


def read_key() -> str:
    """Membaca satu tombol tanpa menunggu Enter. Tombol spesial (panah, F1-F12)
    diabaikan dan dikembalikan sebagai string kosong. Ctrl+C memunculkan
    KeyboardInterrupt dan Ctrl+D memunculkan EOFError. Harus dipanggil di dalam keypress_mode()."""
    if os.name == "nt":
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):          # tombol spesial mengirim dua karakter
            msvcrt.getwch()
            return ""
    else:
        import select

        fd = sys.stdin.fileno()
        key = os.read(fd, 1).decode("utf-8", errors="ignore")
        if key == "\x1b":                    # panah dkk. dikirim sebagai urutan ESC [ ...
            while select.select([fd], [], [], 0.05)[0]:
                os.read(fd, 1)
            return ""
    if key == "\x03":
        raise KeyboardInterrupt
    if key == "\x04":
        raise EOFError
    return key


def write(text: str) -> None:
    """Menulis teks ke layar dan langsung menampilkannya (flush)."""
    sys.stdout.write(text)
    sys.stdout.flush()


# ===== LIVE RUPIAH INPUT =====
def format_thousands(digits: str) -> str:
    """Mengubah string digit murni menjadi format ribuan, contoh: '80000' -> '80.000'."""
    return f"{int(digits):,}".replace(",", ".") if digits else ""


def read_rupiah(prompt: str) -> str:
    """Membaca digit nominal secara real-time sambil menampilkan titik ribuan.
    Hanya angka yang diterima, awalan '0' diabaikan, dan panjangnya dibatasi.
    Mengembalikan string digit murni (kosong jika tidak ada yang diketik)."""
    digits = ""
    with keypress_mode():
        write(prompt)
        while True:
            key = read_key()
            if key in ENTER_KEYS:
                write("\n")
                return digits
            if key in BACKSPACE_KEYS:
                digits = digits[:-1]
            elif key.isascii() and key.isdigit() and len(digits) < MAX_RUPIAH_DIGITS \
                    and (digits or key != "0"):
                digits += key
            else:
                continue                      # tombol lain diabaikan, tidak perlu menggambar ulang
            write(f"\r\033[K{prompt}{format_thousands(digits)}")


def prompt_rupiah(prompt: str, minimum: int = 1, allow_empty: bool = False) -> Optional[int]:
    """Meminta nominal rupiah dengan pemisah ribuan otomatis. Nilai di bawah
    minimum ditolak lalu ditanya ulang. Jika allow_empty=True dan pengguna hanya
    menekan Enter, mengembalikan None. Contoh prompt: 'Harga satuan: Rp'."""
    if not is_interactive():
        return prompt_int(prompt, minimum=minimum, allow_empty=allow_empty)
    while True:
        digits = read_rupiah(prompt)
        if not digits:
            if allow_empty:
                return None
            print("  [!] Input tidak boleh kosong.")
        elif int(digits) < minimum:
            print(f"  [!] Nilai minimal adalah {minimum}.")
        else:
            return int(digits)


# ===== LIVE PRODUCT LOOKUP =====
def render_lookup(prompt: str, text: str, matches: List[Product],
                  stock_of: Callable[[Product], int]) -> None:
    """Menggambar ulang baris input beserta daftar saran di bawahnya. Posisi
    kursor dihitung relatif (bukan disimpan), jadi tampilan tetap benar walau
    layar ikut bergulir karena baris input ada di dasar terminal. stock_of menentukan
    angka stok yang ditampilkan pada tiap saran."""
    lines = ["  [Saran - tekan TAB untuk melengkapi jika hanya 1 cocok]" if matches
             else "  [Tidak ada barang yang cocok]"]
    lines += [f"    - {product.code:<6}{product.name[:26]:<27}stok {stock_of(product)}"
              for product in matches[:MAX_SUGGESTIONS]]
    if len(matches) > MAX_SUGGESTIONS:
        lines.append(f"    ... dan {len(matches) - MAX_SUGGESTIONS} barang lainnya")
    column = len(prompt) + len(text)
    output = f"\r\033[J{prompt}{text}"                  # hapus layar mulai dari baris input
    output += "".join(f"\n\033[K{line}" for line in lines)
    output += f"\033[{len(lines)}A\r"                   # naik kembali ke baris input
    output += f"\033[{column}C" if column else ""       # kursor di akhir teks
    write(output)


def read_lookup(prompt: str, lookup: Callable[[str], List[Product]],
                stock_of: Callable[[Product], int]) -> str:
    """Membaca kode atau nama barang secara real-time. Setiap ketikan memanggil
    lookup(teks) untuk menampilkan saran. TAB melengkapi dengan kode barang jika
    saran tinggal satu. Mengembalikan teks yang diketik (sudah di-strip)."""
    text = ""
    with keypress_mode():
        try:
            while True:
                matches = lookup(text)
                render_lookup(prompt, text, matches, stock_of)
                key = read_key()
                if key in ENTER_KEYS:
                    write(f"\r\033[J{prompt}{text}\n")  # bersihkan saran, sisakan baris input
                    return text.strip()
                if key == "\t":
                    if len(matches) == 1:
                        text = matches[0].code
                elif key in BACKSPACE_KEYS:
                    text = text[:-1]
                elif key and key.isprintable() and len(text) < MAX_LOOKUP_LENGTH:
                    text += key
        except (KeyboardInterrupt, EOFError):
            write(f"\r\033[J{prompt}{text}\n")          # bersihkan saran sebelum keluar
            raise


def prompt_lookup(lookup: Callable[[str], List[Product]], prompt: str,
                  stock_of: Optional[Callable[[Product], int]] = None) -> str:
    """Meminta kode/nama barang dengan saran real-time. lookup biasanya
    Inventory.search. stock_of (opsional) menentukan stok yang ditampilkan, misalnya
    stok sementara saat transaksi; bawaannya stok asli. Mengembalikan teks yang
    diketik (kosong jika hanya Enter)."""
    if not is_interactive():
        return prompt_text(prompt, allow_empty=True)
    return read_lookup(prompt, lookup, stock_of or (lambda product: product.stock))