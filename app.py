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

# --- DROPDOWN 2: TIMEFRAME EKSEKUSI ---
TF_PILIHAN = st.sidebar.selectbox(
    "2. Pilih Timeframe Eksekusi",
    options=["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"],
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
elif TF_PILIHAN == "30 Menit (30m)":
    interval_param = "30m"
    period_param = "7d"       # 7 hari data untuk timeframe 30 menit
    label_tf = "30m"
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

# Tombol "Start Screening"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

# Menampilkan status filter aktif di dashboard utama
st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Filter Intraday: **{FILTER_INTRADAY}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (DYNAMIC BULK DOWNLOAD ROUTINE)
# ==============================================================================
if MULAI_SCAN:
    # Validasi Pengaman Khusus
    if interval_param in ["5m", "15m", "30m"] and MA_PERIODE == 200:
        st.error(f"❌ Batasan Teknis: SMA 200 terlalu besar untuk Timeframe {TF_PILIHAN} pada mode unduh cepat. Silakan gunakan maksimal SMA 50 untuk timeframe menit ini, atau pindah ke timeframe 1 Jam / Daily jika ingin memakai SMA 200.")
        st.stop()

    with st.spinner("Mengunduh data pasar massal secara instan..."):
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
            
            # --- DOWNLOAD DATA DAILY ---
            data_daily_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "5d", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            # --- DOWNLOAD DATA EKSEKUSI ---
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            
            # Perulangan analisa di memori
            for ticker in watchlist
