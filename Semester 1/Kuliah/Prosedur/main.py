"""
Program Modular Kategori IPK Mahasiswa

Struktur modul:
1. input_ipk()      -> FUNGSI input IPK (float)
2. kategori_ipk()   -> FUNGSI percabangan, mengembalikan kategori (str)
3. cetak_hasil()    -> PROSEDUR mencetak nilai akhir (IPK + kategori)
4. main()           -> alur program utama
"""


# ---------------------------------------------------------------
# FUNGSI 1: menerima input IPK (return float)
# ---------------------------------------------------------------
def input_ipk():
    """Meminta IPK dari pengguna (0.00 - 4.00). Return: float."""
    while True:
        try:
            ipk = float(input("Masukkan IPK (0.00 - 4.00): ").replace(",", "."))
            if 0.0 <= ipk <= 4.0:
                return ipk
            print("  IPK harus antara 0.00 dan 4.00.")
        except ValueError:
            print("  Input harus berupa angka, contoh: 3.75")


# ---------------------------------------------------------------
# FUNGSI 2: percabangan penentu kategori (return str)
# ---------------------------------------------------------------
def kategori_ipk(ipk):
    """Menentukan kategori berdasarkan nilai IPK."""
    if ipk >= 3.6:
        return "Cum Laude"
    elif ipk >= 3.0:
        return "Memuaskan"
    elif ipk >= 2.0:
        return "Cukup"
    else:
        return "Kurang"


# ---------------------------------------------------------------
# PROSEDUR: menampilkan nilai akhir ke layar (tanpa return)
# ---------------------------------------------------------------
def cetak_hasil(ipk, kategori):
    """Mencetak nilai akhir: IPK beserta kategorinya."""
    print("\n" + "=" * 36)
    print("         HASIL AKHIR IPK")
    print("=" * 36)
    print(f"IPK akhir : {ipk:.2f}")
    print(f"Kategori  : {kategori}")
    print("=" * 36)


# ---------------------------------------------------------------
# PROGRAM UTAMA
# ---------------------------------------------------------------
def main():
    print("=== PROGRAM KATEGORI IPK MAHASISWA ===\n")
    ipk = input_ipk()                 # 1. input IPK
    kategori = kategori_ipk(ipk)      # 2. tentukan kategori (percabangan)
    cetak_hasil(ipk, kategori)        # 3. tampilkan nilai akhir


if __name__ == "__main__":
    main()