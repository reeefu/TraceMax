---
title: Instalasi
---

# Instalasi

## Persyaratan

| Komponen | Versi |
|---|---|
| Python | 3.9+ |
| PyQt5 | ≥ 5.15 |
| NumPy | ≥ 1.24 |
| SciPy | ≥ 1.10 |
| Matplotlib | ≥ 3.7 |
| OS | Windows 10/11, Linux (Ubuntu 20.04+) |

## Instalasi dari Source

### 1. Clone repository

```bash
git clone https://github.com/reeefu/TraceMax.git
cd TraceMax
```

### 2. Buat virtual environment

```bash
python -m venv .venv
```

Aktifkan:

=== "Windows"

    ```batch
    .venv\Scripts\activate
    ```

=== "Linux"

    ```bash
    source .venv/bin/activate
    ```

### 3. Install dependensi

```bash
pip install -r requirements.txt
```

### 4. Jalankan

```bash
python src/tracemax.py
```

Atau langsung buka file:

```bash
python src/tracemax.py data/contoh.json
```

## Plugin ML Auto-Picker (Opsional)

Plugin ML membutuhkan PyTorch:

```bash
pip install torch
```

Letakkan file weight model di `src/plugin/ml_picker/models/`:

| File | Model |
|---|---|
| `best_model_bilstm.pt` | Bidirectional LSTM |
| `best_model_unidirectional.pt` | Unidirectional LSTM |
    
## Konfigurasi Awal

Konfigurasi default disimpan di `config.py`:

| Parameter | Default | Deskripsi |
|---|---|---|
| `filter` | `False` | Filter aktif saat startup |
| `low_freq` | `10.0` Hz | Frekuensi low-cut awal |
| `high_freq` | `30.0` Hz | Frekuensi high-cut awal |
| `order` | `2` | Orde filter awal |
| `zoom` | `200` samples | Lebar zoom default |
| `winmode` | `max` | Mode window (maximized) |
| `lang` | `en` | Bahasa UI (`en` / `id`) |

Konfigurasi bisa dimuat/disimpan melalui menu **File > Open Configuration** dan **Tools > Save Configuration**.
