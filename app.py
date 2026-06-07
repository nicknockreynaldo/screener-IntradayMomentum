import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="IHSG Ultimate Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

# Fungsi untuk menarik data dari Google Sheets
@st.cache_data(ttl=600)
def get_watchlist():
    URL = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
    df = pd.read_csv(URL, usecols=[0], nrows=200)
    return [kode.strip().upper() + ".JK" for kode in df.iloc[:, 0].dropna().astype(str) if len(kode.strip()) == 4]

# --- Sidebar ---
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

# --- Eksekusi ---
if st.sidebar.button("🚀 Start Screening"):
    # 1. Bersihkan Cache Data agar tidak bentrok dengan sesi sebelumnya
    st.cache_data.clear()
    
    with st.spinner("Menarik data terbaru dari bursa..."):
        watchlist = get_watchlist()
        period = "5d" if TF_PILIHAN == "1H" else "1y"
        interval = "1h" if TF_PILIHAN == "1H" else "1d"
        
        # Tarik data
        data_bulk = yf.download(watchlist, period=period, interval=interval, group_by='ticker', auto_adjust=True, progress=False)
        
        hasil_utama = []
        hasil_cadangan = []
        
        for ticker in watchlist:
            try:
                df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                if df.empty or 'Close' not in df.columns: continue
                
                # Pembersihan wajib
                df = df.ffill().bfill().dropna()
                if len(df) < MA_PERIODE: continue
                
                close = float(df['Close'].iloc[-1])
                ma_val = float(df['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                dist_ma = ((close - ma_val) / ma_val) * 100
                
                # Filter Intraday (Opsional)
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and close < float(df['Open'].iloc[-1]): continue
                
                data_item = {"Kode": ticker.replace(".JK", ""), "Price": close, "Jarak MA (%)": round(dist_ma, 2)}
                
                # Logika Filter
                if close > ma_val:
                    hasil_utama.append(data_item)
                
                hasil_cadangan.append(data_item)
            except: continue

        # Tampilkan Hasil
        if hasil_utama:
            st.success(f"Ditemukan {len(hasil_utama)} saham!")
            st.dataframe(pd.DataFrame(hasil_utama).sort_values("Jarak MA (%)", ascending=False), use_container_width=True, hide_index=True)
        elif hasil_cadangan:
            st.warning("Tidak ada saham di atas MA. Berikut 10 saham terdekat ke MA:")
            df_c = pd.DataFrame(hasil_cadangan).sort_values("Jarak MA (%)", ascending=False).head(10)
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            st.error("Gagal memproses data. Coba lagi.")
