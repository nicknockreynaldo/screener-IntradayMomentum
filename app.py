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

FILTER_INTRADAY = st.sidebar.selectbox(
    "1. Filter Pergerakan Hari Ini (Vs Open)",
    options=["Intraday Momentum (>0%)", "General"],
    index=0,
    help="Intraday Momentum (>0%): Wajib lebih tinggi dari harga Open hari ini (Candle Hijau). General: Bebas mencakup semua saham."
)

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

MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=3
)

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Filter Intraday: **{FILTER_INTRADAY}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (DYNAMIC BULK DOWNLOAD ROUTINE)
# ==============================================================================
if MULAI_SCAN:
    if interval_param in ["5m", "15m", "30m"] and MA_PERIODE == 200:
        st.error(f"❌ Batasan Teknis: SMA 200 terlalu besar untuk Timeframe {TF_PILIHAN} pada mode unduh cepat. Silakan gunakan maksimal SMA 50 untuk timeframe menit ini, atau pindah ke timeframe 1 Jam / Daily jika ingin memakai SMA 200.")
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
            
            data_daily_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "5d", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            
            for ticker in watchlist:
                try:
                    if len(watchlist) == 1:
                        df_d = data_daily_bulk.copy()
                        df_e = data_exec_bulk.copy()
                    else:
                        df_d = data_daily_bulk[ticker].copy()
                        df_e = data_exec_bulk[ticker].copy()
                        
                    kolom_close_e = 'Close' if 'Close' in df_e.columns else 'Adj Close'
                    df_e = df_e.dropna(subset=[kolom_close_e, 'Open', 'High', 'Low'])
                    close_exec = df_e[kolom_close_e].squeeze()
                    
                    if df_e.empty or len(close_exec) < MA_PERIODE:
                        continue
                        
                    harga_terakhir = float(close_exec.iloc[-1])
                    
                    if 'Open' in df_d.columns:
                        open_series = df_d['Open'].dropna().squeeze()
                        if not open_series.empty:
                            open_hari_ini = float(open_series.iloc[-1])
                        else:
                            continue
                    else:
                        continue
                    
                    if FILTER_INTRADAY == "Intraday Momentum (>0%)":
                        if harga_terakhir < open_hari_ini:
                            continue
                                
                    ma_exec_series = close_exec.rolling(window=MA_PERIODE).mean()
                    df_e['MA_Dynamic'] = ma_exec_series
                    nilai_ma_exec = float(ma_exec_series.iloc[-1])
                    
                    if harga_terakhir > nilai_ma_exec:
                        jarak_persen = ((harga_terakhir - nilai_ma_exec) / nilai_ma_exec) * 100
                        clean_ticker = ticker.replace(".JK", "")
                        persen_change = ((harga_terakhir - open_hari_ini) / open_hari_ini) * 100
                        
                        low_2_lalu = float(df_e['Low'].iloc[-3])
                        ma_2_lalu = float(df_e['MA_Dynamic'].iloc[-3])
                        high_1_lalu = float(df_e['High'].iloc[-2])
                        
                        if low_2_lalu <= ma_2_lalu and harga_terakhir > high_1_lalu:
                            status = "🟢 NEW"
                        else:
                            status = "🔵 HOLD"
                                
                        hasil_screener.append({
                            "Kode Saham": clean_ticker,
                            "% Change": persen_change,
                            "Jarak (%)": round(jarak_persen, 2),
                            "Status": status
                        })
                except:
                    pass
                    
            # ==============================================================================
            # 3. OUTPUT INTERAKTIF FULL WIDTH (SORT BY STATUS NEW TERATAS)
            # ==============================================================================
            st.success("🎯 Pemindaian Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                
                df_hasil['is_new']
