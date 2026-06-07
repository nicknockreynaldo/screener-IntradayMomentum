import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# Konfigurasi Halaman
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Setup")
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Custom"])

# --- Kondisional Tampilan Sidebar ---
if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Pilih Timeframe:", ["Daily", "1H", "30min", "15min", "5min"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200])
else:
    TF_PILIHAN = "Daily"
    MA_PERIODE = 50 # Sebagai referensi DMA50 untuk Grade A/B

FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", ["General", "Intraday Momentum (>0%)"])

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

# --- ENGINE ---
if MULAI_SCAN:
    with st.spinner("Menjalankan screening..."):
        URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
        df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
        watchlist = [kode.strip().upper() + ".JK" for kode in df_sheet.iloc[:, 0].dropna().astype(str) if len(kode.strip()) == 4]
        
        tf_map = {"Daily": "1d", "1H": "1h", "30min": "30m", "15min": "15m", "5min": "5m"}
        data_bulk = yf.download(watchlist, period="1y", interval=tf_map[TF_PILIHAN], group_by='ticker', auto_adjust=False, progress=False)
        
        hasil_screener = []
        daftar_saham_lolos_sekarang = []
        
        for ticker in watchlist:
            try:
                df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                if len(df) < 55: continue # Buffer untuk MA200
                
                # Perhitungan Data
                close = float(df['Close'].iloc[-1])
                open_p = float(df['Open'].iloc[-1])
                ma10 = float(df['Close'].rolling(10).mean().iloc[-1])
                ma50 = float(df['Close'].rolling(50).mean().iloc[-1])
                ma_custom = float(df['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                tol_ma10 = 0.97 * ma10
                
                # --- LOGIKA FILTER ---
                # 1. Filter Intraday
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and close < open_p: continue
                
                # 2. Preset Logic
                if PRESET == "Grade A Setup":
                    if not (close >= tol_ma10 and close > ma50): continue
                elif PRESET == "Grade B Setup":
                    if not (close >= tol_ma10 and close < ma50): continue
                else: # Custom
                    if not (close > ma_custom): continue
                
                # Jika Lolos
                clean_ticker = ticker.replace(".JK", "")
                daftar_saham_lolos_sekarang.append(clean_ticker)
                
                status = "🟢 NEW" if clean_ticker not in st.session_state['saham_lolos_sebelumnya'] else "🔵 HOLD"
                jarak_ma50 = ((close - ma50) / ma50) * 100
                
                hasil_screener.append({
                    "Kode Saham": clean_ticker, 
                    "Price": close, 
                    "Jarak ke MA 50 (%)": round(jarak_ma50, 2), 
                    "Status": status
                })
            except: continue

        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        if hasil_screener:
            df_res = pd.DataFrame(hasil_screener)
            df_res['is_new'] = df_res['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_res = df_res.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            st.metric("Saham Lolos Kriteria", f"{len(df_res)} Saham")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
