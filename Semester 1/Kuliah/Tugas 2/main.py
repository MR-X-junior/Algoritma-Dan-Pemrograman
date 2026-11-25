 """Program Pengolah Nilai Mahasiswa Menggunakan Prosedur."""

def input_data(daftar):
    """Prosedur input: mengisi daftar mahasiswa dari keyboard."""
    jumlah = int(input("Masukkan jumlah mahasiswa: "))
    for i in range(jumlah):
        print(f"\nData mahasiswa ke-{i + 1}")
        nama = input("Nama  : ")
        tugas = float(input("Tugas : "))
        uts = float(input("UTS   : "))
        uas = float(input("UAS   : "))
        daftar.append({"nama": nama, "tugas": tugas,
                       "uts": uts, "uas": uas})

def proses_data(daftar):
    """Prosedur pengolahan: hitung nilai akhir, grade, dan status."""
    for mhs in daftar:
        akhir = (mhs["tugas"] * 3 + mhs["uts"] * 3
                 + mhs["uas"] * 4) / 10
        if akhir >= 85:
            grade = "A"
        elif akhir >= 70:
            grade = "B"
        elif akhir >= 60:
            grade = "C"
        elif akhir >= 50:
            grade = "D"
        else:
            grade = "E"
        mhs["akhir"] = akhir
        mhs["grade"] = grade
        mhs["status"] = "LULUS" if akhir >= 60 else "TIDAK LULUS"

def tampil_hasil(daftar):
    """Prosedur output: menampilkan tabel hasil pengolahan."""
    print("\n" + "=" * 52)
    print(f"{'No':<4}{'Nama':<18}{'Akhir':>8}{'Grade':>8}  Status")
    print("=" * 52)
    for no, mhs in enumerate(daftar, start=1):
        print(f"{no:<4}{mhs['nama']:<18}{mhs['akhir']:>8.1f}"
              f"{mhs['grade']:>8}  {mhs['status']}")
    print("=" * 52)

# Program utama
data_mahasiswa = []
input_data(data_mahasiswa)
proses_data(data_mahasiswa)
tampil_hasil(data_mahasiswa)
