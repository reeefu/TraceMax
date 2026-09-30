---
title: Format Data
---

# Format Data

## Format Input (JSON)

TraceMax membaca file JSON dengan struktur minimal:

```json
{
  "time": [0.0, 0.00162, 0.00324, ...],
  "channel-00": [12.0, 15.4, -3.2, ...],
  "channel-01": [8.1, 10.2, -1.5, ...]
}
```

| Field | Tipe | Deskripsi |
|---|---|---|
| `time` | `float[]` | Array waktu dalam detik |
| `channel-XX` | `float[]` | Amplitudo setiap channel, `XX` dimulai dari `00` |

## Format Save (JSON)

Saat menyimpan, TraceMax menyertakan data tambahan:

```json
{
  "time": [...],
  "channel-00": [...],
  "channel-01": [...],
  "scale": [1.0, 1.0],
  "offset": [0, 0],
  "filter": [[10.0, 30.0, 2], [10.0, 30.0, 2]],
  "pick": [[0, 0.0125], [1, 0.0158]],
  "config": { "filter": true, "low_freq": 10.0, ... }
}
```

| Parameter | Deskripsi |
|---|---|
| `scale` | Faktor skala amplitudo per channel |
| `offset` | Offset vertikal per channel (piksel) |
| `filter` | Pengaturan filter per channel: `[low_hz, high_hz, order]` |
| `pick` | Data pick: `[trace_index, arrival_time_seconds]` |
| `config` | Snapshot konfigurasi GUI |

## Format Export Arrival Time (.dat)

```
# TraceMax Arrival Time Data
# trace_index  trace_name  offset_m  arrival_time_s
1  Trace 00  0.0000  0.012345
2  Trace 01  2.0000  0.015678
```

## Menggabungkan File (Combine)

Jika beberapa file dipilih saat **File > Open**, TraceMax menggabungkannya:

1. Panjang data dipotong ke panjang minimum dari semua file
2. Time step dirata-ratakan
3. Hasil disimpan ke file temporary dan langsung dimuat