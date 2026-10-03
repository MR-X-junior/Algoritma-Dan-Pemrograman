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
    {"nama": "Rahmat Adha", "tugas": 99, "uts": 99, "uas": 99},
    {"nama": "Viera", "tugas": 78, "uts": 80, "uas": 82},
    {"nama": "Tiara Maharani", "tugas": 70, "uts": 68, "uas": 72},
    {"nama": "Maisaroh Elvin Aldiyani", "tugas": 60, "uts": 62, "uas": 64},
    {"nama": "Rahmat Noor Sani", "tugas": 44, "uts": 43, "uas": 50},
]

for mahasiswa in data:
    nilai_akhir = (
        mahasiswa["tugas"] * 3
        + mahasiswa["uts"] * 3
        + mahasiswa["uas"] * 4
    ) / 10

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

    print(f"[✓] Nama  : {mahasiswa['nama']}")
    print(f"[✓] TUGAS : {mahasiswa['tugas']}")
    print(f"[✓] UTS   : {mahasiswa['uts']}")
    print(f"[✓] UAS   : {mahasiswa['uas']}")
    print(f"[✓] Nilai : {nilai_akhir:.1f}")
    print(f"[✓] Grade : {grade}")
    print(f"[✓] Status: {status}")
    print("-" * 30)
