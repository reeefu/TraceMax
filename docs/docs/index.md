---
title: TraceMax
hide:
  - navigation
  - toc
---

<h1 style="display: none;">TraceMax</h1>

<div class="hero" markdown>

![TraceMax Banner](Banner.png){ .hero-banner }

Aplikasi desktop untuk **visualisasi**, **editing**, **filtering**, **first-break picking**, dan **analisis refraksi** data seismik.

[Panduan Cepat](getting-started/quick-start.md){ .md-button .md-button--primary }
[Instalasi](getting-started/installation.md){ .md-button }

</div>

---

## Memulai

<div class="grid cards" markdown>

-   ### [Instalasi](getting-started/installation.md)

    Persyaratan sistem, setup Python virtual environment, dan install dependensi.

-   ### [Panduan Cepat](getting-started/quick-start.md)

    Alur kerja dasar program.

</div>

---

## Panduan Pengguna

<div class="grid cards" markdown>

-   ### [Antarmuka](user-guide/interface.md)

    Layout window, menu bar, toolbar (PICK/VIEW/FILTER/ZOOM), dan shortcut keyboard.

-   ### [Format Data](user-guide/data-format.md)

    Struktur JSON input/output, format ekspor `.dat`, dan cara membuat data sendiri.

-   ### [Visualisasi & Navigasi](user-guide/visualization.md)

    Tampilan seismogram, wiggles vs fill-plot, zoom, scroll, dan min-max decimation.

-   ### [Filter](user-guide/filtering.md)

    Butterworth, Chebyshev I, dan Bessel bandpass filter zero-phase. Parameter dan mode filter.

-   ### [First-Break Picking](user-guide/picking.md)

    Manual picking, STA/LTA auto-picker, dan ML auto-picker (BiLSTM / Uni-LSTM).

-   ### [Manajemen Waktu Tiba](user-guide/arrival-times.md)

    Tabel arrival time, editing offset, hapus pick, dan ekspor ke file `.dat`.

-   ### [Analisis Refraksi Hagiwara](user-guide/refraction-analysis.md)

    Satu arah dan dua arah (TAP/TBP), crossover detection, dan model bawah permukaan 2D.

-   ### [Spektrum FFT](user-guide/fft-spectrum.md)

    Analisis domain frekuensi, deteksi puncak otomatis, identifikasi noise.

</div>

---

## Lanjutan

<div class="grid cards" markdown>

-   ### [Sistem Plugin](advanced/plugins.md)

    Arsitektur plugin drop-in, ML Auto-Picker, preprocessing pipeline, dan inferensi.

-   ### [Build Executable](advanced/build.md)

    Paketkan TraceMax menjadi standalone executable dengan PyInstaller.

</div>

---

## Pengembang

<div class="grid cards" markdown>

-   ### [Struktur Proyek](developer/project-structure.md)

    Arsitektur modular, diagram dependensi, penjelasan setiap modul, dan alur data.

-   ### [Membuat Plugin](developer/creating-plugins.md)

    Kontrak plugin, contoh kode lengkap, akses data trace, dan distribusi.

</div>

---

## Bantuan

<div class="grid cards" markdown>

-   ### [FAQ & Troubleshooting](faq.md)

    Pertanyaan umum, solusi error, dan cara melaporkan bug.

-   ### [Changelog](changelog.md)

    Riwayat perubahan dan rilis.

</div>
