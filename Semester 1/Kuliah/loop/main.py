ulang = 25

for i in range(ulang):
  print("Perulangan ke-", i )

hitung = 0
jawab = "ya"
while (jawab == "ya"):
    print("Perulangan ke-", hitung + 1)
    jawab = input("Apakah ingin melanjutkan? (y/n): ")
    hitung += 1