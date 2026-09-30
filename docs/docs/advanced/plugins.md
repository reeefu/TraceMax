---
title: Sistem Plugin
---

# Sistem Plugin

## Arsitektur

Saat startup, TraceMax memindai folder `src/plugin/` menggunakan `pkgutil.iter_modules`. Setiap subfolder yang memiliki `__init__.py` dengan fungsi `register(mainwindow)` dikenali sebagai plugin.

Alur discovery:

1. Scan semua subfolder di `src/plugin/`
2. Import modul dan cek keberadaan `register()`
3. Ambil `PLUGIN_NAME` (fallback ke nama folder)
4. Panggil `register(mainwindow)` yang mengembalikan:

```python
{
    'menu_name': 'ML',           # nama menu di menu bar
    'actions': [action1, ...]    # list QAction untuk menu
}
```

5. Buat menu dan sub-menu secara dinamis di menu bar

## Plugin Bawaan: ML Auto-Picker

| Properti | Nilai |
|---|---|
| Nama | ML Auto-Picker |
| Menu | ML > BiLSTM Auto-Picker |
| Dependensi | PyTorch |

### Model

| Model | File | Arsitektur |
|---|---|---|
| BiLSTM | `best_model_bilstm.pt` | Bidirectional LSTM — memproses sinyal dua arah |
| Uni-LSTM | `best_model_unidirectional.pt` | Unidirectional LSTM — lebih cepat |

Dialog ML Picker memiliki 3 tab: BiLSTM Picker, Uni-LSTM Picker, dan Transformer (placeholder).

### Preprocessing Pipeline

Konstanta default: `WINDOW_LENGTH = 200`, `SAMPLE_RATE = 616.0` Hz.

1. Truncate/pad ke window length
2. Baseline shift: $x = x - x[0]$
3. Bandpass filter 5–120 Hz (Butterworth orde 4, zero-phase SOS)
4. Z-score normalization: $x = \frac{x - \mu}{\sigma}$
5. Min-max scaling ke $[-1, 1]$: $x_{\text{norm}} = 2 \cdot \frac{x - x_{\min}}{x_{\max} - x_{\min}} - 1$

### Inferensi

Inferensi berjalan di background thread (`QThread`) dengan progress signal. Mendukung CPU dan CUDA. Output: prediksi sample index dan attention weights.

### Setup

```bash
pip install torch
```

Letakkan file `.pt` di `src/plugin/ml_picker/models/`. Restart TraceMax.

Untuk panduan membuat plugin sendiri, lihat [Membuat Plugin](../developer/creating-plugins.md).
