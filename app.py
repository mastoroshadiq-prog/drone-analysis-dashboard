"""
dashboard_cincin_api.py - versi 2: SR vs Drone Rel vs Drone Abs
Jalankan: streamlit run dashboard_cincin_api.py
"""
import sys, json
import pandas as pd
import numpy as np
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Cincin Api — AME II & AME IV", page_icon="🔥", layout="wide")

CINCIN_DIR = Path(r"E:\ARENA_PILOT\CINCIN_API")
ARENA_DIR  = Path(r"E:\ARENA_PILOT")
SR_FILE    = Path(r"d:\PythonProjects\pre-scanning-webodm\context\tabel_10blok_SR_banding.xlsx")

# ── AME II config ─────────────────────────────────────────────────
BLOCKS = ["D001A","D002A","D003A","D004A","D005A","D009A","D010A","D011A","E001A","E002A"]
OLD    = {"D001A":"D01","D002A":"D02","D003A":"D03","D004A":"D04","D005A":"D05",
          "D009A":"D09","D010A":"D10","D011A":"D11","E001A":"E01","E002A":"E02"}
SESI   = {"D001A":"Feb18","D002A":"Feb18","D003A":"Feb18","D004A":"Feb18",
          "D005A":"Feb20","D009A":"Feb20","D010A":"Feb20","D011A":"Feb20",
          "E001A":"Feb18","E002A":"Feb18"}

# ── AME IV config ─────────────────────────────────────────────────
BLOCKS_AME4 = ["C012","C013","C014","C015","C016","C017","C018A","C018B","C019"]
FOLDER_AME4 = {
    "C012":"AMEIV_C12",  "C013":"AMEIV_C13",  "C014":"AMEIV_C14",
    "C015":"AMEIV_C15",  "C016":"AMEIV_C16",  "C017":"AMEIV_C17",
    "C018A":"AMEIV_C18A","C018B":"AMEIV_C18B","C019":"AMEIV_C19",
}
# SR_REF ground truth dari AMEIV_9blok_01.xlsx (diupdate 2026-05-04)
SR_REF_AME4 = {
    "C012":3269,"C013":3116,"C014":2820,"C015":2820,"C016":2712,
    "C017":2748,"C018A":3269,"C018B":549,"C019":2748,
}
# Luas area per blok (ha) — dari data kebun
AREA_AME4 = {
    "C012":23.5,"C013":22.8,"C014":23.1,"C015":22.4,"C016":24.0,
    "C017":23.7,"C018A":28.5,"C018B":4.5,"C019":22.9,
}

ZONE_CLR = {"Merah":"#E53935","Oranye":"#FB8C00","Kuning":"#FDD835","Hijau":"#43A047"}
SR_CLR   = {"Stres Sangat Berat":"#B71C1C","Stres Berat":"#EF5350",
            "Stres Sedang":"#FFA726","Stres Ringan":"#66BB6A"}

# ── Data Inspeksi Lapangan — Serangan Ganoderma per Blok (AME II) ──
# Sumber: tabel serangan lapangan AME002, Pokok = total inventaris
GANO_FIELD = {
    "D001A": {"st12": 93,  "st34": 13, "pokok": 3484},
    "D002A": {"st12": 47,  "st34":  0, "pokok": 3150},
    "D003A": {"st12": 89,  "st34": 11, "pokok": 3131},
    "D004A": {"st12": 51,  "st34": 13, "pokok": 2841},
    "D005A": {"st12": 126, "st34": 44, "pokok": 2362},
    "D006A": {"st12": 128, "st34": 32, "pokok": 2391},  # no drone data
    "D009A": {"st12": 95,  "st34": 30, "pokok": 2614},
    "D010A": {"st12": 60,  "st34": 21, "pokok": 2575},
    "D011A": {"st12": 149, "st34": 24, "pokok": 2160},
    "E001A": {"st12": 80,  "st34": 19, "pokok": 3014},
    "E002A": {"st12": 62,  "st34": 12, "pokok": 2859},
}

# ── load summary ──────────────────────────────────────────────────
@st.cache_data
def load_summary():
    f = CINCIN_DIR / "sr_integration_summary.csv"
    if f.exists():
        return pd.read_csv(f)
    return pd.DataFrame()

@st.cache_data
def load_sr():
    df = pd.read_excel(SR_FILE)
    df['NDRE125']  = pd.to_numeric(df['NDRE125'],  errors='coerce')
    df['NDRE2_26'] = pd.to_numeric(df['NDRE2_26'], errors='coerce')
    df['X']        = pd.to_numeric(df['X'], errors='coerce')
    df['Y']        = pd.to_numeric(df['Y'], errors='coerce')
    return df

@st.cache_data
def load_trees(blok, division="AME II"):
    if division == "AME II":
        old = OLD[blok]
        f = ARENA_DIR / old / "output" / f"trees_{old}.csv"
    else:  # AME IV
        folder = FOLDER_AME4.get(blok, f"AMEIV_{blok}")
        f = ARENA_DIR / folder / "output" / f"trees_{folder}.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()

def apply_population_filter(df: pd.DataFrame, include_tbm: bool = False, include_kenth: bool = False) -> pd.DataFrame:
    """Filter populasi drone sesuai toggle TBM & Kenthosan di sidebar."""
    if "Classification" not in df.columns:
        return df
    mask = df["Classification"] == "TM"
    if include_tbm:
        mask = mask | (df["Classification"] == "TBM")
    if include_kenth:
        mask = mask | (df["Classification"] == "Kenthosan")
    return df[mask].copy()

