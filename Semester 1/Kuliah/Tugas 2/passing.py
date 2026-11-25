"""Demo passing parameter pada Python."""

def ubah_angka(x):
    x = x + 10
    print("  di dalam prosedur  :", x)

def tambah_item(daftar):
    daftar.append(99)
    print("  di dalam prosedur  :", daftar)

def ganti_daftar(daftar):
    daftar = [0, 0, 0]
    print("  di dalam prosedur  :", daftar)

print("1. Tipe immutable (int)")
a = 5
ubah_angka(a)
print("  setelah dipanggil  :", a)

print("2. Tipe mutable (list), dimodifikasi")
b = [1, 2, 3]
tambah_item(b)
print("  setelah dipanggil  :", b)

print("3. Tipe mutable (list), diganti total")
c = [1, 2, 3]
ganti_daftar(c)
print("  setelah dipanggil  :", c)

print("4. Bukti objek sama")
d = [1, 2, 3]

def cek_id(daftar):
    print("  id di dalam        :", id(daftar) == id(d))

cek_id(d)
 