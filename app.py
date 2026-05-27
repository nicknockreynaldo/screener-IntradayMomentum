import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import time

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

# --- DROPDOWN 3: PERIODE MA KUSTOM SAKRAL ---
MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=3  # Default otomatis mengarah ke MA 50
)

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Mulai Pemindaian Massal", use_container_width=True)

# Menampilkan status filter aktif di dashboard utama
st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Filter Intraday: **{FILTER_INTRADAY}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (METODE LOOP INDIVIDUAL AMAN)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Mengunduh dan memproses data pasar secara presisi..."):
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
                
            progress_bar = st.progress(0)
            status_text = st.empty()
            hasil_screener = []
            
            # Perulangan download individual untuk menjamin struktur kolom 1D datar murni
            for i, ticker in enumerate(watchlist):
                clean_ticker = ticker.replace(".JK", "")
                status_text.text(f"📥 Memproses ({i+1}/{len(watchlist)}): {clean_ticker}")
                progress_bar.progress((i + 1) / len(watchlist))
                
                try:
                    # Download data harian murni khusus ticker ini (untuk ambil Open harian)
                    df_d = yf.download(ticker, period="3mo", interval="1d", auto_adjust=False, progress=False)
                    
                    if df_d.empty:
                        continue
                        
                    # Handle jika yfinance mengembalikan multi-index kolom meskipun single download
                    if isinstance(df_d.columns, pd.MultiIndex):
                        df_d.columns = df_d.columns.get_level_values(0)
                        
                    # Download data eksekusi khusus ticker ini
                    if interval_param == "1d":
                        df_e = df_d.copy()
                    else:
                        df_e = yf.download(ticker, period=period_param, interval=interval_param, auto_adjust=False, progress=False)
                        if isinstance(df_e.columns, pd.MultiIndex):
                            df_e.columns = df_e.columns.get_level_values(0)
                            
                    if df_e.empty:
                        continue
                    
                    # Ambil list harga close eksekusi secara aman
                    kolom_close_e = 'Close' if 'Close' in df_e.columns else 'Adj Close'
                    close_exec_series = df_e[kolom_close_e].dropna()
                    
                    if close_exec_series.empty:
                        continue
                        
                    # Dapatkan harga berjalan detik ini (mengonversi ke float murni)
                    harga_terakhir = float(close_exec_series.values[-1])
                    
                    # --- 1. LOGIKA FILTER INTRADAY MOMENTUM VS OPEN ---
                    if FILTER_INTRADAY == "Intraday Momentum (>0%)":
                        if 'Open' in df_d.columns:
                            open_series = df_d['Open'].dropna()
                            if not open_series.empty:
                                open_hari_ini = float(open_series.values[-1])
                                if harga_terakhir < open_hari_ini:
                                    continue  # Lewati jika candle hari ini berwarna merah
                                    
                    # --- 2. LOGIKA FILTER UTAMA MOVING AVERAGE ---
                    if len(close_exec_series) >= MA_PERIODE:
                        # Hitung SMA bergulir
                        ma_series = close_exec_series.rolling(window=MA_PERIODE).mean()
                        nilai_ma_exec = float(ma_series.values[-1])
                        
                        # Aturan sakral: Harga terakhir harus di atas nilai SMA
                        if harga_terakhir > nilai_ma_exec:
                            jarak_persen = ((harga_terakhir - nilai_ma_exec) / nilai_ma_exec) * 100
                            
                            hasil_screener.append({
                                "Kode Saham": clean_ticker,
                                "Harga Terakhir": round(harga_terakhir, 2),
                                f"Nilai SMA {MA_PERIODE}": round(nilai_ma_exec, 2),
                                f"Jarak di Atas SMA{MA_PERIODE}": round(jarak_persen, 2)
                            })
                except:
                    pass
                    
                # Jeda mikro agar terhindar dari pemblokiran server
                time.sleep(0.1)
                
            # Bersihkan teks indikator loading loop
            status_text.empty()
            progress_bar.empty()
            
            # ==============================================================================
            # 3. OUTPUT TABEL HASIL SINKRONISASI
            # ==============================================================================
            st.success("🎯 Pemindaian Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                sort_column = f"Jarak di Atas SMA{MA_PERIODE}"
                df_hasil = df_hasil.sort_values(by=sort_column, ascending=True)
                
                df_hasil[sort_column] = df_hasil[sort_column].apply(lambda x: f"+{x}%")
                
                st.metric(label="Saham Lolos Kriteria", value=f"{len(df_hasil)} Saham")
                st.dataframe(df_hasil, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada saham dari database Anda yang memenuhi kriteria di atas.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis utama: {e}")
