"""
PROGRAM CEK IPK
Di buat untuk memunuhi tugas kuliah mata kuliah Algoritma dan pemrograman
"""

# Nama : Rahmat Adha
# NIM  : 2605176027
# Kelas: Pendidikan Komputer 26A

def get_gpa_category(nilai_ipk):
    if not 0 <= nilai_ipk <= 4:
        return "Tidak Valid"
    elif nilai_ipk >= 3.5:
        return "Cum Laude"
    elif nilai_ipk >= 3.0:
        return "Sangat Memuaskan"
    elif nilai_ipk >= 2.0:
        return "Cukup"
    else:
        return "Kurang"


def show_result(nilai_ipk, predikat):
    print("\n----- HASIL IPK -----")
    print(f"IPK      = {nilai_ipk:.2f}")
    print(f"Predikat = {predikat}")
    print("---------------------")


print("PROGRAM CEK IPK")
data_ipk = float(input("Masukkan IPK anda: "))

hasil = get_gpa_category(data_ipk)
show_result(data_ipk, hasil)