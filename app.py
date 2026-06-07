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
    options=["Intraday Momentum (>0%)", "General"],
    index=0,
    help="Intraday Momentum (>0%): Wajib lebih tinggi dari harga Open hari ini (Candle Hijau). General: Bebas mencakup semua saham."
)

# --- DROPDOWN 2: TIMEFRAME EKSEKUSI ---
TF_PILIHAN = st.sidebar.selectbox(
    "2. Pilih Timeframe Eksekusi",
    options=["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"],
    index=0
)

if TF_PILIHAN == "Harian (Daily)":
    interval_param = "1d"
    period_param = "2y"
    label_tf = "Daily"
elif TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"
    label_tf = "1H"
elif TF_PILIHAN == "30 Menit (30m)":
    interval_param = "30m"
    period_param = "7d"
    label_tf = "30m"
elif TF_PILIHAN == "15 Menit (15m)":
    interval_param = "15m"
    period_param = "7d"
    label_tf = "15m"
else:
    interval_param = "5m"
    period_param = "5d"
    label_tf = "5m"

# --- DROPDOWN 3: PERIODE MA KUSTOM ---
MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=3
)

# --- DROPDOWN 4: FILTER TREN UTAMA ---
FILTER_TREND = st.sidebar.selectbox(
    "4. Filter Tren Utama (Akselerasi)",
    options=["General", "Power Play Uptrend (Price > DMA 10)"],
    index=0,
    help="Power Play Uptrend: Wajib mengunci harga terakhir di atas Daily MA 10. General: Tanpa batasan DMA 10."
)

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Intraday: **{FILTER_INTRADAY}** | Tren: **{FILTER_TREND}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (MURNI SINKRON SHEETS)
# ==============================================================================
if MULAI_SCAN:
    if interval_param in ["5m", "15m", "30m"] and MA_PERIODE == 200:
        st.error(f"❌ Batasan Teknis: SMA 200 terlalu besar untuk Timeframe {TF_PILIHAN}. Gunakan maksimal SMA 50 untuk timeframe menit.")
        st.stop()

    with st.spinner("Mengunduh data pasar massal secara instan..."):
        try:
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
            
            data_daily_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "3mo", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengunduh data: {e}")
            st.stop()

        # Perulangan analisa saham (Simpel & Straightforward)
        for ticker in watchlist:
            try:
                if len(watchlist) == 1:
                    df_d = data_daily_bulk.copy()
                    df_e = data_exec_bulk.copy()
                else:
                    df_d = data_daily_bulk[ticker].copy()
                    df_e = data_exec_bulk[ticker].copy()
                    
                kolom_close_e = 'Close' if 'Close' in df_e.columns else 'Adj Close'
                df_e = df_e.dropna(subset=[kolom_close_e])
                close_exec = df_e[kolom_close_e].squeeze()
                
                if df_e.empty or len(close_exec) < MA_PERIODE:
                    continue
                    
                harga_terakhir = float(close_exec.iloc[-1])
                
                # --- FILTER 1: POWER PLAY UPTREND (PRICE > DMA 10) ---
                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)":
                    kolom_close_d = 'Close' if 'Close' in df_d.columns else 'Adj Close'
                    df_d = df_d.dropna(subset=[kolom_close_d])
                    close_daily = df_d[kolom_close_d].squeeze()
                    
                    if len(close_daily) >= 10:
                        dma_10_series = close_daily.rolling(window=10).mean()
                        nilai_dma_10 = float(dma_10_series.iloc[-1])
                        if harga_terakhir < nilai_dma_10:
                            continue
                    else:
                        continue
                
                # Ekstrak Harga Open Harian untuk filter intraday
                if 'Open' in df_d.columns:
                    open_series = df_d['Open'].dropna().squeeze()
                    if not open_series.empty:
                        open_hari_ini = float(open_series.iloc[-1])
                    else:
                        continue
                else:
                    continue
                
                # --- FILTER 2: INTRADAY MOMENTUM ---
                if FILTER_INTRADAY == "Intraday Momentum (>0%)":
                    if harga_terakhir < open_hari_ini:
                        continue
                            
                # --- FILTER 3: UTAMA MOVING AVERAGE ---
                ma_exec_series = close_exec.rolling(window=MA_PERIODE).mean()
                nilai_ma_exec = float(ma_exec_series.iloc[-1])
                
                # Kondisi Mutlak: Harga wajib di atas MA pilihan
                if harga_terakhir > nilai_ma_exec:
                    jarak_persen = ((harga_terakhir - nilai_ma_exec) / nilai_ma_exec) * 100
                    clean_ticker = ticker.replace(".JK", "")
                    persen_change = ((harga_terakhir - open_hari_ini) / open_hari_ini) * 100
                    
                    hasil_screener.append({
                        "Kode Saham": clean_ticker,
                        "% Change": persen_change,
                        "Jarak (%)": round(jarak_persen, 2),
                        "Status": "🟢 BULLISH"
                    })
            except:
                pass

        # ==============================================================================
        # 3. OUTPUT INTERAKTIF FULL WIDTH
        # ==============================================================================
        st.success("🎯 Pemindaian Selesai!")
        
        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            df_hasil = df_hasil.sort_values(by=["Kode Saham"], ascending=True)
            
            st.metric(label="Saham Lolos Kriteria", value=f"{len(df_hasil)} Saham")
            
            st.dataframe(
                df_hasil,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                    "Jarak (%)": st.column_config.NumberColumn("Jarak (%)", format="+%.2f%%")
                }
            )
        else:
            st.warning("Tidak ada saham dari database Anda yang memenuhi kriteria di atas.")
