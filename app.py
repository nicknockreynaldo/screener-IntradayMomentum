import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN & SIDEBAR INTERAKTIF MULTI-FILTER
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")
st.write("Atur parameter filter tren besar (Daily) dan eksekusi (Intraday) pada panel sebelah kiri.")

st.sidebar.header("⚙️ Parameter Sensor")

# --- FILTER 1: FILTER TREN UTAMA (DAILY MA 10) ---
FILTER_DAILY_MA10 = st.sidebar.selectbox(
    "1. Filter Tren Besar (Daily MA 10)",
    options=[
        "Power Play Uptrend",
        "Flexible"
    ],
    index=0
)

# --- FILTER 2: TIMEFRAME EKSEKUSI ---
TF_PILIHAN = st.sidebar.selectbox(
    "2. Pilih Timeframe Eksekusi",
    options=["1 Jam (1H)", "Harian (Daily)"],
    index=0
)

if TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"
    label_tf = "1H"
else:
    interval_param = "1d"
    period_param = "1y"
    label_tf = "Daily"

# --- FILTER 3: PERIODE MA KUSTOM (DIUBAH JADI DROPDOWN FIXED SAKRAL) ---
MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=3  # Default otomatis mengarah ke MA 50 (pilihan ke-4)
)

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Mulai Pemindaian Massal", use_container_width=True)

# Menampilkan status filter aktif di dashboard utama
st.info(f"📋 **Kondisi Aktif:** Harga Terakhir harus berada di atas **SMA {MA_PERIODE} ({label_tf})** | Mode Tren: **{FILTER_DAILY_MA10}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (DUAL INTERVAL DOWNLOAD)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Mengunduh dan menyinkronkan data pasar multi-timeframe..."):
        try:
            # Ambil database dari Google Sheets (Kolom A)
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])
            
            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()
            
            watchlist = []
            for kode in watchlist_raw:
                if kode.isalpha() and len(kode) == 4 and kode != 'QUOTE':
                    watchlist.append(kode + ".JK")
            
            if not watchlist:
                st.error("Gagal mendeteksi kode saham yang valid di Google Sheets Anda.")
                st.stop()
                
            st.write(f"🔍 Memproses data untuk **{len(watchlist)} saham**...")
            
            # --- DOWNLOAD DATA 1: DATA DAILY UTK FILTER TREN ---
            data_daily_bulk = yf.download(watchlist, period="3mo", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            # --- DOWNLOAD DATA 2: DATA EKSEKUSI (Bisa 1H / Daily) ---
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            
            # Perulangan analisa di memori
            for ticker in watchlist:
                try:
