import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI & SESSION STATE
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Sensor")

# --- TAMBAHAN PRESET ---
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)", "Custom"])

if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Pilih Timeframe:", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200], index=1)
    FILTER_INTRADAY = st.sidebar.selectbox("Filter Pergerakan Hari Ini (Vs Open):", ["General", "Intraday Momentum (>0%)"])
    FILTER_TREND = st.sidebar.selectbox("Filter Tren Utama (Akselerasi):", ["General", "Power Play Uptrend (Price > DMA 10)"])
else:
    # Logic preset otomatis
    if PRESET == "Grade D (Market Merah Cari Alpha)":
        TF_PILIHAN = "1 Jam (1H)"
        MA_PERIODE = 20
    else:
        TF_PILIHAN = "Harian (Daily)"
        MA_PERIODE = 50
    FILTER_INTRADAY = "General"
    FILTER_TREND = "General"

# Konfigurasi TF
tf_map = {
    "Harian (Daily)": ("1d", "2y"),
    "1 Jam (1H)": ("1h", "1mo"),
    "30 Menit (30m)": ("30m", "7d"),
    "15 Menit (15m)": ("15m", "7d"),
    "5 Menit (5m)": ("5m", "5d")
}
interval_param, period_param = tf_map[TF_PILIHAN]

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)
st.info(f"📋 **Kondisi:** Harga > SMA {MA_PERIODE} ({TF_PILIHAN}) | Intraday: **{FILTER_INTRADAY}**")

# ==============================================================================
# 2. LOGIKA UTAMA
# ==============================================================================
if MULAI_SCAN:
    st.cache_data.clear() # Pastikan data fresh
    with st.spinner("Memproses data..."):
        URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
        df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
        watchlist = [kode.strip().upper() + ".JK" for kode in df_sheet.iloc[:, 0].dropna().astype(str) if len(kode.strip()) == 4]
        
        data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
        
        hasil_screener = []
        daftar_saham_lolos_sekarang = []
        
        for ticker in watchlist:
            try:
                df_saham = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                df_saham = df_saham.dropna(subset=['Close'])
                if df_saham.empty or len(df_saham) < MA_PERIODE: continue
                
                harga_hari_ini = float(df_saham['Close'].iloc[-1])
                ma_hari_ini = float(df_saham['Close'].rolling(window=MA_PERIODE).mean().iloc[-1])
                
                # Filter Utama
                if harga_hari_ini <= ma_hari_ini: continue
                
                # Filter Tambahan
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and harga_hari_ini < float(df_saham['Open'].iloc[-1]): continue
                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)" and harga_hari_ini < float(df_saham['Close'].rolling(10).mean().iloc[-1]): continue
                
                clean_ticker = ticker.replace(".JK", "")
                daftar_saham_lolos_sekarang.append(clean_ticker)
                
                status = "🟢 NEW" if clean_ticker not in st.session_state['saham_lolos_sebelumnya'] else "🔵 HOLD"
                persen_change = ((harga_hari_ini - float(df_saham['Open'].iloc[-1])) / float(df_saham['Open'].iloc[-1])) * 100
                jarak_ma50 = ((harga_hari_ini - ma_hari_ini) / ma_hari_ini) * 100
                
                hasil_screener.append({
                    "Kode Saham": clean_ticker,
                    "% Change": persen_change,
                    "Jarak ke MA 50 (%)": round(jarak_ma50, 2),
                    "Status": status
                })
            except: continue

        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        # ==============================================================================
        # 3. OUTPUT (Struktur kolom SAMA PERSIS dengan screener lama Anda)
        # ==============================================================================
        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_hasil = df_hasil.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            
            st.success("🎯 Pemindaian Selesai!")
            st.metric("Saham Lolos Kriteria", f"{len(df_hasil)} Saham")
            st.dataframe(df_hasil, use_container_width=True, hide_index=True, column_config={
                "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="+%.2f%%")
            })
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria filter aktif saat ini.")
