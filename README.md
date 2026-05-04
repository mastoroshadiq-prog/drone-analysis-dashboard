# AME Plantation Health Dashboard — Cincin Api

Dashboard analisis kesehatan perkebunan sawit AME II & AME IV berbasis drone NDRE dan data SR 2026.

## 🚀 Deploy ke Streamlit Cloud

1. Fork / push repo ini ke GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Pilih repo → main branch → **`app.py`**
4. Deploy

## 📁 Struktur Data

```
data/
├── arena/
│   ├── D01/output/trees_D01.csv     # AME II blok D001A
│   ├── D02/output/trees_D02.csv     # AME II blok D002A
│   ├── ...
│   ├── AMEIV_C12/output/trees_AMEIV_C12.csv   # AME IV
│   └── ...
├── cincin_api/
│   ├── D001A/
│   │   ├── D001A_absolute_cincin_api.csv
│   │   ├── D001A_relative_cincin_api.csv
│   │   ├── D001A_sr_2026_input_cincin_api.csv
│   │   └── D001A_sr_joined.csv
│   └── ...
└── context/
    └── tabel_10blok_SR_banding.xlsx  # SR ground truth AME II
```

## 🔧 Dependencies

```
streamlit >= 1.32
pandas >= 2.0
numpy >= 1.26
plotly >= 5.20
openpyxl >= 3.1
pyproj >= 3.6
```

Install lokal:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📊 Fitur Dashboard

| Tab | Konten |
|-----|--------|
| 🔁 Cincin Api | Ring deteksi Ganoderma 3 sumber (SR / Drone Relatif / Drone Absolut) |
| 🌡️ Kesehatan Blok | Distribusi 4-zona NDRE per blok + perbandingan SR 2026 |

### Data Sources
- **Drone NDRE Absolut** — kalibrasi panel MAPIR T4-R125
- **Drone NDRE Relatif** — WebODM output
- **SR 2026** — Sensus Rekomendasi (Pokok Utama + Sisip)

## ⚠️ Catatan

- Data `.tif` dan `.mbtiles` (layer peta) **tidak disertakan** di repo (terlalu besar).  
  Dashboard ini fokus pada analisis statistik dan visualisasi chart.
- AME IV: data SR per-blok belum tersedia → chart SR dinonaktifkan otomatis.

---
*Dikembangkan untuk keperluan audit kesehatan kebun AME — 2026*
