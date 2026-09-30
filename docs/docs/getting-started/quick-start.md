---
title: Panduan Cepat
---

# Panduan Cepat

Panduan ini mencakup alur kerja dasar TraceMax, yaitu: buka data, visualisasi, filter, picking, dan ekspor.

## 1. Buka File Data

Gunakan menu **File > Open** atau jalankan dari terminal:

```bash
python src/tracemax.py data.json
```

TraceMax membaca file JSON dengan array `time` dan `channel-XX`. Beberapa file bisa dibuka sekaligus dimana TraceMax akan menggabungkannya secara otomatis (fitur Combine).

Setelah file dimuat, status bar di bawah menampilkan nama file, jumlah sample, dan durasi rekaman.

## 2. Navigasi Seismogram

| Aksi | Kontrol |
|---|---|
| Pan horizontal | Klik tahan + geser, atau klik kanan + geser |
| Zoom amplitudo | Tekan `+` / `-` |
| Scroll antar trace | Mouse wheel (saat trace zoom aktif) |
| Pilih trace | Double-click atau tekan `Space` |
| Pilih semua / batal | Tekan `Escape` |

Gunakan grup **TRACE ZOOM** di toolbar untuk membatasi tampilan ke 1, 3, atau 5 trace. Tombol ▲▼ untuk scroll.

## 3. Terapkan Filter

1. Nyalakan tombol **Filter** di grup VIEW pada toolbar
2. Atur frekuensi di grup FILTER:
    - **Low (Hz)**: frekuensi cutoff bawah (highpass)
    - **High (Hz)**: frekuensi cutoff atas (lowpass)
    - **Order**: orde filter (1–8)
    - **Tipe**: Butterworth / Chebyshev I / Bessel
3. Klik **Apply**

Filter diterapkan secara zero-phase menggunakan `filtfilt`, sehingga tidak ada pergeseran fase.

## 4. Picking First-Break

### Manual Picking

1. Klik **START PICK** di grup PICK (tombol menjadi merah)
2. Arahkan kursor ke posisi first-break pada trace
3. Tekan `P` atau klik pada posisi yang diinginkan
4. Garis indikator pick muncul pada trace
5. Log pick muncul di text box: `trace(01) 0.012345`

### Auto-Picking (STA/LTA)

1. Buka menu **Tools > STA/LTA Picker**
2. Atur parameter: STA window, LTA window, threshold
3. Klik **Preview** untuk melihat hasil pada satu trace
4. Klik **Apply Picks** untuk menerapkan ke semua trace

## 5. Lihat dan Ekspor Hasil

1. Klik **VIEW DATA** di grup PICK, atau menu **Tools > Arrival Times**
2. Dialog tabel menampilkan trace, offset, dan arrival time
3. Edit offset (jarak source-receiver) dengan klik pada sel Offset
4. Klik **Export .dat** untuk menyimpan ke file

Format ekspor `.dat`:

```
# TraceMax Arrival Time Data
# trace_index  trace_name  offset_m  arrival_time_s
1  Trace 00  0.0000  0.012345
2  Trace 01  2.0000  0.015678
```

## Langkah Selanjutnya

- [Filter](../user-guide/filtering.md) > Detail penggunaan filter
- [Picking](../user-guide/picking.md) > Manual, STA/LTA, dan ML picker
- [Analisis Refraksi](../user-guide/refraction-analysis.md) > Metode Hagiwara
