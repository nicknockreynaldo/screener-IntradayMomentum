import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN & INRESIALISASI SESSION STATE (MEMORI SCREENER)
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")
st.write("Saring momentum saham andalan Anda berdasarkan kombinasi Timeframe, Moving Average, dan pergerakan Intraday.")

# Mengunci memori lintas klik berdasarkan input filter apa pun yang dipilih di sidebar
if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Sensor")

# --- DROPDOWN 1: FILTER INTRADAY MOMENTUM VS OPEN ---
FILTER_INTRADAY = st.sidebar.selectbox(
    "1. Filter Pergerakan Hari Ini (Vs Open)",
    options=["Intraday Momentum (>0%)", "General"],
    index=0
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
    index=3  # Default ke MA 50
)

# --- DROPDOWN 4: FILTER TREN UTAMA ---
FILTER_TREND = st.sidebar.selectbox(
    "4. Filter Tren Utama (Akselerasi)",
    options=["General", "Power Play Uptrend (Price > DMA 10)"],
    index=0
)

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Intraday: **{FILTER_INTRADAY}** | Tren: **{FILTER_TREND}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (ANTI BULK-DROPOUT LOGIC)
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
            
            # Trik Safetynet: Mengunduh dengan struktur group_by Ticker agar data terisolasi dengan aman
            data_daily_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "3mo", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
            
            if interval_param == "1d":
                data_exec_bulk = data_daily_bulk
            else:
                data_exec_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
                
            hasil_screener = []
            daftar_saham_lolos_sekarang = []
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengunduh data: {e}")
            st.stop()

        # Perulangan analisa saham
        for ticker in watchlist:
            try:
                # Ambil sub-dataframe khusus untuk ticker ini secara independen
                if len(watchlist) == 1:
                    df_d = data_daily_bulk.copy()
                    df_e = data_exec_bulk.copy()
                else:
                    if ticker not in data_daily_bulk.columns.levels[0]:
                        continue
                    df_d = data_daily_bulk[ticker].copy()
                    df_e = data_exec_bulk[ticker].copy()
                
                # Pembersihan toleran: Hanya drop jika baris Close benar-benar kosong
                df_e = df_e.dropna(subset=['Close'])
                if df_e.empty or len(df_e) < MA_PERIODE:
                    continue
                    
                harga_hari_ini = float(df_e['Close'].iloc[-1])
                
                # --- FILTER 1: POWER PLAY TREN UTAMA ---
                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)":
                    df_d = df_d.dropna(subset=['Close'])
                    if len(df_d) >= 10:
                        dma_10_series = df_d['Close'].rolling(window=10).mean()
                        if harga_hari_ini < float(dma_10_series.iloc[-1]):
                            continue
                    else:
                        continue
                
                # Ekstrak data harga Open hari ini secara aman untuk filter intraday
                if 'Open' in df_d.columns and not df_d['Open'].dropna().empty:
                    open_hari_ini = float(df_d['Open'].dropna().iloc[-1])
                else:
                    open_hari_ini = harga_hari_ini
                
                # --- FILTER 2: INTRADAY MOMENTUM ---
                if FILTER_INTRADAY == "Intraday Momentum (>0%)":
                    if harga_hari_ini < open_hari_ini:
                        continue
                            
                # --- FILTER 3: UTAMA MOVING AVERAGE TIMEFRAME EKSEKUSI ---
                ma_exec_series = df_e['Close'].rolling(window=MA_PERIODE).mean()
                ma_exec_hari_ini = float(ma_exec_series.iloc[-1])
                
                # KONDISI UTAMA KELOLOSAN FILTER INPUT SIDEBAR
                if harga_hari_ini > ma_exec_hari_ini:
                    clean_ticker = ticker.replace(".JK", "")
                    daftar_saham_lolos_sekarang.append(clean_ticker)
                    
                    # Logika Mengunci Session State lintas klik
                    if clean_ticker not in st.session_state['saham_lolos_sebelumnya']:
                        status = "🟢 NEW"
                    else:
                        status = "🔵 HOLD"
                        
                    jarak_persen = ((harga_hari_ini - ma_exec_hari_ini) / ma_exec_hari_ini) * 100
                    persen_change = ((harga_hari_ini - open_hari_ini) / open_hari_ini) * 100
                    
                    hasil_screener.append({
                        "Kode Saham": clean_ticker,
                        "% Change": persen_change,
                        "Jarak ke MA 50 (%)": round(jarak_persen, 2),
                        "Status": status
                    })
            except:
                pass

        # Perbarui memori session state dengan hasil scanning detik ini
        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        # ==============================================================================
        # 3. OUTPUT TABEL INTERAKTIF
        # ==============================================================================
        st.success("🎯 Pemindaian Selesai!")
        
        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            
            # Dorong status NEW ke atas tabel hasil
            df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_hasil = df_hasil.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            
            st.metric(label="Saham Lolos Kriteria", value=f"{len(df_hasil)} Saham")
            
            st.dataframe(
                df_hasil,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                    "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="+%.2f%%")
                }
            )
        else:
            st.warning("Tidak ada saham dari database Anda yang memenuhi kriteria di atas.")
