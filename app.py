import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="IHSG Power Screener", page_icon="📈", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

st.sidebar.header("⚙️ Parameter Setup")
SETUP = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup"])
FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", ["General", "Intraday Momentum (>0%)"])

# Info panduan tetap muncul agar Anda tidak lupa aturan main
if SETUP == "Grade A Setup":
    st.sidebar.info("Grade A: Price > DMA10 (tol. 3%) AND Price > DMA50")
else:
    st.sidebar.info("Grade B: Price > DMA10 (tol. 3%) AND Price < DMA50")

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

if st.sidebar.button("🚀 Start Screening"):
    # 1. Ambil Watchlist
    df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
    watchlist = [kode + ".JK" for kode in df_sheet.iloc[:, 0].dropna().astype(str) if len(kode) == 4]
    
    hasil_screener = []
    
    # 2. Download Data Bulk (Interval Daily sesuai GSheet)
    data_bulk = yf.download(watchlist, period="1y", interval="1d", group_by='ticker', progress=False)
    
    # 3. Screening Loop
    for ticker in watchlist:
        try:
            df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
            if len(df) < 50: continue
            
            # Harga & Indikator
            close = df['Close'].iloc[-1]
            ma10 = df['Close'].rolling(10).mean().iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            tol_dma10 = 0.97 * ma10
            
            # Logika Intraday
            open_price = df['Open'].iloc[-1]
            if FILTER_INTRADAY == "Intraday Momentum (>0%)" and close < open_price:
                continue
                
            # Logika Grade A / B (Tanpa Filter Tren Tambahan)
            if SETUP == "Grade A Setup":
                if not (close >= tol_dma10 and close > ma50): continue
            else: # Grade B
                if not (close >= tol_dma10 and close < ma50): continue
            
            hasil_screener.append({"Kode": ticker.replace(".JK", ""), "Price": close, "MA50": ma50})
            
        except: continue
        
    # 4. Tampil Hasil
    if hasil_screener:
        st.success(f"Ditemukan {len(hasil_screener)} saham!")
        st.dataframe(pd.DataFrame(hasil_screener))
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria.")
