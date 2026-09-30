---
title: First-Break Picking
---

# First-Break Picking

## Manual Picking

### Cara Kerja

1. Klik **START PICK** di grup PICK pada toolbar (tombol berubah merah)
2. Arahkan kursor ke posisi first-break
3. Tekan `P`. pick ditandai pada trace terdekat
4. Log pick muncul di text box, misal: `trace(01) 0.012345`
5. Klik **STOP PICK** untuk keluar mode picking

Posisi pick dihitung berdasarkan posisi kursor relatif terhadap lebar canvas:

$$t_p = t_{\text{start}} + (t_{\text{end}} - t_{\text{start}}) \times \frac{x_{\text{cursor}}}{\text{width}}$$

### Menghapus Pick

- **Semua pick**: Klik **CLEAR PLOT**
- **Satu pick**: Buka dialog Arrival Times, pilih baris, klik **Delete Row**

### Import Pick dari File

Klik **IMPORT PICK** untuk memuat pick dari file `.dat`. Format file:

```
trace_index  trace_name  offset  arrival_time
```

TraceMax mencocokkan trace berdasarkan nama. Jika nama tidak ditemukan, fallback ke index.

## STA/LTA Auto-Picker

Buka melalui menu **Tools > STA/LTA Picker**.

### Parameter

| Parameter | Rentang | Default | Deskripsi |
|---|---|---|---|
| STA Window | 0.1–500 ms | 5.0 ms | Panjang window short-term |
| LTA Window | 1.0–5000 ms | 50.0 ms | Panjang window long-term |
| Threshold | 1.00–100.00 | 3.00 | Rasio minimum untuk trigger |
| Target | - | All traces | Terapkan ke semua atau trace terpilih |

### Algoritma

1. **Demean**: hapus rata-rata dari sinyal
2. **Energi**: hitung $P_i = d_i^2$
3. **Padding**: tambahkan `nlta` sample di kiri menggunakan median noise
4. **Cumulative sum**: hitung rata-rata STA dan LTA secara efisien (O(1) per sample)
5. **Rasio**: $R_i = \frac{\text{STA}_i}{\text{LTA}_i + \epsilon}$, dengan $\epsilon = \max(P) \times 10^{-4} + 10^{-12}$
6. **Trigger**: first-break = index pertama di mana $R_i \geq \text{threshold}$

### Preview

1. Pilih trace dari dropdown **Preview trace**
2. Klik **Preview**
3. Plot atas: waveform dengan garis pick (merah putus-putus)
4. Plot bawah: kurva rasio STA/LTA dengan garis threshold (merah horizontal)

### Menerapkan Pick

- **Apply Picks**. menerapkan ke target dan tutup
- **Apply & Open Arrivals**. menerapkan dan langsung buka dialog Arrival Times

### Preprocessing

Sebelum inferensi, setiap trace melewati pipeline:

1. Truncate/pad ke `window_length`
2. Baseline shift: $x = x - x[0]$
3. Bandpass filter 5–120 Hz (Butterworth orde 4)
4. Z-score normalization
5. Min-max scaling ke $[-1, 1]$

### Preview

Plot dua panel:

- **Atas**: Waveform ternormalisasi dengan marker pick prediksi
- **Bawah**: Attention weights (area amber) menunjukkan fokus model

## Perbandingan

| Metode | Kecepatan | Kapan Digunakan |
|---|---|---|
| Manual | Lambat | Data sedikit, QC, kalibrasi |
| STA/LTA | Cepat | SNR baik, data banyak |
| ML Picker | Cepat | SNR bervariasi, data banyak |
