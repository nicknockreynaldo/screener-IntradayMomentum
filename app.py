import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN & SIDEBAR INTERAKTIF LEAN & CLEAN
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")
st.write("Saring momentum saham andalan Anda berdasarkan kombinasi Timeframe, Moving Average, dan pergerakan Intraday.")

st.sidebar.header("⚙️ Parameter Sensor")

# --- DROPDOWN 1: FILTER INTRADAY MOMENTUM VS OPEN ---
FILTER_INTRADAY = st.sidebar.selectbox(
    "1. Filter Pergerakan Hari Ini (Vs Open)",
    options=[
        "Intraday Momentum (>0%)",
        "General"
    ],
    index=0,
    help="Intraday Momentum (>0%): Wajib lebih tinggi dari harga Open hari ini (Candle Hijau). General: Bebas mencakup semua saham."
)

# --- DROPDOWN 2: TIMEFRAME EKSEKUSI (REVISI: URUTAN DIMULAI DARI DAILY) ---
TF_PILIHAN = st.sidebar.selectbox(
    "2. Pilih Timeframe Eksekusi",
    options=["Harian (Daily)", "1 Jam (1H)", "15 Menit (15m)", "5 Menit (5m)"],
    index=0  # Default otomatis diarahkan ke Harian (Daily)
)

# Logika penyesuaian period & interval secara dinamis agar aman dari rate-limit
if TF_PILIHAN == "Harian (Daily)":
    interval_param = "1d"
    period_param = "2y"       # 2 tahun data harian (Wajib untuk mengamankan SMA 200)
    label_tf = "Daily"
elif TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"      # 1 bulan data untuk timeframe 1 jam
    label_tf = "1H"
elif TF_PILIHAN == "15 Menit (15m)":
    interval_param = "15m"
    period_param = "7d"       # 7 hari data untuk timeframe 15 menit
    label_tf = "15m"
else:  # 5 Menit (5m)
    interval_param = "5m"
    period_param = "5d"       # 5 hari data menit aman & melimpah untuk SMA 50
    label_tf = "5m"

# --- DROPDOWN 3: PERIODE MA KUSTOM SAKRAL ---
MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=3  # Default otomatis mengarah ke MA 50
)

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

# REVISI: Mengubah teks tombol menjadi "Start Screening"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

# Menampilkan status filter aktif di dashboard utama
st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Filter Intraday: **{FILTER_INTRADAY}**")
