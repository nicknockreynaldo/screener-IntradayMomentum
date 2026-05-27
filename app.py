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
    options=["1 Jam (1H)", "Harian (Daily)"],
    index=0
)

if TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"
    label_tf = "1H"
else:
    interval_param = "1d"
    period_param = "2y"  # Rentang data aman untuk kalkulasi SMA 200
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
# 2. LOGIKA UTAMA SCREENER (FAST BULK DOWNLOAD)
# ==============================================================================
if MULAI_SCAN:
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
            
            # --- DOWNLOAD DATA DAILY 2 TAHUN ---
            data_daily_bulk = yf.download(watchlist, period="2y", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            # --- DOWNLOAD DATA EKSEKUSI ---
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            
            # Perulangan analisa di memori
            for ticker in watchlist:
                try:
                    if len(watchlist) == 1:
                        df_d = data_daily_bulk.copy()
                        df_e = data_exec_bulk.copy()
                    else:
                        df_d = data_daily_bulk[ticker].copy()
                        df_e = data_exec_bulk[ticker].copy()
                        
                    # Dapatkan Harga Terakhir dari data eksekusi
                    kolom_close_e = 'Close' if 'Close' in df_e.columns else 'Adj Close'
                    close_exec = df_e[kolom_close_e].dropna().squeeze()
                    
                    if close_exec.empty:
                        continue
                    harga_terakhir = float(close_exec.iloc[-1])
                    
                    # --- 1. LOGIKA FILTER INTRADAY MOMENTUM VS OPEN ---
                    if FILTER_INTRADAY == "Intraday Momentum (>0%)":
                        if 'Open' in df_d.columns:
                            open_series = df_d['Open'].dropna().squeeze()
                            if not open_series.empty:
                                open_hari_ini = float(open_series.iloc[-1])
                                if harga_terakhir < open_hari_ini:
                                    continue  # Skip candle merah
                                
                    # --- 2. LOGIKA FILTER UTAMA MOVING AVERAGE ---
                    if len(close_exec) >= MA_PERIODE:
                        ma_exec_series = close_exec.rolling(window=MA_PERIODE).mean()
                        nilai_ma_exec = float(ma_exec_series.iloc[-1])
                        
                        if harga_terakhir > nilai_ma_exec:
                            jarak_persen = ((harga_terakhir - nilai_ma_exec) / nilai_ma_exec) * 100
                            clean_ticker = ticker.replace(".JK", "")
                                    
                            hasil_screener.append({
                                "Kode Saham": clean_ticker,
                                "Harga Terakhir": int(harga_terakhir),
                                f"Nilai SMA {MA_PERIODE}": round(nilai_ma_exec, 2),
                                "Jarak (%)": round(jarak_persen, 2)  # Disimpan sebagai float murni agar sorting angka akurat
                            })
                except:
                    pass
                    
            # ==============================================================================
            # 3. OUTPUT INTERAKTIF (BISA DI-SORTING & PAS DILAYAR)
            # ==============================================================================
            st.success("🎯 Pemindaian Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                
                # Default urutan awal saat pertama load: Urutkan berdasarkan Kode Saham dari A ke Z
                df_hasil = df_hasil.sort_values(by="Kode Saham", ascending=True)
                
                st.metric(label="Saham Lolos Kriteria", value=f"{len(df_hasil)} Saham")
                
                # Tampilkan tabel interaktif yang dipaksa lebar penuh tanpa scrollbar horizontal
                st.dataframe(
                    df_hasil,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Jarak (%)": st.column_config.NumberColumn(
                            "Jarak (%)",
                            format="+%.2f%%"  # Memasang logo plus dan persen secara visual saja tanpa merusak sistem angka sorting
                        )
                    }
                )
            else:
                st.warning("Tidak ada saham dari database Anda yang memenuhi kriteria di atas.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis utama: {e}")
