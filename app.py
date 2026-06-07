import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="IHSG Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

# --- SIDEBAR SETUP ---
st.sidebar.header("⚙️ Parameter Setup")
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Grade A Setup", "Grade B Setup", "Custom"])

# Menambahkan keterangan di sidebar untuk panduan
if PRESET == "Grade A Setup":
    st.sidebar.info("Grade A: Price > DMA10 (tol. 3%) AND Price > DMA50")
elif PRESET == "Grade B Setup":
    st.sidebar.info("Grade B: Price > DMA10 (tol. 3%) AND Price < DMA50")

FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", ["General", "Intraday Momentum (>0%)"])

# Penentuan parameter dinamis
if PRESET == "Custom":
    TF_PILIHAN = st.sidebar.selectbox("Timeframe:", ["Daily", "1H", "30min", "15min", "5min"])
    MA_PERIODE = st.sidebar.selectbox("Periode MA:", [5, 10, 20, 50, 200])
else:
    TF_PILIHAN = "Daily" # Force Daily untuk Grade A/B
    MA_PERIODE = 50      # Default referensi DMA50

# --- LOGIKA SCREENING (DENGAN FIX ERROR) ---
def run_screening(df, preset, ma_period, filter_intra):
    # Memastikan nilai adalah float tunggal agar tidak error saat perbandingan
    curr_price = float(df['Close'].iloc[-1])
    curr_open = float(df['Open'].iloc[-1])
    
    dma10 = float(df['Close'].rolling(10).mean().iloc[-1])
    dma50 = float(df['Close'].rolling(ma_period).mean().iloc[-1])
    tolerance = 0.97 * dma10 # Toleransi 3%
    
    # Filter Intraday
    if filter_intra == "Intraday Momentum (>0%)" and curr_price <= curr_open:
        return False
        
    # Logic Filtering
    if preset == "Grade A Setup":
        return curr_price >= tolerance and curr_price > dma50
    elif preset == "Grade B Setup":
        return curr_price >= tolerance and curr_price < dma50
    else: # Mode Custom
        return curr_price > dma10 and curr_price > dma50

# --- PROSES EKSEKUSI ---
if st.sidebar.button("🚀 Start Screening"):
    st.write(f"Menjalankan screening dengan: **{PRESET}**")
    
    # Contoh list saham
    list_saham = ['BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'TLKM.JK'] 
    
    results = []
    # Mapping label ke parameter yfinance
    tf_param = {"Daily": "1d", "1H": "1h", "30min": "30m", "15min": "15m", "5min": "5m"}[TF_PILIHAN]
    
    for ticker in list_saham:
        df = yf.download(ticker, period="1y", interval=tf_param, progress=False)
        
        # Validasi apakah data cukup untuk menghitung MA
        if not df.empty and len(df) >= MA_PERIODE:
            if run_screening(df, PRESET, MA_PERIODE, FILTER_INTRADAY):
                results.append(ticker)
    
    if results:
        st.success(f"Saham yang lolos: {', '.join(results)}")
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria.")
