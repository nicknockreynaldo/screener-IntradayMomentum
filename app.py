import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="IHSG Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

# --- SIDEBAR SETUP ---
st.sidebar.header("⚙️ Parameter Setup")
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Custom"])
FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", ["General", "Intraday Momentum (>0%)"])

# Penentuan parameter dinamis
if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Timeframe:", ["1d", "1h", "30m", "15m", "5m"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200])
else:
    TF_PILIHAN = "1d" # Force Daily untuk Grade A/B
    MA_PERIODE = 50   # Force MA50 sebagai referensi

# --- LOGIKA SCREENING ---
def run_screening(df, preset, ma_period, filter_intra):
    curr_price = df['Close'].iloc[-1]
    curr_open = df['Open'].iloc[-1]
    
    # Perhitungan Dasar
    dma10 = df['Close'].rolling(10).mean().iloc[-1]
    dma50 = df['Close'].rolling(ma_period).mean().iloc[-1]
    tolerance = 0.97 * dma10 # Toleransi 3%
    
    # Filter Intraday (Berlaku untuk semua mode)
    if filter_intra == "Intraday Momentum (>0%)" and curr_price <= curr_open:
        return False
        
    # Logic Filtering
    if preset == "Grade A Setup":
        return curr_price >= tolerance and curr_price > dma50
    elif preset == "Grade B Setup":
        return curr_price >= tolerance and curr_price < dma50
    else: # Mode Custom (Logika bebas sesuai keinginan Anda)
        return curr_price > dma10 and curr_price > dma50

# --- PROSES EKSEKUSI ---
if st.sidebar.button("🚀 Start Screening"):
    st.write(f"Menjalankan screening dengan: **{PRESET}**")
    
    # Contoh list saham (bisa di-extend)
    list_saham = ['BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'TLKM.JK'] 
    
    results = []
    for ticker in list_saham:
        df = yf.download(ticker, period="1y", interval=TF_PILIHAN, progress=False)
        if not df.empty:
            if run_screening(df, PRESET, MA_PERIODE, FILTER_INTRADAY):
                results.append(ticker)
    
    if results:
        st.success(f"Saham yang lolos: {', '.join(results)}")
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria.")
