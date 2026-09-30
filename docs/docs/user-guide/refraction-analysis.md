---
title: Analisis Refraksi Hagiwara
---

# Analisis Refraksi Hagiwara

Buka melalui menu **Tools > Hagiwara Analysis**. Dialog ini mengimplementasikan metode Hagiwara (1939) untuk menentukan kecepatan lapisan dan kedalaman refraktor dari data waktu tiba.

## Mode Analisis

| Mode | Deskripsi |
|---|---|
| **Single Direction** | Shooting satu arah. satu titik sumber, satu barisan receiver |
| **Two Directions (TAP/TBP)** | Shooting dua arah (reversed). dua titik sumber di ujung-ujung barisan |

Mode dua arah lebih akurat untuk lapisan yang miring (dipping layers).

## Tab Data

### Single Direction

Tabel dengan kolom:

| Kolom | Deskripsi |
|---|---|
| Trace | Nama trace |
| Offset (m) | Jarak dari sumber ke receiver |
| Arrival Time (s) | Waktu tiba first-break |
| Elevation (°) | Sudut kemiringan terrain antar geophone |

Data bisa dimuat dari:

- **Load from Picks**. ambil dari pick yang ada di canvas
- **Load .dat File**. impor file `.dat`
- **Add Row** / **Delete Row**. input manual

#### Uniform Spacing

Nyalakan tombol **Use uniform spacing** (default: aktif, 2.00 m) untuk menggunakan jarak antar receiver yang seragam. Offset dihitung otomatis: 0, 2, 4, 6, ...

### Two Directions

Dua tabel terpisah:

- **Forward Shot (TAP)**: waktu tiba dari sumber A ke receiver
- **Backward Shot (TBP)**: waktu tiba dari sumber B ke receiver

Masing-masing bisa dimuat dari picks, file `.dat`, atau file JSON.

## Metode Deteksi Crossover

Crossover distance adalah titik di mana gelombang refraksi menjadi lebih cepat dari gelombang langsung.

| Metode | Cara Kerja |
|---|---|
| **Auto (Knee-Point)** | Regresi inkremental, detrend residual, minimum = crossover |
| **Auto (MSE)** | Uji semua split index, minimasi total sum of squared errors |
| **Manual** | Tentukan index crossover secara manual melalui spinbox |

## Tab Travel-Time Curve

Plot waktu tiba (ms) vs offset (m) dengan:

- **Garis direct wave** ($V_1$). yaitu regresi linear segmen pertama
- **Garis refracted wave** ($V_2$). yaitu regresi linear segmen kedua
- **Garis crossover**. yaitu batas antara direct dan refracted

Kecepatan dihitung dari slope: $V = \frac{1}{\text{slope}}$.

## Tab Knee-Point Analysis

### Single Direction

- **Kiri**: Kurva detrended residual. minimum menunjukkan crossover
- **Kanan**: Klasifikasi titik: hijau (direct) dan merah segitiga (refracted)

### Two Directions

- **Kiri**: Residual forward (TAP)
- **Kanan**: Residual backward (TBP)

## Tab Hagiwara Analysis (Model Bawah Permukaan)

### Perhitungan Single Direction

1. **Kecepatan**: $V_1 = \frac{1}{s_1}$, $V_2 = \frac{1}{s_2}$ dari regresi linear
2. **Sudut kritis**: $i_c = \arcsin\left(\frac{V_1}{V_2}\right)$
3. **Ketebalan di bawah sumber**: $h_1 = \frac{t_i \cdot V_1}{2 \cos(i_c)}$
4. **Profil kedalaman** (setiap geophone):

$$\text{Depth}_i = \left(t_i - \frac{x_i}{V_2}\right) \cdot \frac{V_1 V_2}{2\sqrt{V_2^2 - V_1^2}}$$

### Perhitungan Two Directions

1. **Reciprocal time**: $T_{AB} = \frac{T_{AP}[\text{last}] + T_{BP}[\text{last}]}{2}$
2. **Kecepatan langsung**: rata-rata dari regresi forward dan backward
3. **Delay time Hagiwara**: $h'_p = \frac{T_{AP} + T_{BP} - T_{AB}}{2}$
4. **Kecepatan refraksi**: harmonic mean $V_2 = \frac{2 V_a |V_b|}{V_a + |V_b|}$
5. **Kedalaman per geophone**: $h_p = \frac{V_1}{\cos(i_c)} \cdot \Delta T_p$

### Visualisasi 2D Cross-Section

Dua subplot:

- **Kiri**: Travel-time fit lines
- **Kanan**: Model geologis 2D:
    - **Topografi permukaan** dari sudut elevasi: $h_i = h_{i-1} + \Delta x \cdot \tan(\theta)$
    - **Interface refraktor** dihitung dari kedalaman di setiap posisi
    - Layer 1 (overburden) berwarna biru muda
    - Layer 2 (bedrock) berwarna cokelat muda
    - Label kecepatan $V_1$, $V_2$ ditampilkan
    - Kurva terrain dan interface dihaluskan dengan cubic spline

## Ekspor Hasil

| Tombol | Output |
|---|---|
| **Export Results** | File `.dat` atau `.json` berisi parameter analisis |
| **Export PNG** | Tiga file gambar (200 DPI): `*_travel_time.png`, `*_kneepoint.png`, `*_hagiwara.png` |
