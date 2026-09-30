---
title: Spektrum FFT
---

# Spektrum FFT

Buka melalui menu **Tools > FFT Spectrum**. Dialog menampilkan spektrum frekuensi dari trace terpilih (atau semua trace jika tidak ada yang dipilih).

## Perhitungan

1. **Sampling interval**: $dt = \frac{t_{\text{end}} - t_0}{n - 1}$
2. **Frekuensi Nyquist**: $f_{\text{nyq}} = \frac{1}{2 \cdot dt}$
3. **Preprocessing**: demean dan windowing Hanning: $d_{\text{win}} = (d - \mu) \cdot \text{Hanning}(N)$
4. **FFT**: $S = |\text{rfft}(d_{\text{win}})| \cdot \frac{2}{N}$

## Tampilan

- **Sumbu X**: Frekuensi (Hz)
- **Sumbu Y**: Amplitudo (linear atau log)
- **Garis putus-putus**: 3 puncak frekuensi dominan teratas (> 0.001 Hz), dilabel dengan `X.XX Hz`
- **Garis Nyquist**: batas frekuensi maksimum yang bisa direpresentasikan

## Kontrol

| Tombol | Fungsi |
|---|---|
| **Log Scale** / **Linear Scale** | Toggle skala Y antara linear dan logaritmik |
| **Close** | Tutup dialog |

## Penggunaan

### Menentukan Parameter Filter

1. Buka FFT Spectrum untuk trace yang ingin dianalisis
2. Identifikasi rentang frekuensi sinyal (biasanya puncak dominan)
3. Identifikasi frekuensi noise (puncak sempit, misalnya 50 Hz)
4. Atur filter bandpass berdasarkan informasi ini

### Noise Umum

| Frekuensi | Kemungkinan Sumber |
|---|---|
| < 5 Hz | Ground roll, drift instrumen |
| 50 Hz / 60 Hz | Interferensi listrik (PLN) |
| > 200 Hz | Noise elektronik, aliasing |
