---
title: Visualisasi & Navigasi
---

# Visualisasi & Navigasi

## Tampilan Seismogram

Canvas menampilkan trace secara vertikal dimana tiap trace menempati satu lane horizontal dengan baseline di tengah. Amplitudo positif digambar ke atas, negatif ke bawah.

Saat jumlah sample melebihi lebar pixel canvas, TraceMax menggunakan algoritma **min-max decimation** dimana tiap bucket pixel diwakili oleh nilai minimum dan maksimum, sehingga puncak first-break dan detail frekuensi tinggi tetap terlihat meskipun di-zoom out.

## Mode Tampilan

### Wiggles (Default)

Setiap trace ditampilkan sebagai garis osilasi standar.

### Fill-Plot

Aktifkan dengan menyalakan tombol **Fill Trace** di grup VIEW. Area positif (ke kanan) dari trace diisi dengan warna trace.

### Zoom Amplitudo

| Kontrol | Efek |
|---|---|
| `+` atau `=` | Perbesar amplitudo ×1.2 |
| `-` | Perkecil amplitudo ÷1.2 |
| **Autoscale** (checkbox) | Skalakan otomatis setiap trace ke tinggi lane |

### Trace Zoom

Grup **TRACE ZOOM** di toolbar mengatur berapa trace yang terlihat:

| Tombol | Tampilan |
|---|---|
| **All** | Semua trace |
| **1** | 1 trace |
| **3** | 3 trace |
| **5** | 5 trace |

Saat trace zoom aktif, gunakan tombol **▲▼** atau **mouse wheel** untuk scroll antar trace. Label menunjukkan posisi: `1-3 of 12`.

### Zoom Window

Nyalakan tombol **Zoom** di grup VIEW untuk menampilkan sebagian data (sesuai parameter `zoom` dalam sample). Matikan untuk menampilkan seluruh trace.

## Seleksi Trace

| Kontrol | Aksi |
|---|---|
| Double-click | Pilih/batal pilih satu trace |
| `Space` | Pilih/batal pilih trace di bawah kursor |
| `Escape` | Batal pilih semua |

Trace terpilih ditandai dengan highlight. Filter dan beberapa operasi editing hanya berlaku pada trace terpilih.

## Indikator Kursor

Saat mouse bergerak di atas canvas, garis vertikal mengikuti posisi kursor dan menampilkan koordinat waktu secara real-time.
