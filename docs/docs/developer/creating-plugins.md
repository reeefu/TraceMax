---
title: Membuat Plugin
---

# Membuat Plugin

## Struktur Minimum

```
src/plugin/
└── nama_plugin/
    └── __init__.py    # wajib
```

## Kontrak Plugin

File `__init__.py` harus menyediakan:

### 1. Metadata (opsional)

```python
PLUGIN_NAME = 'Nama Plugin'   # fallback: nama folder
PLUGIN_MENU = 'Menu Name'     # nama menu di menu bar
```

### 2. Fungsi `register(mainwindow)` (wajib)

```python
def register(mainwindow):
    from PyQt5.QtWidgets import QAction
    
    action = QAction('&Nama Fitur', mainwindow)
    action.triggered.connect(lambda: my_function(mainwindow))
    
    return {
        'menu_name': PLUGIN_MENU,
        'actions': [action]
    }
```

`register()` dipanggil saat startup dengan instance `SeismoWin` sebagai parameter. Return dict berisi:

| Key | Tipe | Deskripsi |
|---|---|---|
| `menu_name` | `str` | Nama menu yang akan dibuat di menu bar |
| `actions` | `list[QAction]` | Daftar action yang ditambahkan ke menu |

## Contoh Plugin Sederhana

Plugin yang menampilkan statistik trace terpilih:

```python
# src/plugin/trace_stats/__init__.py

import numpy as np
from PyQt5.QtWidgets import QAction, QMessageBox

PLUGIN_NAME = 'Trace Statistics'
PLUGIN_MENU = 'Analysis'

def register(mainwindow):
    action = QAction('&Trace Statistics', mainwindow)
    action.triggered.connect(lambda: show_stats(mainwindow))
    return {'menu_name': PLUGIN_MENU, 'actions': [action]}

def show_stats(mainwindow):
    canvas = mainwindow.parea
    selected = [t for t in canvas.traces if t.selected]
    
    if not selected:
        QMessageBox.warning(mainwindow, 'Warning', 'Pilih trace terlebih dahulu.')
        return
    
    info = []
    for t in selected:
        d = np.array(t.data)
        info.append(
            f"{t.name}:\n"
            f"  Samples: {len(d)}\n"
            f"  Min: {d.min():.4f}\n"
            f"  Max: {d.max():.4f}\n"
            f"  Mean: {d.mean():.4f}\n"
            f"  Std: {d.std():.4f}"
        )
    
    QMessageBox.information(mainwindow, 'Trace Statistics', '\n\n'.join(info))
```

## Mengakses Data

Dari `mainwindow`, Anda bisa mengakses:

| Properti | Tipe | Deskripsi |
|---|---|---|
| `mainwindow.parea` | `plotter` | Canvas utama |
| `mainwindow.parea.traces` | `list[trace]` | Semua trace yang dimuat |
| `mainwindow.parea.timeaxis` | `list[float]` | Array waktu |
| `mainwindow.panel` | `ControlPanel` | Toolbar |

Setiap `trace` memiliki atribut:

| Atribut | Tipe | Deskripsi |
|---|---|---|
| `name` | `str` | Nama trace |
| `data` | `list` | Data amplitudo mentah |
| `vdata` | `list` | Data tampilan (setelah filter) |
| `selected` | `bool` | Status seleksi |
| `pickpoint` | `int` | Sample index pick (-1 jika belum di-pick) |
| `picktime` | `float` | Waktu tiba dalam detik |
| `freq` | `tuple` | `(low_hz, high_hz, order[, ftype])` |

## Testing

1. Letakkan folder plugin di `src/plugin/`
2. Jalankan TraceMax
3. Cek apakah menu plugin muncul di menu bar
4. Jika ada error, jalankan dari terminal untuk melihat traceback

## Referensi

Lihat `src/plugin/ml_picker/` sebagai contoh plugin lengkap dengan dialog Matplotlib, background thread, dan model deep learning.
