import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="IHSG Ultimate Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

@st.cache_data(ttl=900)
def fetch_data(watchlist, period, interval):
    return yf.download(watchlist, period=period, interval=interval, group_by='ticker', auto_adjust=True, progress=False)

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Setup")
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)", "Custom"])

if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Pilih Timeframe:", ["Daily", "1H"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200])
elif PRESET == "Grade D (Market Merah Cari Alpha)":
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
        daftar_semua_saham = [] # Untuk daftar cadangan
        
        for ticker in watchlist:
            try:
                df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                if df.empty or 'Close' not in df.columns: continue
                
                df = df.ffill().bfill().dropna()
                if len(df) < max(55, MA_PERIODE): continue
                
                close = float(df['Close'].iloc[-1])
                ma_val = float(df['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                dist_ma = ((close - ma_val) / ma_val) * 100
                
                # Logika Filter utama
                is_valid = (close > ma_val)
                
                # Simpan untuk cadangan (Top 10 terdekat ke MA)
                daftar_semua_saham.append({"Kode Saham": ticker.replace(".JK", ""), "Price": close, "Jarak ke MA (%)": round(dist_ma, 2)})
                
                if not is_valid: continue
                
                hasil_screener.append({"Kode Saham": ticker.replace(".JK", ""), "Price": round(close, 2), "Jarak ke MA (%)": round(dist_ma, 2)})
            except: continue

        if hasil_screener:
            st.success(f"Ditemukan {len(hasil_screener)} saham di atas MA{MA_PERIODE}!")
            st.dataframe(pd.DataFrame(hasil_screener), use_container_width=True)
        else:
            st.warning("Tidak ada saham yang di atas MA. Menampilkan daftar saham terdekat ke MA:")
            df_cadangan = pd.DataFrame(daftar_semua_saham).sort_values("Jarak ke MA (%)", ascending=False).head(10)
            st.dataframe(df_cadangan, use_container_width=True)
