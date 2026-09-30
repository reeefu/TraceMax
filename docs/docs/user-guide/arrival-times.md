---
title: Arrival Times
---

# Arrival Times

Buka dialog melalui tombol **VIEW DATA** di toolbar, atau menu **Tools > Arrival Times**. Dialog ini bersifat modeless dan bisa tetap terbuka sambil bekerja di canvas.

## Tabel

| Kolom | Editable | Deskripsi |
|---|---|---|
| **#** | Tidak | Nomor trace (1-based) |
| **Trace** | Tidak | Nama trace |
| **Offset (m)** | Ya | Jarak source-receiver dalam meter (default: 0.0) |
| **Arrival Time (s)** | Tidak | Waktu tiba dalam detik (6 desimal) |

Hanya trace yang sudah di-pick yang muncul di tabel.

## Operasi

### Refresh

Klik **Refresh** untuk memuat ulang semua pick dari canvas.

### Edit Offset

Klik langsung pada sel **Offset (m)** untuk mengedit. Offset dibutuhkan untuk:

- Analisis refraksi Hagiwara
- Kurva travel-time (waktu vs jarak)
- Ekspor data

### Hapus Pick

Pilih baris, klik **Delete Row**. Pick dihapus dari canvas dan tabel.

### Ekspor .dat

Klik **Export .dat** untuk menyimpan data ke file teks:

```
# TraceMax Arrival Time Data
# trace_index  trace_name  offset_m  arrival_time_s
1  Trace 00  0.0000  0.012345
2  Trace 01  2.0000  0.015678
```

File `.dat` bisa diimpor kembali melalui **IMPORT PICK** di toolbar, atau dimuat di dialog Hagiwara.
