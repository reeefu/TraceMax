---
title: Antarmuka
---

# Antarmuka

## Layout Utama

Window TraceMax terdiri dari empat area:

1. **Menu Bar** > akses semua fitur melalui menu
2. **Toolbar** > panel kontrol di bagian atas (tinggi 120 px)
3. **Canvas** > area tampilan seismogram
4. **Status Bar** > informasi file dan rekaman di bagian bawah

## Menu

### File

| Menu | Fungsi |
|---|---|
| Open | Buka file data JSON (bisa pilih beberapa file sekaligus untuk di-combine) |
| Open Configuration | Muat konfigurasi GUI dari file JSON, aplikasi restart otomatis |
| Save | Simpan data beserta pick, filter, dan konfigurasi ke file JSON |
| Restart | Restart aplikasi (tanpa menutup) |
| Close | Tutup aplikasi |

### Tools

| Menu | Fungsi |
|---|---|
| Stack | Rata-ratakan amplitudo trace terpilih menjadi satu trace baru (`stack-NN`) |
| Normalize | Hapus DC offset dan normalisasi amplitudo semua trace |
| Save Configuration | Simpan konfigurasi GUI saat ini ke file JSON |
| FFT Spectrum | Buka dialog analisis spektrum frekuensi |
| Arrival Times | Buka dialog tabel waktu tiba (modeless) |
| STA/LTA Picker | Buka dialog auto-picker STA/LTA |
| Hagiwara Analysis | Buka dialog analisis refraksi Hagiwara |

### Help

| Menu | Fungsi |
|---|---|
| Usage Instruction | Buka dokumentasi HTML bawaan |
| About | Informasi versi dan lisensi |

## Toolbar

### Grup PICK

| Elemen | Fungsi |
|---|---|
| Text box (log) | Menampilkan riwayat pick: `trace(01) 0.012345` |
| **START PICK** / **STOP PICK** | Toggle mode picking (tombol merah saat aktif) |
| **IMPORT PICK** | Import data pick dari file `.dat` |
| **VIEW DATA** | Buka dialog tabel Arrival Times |
| **CLEAR PLOT** | Hapus semua pick dari canvas |

### Grup VIEW

| Checkbox | Fungsi |
|---|---|
| **Zoom** | Toggle zoom window vs tampilan penuh |
| **Autoscale** | Otomatis skalakan amplitudo setiap trace sesuai tinggi lane |
| **Filter** | Aktifkan/nonaktifkan filter zero-phase |
| **Fill Trace** | Isi area positif trace dengan warna (wiggle fill) |

### Grup FILTER

| Elemen | Deskripsi |
|---|---|
| Label trace | Menampilkan trace terpilih (`Selected: Trace 01` / `Selected: All traces`) |
| Low (Hz) | Slider + text input, rentang 0–300 Hz, frekuensi cutoff bawah |
| High (Hz) | Slider + text input, rentang 0–300 Hz, frekuensi cutoff atas |
| Order | orde filter, default 2 |
| Tipe | Combo: Butterworth, Chebyshev I, Bessel |
| **Apply** | Terapkan pengaturan filter ke trace terpilih (atau semua trace) |

Filter diterapkan hanya ke trace yang dipilih. Jika tidak ada trace terpilih, filter diterapkan ke semua trace.

### Grup TRACE ZOOM

| Elemen | Fungsi |
|---|---|
| Label | Menampilkan `All traces` atau `1-3 of 12` |
| **All** | Tampilkan semua trace |
| **1** / **3** / **5** | Tampilkan 1, 3, atau 5 trace saja |
| **▲** / **▼** | Scroll ke trace sebelumnya/berikutnya |

## Kontrol Mouse

| Aksi | Kontrol |
|---|---|
| Pilih/batal pilih trace | Double-click kiri pada trace |
| Pan horizontal | Klik tahan kiri (500 ms) + geser, atau klik kanan + geser |
| Tracking posisi | Gerak mouse menampilkan garis indikator vertikal dan koordinat waktu |
| Scroll trace | Mouse wheel (saat trace zoom 1/3/5 aktif) |

## Shortcut Keyboard

### Picking & Editing

| Tombol | Aksi |
|---|---|
| `P` | Pick first-break pada posisi kursor |
| `Space` | Pilih/batal pilih trace di bawah kursor |
| `Escape` | Batal pilih semua trace dan hapus block selection |
| `D` | Hapus trace terpilih |
| `↑` | Pindahkan trace terpilih ke atas |
| `↓` | Pindahkan trace terpilih ke bawah |
| `I` | Tampilkan informasi trace |

### Block Selection

| Tombol | Aksi |
|---|---|
| `B` | Toggle block selection (tekan sekali untuk mulai, sekali lagi untuk akhir) |
| `0` / `Home` | Set awal block ke posisi paling kiri |
| `9` / `End` | Set akhir block ke posisi paling kanan |
| `Q` | Batalkan block selection |
| `M` | Mute (nol-kan amplitudo) dalam block |
| `C` | Cut (potong dan hapus) segmen block dari semua trace |

### Tampilan

| Tombol | Aksi |
|---|---|
| `+` / `=` | Perbesar amplitudo (×1.2) |
| `-` | Perkecil amplitudo (÷1.2) |
| `H` | Geser baseline ke atas (+1 px) |
| `J` | Geser baseline ke bawah (-1 px) |
| `[` | Kurangi frekuensi low-cut 1 Hz |
| `]` | Tambah frekuensi low-cut 1 Hz |
| `{` | Kurangi frekuensi high-cut 1 Hz |
| `}` | Tambah frekuensi high-cut 1 Hz |
