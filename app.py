import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

# Sidebar Parameter
st.sidebar.header("⚙️ Parameter Sensor")
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)"])
DEBUG_MODE = st.sidebar.checkbox("Aktifkan Mode Debug", value=False)
FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Open)", ["General", "Intraday Momentum (>0%)"])

# Penyesuaian Timeframe & MA
if PRESET == "Manual (Default)":
    TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1)
    FILTER_TREND = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Power Play Uptrend (Price > DMA 10)"])
else:
    TF_PILIHAN = "5 Menit (5m)" if PRESET == "Grade D (Market Merah Cari Alpha)" else "1 Jam (1H)"
    MA_PERIODE = 50 
    FILTER_TREND = "General"

tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "1mo"), "15 Menit (15m)": ("15m", "1mo"), "5 Menit (5m)": ("5m", "1mo")}
interval_param, period_param = tf_map[TF_PILIHAN]

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

if MULAI_SCAN:
    with st.spinner("Mengambil data terbaru..."):
        try:
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            watchlist = [k.strip().upper() + ".JK" for k in df_sheet.iloc[:, 0].dropna().astype(str) if len(k.strip()) == 4]
            
            data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=True, progress=False)
            
            hasil_screener = []
            for ticker in watchlist:
                df_s = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                df_s = df_s.sort_index().dropna(subset=['Close'])
                if df_s.empty or len(df_s) < 60: continue
                
                close = float(df_s['Close'].iloc[-1])
                ma10 = float(df_s['Close'].rolling(10).mean().iloc[-1])
                ma20 = float(df_s['Close'].rolling(20).mean().iloc[-1])
                ma50 = float(df_s['Close'].rolling(50).mean().iloc[-1])
                
                # Logika Filter
                if PRESET == "Manual (Default)": is_lolos = True # Semua saham tampil di manual
                elif PRESET == "Grade A Setup": is_lolos = (close > ma10 and close > ma50)
                elif PRESET == "Grade B Setup": is_lolos = (close >= (ma10 * 0.95) and close < ma50)
                elif PRESET == "Grade D (Market Merah Cari Alpha)": is_lolos = (close > ma50)
                
                if is_lolos:
                    clean = ticker.replace(".JK", "")
                    hasil_screener.append({
                        "Kode Saham": clean,
                        "Price": f"Rp{close:,.0f}",
                        "Jarak ke MA 10 (%)": f"{((close - ma10) / ma10) * 100:.2f}%",
                        "Jarak ke MA 20 (%)": f"{((close - ma20) / ma20) * 100:.2f}%",
                        "Jarak ke MA 50 (%)": f"{((close - ma50) / ma50) * 100:.2f}%"
                    })
            
            if hasil_screener:
                df_h = pd.DataFrame(hasil_screener)
                
                # Menampilkan jumlah saham
                st.metric("Saham Lolos Kriteria", f"{len(df_h)} Saham")
                
                # Tabel ditampilkan apa adanya tanpa modifikasi kolom agar tidak terpotong
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else: 
                st.warning("Tidak ada saham yang memenuhi kriteria.")
        except Exception as e: st.error(f"Error: {e}")
