import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="IHSG Ultimate Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

# Cache data untuk kecepatan (TTL 900 detik = 15 menit)
@st.cache_data(ttl=900)
def fetch_data(watchlist, period, interval):
    return yf.download(watchlist, period=period, interval=interval, group_by='ticker', auto_adjust=False, progress=False)

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Setup")
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Market Merah Cari Alpha", "Custom"])

# --- Logika Preset & Konfigurasi ---
if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Pilih Timeframe:", ["Daily", "1H"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200])
elif PRESET == "Market Merah Cari Alpha":
    TF_PILIHAN = "1H"
    MA_PERIODE = 20
else:
    TF_PILIHAN = "Daily"
    MA_PERIODE = 50

FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", ["General", "Intraday Momentum (>0%)"])

if st.sidebar.button("🚀 Start Screening"):
    with st.spinner("Menjalankan screening..."):
        URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
        df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
        watchlist = [kode.strip().upper() + ".JK" for kode in df_sheet.iloc[:, 0].dropna().astype(str) if len(kode.strip()) == 4]
        
        current_period = "5d" if TF_PILIHAN == "1H" else "1y"
        tf_map = {"Daily": "1d", "1H": "1h"}
        
        data_bulk = fetch_data(tuple(watchlist), current_period, tf_map[TF_PILIHAN])
        
        hasil_screener = []
        daftar_saham_lolos_sekarang = []
        
        # Iterasi screening
        for ticker in watchlist:
            try:
                df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                if df.empty or 'Close' not in df.columns: continue
                
                # DATA CLEANING AGRESIF
                df = df.ffill().bfill().dropna()
                if len(df) < max(55, MA_PERIODE): continue
                
                close = float(df['Close'].iloc[-1])
                open_p = float(df['Open'].iloc[-1])
                ma10 = float(df['Close'].rolling(10).mean().iloc[-1])
                ma50 = float(df['Close'].rolling(50).mean().iloc[-1])
                ma_custom = float(df['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                tol_ma10 = 0.97 * ma10
                
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and close < open_p: continue
                
                # Logika Filter
                is_valid = False
                if PRESET == "Grade A Setup":
                    is_valid = (close >= tol_ma10 and close > ma50)
                elif PRESET == "Grade B Setup":
                    is_valid = (close >= tol_ma10 and close < ma50)
                elif PRESET == "Market Merah Cari Alpha":
                    is_valid = (close > ma_custom)
                else: 
                    is_valid = (close > ma_custom)
                
                if not is_valid: continue
                
                clean_ticker = ticker.replace(".JK", "")
                daftar_saham_lolos