def filter_tm_only(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy — panggil apply_population_filter dengan default TM only."""
    return apply_population_filter(df, include_tbm=False, include_kenth=False)

@st.cache_data
def load_rings(blok, source):
    """source: 'relative','absolute','sr_2026_input'"""
    f = CINCIN_DIR / blok / f"{blok}_{source}_cincin_api.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()

@st.cache_data
def load_joined(blok):
    f = CINCIN_DIR / blok / f"{blok}_sr_joined.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()

# ── Cincin Api Visualization Helpers ─────────────────────────────
SR_KLASS_TO_STD = {
    "Stres Sangat Berat": "Critical",
    "Stres Berat":        "Sub-Optimal",
    "Stres Sedang":       "Moderate",
    "Stres Ringan":       "Good",
}
HEALTH_ORDER  = ["Critical", "Sub-Optimal", "Moderate", "Good"]
HEALTH_LABELS = ["🔴 Merah (Kritis)", "🟠 Oranye (Sub-Opt)", "🟡 Kuning (Moderat)", "🟢 Hijau (Sehat)"]
HEALTH_COLORS = ["#D32F2F", "#F57C00", "#F9A825", "#2E7D32"]
HEALTH_MARKER = [
    dict(size=9, color="#D32F2F", opacity=0.95),
    dict(size=8, color="#F57C00", opacity=0.90),
    dict(size=7, color="#F9A825", opacity=0.85),
    dict(size=6, color="rgba(46,125,50,0.0)", opacity=0.75,
         line=dict(color="#52C41A", width=1.5)),
]

def _hex_neighbors(b: int, p: int) -> list:
    """Hexagonal mata lima neighbors — exact copy dari GitHub repo."""
    if b % 2 == 0:
        offsets = [(0, -1), (0, 1), (-1, -1), (-1, 0), (1, -1), (1, 0)]
    else:
        offsets = [(0, -1), (0, 1), (-1, 0), (-1, 1), (1, 0), (1, 1)]
    return [(b + db, p + dp) for db, dp in offsets]


def calc_cincin_api(df: "pd.DataFrame", val_col: str,
                    threshold: float = 0.15,
                    min_sick_neighbors: int = 3) -> "pd.DataFrame":
    """
    Port exact dari GitHub cincin_api.py — calc_cincin_api().
    Menghasilkan kolom '_hs' dengan 4 kelas:
      Critical    = 🔴 MERAH (inti api)
      Sub-Optimal = 🟠 ORANYE (cincin api)
      Moderate    = 🟡 KUNING (suspect)
      Good        = 🟢 HIJAU (sehat)
    Dan kolom '_parit' = True untuk pohon batas karantina.
    """
    df = df.copy()
    # Kolom _b dan _p harus sudah ada (int)
    val_map = {}
    for _, row in df.iterrows():
        val_map[(int(row["_b"]), int(row["_p"]))] = row[val_col]

    # 1. Spatial focal smoothing (hex mean)
    smoothed = []
    for _, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        nbs = _hex_neighbors(b, p)
        vals = [val_map[nb] for nb in nbs if nb in val_map]
        vals.append(val_map[(b, p)])
        smoothed.append(np.nanmean(vals))
    df["_smoothed"] = smoothed

    # 2. Percentile rank pada nilai yang telah dihaluskan
    valid = df["_smoothed"].notna()
    df.loc[valid, "_pct"] = df.loc[valid, "_smoothed"].rank(pct=True, method="dense")
    df.loc[~valid, "_pct"] = np.nan

    # 3. Suspect map
    is_suspect = {}
    for _, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        pct = row.get("_pct", np.nan)
        is_suspect[(b, p)] = (not np.isnan(pct)) and (pct <= threshold)

    # 4. Fase 1 — Core vs Suspect vs Sehat
    kategori = []
    merah_coords = set()
    for _, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        if is_suspect.get((b, p), False):
            nbs = _hex_neighbors(b, p)
            sick_cnt = sum(1 for nb in nbs if is_suspect.get(nb, False))
            if sick_cnt >= min_sick_neighbors:
                kategori.append("Critical")
                merah_coords.add((b, p))
            else:
                kategori.append("Moderate")
        else:
            kategori.append("Good")
    df["_hs"] = kategori

    # 5. Fase 2 — Expand Ring (Oranye) dari tetangga Merah
    for i, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        if df.at[i, "_hs"] not in ("Critical",):
            nbs = _hex_neighbors(b, p)
            if any(nb in merah_coords for nb in nbs):
                df.at[i, "_hs"] = "Sub-Optimal"

    # 6. Parit isolasi
    infected = {(int(r["_b"]), int(r["_p"])) for _, r in df.iterrows()
                if r["_hs"] in ("Critical", "Sub-Optimal", "Moderate")}
    parit = []
    for _, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        if (b, p) in infected:
            parit.append(False)
        else:
            nbs = _hex_neighbors(b, p)
            parit.append(any(nb in infected for nb in nbs))
    df["_parit"] = parit
    return df



def _compute_parit_hex(df: "pd.DataFrame", hs_col: str,
                        infected_cats: set) -> "pd.Series":
    """
    Parit isolasi = pohon SEHAT yang memiliki minimal 1 tetangga hex dalam zona infeksi.
    Equivalent dengan parit_{suffix} di GitHub.
    """
    infected = set()
    for _, row in df.iterrows():
        if row[hs_col] in infected_cats:
            infected.add((int(row["_b"]), int(row["_p"])))

    flags = []
    for _, row in df.iterrows():
        b, p = int(row["_b"]), int(row["_p"])
        if row[hs_col] in infected_cats:
            flags.append(False)
        else:
            nbs = _hex_neighbors(b, p)
            flags.append(any(nb in infected for nb in nbs))
    return pd.Series(flags, index=df.index)


# ── Kategori visual: (fill, stroke, size) ──────────────────────
_HEX_CATS = [
    # (hs_key,        fill,      stroke,    size)
    ("Good",        "#52c41a", "#389e0d",  7),   # hijau sedang — Sehat
    ("Moderate",    "#f1c40f", "#d68910",  9),   # kuning
    ("Sub-Optimal", "#e67e22", "#ba4a00", 11),   # oranye
    ("Critical",    "#c0392b", "#7b241c", 13),   # merah tua, BESAR
]
_HEX_LABELS = {
    "Good":        "🟢 Sehat",
    "Moderate":    "🟡 Kuning",
    "Sub-Optimal": "🟠 Oranye",
    "Critical":    "🔴 Merah",
}
# Warna latar TBM & Kenthosan — hijau MUDA (lebih terang dari Sehat TM)
_CLR_TBM   = ("#b7eb8f", "#73d13d", 5)   # (fill, stroke, size) — hijau muda
_CLR_KENTH = ("#d9f7be", "#95de64", 4)   # hijau sangat muda


def make_cincin_hex(df_grid, health_col, label_map, title,
                    infected_cats=None, df_grey=None,
                    df_tbm=None, df_kenth=None):
    """
    Visualisasi Cincin Api — replica exact create_plotly_hex_map() dari GitHub.

    Layout mata lima:  x = n_pokok + (n_baris % 2) * 0.5
    Y = n_baris dengan autorange='reversed' (baris 1 di atas)
    Parit isolasi = circle-open biru, diplot PERTAMA (layer bawah)
    Pohon diplot di atas parit
    """
    if infected_cats is None:
        infected_cats = {"Critical", "Sub-Optimal"}

    fig = go.Figure()

    # ── Siapkan data ──
    df = df_grid.copy()

    # Bypass: jika _b/_p sudah ada (dari calc_cincin_api atau GPS konversi), skip setup
    if "_b" in df.columns and "_p" in df.columns:
        df = df.dropna(subset=["_b", "_p"])
        if df.empty:
            fig.add_annotation(text="Tidak ada data grid",
                               x=0.5, y=0.5, showarrow=False, font_color="#333")
            return fig
        df["_b"] = df["_b"].astype(int)
        df["_p"] = df["_p"].astype(int)
    else:
        b_col = "N_BARIS" if "N_BARIS" in df.columns else "n_baris"
        p_col = "N_POKOK" if "N_POKOK" in df.columns else "n_pokok"
        df["_b"] = pd.to_numeric(df[b_col], errors="coerce")
        df["_p"] = pd.to_numeric(df[p_col], errors="coerce")
        df = df.dropna(subset=["_b", "_p"])
        if df.empty:
            fig.add_annotation(text="Tidak ada data N_BARIS/N_POKOK",
                               x=0.5, y=0.5, showarrow=False, font_color="#333")
            return fig
        df["_b"] = df["_b"].astype(int)
        df["_p"] = df["_p"].astype(int)

    # Standarkan health status (skip jika sudah ada _hs dari calc_cincin_api)
    if "_hs" not in df.columns:
        if label_map:
            df["_hs"] = df[health_col].map(label_map).fillna("Unknown")
        else:
            df["_hs"] = df[health_col].fillna("Unknown")
    elif health_col != "_hs" and health_col in df.columns:
        # health_col ada dan bukan _hs → re-map jika ada label_map
        if label_map:
            df["_hs"] = df[health_col].map(label_map).fillna(df["_hs"])

    # Hexagonal mata lima x-offset (skip jika sudah ada _x/_y)
    if "_x" not in df.columns:
        df["_x"] = df["_p"] + (df["_b"] % 2) * 0.5
    if "_y" not in df.columns:
        df["_y"] = df["_b"]

    # Hitung parit (skip jika sudah ada dari calc_cincin_api)
    if "_parit" not in df.columns:
        df["_parit"] = _compute_parit_hex(df, "_hs", infected_cats)


    # ── Layer 0: Pohon tidak ter-match (abu-abu) ──
    if df_grey is not None and not df_grey.empty:
        dg = df_grey.copy()
        dg["_b"] = pd.to_numeric(dg.get(b_col, dg.get("N_BARIS", dg.get("n_baris"))),
                                  errors="coerce")
        dg["_p"] = pd.to_numeric(dg.get(p_col, dg.get("N_POKOK", dg.get("n_pokok"))),
                                  errors="coerce")
        dg = dg.dropna(subset=["_b", "_p"])
        if not dg.empty:
            dg["_x"] = dg["_p"] + (dg["_b"].astype(int) % 2) * 0.5
            dg["_y"] = dg["_b"]
            fig.add_trace(go.Scatter(
                x=dg["_x"], y=dg["_y"], mode="markers",
                marker=dict(size=5, color="#e0e0e0",
                            line=dict(color="#bdbdbd", width=0.8)),
                hoverinfo="skip", showlegend=False,
            ))

    # ── Layer 0b: TBM (hijau muda) ───────────────────────────────────
    for bg_df, (fill, stroke, sz), label in [
        (df_tbm,   _CLR_TBM,   "TBM (Sisip)"),
        (df_kenth, _CLR_KENTH, "Kenthosan"),
    ]:
        if bg_df is None or bg_df.empty:
            continue
        bg = bg_df.copy()
        # Gunakan _x/_y jika sudah ada (GPS converted)
        if "_x" not in bg.columns or "_y" not in bg.columns:
            if "_b" in bg.columns and "_p" in bg.columns:
                bg["_x"] = bg["_p"] + (bg["_b"].astype(int) % 2) * 0.5
                bg["_y"] = bg["_b"]
            else:
                continue
        fig.add_trace(go.Scatter(
            x=bg["_x"], y=bg["_y"], mode="markers",
            marker=dict(size=sz, color=fill,
                        line=dict(color=stroke, width=0.8)),
            name=label, hoverinfo="skip", showlegend=False,
        ))

    # ── Layer 1: Parit isolasi + batas polygon per kluster ────────
    m_par  = df["_parit"]
    df_par = df[m_par]
    if not df_par.empty:
        fig.add_trace(go.Scatter(
            x=df_par["_x"], y=df_par["_y"],
            mode="markers",
            marker=dict(
                size=16, symbol="circle-open",
                color="#2980b9", line=dict(width=3, color="#2980b9"),
            ),
            name="⛏️ Parit Isolasi",
            hoverinfo="skip", showlegend=False,
        ))

    # ── Layer 1b: Garis batas parit isolasi (GitHub triangle-segments) ──
    #   Recompute parit dari SEMUA sel di df (termasuk phantom cells),
    #   sehingga ring parit sepadat SR → triangle algorithm menghasilkan
    #   batas tertutup yang rapi.
    _quar_mask = df["_hs"].isin({"Critical", "Sub-Optimal", "Moderate"})
    if _quar_mask.any():
        try:
            # 1. Set seluruh sel yang ada di df (real + phantom)
            all_cells = set(
                zip(df["_b"].astype(int), df["_p"].astype(int))
            )
            infected_coords = set(
                zip(df.loc[_quar_mask, "_b"].astype(int),
                    df.loc[_quar_mask, "_p"].astype(int))
            )
            # 2. Recompute parit: setiap sel NON-infected yang bersebelahan
            #    dengan infected (termasuk phantom cells yang baru ditambahkan)
            parit_coords_s = set()
            for (b, p) in all_cells:
                if (b, p) not in infected_coords:
                    for nb in _hex_neighbors(b, p):
                        if nb in infected_coords:
                            parit_coords_s.add((b, p))
                            break
            all_nodes = infected_coords.union(parit_coords_s)

            # 3. Cari semua segitiga ketetanggaan dalam all_nodes
            triangles = set()
            for u in all_nodes:
                neighbors = [n for n in _hex_neighbors(*u) if n in all_nodes]
                for v in neighbors:
                    v_nb = set(_hex_neighbors(*v))
                    for w in set(neighbors).intersection(v_nb):
                        triangles.add(tuple(sorted([u, v, w])))

            # 4. Fungsi midpoint dalam koordinat display
            def _mid(u, v):
                xu = u[1] + (u[0] % 2) * 0.5; yu = u[0]
                xv = v[1] + (v[0] % 2) * 0.5; yv = v[0]
                return ((xu + xv) / 2, (yu + yv) / 2)

            # 5. Segmen pemisah di batas parit ↔ infected
            trench_x, trench_y = [], []
            for u, v, w in triangles:
                nodes   = [u, v, w]
                p_nodes = [n for n in nodes if n in parit_coords_s]
                i_nodes = [n for n in nodes if n in infected_coords]
                if len(p_nodes) == 2 and len(i_nodes) == 1:
                    m1 = _mid(i_nodes[0], p_nodes[0])
                    m2 = _mid(i_nodes[0], p_nodes[1])
                    trench_x.extend([m1[0], m2[0], None])
                    trench_y.extend([m1[1], m2[1], None])
                elif len(p_nodes) == 1 and len(i_nodes) == 2:
                    m1 = _mid(p_nodes[0], i_nodes[0])
                    m2 = _mid(p_nodes[0], i_nodes[1])
                    trench_x.extend([m1[0], m2[0], None])
                    trench_y.extend([m1[1], m2[1], None])

            if trench_x:
                fig.add_trace(go.Scatter(
                    x=trench_x, y=trench_y, mode="lines",
                    line=dict(color="#2980b9", width=2.5, dash="dash"),
                    name="Garis Batas Parit",
                    hoverinfo="skip", showlegend=False,
                ))
        except Exception:
            pass


    # ── Layer 2: Pohon per kategori (di atas parit) ──
    # Phantom cells dikecualikan dari rendering — hanya digunakan oleh
    # triangle algorithm untuk menghitung garis batas parit.
    _is_phantom = df.get("_phantom", pd.Series(False, index=df.index))
    df_real = df[~_is_phantom]
    for hs, fill, stroke, size in _HEX_CATS:
        m = df_real["_hs"] == hs
        sub = df_real[m]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["_x"], y=sub["_y"],
            mode="markers",
            marker=dict(
                size=size,
                color=fill,
                line=dict(color=stroke, width=1.5),
                opacity=0.92,
            ),
            name=_HEX_LABELS.get(hs, hs),
            customdata=sub[["_b", "_p"]].values,
            hovertemplate=(
                f"<b>{_HEX_LABELS.get(hs, hs)}</b><br>"
                "Baris %{customdata[0]} · Pokok %{customdata[1]}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # ── Layout — exact match GitHub ──
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#1a1a1a"), x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False, title="",
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False, title="",
            autorange="reversed",
            scaleanchor="x",
        ),
        margin=dict(l=0, r=0, t=36, b=0),
        showlegend=False,
        dragmode="pan",
        height=620,
        hoverlabel=dict(bgcolor="white", font_size=12,
                        font_family="Arial", font_color="#1e212b"),
    )
    return fig



def make_cincin_scatter(trees_df, rings_df, lat_col, lon_col,
                        health_col, title, label_map=None):
    """
    Dot-map visualization: tiap pohon = titik berwarna.
    label_map: dict memetakan health_col value → key standard (Good/Moderate/Sub-Optimal/Critical)
    """
    fig = go.Figure()

    for hs, lbl, mstyle in zip(HEALTH_ORDER, HEALTH_LABELS, HEALTH_MARKER):
        if label_map:
            mask = trees_df[health_col].map(label_map) == hs
        else:
            mask = trees_df[health_col] == hs
        subset = trees_df[mask]
        if subset.empty:
            continue
        marker_cfg = dict(**mstyle)
        fig.add_trace(go.Scatter(
            x=subset[lon_col], y=subset[lat_col],
            mode="markers",
            marker=marker_cfg,
            name=lbl,
            hovertemplate=(
                f"<b>{lbl}</b><br>"
                "Lon: %{x:.5f}<br>Lat: %{y:.5f}<extra></extra>"
            ),
        ))

    # Ring overlay — blue isolation circles
    if rings_df is not None and not rings_df.empty:
        ring_lons_all, ring_lats_all = [], []
        for _, ring in rings_df.iterrows():
            r_m = max(ring.Radius_m, 5.0) + 6   # parit sedikit di luar radius
            rlats, rlons = _circle_latlon(ring.Center_Latitude, ring.Center_Longitude, r_m)
            ring_lats_all.extend(rlats + [None])
            ring_lons_all.extend(rlons + [None])
        fig.add_trace(go.Scatter(
            x=ring_lons_all, y=ring_lats_all,
            mode="lines",
            line=dict(color="#1565C0", width=2.8),
            name="🔵 Parit Isolasi",
            hoverinfo="skip",
        ))
        # Ring centers marker
        fig.add_trace(go.Scatter(
            x=rings_df.Center_Longitude, y=rings_df.Center_Latitude,
            mode="markers",
            marker=dict(size=5, color="#42A5F5",
                        line=dict(color="#0D47A1", width=1)),
            name="🎯 Pusat Cincin",
            hovertemplate="<b>%{customdata}</b><br>Sev: %{text}<extra></extra>",
            customdata=rings_df.Ring_ID,
            text=rings_df.Severity_Score.round(2).astype(str),
        ))

    lon_vals = trees_df[lon_col].dropna()
    lat_vals = trees_df[lat_col].dropna()
    lon_pad = (lon_vals.max() - lon_vals.min()) * 0.05 or 0.001
    lat_pad = (lat_vals.max() - lat_vals.min()) * 0.05 or 0.001

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="white")),
        height=560,
        plot_bgcolor="#0A0E17",
        paper_bgcolor="#0E1117",
        font_color="white",
        showlegend=True,
        legend=dict(
            font=dict(size=13, color="white"),
            bgcolor="rgba(14,17,23,0.85)",
            bordercolor="#334",
            borderwidth=1,
            orientation="v",
            x=0.01, y=0.99, xanchor="left", yanchor="top",
        ),
        xaxis=dict(showgrid=False, zeroline=False, visible=False,
                   range=[lon_vals.min()-lon_pad, lon_vals.max()+lon_pad]),
        yaxis=dict(showgrid=False, zeroline=False, visible=False,
                   scaleanchor="x", scaleratio=1,
                   range=[lat_vals.min()-lat_pad, lat_vals.max()+lat_pad]),
        margin=dict(l=4, r=4, t=44, b=4),
    )
    return fig


# ── Hybrid C: SR Grid Visualization ──────────────────────────────

def _circle_2d(cx: float, cy: float, r: float, n: int = 64):
    """Circle in 2D grid space (no geo correction needed)."""
    angles = np.linspace(0, 2 * np.pi, n + 1)
    xs = (cx + r * np.cos(angles)).tolist()
    ys = (cy + r * np.sin(angles)).tolist()
    return xs, ys


def _estimate_grid_spacing(df_sr: "pd.DataFrame") -> float:
    """
    Estimasi jarak antar pohon (meter) dari koordinat UTM X/Y per baris tanam.
    Fallback ke 9.0m jika data tidak cukup.
    """
    df = df_sr.copy()
    for col in ["N_BARIS", "N_POKOK", "X", "Y"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df = df.dropna(subset=["N_BARIS", "N_POKOK", "X", "Y"])
    if df.empty:
        return 9.0

    within_dists = []
    for _, grp in df.groupby("N_BARIS"):
        grp = grp.sort_values("N_POKOK")
        xs, ys = grp["X"].values, grp["Y"].values
        for i in range(1, len(xs)):
            d = np.hypot(xs[i] - xs[i-1], ys[i] - ys[i-1])
            if 3.0 < d < 20.0:
                within_dists.append(d)

    between_dists = []
    centroids = df.groupby("N_BARIS")[["X", "Y"]].mean().sort_index()
    cx_arr, cy_arr = centroids["X"].values, centroids["Y"].values
    for i in range(1, len(cx_arr)):
        d = np.hypot(cx_arr[i] - cx_arr[i-1], cy_arr[i] - cy_arr[i-1])
        if 3.0 < d < 20.0:
            between_dists.append(d)

    all_dists = within_dists + between_dists
    return float(np.median(all_dists)) if all_dists else 9.0


def make_cincin_grid(df_sr, rings_df, health_col, label_map, title):
    """
    Hybrid-C SR panel: tiap pohon diplot pada grid N_BARIS × N_POKOK.
    Ring radius dikonversi dari meter ke grid-unit menggunakan spacing estimasi.
    """
    fig = go.Figure()

    df = df_sr.copy()
    df["gx"] = pd.to_numeric(df.get("N_POKOK"), errors="coerce")
    df["gy"] = -pd.to_numeric(df.get("N_BARIS"), errors="coerce")  # flip: baris 1 di atas
    df = df.dropna(subset=["gx", "gy"])

    if df.empty:
        fig.add_annotation(text="Tidak ada data N_BARIS/N_POKOK",
                           x=0.5, y=0.5, showarrow=False, font_color="white")
        return fig

    # Estimasi spacing (meter per unit grid)
    sp_m = _estimate_grid_spacing(df_sr)

    # ── Plot pohon per status kesehatan ──
    for hs, lbl, mstyle in zip(HEALTH_ORDER, HEALTH_LABELS, HEALTH_MARKER):
        mask = df[health_col].map(label_map) == hs if label_map else df[health_col] == hs
        subset = df[mask]
        if subset.empty:
            continue
        hover_baris = (-subset["gy"]).astype(int).astype(str)
        fig.add_trace(go.Scatter(
            x=subset["gx"], y=subset["gy"],
            mode="markers",
            marker=dict(**mstyle),
            name=lbl,
            text=hover_baris,
            hovertemplate=(
                f"<b>{lbl}</b><br>"
                "Baris: %{text}<br>Pokok: %{x:.0f}<extra></extra>"
            ),
        ))

    # ── Ring overlay dalam grid space ──
    if rings_df is not None and not rings_df.empty:
        # Build lookup: geo → grid via nearest SR tree
        geo_df = df_sr.copy()
        geo_df["gx"] = pd.to_numeric(geo_df.get("N_POKOK"), errors="coerce")
        geo_df["gy"] = -pd.to_numeric(geo_df.get("N_BARIS"), errors="coerce")
        for gc in ["sr_lon", "sr_lat", "gx", "gy"]:
            geo_df[gc] = pd.to_numeric(geo_df.get(gc), errors="coerce")
        geo_valid = geo_df.dropna(subset=["sr_lon", "sr_lat", "gx", "gy"])

        ring_xs, ring_ys = [], []
        center_xs, center_ys = [], []
        ring_ids, ring_sevs = [], []

        for _, ring in rings_df.iterrows():
            if geo_valid.empty:
                break
            dists = np.hypot(
                geo_valid["sr_lon"].values - ring.Center_Longitude,
                geo_valid["sr_lat"].values - ring.Center_Latitude,
            )
            nearest = geo_valid.iloc[dists.argmin()]
            # Skip if nearest tree > ~200m away (0.002 deg)
            if dists.min() > 0.003:
                continue
            cx, cy = nearest["gx"], nearest["gy"]
            # Radius in grid units (parit = radius + 1.5 spacing buffer)
            r_grid = (ring.Radius_m + sp_m * 1.5) / sp_m
            rxs, rys = _circle_2d(cx, cy, r_grid)
            ring_xs.extend(rxs + [None])
            ring_ys.extend(rys + [None])
            center_xs.append(cx)
            center_ys.append(cy)
            ring_ids.append(ring.Ring_ID)
            ring_sevs.append(f"{ring.Severity_Score:.2f}")

        if ring_xs:
            fig.add_trace(go.Scatter(
                x=ring_xs, y=ring_ys,
                mode="lines",
                line=dict(color="#1565C0", width=2.8),
                name="🔵 Parit Isolasi",
                hoverinfo="skip",
            ))
        if center_xs:
            fig.add_trace(go.Scatter(
                x=center_xs, y=center_ys,
                mode="markers",
                marker=dict(size=6, color="#42A5F5",
                            symbol="diamond",
                            line=dict(color="#0D47A1", width=1.5)),
                name="🎯 Pusat Cincin",
                text=ring_sevs,
                customdata=ring_ids,
                hovertemplate="<b>%{customdata}</b><br>Sev: %{text}<extra></extra>",
            ))

    gx_vals = df["gx"].dropna()
    gy_vals = df["gy"].dropna()
    gx_pad = max((gx_vals.max() - gx_vals.min()) * 0.03, 1.0)
    gy_pad = max((gy_vals.max() - gy_vals.min()) * 0.03, 1.0)

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="white")),
        height=580,
        plot_bgcolor="#080C14",
        paper_bgcolor="#0E1117",
        font_color="white",
        showlegend=True,
        legend=dict(
            font=dict(size=13, color="white"),
            bgcolor="rgba(10,14,23,0.88)",
            bordercolor="#445", borderwidth=1,
            x=0.01, y=0.99, xanchor="left", yanchor="top",
        ),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.04)",
            gridwidth=1, dtick=5,
            zeroline=False, showticklabels=True,
            tickfont=dict(size=9, color="#888"),
            title=dict(text="← Pokok →", font=dict(size=10, color="#666")),
            range=[gx_vals.min() - gx_pad, gx_vals.max() + gx_pad],
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.04)",
            gridwidth=1, dtick=5,
            zeroline=False, showticklabels=True,
            tickfont=dict(size=9, color="#888"),
            tickformat="d",
            tickvals=list(range(int(gy_vals.min()), int(gy_vals.max())+1, 5)),
            ticktext=[str(abs(v)) for v in range(int(gy_vals.min()), int(gy_vals.max())+1, 5)],
            scaleanchor="x", scaleratio=1,
            title=dict(text="Baris ↑", font=dict(size=10, color="#666")),
            range=[gy_vals.min() - gy_pad, gy_vals.max() + gy_pad],
        ),
        margin=dict(l=30, r=4, t=48, b=30),
        annotations=[dict(
            text=f"Grid spacing estimasi: ~{sp_m:.1f} m/unit",
            x=1.0, y=0.0, xref="paper", yref="paper",
            xanchor="right", yanchor="bottom",
            showarrow=False, font=dict(size=9, color="#556"),
        )],
    )
    return fig


def zone_counts(df_trees, mode="absolute"):
    if df_trees.empty: return 0,0,0,0
    hs_col = "Health_Status_Abs" if mode=="absolute" and "Health_Status_Abs" in df_trees.columns else "Health_Status"
    mode_rings_csv = CINCIN_DIR  # placeholder
    merah = oranye = kuning = hijau = 0
    for _, row in df_trees.iterrows():
        h = str(row.get(hs_col,""))
        if h in ("Critical","Suspect"):   merah  += 1
        elif h in ("Sub-Optimal","Abnormal"): oranye += 1
        elif h in ("Normal","Moderate"):  kuning += 1
        else:                             hijau  += 1
    return merah, oranye, kuning, hijau

# ── sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Filter")

    # ── Level 1: Divisi ───────────────────────────────────────────
    division = st.selectbox(
        "Divisi",
        ["AME II", "AME IV"],
        help="AME II: Blok D001A–E002A (Feb 2026) | AME IV: Blok C012–C019"
    )

    # ── Level 2: Blok (tergantung Divisi) ─────────────────────────
    _block_list = BLOCKS if division == "AME II" else BLOCKS_AME4
    blok_sel = st.multiselect("Blok", _block_list, default=_block_list)

    st.divider()
    st.subheader("🌱 Populasi Drone")
    include_tbm   = st.toggle(
        "Sertakan TBM (Sisip)",
        value=False,
        help="TBM = Tanaman Belum Menghasilkan (sisip muda, umur <3 tahun)"
    )
    include_kenth = st.toggle(
        "Sertakan Kenthosan",
        value=False,
        help="Kenthosan = vegetasi di luar jalur tanam (tumbuh liar)"
    )

    _pop_label = "TM"
    if include_tbm:   _pop_label += " + TBM"
    if include_kenth: _pop_label += " + Kenthosan"
    st.caption(f"Mode: **{_pop_label}**")

    st.divider()
    if st.button("🔄 Refresh Data Cache", help="Paksa reload trees_*.csv dari disk (setelah re-run deteksi)"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    if division == "AME II":
        st.caption("🔥 Cincin Api AME II")
        st.caption("📡 MAPIR T4-R125 | Feb 2026")
        st.caption("📋 SR Excel: 28.489 pohon")
    else:
        st.caption("🌴 AME IV — C012–C019")
        st.caption("📡 MAPIR | Feb 2026")
        st.caption(f"📋 SR Ref: {sum(SR_REF_AME4.values()):,} pokok")

df_sum    = load_summary()   if division == "AME II" else pd.DataFrame()
df_sr_all = load_sr()        if division == "AME II" else pd.DataFrame()

_div_title = "AME II" if division == "AME II" else "AME IV"
st.title(f"🔥 Cincin Api - {_div_title} | NDRE Drone Relatif vs NDRE Drone Absolut")
st.caption("Sumber: WebODM Relatif · Kalibrasi Panel MAPIR Absolut" +
           (" · SR Excel 2025+2026" if division == "AME II" else " · SR Referensi Blok"))

tab2, tab4 = st.tabs([
    "🔁 Cincin Api", "🌡️ Kesehatan Blok"
])
# Tab 1 (Overview SR) dan Tab 3 (NDRE Tren 25→26) sementara disembunyikan
# Untuk mengaktifkan kembali: ganti kembali st.tabs menjadi 5 tab dan hapus 'if False:'
tab1 = tab3 = None   # placeholder agar referensi kode lama tidak error
tab5 = tab4          # Tab4 + Tab5 digabung: konten tab5 di-render di tab4


# ════ TAB 1: SR Overview (SEMENTARA DISEMBUNYIKAN) ════════════════
if tab1:  # tab1 = None → blok ini dilewati; hapus 'tab1 = None' di atas untuk mengaktifkan
    st.subheader(f"Data SR — {'10 Blok AME II' if division == 'AME II' else '9 Blok AME IV'}")
    if division == "AME IV":
        st.info("📊 Data SR lapangan (Excel) hanya tersedia untuk AME II. "
                "AME IV menggunakan SR Referensi Blok untuk validasi akurasi deteksi drone.")
        # Tampilkan tabel akurasi AME IV
        ameiv_rows = []
        for blok in blok_sel:
            df_t = load_trees(blok, division)
            n_tm  = int((df_t['Classification']=='TM').sum()) if not df_t.empty and 'Classification' in df_t.columns else 0
            n_tbm = int((df_t['Classification']=='TBM').sum()) if not df_t.empty and 'Classification' in df_t.columns else 0
            sr_r  = SR_REF_AME4.get(blok, 0)
            area  = AREA_AME4.get(blok, 0)
            acc   = round(n_tm/sr_r*100,1) if sr_r else 0
            sph_d = round(n_tm/area,1) if area else 0
            sph_s = round(sr_r/area,1) if area else 0
            # stress
            hs_col = 'Health_Status_Abs' if not df_t.empty and 'Health_Status_Abs' in df_t.columns else None
            stress_pct = 0
            if hs_col and not df_t.empty:
                tm_df = df_t[df_t['Classification']=='TM'] if 'Classification' in df_t.columns else df_t
                stress = tm_df[hs_col].isin({'Critical','Sub-Optimal'}).sum()
                stress_pct = round(stress/n_tm*100,1) if n_tm else 0
            ameiv_rows.append({'Blok':blok,'SR Ref':sr_r,'TM Drone':n_tm,
                               'Akurasi%':acc,'SPH Drone':sph_d,'SPH SR':sph_s,
                               'Stress%':stress_pct})
        df_ameiv = pd.DataFrame(ameiv_rows)
        if not df_ameiv.empty:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total TM Drone",f"{df_ameiv['TM Drone'].sum():,}")
            c2.metric("Total SR Ref",  f"{df_ameiv['SR Ref'].sum():,}")
            c3.metric("Akurasi Rata-rata",f"{df_ameiv['Akurasi%'].mean():.1f}%")
            c4.metric("Stress Rata-rata",f"{df_ameiv['Stress%'].mean():.1f}%")
            st.dataframe(df_ameiv.style.format({'Akurasi%':'{:.1f}%','SPH Drone':'{:.1f}',
                                                'SPH SR':'{:.1f}','Stress%':'{:.1f}%'}),
                         use_container_width=True)
            fig_acc = go.Figure(go.Bar(
                x=df_ameiv['Blok'], y=df_ameiv['Akurasi%'],
                marker_color=['#43A047' if 90<=v<=115 else '#E53935' for v in df_ameiv['Akurasi%']],
                text=[f"{v:.1f}%" for v in df_ameiv['Akurasi%']], textposition='outside'
            ))
            fig_acc.add_hline(y=100, line_dash='dash', line_color='white', annotation_text='100% = SR')
            fig_acc.add_hline(y=115, line_dash='dot', line_color='orange', annotation_text='Batas atas 115%')
            fig_acc.update_layout(title='Akurasi TM Drone vs SR per Blok AME IV',
                height=350, plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', font_color='white')
            st.plotly_chart(fig_acc, use_container_width=True)
    else:
        # AME II — kode asli
        st.info(
            "📈 **Overview SR** — Ringkasan kondisi kesehatan 10 blok berdasarkan data SR: "
            "total pohon, distribusi SPH, rata-rata NDRE, dan jumlah cincin api per blok."
        )
        if not df_sum.empty:
            df_f = df_sum[df_sum.Blok.isin(blok_sel)]
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Total Pohon SR", f"{df_f.N_SR.sum():,}")
            c2.metric("Pokok Utama",    f"{df_f.N_Utama.sum():,}")
            c3.metric("Sisip",          f"{df_f.N_Sisip.sum():,}")
            c4.metric("Mati",           f"{df_f.N_Mati.sum():,}")
            c5.metric("Match Drone (avg)", f"{df_f.Match_Pct.mean():.1f}%")

        # SPH per blok
        fig_sph = go.Figure()
        if not df_sum.empty:
            df_f = df_sum[df_sum.Blok.isin(blok_sel)]
            fig_sph.add_trace(go.Bar(
                x=df_f.Blok, y=df_f.SPH_SR,
                marker_color=["#E53935" if v<110 else "#FFA726" if v<125 else "#43A047"
                              for v in df_f.SPH_SR],
                text=[f"{v}" for v in df_f.SPH_SR], textposition="outside",
                name="SPH SR",
            ))
        fig_sph.add_hline(y=136, line_dash="dash", line_color="#FFEE58",
                          annotation_text="SPH Ideal: 136")
        fig_sph.update_layout(title="SPH per Blok (dari data SR Pokok Utama)",
            height=350, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
        st.plotly_chart(fig_sph, use_container_width=True)

        # Ket status stacked
        ket_data = []
        for blok in blok_sel:
            sub = df_sr_all[df_sr_all.BLOK_B==blok]
            ket_data.append({
                "Blok":blok,
                "Pokok Utama": (sub.Ket=="Pokok Utama").sum(),
                "Sisip":       sub.Ket.str.contains("Sisip",na=False).sum(),
                "Mati":        sub.Ket.str.contains("Mati",na=False).sum(),
                "Tamb":        (sub.Ket=="Tamb").sum(),
            })
        df_ket = pd.DataFrame(ket_data)
        fig_ket = go.Figure()
        for col, clr in [("Pokok Utama","#43A047"),("Sisip","#42A5F5"),("Tamb","#FFA726"),("Mati","#E53935")]:
            fig_ket.add_trace(go.Bar(name=col, x=df_ket.Blok, y=df_ket[col], marker_color=clr))
        fig_ket.update_layout(barmode="stack", title="Status Pohon per Blok (SR)",
            height=350, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
        st.plotly_chart(fig_ket, use_container_width=True)

        # Tabel
        if not df_sum.empty:
            st.dataframe(df_sum[df_sum.Blok.isin(blok_sel)][
                ["Blok","N_SR","N_Utama","N_Sisip","N_Mati","SPH_SR",
                 "NDRE_SR_2025","NDRE_SR_2026","Delta_NDRE_SR","Match_Pct"]
            ], use_container_width=True)

# ════ TAB 2: 3-Arah Rings ═══════════════════════════════════════
with tab2:
    st.subheader("🔁 Perbandingan Cincin Api — 3 Sumber")
    if division == "AME IV":
        st.info("🔁 **3-Arah Rings** belum tersedia untuk AME IV. "
                "Cincin Api hanya dihitung untuk AME II menggunakan data SR lapangan. "
                "Gunakan **Tab Zona Drone** atau **Detail Blok** untuk analisis AME IV.")
    else:
        st.info(
            "🔄 **3-Arah Rings** — Perbandingan side by side cincin api dari 3 sumber: "
            "Data SR, NDRE Drone Relatif, dan NDRE Drone Absolut. "
            "Digunakan untuk mendeteksi konsistensi antar metode pengukuran."
        )
    if not df_sum.empty and division == "AME II":
        df_f = df_sum[df_sum.Blok.isin(blok_sel)]

        # Bar chart 3 sumber
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(name="🌿 Data SR 2026",
            x=df_f.Blok, y=df_f.Rings_SR, marker_color="#8D6E63",
            text=df_f.Rings_SR, textposition="outside",
            textfont=dict(color="#FFFFFF")))
        fig3.add_trace(go.Bar(name="🔵 NDRE Drone Relatif",
            x=df_f.Blok, y=df_f.Rings_DroneRel, marker_color="#42A5F5",
            text=df_f.Rings_DroneRel, textposition="outside",
            textfont=dict(color="#FFFFFF")))
        fig3.add_trace(go.Bar(name="🟢 NDRE Drone Absolut",
            x=df_f.Blok, y=df_f.Rings_DroneAbs, marker_color="#66BB6A",
            text=df_f.Rings_DroneAbs, textposition="outside",
            textfont=dict(color="#FFFFFF")))
        fig3.update_layout(barmode="group", title="Jumlah Cincin Api per Blok — 3 Sumber",
            height=420, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white",
            legend=dict(font=dict(size=14, color="white"), bgcolor="rgba(0,0,0,0)",
                        orientation="h", y=1.08, x=0))
        st.plotly_chart(fig3, use_container_width=True)



    # ── Cincin Api Dot Map (AME II only) ──────────────────────────────────
    blok_viz = BLOCKS[0]  # safe default — overridden by selectbox di bawah jika AME II
    if division != "AME II":
        st.info("🗺️ Peta Cincin Api hanya tersedia untuk AME II (membutuhkan data SR lapangan & ring boundary).")
    else:
        st.divider()
        st.markdown("### 🗺️ Peta Cincin Api — SR 2026 vs Drone Absolut")
        st.caption(
            "Setiap titik = 1 pohon. "
            "🔴 Merah=Kritis · 🟠 Oranye=Sub-Optimal · 🟡 Kuning=Moderat · 🟢 Hijau=Sehat (hollow). "
            "🔵 Lingkaran biru = batas parit isolasi."
        )

        _idx_viz = BLOCKS.index(blok_sel[0]) if (blok_sel and blok_sel[0] in BLOCKS) else 0
        blok_viz = st.selectbox(
            "Pilih Blok Visualisasi Cincin", BLOCKS,
            index=_idx_viz,
            key="cincin_blok_sel"
        )

    if division == "AME II":
        df_trees_viz = apply_population_filter(
            load_trees(blok_viz, "AME II"), include_tbm=False, include_kenth=False
        )
        r_sr_viz  = load_rings(blok_viz, "sr_2026_input")
        r_abs_viz = load_rings(blok_viz, "absolute")
    else:
        df_trees_viz = pd.DataFrame()
        r_sr_viz     = pd.DataFrame()
        r_abs_viz    = pd.DataFrame()

    if not df_sr_all.empty and 'BLOK_B' in df_sr_all.columns:
        df_sr_viz = df_sr_all[df_sr_all.BLOK_B == blok_viz].copy()
        df_sr_viz['klass_norm'] = (
            df_sr_viz.KLASSNDRE2_26
            .str.strip()
            .str.replace('\xa0', ' ', regex=False)
        )
    else:
        df_sr_viz = pd.DataFrame()

    # Konversi UTM (X/Y EPSG:32749) → WGS84 lat/lon
    from pyproj import Transformer as _Tr
    _tr = _Tr.from_crs("EPSG:32749", "EPSG:4326", always_xy=True)
    if not df_sr_viz.empty and 'X' in df_sr_viz.columns:
        _xy_ok = df_sr_viz.X.notna() & df_sr_viz.Y.notna()
        _lons, _lats = _tr.transform(
            df_sr_viz.loc[_xy_ok, "X"].tolist(),
            df_sr_viz.loc[_xy_ok, "Y"].tolist()
        )
        df_sr_viz.loc[_xy_ok, "sr_lon"] = _lons
        df_sr_viz.loc[_xy_ok, "sr_lat"] = _lats
        df_sr_viz = df_sr_viz.dropna(subset=["sr_lon", "sr_lat"])


    # KPI row — 4 metrik faktual (Severity Score dihilangkan: bobot belum tervalidasi)
    mk1, mk2, mk3, mk4 = st.columns(4)
    mk1.metric("🌿 Pohon SR",  f"{len(df_sr_viz):,}")
    mk2.metric("🔵 Ring SR",   f"{len(r_sr_viz)}" if not r_sr_viz.empty else "—")
    mk3.metric("🟢 Pohon TM",  f"{len(df_trees_viz):,}")
    mk4.metric("🔵 Ring Abs",  f"{len(r_abs_viz)}" if not r_abs_viz.empty else "—")

    # ── KPI Distribusi Stres — SR 2026 vs Drone Absolut ──────────────
    # (ditampilkan langsung di atas dua visualisasi Cincin Api)
    _ABS_MAP2  = {"Critical": "Stres Sangat Berat", "Sub-Optimal": "Stres Berat",
                  "Moderate": "Stres Sedang",       "Good": "Stres Ringan"}
    # SR counts per kategori
    _sr_vc_kpi = {}
    if not df_sr_viz.empty and "KLASSNDRE2_26" in df_sr_viz.columns:
        _sr_vc_kpi = df_sr_viz["KLASSNDRE2_26"].str.strip().value_counts().to_dict()
    # Drone Absolute counts per kategori
    _df_tv_kpi = apply_population_filter(load_trees(blok_viz, division), include_tbm, include_kenth)
    _drone_vc_kpi = {}
    if not _df_tv_kpi.empty and "Health_Status_Abs" in _df_tv_kpi.columns:
        _drone_vc_kpi = _df_tv_kpi["Health_Status_Abs"].map(_ABS_MAP2).value_counts().to_dict()

    st.markdown("#### 📊 Distribusi Stres — SR 2026 vs Drone Absolut")
    _kl, _kr = st.columns(2, gap="large")

    _sr_tot   = max(sum(_sr_vc_kpi.values()),   1)
    _dr_tot   = max(sum(_drone_vc_kpi.values()), 1)

    def _pct(vc, key, total):
        return f"{vc.get(key, 0) / total * 100:.1f}%"

    with _kl:
        st.markdown("**🌿 SR 2026**")
        ks1, ks2, ks3, ks4 = st.columns(4)
        ks1.metric("🔴 Sangat Berat", f"{_sr_vc_kpi.get('Stres Sangat Berat', 0):,}",
                   _pct(_sr_vc_kpi, 'Stres Sangat Berat', _sr_tot), delta_color="off")
        ks2.metric("🟠 Berat",        f"{_sr_vc_kpi.get('Stres Berat',        0):,}",
                   _pct(_sr_vc_kpi, 'Stres Berat',        _sr_tot), delta_color="off")
        ks3.metric("🟡 Sedang",       f"{_sr_vc_kpi.get('Stres Sedang',       0):,}",
                   _pct(_sr_vc_kpi, 'Stres Sedang',       _sr_tot), delta_color="off")
        ks4.metric("🟢 Ringan",       f"{_sr_vc_kpi.get('Stres Ringan',       0):,}",
                   _pct(_sr_vc_kpi, 'Stres Ringan',       _sr_tot), delta_color="off")
    with _kr:
        st.markdown("**🚁 Drone Absolut**")
        kd1, kd2, kd3, kd4 = st.columns(4)
        kd1.metric("🔴 Sangat Berat", f"{_drone_vc_kpi.get('Stres Sangat Berat', 0):,}",
                   _pct(_drone_vc_kpi, 'Stres Sangat Berat', _dr_tot), delta_color="off")
        kd2.metric("🟠 Berat",        f"{_drone_vc_kpi.get('Stres Berat',        0):,}",
                   _pct(_drone_vc_kpi, 'Stres Berat',        _dr_tot), delta_color="off")
        kd3.metric("🟡 Sedang",       f"{_drone_vc_kpi.get('Stres Sedang',       0):,}",
                   _pct(_drone_vc_kpi, 'Stres Sedang',       _dr_tot), delta_color="off")
        kd4.metric("🟢 Ringan",       f"{_drone_vc_kpi.get('Stres Ringan',       0):,}",
                   _pct(_drone_vc_kpi, 'Stres Ringan',       _dr_tot), delta_color="off")

    col_sr, col_dr = st.columns(2, gap="small")

    df_sr_ca = pd.DataFrame()  # default — diisi di col_sr jika df_sr_viz tidak kosong

    # ─ SR Panel: calc_cincin_api pada NDRE2_26 (sama seperti GitHub) ─
    with col_sr:
        if len(df_sr_viz) > 0:
            df_sr_ca = df_sr_viz.copy()
            df_sr_ca["NDRE2_26"] = pd.to_numeric(df_sr_ca["NDRE2_26"], errors="coerce")
            df_sr_ca["_b"] = pd.to_numeric(df_sr_ca["N_BARIS"], errors="coerce")
            df_sr_ca["_p"] = pd.to_numeric(df_sr_ca["N_POKOK"],  errors="coerce")
            df_sr_ca = df_sr_ca.dropna(subset=["_b", "_p", "NDRE2_26"])
            df_sr_ca["_b"] = df_sr_ca["_b"].astype(int)
            df_sr_ca["_p"] = df_sr_ca["_p"].astype(int)
            df_sr_ca["_x"] = df_sr_ca["_p"] + (df_sr_ca["_b"] % 2) * 0.5
            df_sr_ca["_y"] = df_sr_ca["_b"]
            df_sr_ca = calc_cincin_api(df_sr_ca, val_col="NDRE2_26", threshold=0.15)
            fig_csr = make_cincin_hex(
                df_grid=df_sr_ca,
                health_col="_hs",
                label_map=None,
                title=f"🌿 SR 2026 — {blok_viz}  ({len(df_sr_ca):,} pohon · {len(r_sr_viz)} ring)",
            )
            st.plotly_chart(fig_csr, use_container_width=True, key="map_sr")
        else:
            st.warning(f"Data SR tidak tersedia untuk {blok_viz}")


    # ─ Drone Panel: trees_*.csv → TM (+ TBM/Kenth toggle) → calc_cincin_api ─
    with col_dr:
        df_trees_all = load_trees(blok_viz, "AME II")   # semua deteksi drone
        # TM saja untuk cincin api classification
        df_trees_drone = df_trees_all[df_trees_all["Classification"] == "TM"].copy() \
            if "Classification" in df_trees_all.columns else df_trees_all.copy()
        # TBM & Kenthosan sebagai latar (dikontrol sidebar toggle)
        df_tbm_bg   = df_trees_all[df_trees_all["Classification"] == "TBM"].copy() \
            if include_tbm   and "Classification" in df_trees_all.columns else pd.DataFrame()
        df_kenth_bg = df_trees_all[df_trees_all["Classification"] == "Kenthosan"].copy() \
            if include_kenth and "Classification" in df_trees_all.columns else pd.DataFrame()
        if not df_trees_drone.empty and "NDRE_Absolute" in df_trees_drone.columns:
            df_dr = df_trees_drone.copy()
            df_dr["NDRE_Absolute"] = pd.to_numeric(df_dr["NDRE_Absolute"], errors="coerce")
            df_dr = df_dr.dropna(subset=["NDRE_Absolute", "Latitude", "Longitude"])

            # ── GPS reference seluruh blok (TM + TBM + Kenth) ────────────
            all_lats = pd.concat([df_dr["Latitude"]] +
                ([df_tbm_bg["Latitude"]]   if not df_tbm_bg.empty   else []) +
                ([df_kenth_bg["Latitude"]] if not df_kenth_bg.empty else []))
            all_lons = pd.concat([df_dr["Longitude"]] +
                ([df_tbm_bg["Longitude"]]   if not df_tbm_bg.empty   else []) +
                ([df_kenth_bg["Longitude"]] if not df_kenth_bg.empty else []))
            lat_min_all = all_lats.min(); lat_max_all = all_lats.max()
            lon_min_all = all_lons.min(); lon_max_all = all_lons.max()
            lat_rng = max(lat_max_all - lat_min_all, 1e-9)
            lon_rng = max(lon_max_all - lon_min_all, 1e-9)

            # SR range untuk scaling visual
            sr_b_max = int(df_sr_ca["_b"].max()) if not df_sr_ca.empty else 100
            sr_p_max = int(df_sr_ca["_p"].max()) if not df_sr_ca.empty else 30

            def _gps_snap_grid(df_sub, ndre_col=None):
                """
                Snap GPS → integer grid identik dengan SR (_b=1..sr_b_max, _p=1..sr_p_max).
                Sel ganda: jika ndre_col ada → simpan NDRE terendah (paling sakit);
                           jika tidak ada (TBM/Kenth) → simpan satu saja.
                Hasil: kerapatan visual sama dengan SR panel.
                """
                d = df_sub.copy()
                d = d.dropna(subset=["Latitude", "Longitude"])
                if d.empty:
                    return d
                # Snap ke integer grid SR
                d["_b"] = (((lat_max_all - d["Latitude"]) / lat_rng)
                           * (sr_b_max - 1) + 1).round().astype(int).clip(1, sr_b_max)
                d["_p"] = (((d["Longitude"] - lon_min_all) / lon_rng)
                           * (sr_p_max - 1) + 1).round().astype(int).clip(1, sr_p_max)
                # Deduplication per sel
                if ndre_col and ndre_col in d.columns:
                    # TM: simpan pohon dengan NDRE paling rendah (paling stres)
                    d = (d.sort_values(ndre_col, ascending=True)
                           .drop_duplicates(subset=["_b", "_p"], keep="first"))
                else:
                    # TBM/Kenth: simpan satu per sel
                    d = d.drop_duplicates(subset=["_b", "_p"], keep="first")
                # Hex display coords
                d["_x"] = d["_p"] + (d["_b"] % 2) * 0.5
                d["_y"] = d["_b"].astype(float)
                return d


            # ── Integer grid HANYA untuk calc_cincin_api algorithm ────────
            lat_mean    = df_dr["Latitude"].mean()
            lat_range_m = (df_dr["Latitude"].max() - df_dr["Latitude"].min()) * 111111.0
            lon_range_m = (df_dr["Longitude"].max() - df_dr["Longitude"].min()) \
                          * 111111.0 * np.cos(np.radians(lat_mean))
            aspect     = lon_range_m / max(lat_range_m, 1.0)
            n_rows_est = max(2, int(np.round(np.sqrt(len(df_dr) / aspect))))
            n_cols_est = max(2, int(np.round(len(df_dr) / n_rows_est)))
            lat_sp = (df_dr["Latitude"].max() - df_dr["Latitude"].min()) / max(n_rows_est - 1, 1)
            lon_sp = (df_dr["Longitude"].max() - df_dr["Longitude"].min()) / max(n_cols_est - 1, 1)
            df_dr["_b"] = ((df_dr["Latitude"].max() - df_dr["Latitude"]) / lat_sp).round().astype(int)
            df_dr["_p"] = ((df_dr["Longitude"] - df_dr["Longitude"].min()) / lon_sp).round().astype(int)
            df_dr["_b"] = df_dr["_b"] - df_dr["_b"].min() + 1
            df_dr["_p"] = df_dr["_p"] - df_dr["_p"].min() + 1
            df_dr = calc_cincin_api(df_dr, val_col="NDRE_Absolute", threshold=0.15)

            # Override _x/_y dengan grid integer SR (kerapatan sama dengan SR panel)
            df_dr = _gps_snap_grid(df_dr, ndre_col="NDRE_Absolute")
            df_tbm_plot   = _gps_snap_grid(df_tbm_bg)   if not df_tbm_bg.empty   else pd.DataFrame()
            df_kenth_plot = _gps_snap_grid(df_kenth_bg) if not df_kenth_bg.empty else pd.DataFrame()

            # ── Isi grid drone dengan phantom "Good" cells ──────────────
            # occupied_bp = hanya TM, JANGAN masukkan TBM/Kenth.
            # Alasannya: TBM/Kenth di-render lewat df_tbm/df_kenth (Layer 0b),
            # jika posisi mereka dimasukkan ke occupied_bp maka phantom cells
            # tidak dibuat → saat filter TBM/Kenth aktif, posisi tersebut
            # kosong di df → parit ring bocor → batas putus.
            # Phantom cells di posisi TBM/Kenth tidak terlihat (_phantom=True)
            # tapi cukup untuk membuat triangle algorithm menemukan tetangga.
            occupied_bp = set(zip(df_dr["_b"].astype(int), df_dr["_p"].astype(int)))
            phantom_rows = []
            for _pb in range(1, sr_b_max + 1):
                for _pp in range(1, sr_p_max + 1):
                    if (_pb, _pp) not in occupied_bp:
                        phantom_rows.append({
                            "_b": _pb, "_p": _pp,
                            "_x": _pp + (_pb % 2) * 0.5,
                            "_y": float(_pb),
                            "_hs": "Good", "_parit": False,
                            "_phantom": True,
                        })
            if phantom_rows:
                df_phantom = pd.DataFrame(phantom_rows)
                df_dr["_phantom"] = False
                df_dr = pd.concat([df_dr, df_phantom], ignore_index=True)


            n_tbm   = len(df_tbm_plot)
            n_kenth = len(df_kenth_plot)
            title_suffix = f"TM:{len(df_dr):,}"
            if n_tbm   > 0: title_suffix += f" · TBM:{n_tbm:,}"
            if n_kenth > 0: title_suffix += f" · Kenth:{n_kenth:,}"


            fig_cdr = make_cincin_hex(
                df_grid=df_dr,
                health_col="_hs",
                label_map=None,
                df_grey=None,
                df_tbm=df_tbm_plot   if not df_tbm_plot.empty   else None,
                df_kenth=df_kenth_plot if not df_kenth_plot.empty else None,
                title=f"🚁 Drone Absolut — {blok_viz}  ({title_suffix})",
            )
            st.plotly_chart(fig_cdr, use_container_width=True, key="map_dr")

        else:
            st.warning(f"Data trees drone tidak tersedia untuk {blok_viz}")


    # Detail ring table side-by-side
    with st.expander("📋 Detail Ring — SR vs Drone Abs", expanded=False):
        dc1, dc2 = st.columns(2)
        _col_rename = {
            "Ring_ID":        "ID Cincin",
            "Member_Count":   "Jml Pohon",
            "Suspect_Count":  "Pohon Kritis",
            "Abnormal_Count": "Pohon Stres Berat",
            "Mean_NDRE":      "Rata-rata NDRE",
        }
        _show_cols = [c for c in ["Ring_ID","Member_Count","Suspect_Count",
                                   "Abnormal_Count","Mean_NDRE"] if c in r_sr_viz.columns]
        with dc1:
            st.caption("**Cincin Api — Data SR 2026**")
            if not r_sr_viz.empty:
                st.dataframe(
                    r_sr_viz[_show_cols]
                    .sort_values("Member_Count", ascending=False)
                    .rename(columns=_col_rename),
                    use_container_width=True, height=250
                )
        _show_cols_abs = [c for c in ["Ring_ID","Member_Count","Suspect_Count",
                                       "Abnormal_Count","Mean_NDRE"] if c in r_abs_viz.columns]
        with dc2:
            st.caption("**Cincin Api — NDRE Drone Absolut**")
            if not r_abs_viz.empty:
                st.dataframe(
                    r_abs_viz[_show_cols_abs]
                    .sort_values("Member_Count", ascending=False)
                    .rename(columns=_col_rename),
                    use_container_width=True, height=250
                )




# ════ TAB 3: NDRE Tren 2025→2026 (SEMENTARA DISEMBUNYIKAN) ════════
if tab3:  # tab3 = None → blok ini dilewati; hapus 'tab3 = None' di atas untuk mengaktifkan
    st.subheader("🌱 Tren NDRE 2025 → 2026 (SR Data)")
    if division == "AME IV":
        st.info("📊 **NDRE Tren** hanya tersedia untuk AME II (memerlukan data SR historis 2025+2026). "
                "AME IV belum memiliki data SR multi-tahun.")
    else:
        st.info(
            "📉 **NDRE Tren 25→26** — Tren perubahan nilai NDRE dari 2025 ke 2026 per blok berdasarkan data SR. "
            "Digunakan untuk mengidentifikasi blok yang mengalami penurunan kesehatan secara temporal "
            "sebagai sinyal peringatan dini penyebaran Cincin Api."
        )
        tren_rows = []
        for blok in blok_sel:
            sub = df_sr_all[df_sr_all.BLOK_B==blok]
            nd25 = pd.to_numeric(sub.NDRE125,  errors='coerce').mean()
            nd26 = pd.to_numeric(sub.NDRE2_26, errors='coerce').mean()
            tren_rows.append({"Blok":blok,"2025":nd25,"2026":nd26,"Delta":nd26-nd25})
        df_tren = pd.DataFrame(tren_rows)

        fig_tren = go.Figure()
        fig_tren.add_trace(go.Bar(name="NDRE 2025", x=df_tren.Blok, y=df_tren["2025"],
            marker_color="#78909C", text=df_tren["2025"].round(4), textposition="outside"))
        fig_tren.add_trace(go.Bar(name="NDRE 2026", x=df_tren.Blok, y=df_tren["2026"],
            marker_color="#42A5F5", text=df_tren["2026"].round(4), textposition="outside"))
        fig_tren.update_layout(barmode="group",
            title="NDRE Rata-Rata per Blok: 2025 vs 2026 (SR)",
            height=380, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
        st.plotly_chart(fig_tren, use_container_width=True)

        fig_delta = go.Figure(go.Bar(
            x=df_tren.Blok,
            y=df_tren.Delta,
            marker_color=["#43A047" if v>0 else "#E53935" for v in df_tren.Delta],
            text=[f"{v:+.4f}" for v in df_tren.Delta],
            textposition="outside",
        ))
        fig_delta.add_hline(y=0, line_color="white", line_dash="dash")
        fig_delta.update_layout(title="Delta NDRE (2026-2025): Hijau=Membaik, Merah=Menurun",
            height=340, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
        st.plotly_chart(fig_delta, use_container_width=True)

        # Distribusi klasifikasi SR per blok
        st.subheader("Distribusi Kelas Stres 2025 → 2026")
        klass_rows = []
        for blok in blok_sel:
            sub = df_sr_all[df_sr_all.BLOK_B==blok]
            for yr, col in [("2025","KlassNDRE12025"),("2026","KLASSNDRE2_26")]:
                vc = sub[col].str.strip().str.replace('\xa0',' ',regex=False).value_counts()
                for k,v in vc.items():
                    klass_rows.append({"Blok":blok,"Tahun":yr,"Klass":k,"Count":v})
        df_kl = pd.DataFrame(klass_rows)
        df_kl = df_kl[df_kl.Klass.isin(["Stres Sangat Berat","Stres Berat","Stres Sedang","Stres Ringan"])]
        if not df_kl.empty:
            fig_kl = px.bar(df_kl, x="Blok", y="Count", color="Klass", facet_col="Tahun",
                color_discrete_map=SR_CLR, height=400, barmode="stack",
                title="Distribusi Klasifikasi SR 2025 vs 2026")
            fig_kl.update_layout(plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
            st.plotly_chart(fig_kl, use_container_width=True)

# ════ TAB 4+5: Kesehatan Blok — Zona Drone (atas) + Detail Blok (bawah) ═════
# Bagian atas: Zona Drone — agregat lintas semua blok terpilih
with tab4:
    st.subheader(f"🌡️ Zona Kesehatan Blok — NDRE Absolut | Pohon: **{_pop_label}**")
    if not include_tbm and not include_kenth:
        st.caption("TBM dan Kenthosan dieliminasi — hanya Tanaman Menghasilkan (TM) yang diklasifikasikan.")
    else:
        _excl = []
        if not include_tbm:   _excl.append("TBM")
        if not include_kenth: _excl.append("Kenthosan")
        _incl_msg = f"Mode campuran: {_pop_label}."
        _excl_msg = f" Dikecualikan: {', '.join(_excl)}." if _excl else ""
        st.caption(_incl_msg + _excl_msg)
    zone_rows = []
    for blok in blok_sel:
        df_t = load_trees(blok, division)
        if df_t.empty: continue
        df_t_all = df_t
        df_t = apply_population_filter(df_t, include_tbm, include_kenth)
        n_tbm    = int((df_t_all.get("Classification", pd.Series()) == "TBM").sum())
        n_kenth  = int((df_t_all.get("Classification", pd.Series()) == "Kenthosan").sum())
        total = len(df_t)
        hs = "Health_Status_Abs" if "Health_Status_Abs" in df_t.columns else "Health_Status"
        vc = df_t[hs].value_counts()
        merah  = int(vc.get("Critical",0))
        oranye = int(vc.get("Sub-Optimal",0))
        kuning = int(vc.get("Moderate",0))
        hijau  = int(vc.get("Good",0))
        # SR data per blok (AME II: dari KLASSNDRE2_26 ; AME IV: tidak ada breakdown SR)
        _sr_blok = df_sr_all[df_sr_all.BLOK_B == blok] \
                   if (division == "AME II" and "BLOK_B" in df_sr_all.columns) \
                   else pd.DataFrame()
        _sr_vc = _sr_blok["KLASSNDRE2_26"].value_counts() \
                 if not _sr_blok.empty and "KLASSNDRE2_26" in _sr_blok.columns \
                 else pd.Series(dtype=int)
        zone_rows.append({
            "Blok":blok, "Merah":merah, "Oranye":oranye, "Kuning":kuning, "Hijau":hijau,
            "Total_TM":total, "TBM":n_tbm, "Kenthosan":n_kenth,
            "SR_Merah":  int(_sr_vc.get("Stres Sangat Berat", 0)),
            "SR_Oranye": int(_sr_vc.get("Stres Berat",        0)),
            "SR_Kuning": int(_sr_vc.get("Stres Sedang",       0)),
            "SR_Hijau":  int(_sr_vc.get("Stres Ringan",       0)),
            "SR_Total":  int(len(_sr_blok)),
        })
    df_zone = pd.DataFrame(zone_rows)

    # KPIs
    if not df_zone.empty:
        tot = df_zone.Total_TM.sum()
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Total Pohon TM",f"{tot:,}")
        c2.metric("🔴 Stres Sangat Berat", f"{df_zone.Merah.sum():,}")
        c3.metric("🔴 Stres Berat",        f"{df_zone.Oranye.sum():,}")
        c4.metric("🟡 Stres Sedang",       f"{df_zone.Kuning.sum():,}")
        c5.metric("🟢 Stres Ringan",       f"{df_zone.Hijau.sum():,}")

        fig_z = go.Figure()
        # Urutan: dari paling kritis ke paling sehat (stack bawah ke atas)
        # Warna konsisten dengan UNIFIED_COLORS: Merah Tua → Merah Muda → Kuning → Hijau
        for col, legend_label, clr, txt_clr in [
            ("Merah",  "Stres Sangat Berat (Kritis)", "#B71C1C", "#FFFFFF"),
            ("Oranye", "Stres Berat (Sub-Optimal)",   "#EF5350", "#FFFFFF"),
            ("Kuning", "Stres Sedang (Moderat)",       "#FDD835", "#111111"),
            ("Hijau",  "Stres Ringan",                 "#43A047", "#FFFFFF"),   # bukan 'Sehat' — konsisten SR
        ]:
            fig_z.add_trace(go.Bar(
                name=legend_label,
                x=df_zone.Blok,
                y=df_zone[col],
                marker_color=clr,
                text=df_zone[col],
                textposition="inside",
                textfont=dict(color=txt_clr, size=11, family="Arial Black"),
            ))
        fig_z.update_layout(
            barmode="stack",
            title=dict(text="4-Zona Kesehatan per Blok (NDRE Absolut)",
                       font=dict(color="#FFFFFF", size=14)),
            height=420,
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font=dict(color="#FFFFFF"),
            legend=dict(
                font=dict(color="#FFFFFF", size=12),
                bgcolor="rgba(255,255,255,0.05)",
                bordercolor="rgba(255,255,255,0.2)",
                borderwidth=1,
                traceorder="reversed",   # tampilkan Hijau di atas legend (sesuai urutan visual bar)
            ),
            xaxis=dict(
                tickfont=dict(color="#FFFFFF", size=12),
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis=dict(
                tickfont=dict(color="#FFFFFF", size=12),
                gridcolor="rgba(255,255,255,0.06)",
            ),
            margin=dict(t=55, b=30, l=40, r=20),
        )
        st.plotly_chart(fig_z, use_container_width=True)

        # ── Perbandingan SR 2026 — chart kedua (AME II saja) ───────────
        if division == "AME II" and df_zone["SR_Total"].sum() > 0:
            fig_sr_z = go.Figure()
            for col_sr, lbl_sr, clr_sr, txt_sr in [
                ("SR_Merah",  "Stres Sangat Berat (SR 2026)", "#B71C1C", "#FFFFFF"),
                ("SR_Oranye", "Stres Berat (SR 2026)",         "#EF5350", "#FFFFFF"),
                ("SR_Kuning", "Stres Sedang (SR 2026)",         "#FDD835", "#111111"),
                ("SR_Hijau",  "Stres Ringan (SR 2026)",         "#43A047", "#FFFFFF"),
            ]:
                fig_sr_z.add_trace(go.Bar(
                    name=lbl_sr, x=df_zone.Blok, y=df_zone[col_sr],
                    marker_color=clr_sr, text=df_zone[col_sr],
                    textposition="inside",
                    textfont=dict(color=txt_sr, size=11, family="Arial Black"),
                ))
            fig_sr_z.update_layout(
                barmode="stack",
                title=dict(text="4-Zona Kesehatan per Blok (Data SR 2026)",
                           font=dict(color="#FFFFFF", size=14)),
                height=380, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
                font=dict(color="#FFFFFF"),
                legend=dict(font=dict(color="#FFFFFF", size=12),
                            bgcolor="rgba(255,255,255,0.05)",
                            bordercolor="rgba(255,255,255,0.2)", borderwidth=1,
                            traceorder="reversed"),
                xaxis=dict(tickfont=dict(color="#FFFFFF", size=12), gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(tickfont=dict(color="#FFFFFF", size=12), gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(t=55, b=30, l=40, r=20),
            )
            st.plotly_chart(fig_sr_z, use_container_width=True)
        elif division == "AME IV":
            st.caption("⚠️ Data SR per blok tidak tersedia untuk AME IV — perbandingan chart hanya tersedia untuk AME II.")


# Label & warna SERAGAM untuk SR dan Drone agar mudah compare
UNIFIED_LABELS = ["Stres Sangat Berat","Stres Berat","Stres Sedang","Stres Ringan"]
UNIFIED_COLORS = ["#B71C1C","#EF5350","#FFA726","#66BB6A"]
UNIFIED_CLR    = dict(zip(UNIFIED_LABELS, UNIFIED_COLORS))
DRONE_ABS_TO_UNIFIED = {"Critical":"Stres Sangat Berat","Sub-Optimal":"Stres Berat",
                         "Moderate":"Stres Sedang","Good":"Stres Ringan"}
DRONE_REL_TO_UNIFIED = {"Suspect":"Stres Sangat Berat","Abnormal":"Stres Berat",
                         "Normal":"Stres Sedang","Healthy":"Stres Ringan"}

# ════ Bagian bawah: Detail per Blok tunggal (masih di tab4/tab5 yang sama) ════
with tab5:
    st.divider()
    st.subheader("🗺️ Detail per Blok — Perbandingan SR vs Drone")
    sel = st.selectbox("Pilih Blok", blok_sel)

    df_t_raw = load_trees(sel, division)
    df_t     = apply_population_filter(df_t_raw, include_tbm, include_kenth)
    n_tbm   = int((df_t_raw.get("Classification", pd.Series()) == "TBM").sum())
    n_kenth = int((df_t_raw.get("Classification", pd.Series()) == "Kenthosan").sum())

    # SR data — AME II: dari Excel, AME IV: dari SR reference config
    if division == "AME II":
        df_sr = df_sr_all[df_sr_all.BLOK_B==sel].copy()
        df_sr['NDRE2_26']   = pd.to_numeric(df_sr['NDRE2_26'], errors='coerce')
        df_sr['klass_norm'] = df_sr.KLASSNDRE2_26.str.strip().str.replace('\xa0',' ',regex=False)
        r_sr  = load_rings(sel, "sr_2026_input")
        r_rel = load_rings(sel, "relative")
        r_abs = load_rings(sel, "absolute")
        df_j  = load_joined(sel)
    else:
        df_sr = pd.DataFrame()
        r_sr  = pd.DataFrame()
        r_rel = pd.DataFrame()
        r_abs = pd.DataFrame()
        df_j  = pd.DataFrame()

    # ── Distribusi Statistik Populasi per-Blok ───────────────────
    st.markdown("### 📊 Distribusi Populasi Drone — " + sel)
    _n_tm    = int((df_t_raw.get("Classification", pd.Series()) == "TM").sum())
    _n_tbm   = int((df_t_raw.get("Classification", pd.Series()) == "TBM").sum())
    _n_kenth = int((df_t_raw.get("Classification", pd.Series()) == "Kenthosan").sum())
    _n_total = len(df_t_raw)
    # SPH estimasi dari GPS bbox (hektar = lat_m × lon_m / 10000)
    _sph_est = 0
    if not df_t_raw.empty and "Latitude" in df_t_raw.columns:
        _lat_m = (df_t_raw["Latitude"].max()  - df_t_raw["Latitude"].min())  * 111111.0
        _lon_m = (df_t_raw["Longitude"].max() - df_t_raw["Longitude"].min()) \
                 * 111111.0 * np.cos(np.radians(df_t_raw["Latitude"].mean()))
        _area_ha = max((_lat_m * _lon_m) / 10000, 0.01)
        _sph_est = round(_n_tm / _area_ha, 1)
    # SPH SR
    if division == "AME II":
        _sr_row  = df_sum[df_sum.Blok == sel] if not df_sum.empty else pd.DataFrame()
        _sph_sr  = float(_sr_row.SPH_SR.values[0])  if not _sr_row.empty else 0
        _ndre_sr = float(_sr_row.NDRE_SR_2026.values[0]) if not _sr_row.empty and "NDRE_SR_2026" in _sr_row.columns else \
                   float(pd.to_numeric(df_sr["NDRE2_26"], errors="coerce").mean()) if not df_sr.empty else 0
    else:
        _sr_ref_n = SR_REF_AME4.get(sel, 0)
        _area_ref = AREA_AME4.get(sel, 1)
        _sph_sr   = round(_sr_ref_n / _area_ref, 1) if _area_ref else 0
        _ndre_sr  = 0
    sp1, sp2, sp3, sp4, sp5, sp6 = st.columns(6)
    sp1.metric("🌿 TM (Drone)",       f"{_n_tm:,}")
    sp2.metric("🌱 TBM (Drone)",      f"{_n_tbm:,}")
    sp3.metric("🍃 Kenthosan",        f"{_n_kenth:,}")
    sp4.metric("📦 Total Deteksi",    f"{_n_total:,}")
    sp5.metric("📐 SPH Drone (est.)", f"{_sph_est:,}")
    sp6.metric("📐 SPH SR",           f"{_sph_sr:.0f}" if _sph_sr else "—")
    st.divider()

    # ── 3 DONUT — label & warna seragam ─────────────────────────
    st.markdown("### Distribusi Klasifikasi Kesehatan — Label & Warna Seragam")
    _drone_info = f"🌿 Drone: **{len(df_t):,} pohon ({_pop_label})**"
    if not include_tbm:   _drone_info += f" | ⛔ TBM: {n_tbm}"
    if not include_kenth: _drone_info += f" | ⛔ Kenthosan: {n_kenth}"
    _drone_info += f" (total deteksi: {len(df_t_raw):,}). SR: semua Pokok Utama."
    st.info(_drone_info)

    def make_donut(title, vc_unified, n_total):
        vals = [int(vc_unified.get(lbl, 0)) for lbl in UNIFIED_LABELS]
        custom = [f"{lbl}<br>{v:,} pohon ({v/n_total*100:.1f}%)" if n_total else lbl
                  for lbl, v in zip(UNIFIED_LABELS, vals)]
        fig = go.Figure(go.Pie(
            labels=UNIFIED_LABELS, values=vals,
            marker=dict(colors=UNIFIED_COLORS, line=dict(color="#0E1117", width=2)),
            hole=0.52, textinfo="percent",
            textfont=dict(color="#FFFFFF", size=13),
            hovertext=custom, hoverinfo="text",
            sort=False, direction="clockwise",
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, color="#FFFFFF")),
            height=310, margin=dict(t=50,b=10,l=10,r=10),
            legend=dict(font=dict(size=11, color="#FFFFFF"), bgcolor="rgba(0,0,0,0)", orientation="v"),
            plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="#FFFFFF",
            annotations=[dict(text=f"<b>{n_total:,}</b><br>pohon",
                              x=0.5, y=0.5, showarrow=False,
                              font=dict(size=13, color="#FFFFFF"))]
        )
        return fig

    # ── SR donut: KLASSNDRE2_26 (threshold absolut) — konsisten dg SR bar chart ──
    vc_sr_u = {}
    if not df_sr.empty and "KLASSNDRE2_26" in df_sr.columns:
        vc_sr_u = df_sr["KLASSNDRE2_26"].value_counts().to_dict()



    vc_rel_u = {}
    if not df_t.empty and "Health_Status" in df_t.columns:
        vc_rel_u = df_t["Health_Status"].map(DRONE_REL_TO_UNIFIED).value_counts().to_dict()

    vc_abs_u = {}
    if not df_t.empty and "Health_Status_Abs" in df_t.columns:
        vc_abs_u = df_t["Health_Status_Abs"].map(DRONE_ABS_TO_UNIFIED).value_counts().to_dict()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(make_donut(f"🌿 Data SR 2026", vc_sr_u, len(df_sr)), use_container_width=True)
    with c2:
        st.plotly_chart(make_donut(f"🔵 NDRE Drone Relatif", vc_rel_u, len(df_t)), use_container_width=True)
    with c3:
        st.plotly_chart(make_donut(f"🟢 NDRE Drone Absolut", vc_abs_u, len(df_t)), use_container_width=True)

    # ── Populasi Blok Terpilih — Drone vs SR (Chart) ───────────────
    st.markdown(f"#### 🌴 Populasi Blok **{sel}** — Drone vs SR 2026")
    _sr_total = len(df_sr) if not df_sr.empty else 0
    # Breakdown SR dari kolom Ket:
    #   Pokok Utama → TM | Sisip*/Tamb → TBM setara | Mati* → pohon mati
    _sr_tm = _sr_tbm_sr = _sr_mati = 0
    if not df_sr.empty and "Ket" in df_sr.columns:
        _vc_ket  = df_sr["Ket"].str.strip().value_counts()
        _sr_tm   = int(_vc_ket.get("Pokok Utama", 0))
        _sr_tbm_sr = int(sum(v for k, v in _vc_ket.items()
                             if "sisip" in k.lower() or k.strip() == "Tamb"))
        _sr_mati = int(sum(v for k, v in _vc_ket.items()
                           if "mati" in k.lower()))
    else:
        _sr_tm = _sr_total

    _kategori = ["TM (Pokok Utama)", "TBM (Sisip/Tambahan)", "Kenthosan", "Pohon Mati"]
    _drone_vals = [_n_tm,     _n_tbm,    _n_kenth, 0        ]
    _sr_vals    = [_sr_tm,    _sr_tbm_sr, 0,       _sr_mati ]

    fig_pop = go.Figure()
    fig_pop.add_trace(go.Bar(
        name=f"🛸 Drone ({sel})",
        x=_kategori, y=_drone_vals,
        marker_color="#42A5F5",
        text=_drone_vals,
        textposition="outside",
        textfont=dict(color="#FFFFFF", size=12, family="Arial Black"),
    ))
    fig_pop.add_trace(go.Bar(
        name="📋 SR 2026",
        x=_kategori, y=_sr_vals,
        marker_color="#8D6E63",
        text=_sr_vals,
        textposition="outside",
        textfont=dict(color="#FFFFFF", size=12, family="Arial Black"),
    ))
    fig_pop.update_layout(
        barmode="group",
        title=dict(text=f"Komposisi Populasi — {sel}  (Drone vs SR 2026)",
                   font=dict(color="#FFFFFF", size=14)),
        height=360,
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font=dict(color="#FFFFFF"),
        legend=dict(font=dict(color="#FFFFFF", size=12),
                    bgcolor="rgba(255,255,255,0.05)",
                    bordercolor="rgba(255,255,255,0.2)", borderwidth=1),
        xaxis=dict(tickfont=dict(color="#FFFFFF", size=12),
                   gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(tickfont=dict(color="#FFFFFF", size=12),
                   gridcolor="rgba(255,255,255,0.06)"),
        margin=dict(t=55, b=30, l=40, r=20),
    )
    st.plotly_chart(fig_pop, use_container_width=True)
    if division == "AME II":
        st.caption(
            "ℹ️ TBM Drone = 0 adalah valid: AME II vintage 2011–2013 (13–15 th) — "
            "tidak ada TBM nyata. TBM awal merupakan artefak nDSM (DTM compression) "
            "dan telah direklasifikasi → TM. Sisip Des25 (SR) berumur ±5 bln, "
            "kanopi terlalu kecil untuk dideteksi sebagai crown individual."
        )


    # ── Bar 3 sumber per kelas ───────────────────────────────────
    st.markdown("### Jumlah Pohon per Kelas — 3 Sumber Side-by-Side")
    bar_rows = [{"Kelas":lbl,
                 "Data SR 2026":int(vc_sr_u.get(lbl,0)),
                 "NDRE Drone Relatif":int(vc_rel_u.get(lbl,0)),
                 "NDRE Drone Absolut":int(vc_abs_u.get(lbl,0))}
                for lbl in UNIFIED_LABELS]
    df_bar = pd.DataFrame(bar_rows)
    fig_bar3 = go.Figure()
    for src, clr_src in [("Data SR 2026","#8D6E63"),("NDRE Drone Relatif","#42A5F5"),("NDRE Drone Absolut","#66BB6A")]:
        fig_bar3.add_trace(go.Bar(name=src, x=df_bar["Kelas"], y=df_bar[src],
            marker_color=clr_src, text=df_bar[src], textposition="outside"))
    fig_bar3.update_layout(barmode="group",
        title=f"Perbandingan 3 Sumber per Kelas — {sel}",
        xaxis=dict(categoryorder="array", categoryarray=UNIFIED_LABELS),
        legend=dict(font_color="white", bgcolor="rgba(0,0,0,0)"),
        height=380, plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
    st.plotly_chart(fig_bar3, use_container_width=True)

