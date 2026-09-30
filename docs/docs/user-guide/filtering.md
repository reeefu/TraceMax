---
title: Filter
---

# Filter

TraceMax menggunakan filter digital **zero-phase** via `scipy.signal.filtfilt`. sinyal difilter dua kali (maju dan mundur) sehingga tidak ada pergeseran fase.

## Jenis Filter

| Filter | Karakteristik |
|---|---|
| **Butterworth** | Respons paling datar di passband. Pilihan umum untuk analisis seismik. |
| **Chebyshev I** | Roll-off lebih tajam, tapi ada ripple 1 dB di passband. Baik untuk memisahkan frekuensi berdekatan. |
| **Bessel** | Fase paling linier dimana bentuk gelombang paling terjaga. Roll-off lebih lambat. Baik untuk analisis waktu tiba. |

## Parameter

| Parameter | Rentang | Default | Deskripsi |
|---|---|---|---|
| Low (Hz) | 0–300 | 10.0 | Frekuensi cutoff bawah |
| High (Hz) | 0–300 | 30.0 | Frekuensi cutoff atas |
| Order | 1–8 | 2 | Orde filter (semakin tinggi = cutoff semakin tajam) |
| Tipe | - | Butterworth | Jenis filter |

## Mode Filter

Mode filter ditentukan otomatis berdasarkan parameter:

| Kondisi | Mode |
|---|---|
| Low > 0 dan High < Nyquist | **Bandpass** yang meloloskan frekuensi antara Low dan High |
| Low ≤ 0 | **Lowpass** yang meloloskan frekuensi di bawah High |
| High ≥ Nyquist | **Highpass** yang meloloskan frekuensi di atas Low |

## Cara Menggunakan

1. Centang **Filter** di grup VIEW
2. Pilih trace yang ingin difilter (atau kosongkan untuk filter semua)
3. Atur parameter di grup FILTER
4. Klik **Apply**

Filter bisa juga diatur cepat via keyboard:

| Tombol | Aksi |
|---|---|
| `[` | Low-cut −1 Hz |
| `]` | Low-cut +1 Hz |
| `{` | High-cut −1 Hz |
| `}` | High-cut +1 Hz |

## Pengaturan Per Trace

Setiap trace menyimpan pengaturan filter sendiri (`low_hz, high_hz, order, ftype`). Jika satu trace dipilih, slider dan text input otomatis menampilkan nilai filter trace tersebut.

Saat disimpan ke file JSON, pengaturan filter per channel tersimpan di field `filter`:

```json
"filter": [[10.0, 30.0, 2], [5.0, 50.0, 4]]
```
