"""
Program Penghitung Nilai Akhir, Grade, dan Status Kelulusan Mahasiswa.
Dibuat untuk memenuhi Tugas 1 Praktikum Algoritma dan Pemrograman.
"""

# Kelompok 1:
# 2605176004 - Maisaroh Elvin Aldiyani
# 2605176027 - Rahmat Adha
# 2605176028 - Rahmat Noor Sani
#
# https://github.com/MR-X-junior/Algoritma-Dan-Pemrograman/tree/main/Tugas%201

data = [
    ["Maisaroh Elvin Aldiyani", 99, 99, 99],
    ["Rahmat Adha", 78, 80, 82],
    ["Viera", 70, 68, 72],
    ["Tiara", 60, 62, 64],
    ["Rahmat Noor Sani", 44, 43, 50],
]

for mahasiswa in data:
    nama = mahasiswa[0]
    tugas = mahasiswa[1]
    uts = mahasiswa[2]
    uas = mahasiswa[3]

    nilai_akhir = (tugas * 3 + uts * 3 + uas * 4) / 10

    if nilai_akhir >= 85:
        grade = "A"
    elif nilai_akhir >= 75:
        grade = "B"
    elif nilai_akhir >= 65:
        grade = "C"
    elif nilai_akhir >= 50:
        grade = "D"
    else:
        grade = "E"

    if nilai_akhir >= 60:
        status = "LULUS"
    else:
        status = "TIDAK LULUS"

    print(f"[✓] Nama  : {nama}")
    print(f"[✓] TUGAS : {tugas}")
    print(f"[✓] UTS   : {uts}")
    print(f"[✓] UAS   : {uas}")
    print(f"[✓] Nilai : {nilai_akhir:.1f}")
    print(f"[✓] Grade : {grade}")
    print(f"[✓] Status: {status}")
    print("-" * 30)