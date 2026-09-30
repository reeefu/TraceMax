---
title: Build Executable
---

# Build Executable

TraceMax bisa dipaketkan menjadi executable standalone dengan PyInstaller.

## Persyaratan

```bash
pip install pyinstaller
```

## Build

=== "Windows"

    ```batch
    build_windows.bat
    ```

    Bersihkan build sebelumnya:

    ```batch
    build_windows.bat clean
    ```

    Output: `dist\TraceMax\TraceMax.exe`

=== "Linux"

    ```bash
    chmod +x build_linux.sh
    ./build_linux.sh
    ```

    Bersihkan build sebelumnya:

    ```bash
    ./build_linux.sh clean
    ```

    Output: `dist/TraceMax/TraceMax`

## File Spec

Build menggunakan `tracemax.spec` yang sudah dikonfigurasi. Spec ini mencakup:

- Entry point `src/tracemax.py`
- Asset files (CSS, strings, logo, icon)
- Plugin files
- Hidden imports

Saat dijalankan sebagai frozen app, TraceMax mendeteksi `sys._MEIPASS` untuk mencari lokasi assets.

## Distribusi

1. Zip seluruh folder `dist/TraceMax/`
2. Kirim ke pengguna
3. Pengguna extract dan jalankan executable