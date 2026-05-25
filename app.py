import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==============================================================================
# 1. KONFIGURASI HALAMAN & LINK PERMANEN
# ==============================================================================
st.set_page_config(page_title="IHSG SMA 50 Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG SMA 50 Market Screener")
st.subheader("Timeframe: Daily (Kebal Bug Yahoo Finance)")

# --- LINK PERMANEN ANDA (SUDAH DIREVISI) ---
# Tautan Google Sheets Anda yang sudah dikonversi otomatis ke format CSV ekspor
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

st.write("Aplikasi telah terhubung secara permanen dengan Google Sheets Anda. Klik tombol di bawah untuk memulai pemindaian cepat.")

MULAI_SCAN = st.button("🚀 Mulai Pemindaian Market Massal", use_container_width=True)

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (BULK DOWNLOAD)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Menghubungkan ke Google Sheets dan mengunduh data bursa secara massal..."):
        try:
            # Mengunci Kolom A (Quote) saja untuk kebal dari error struktur kolom samping
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])
            
            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()
            
            # Filter hanya mengambil kode saham yang valid (4 huruf alfabet)
            watchlist = []
            for kode in watchlist_raw:
                if kode.isalpha() and len(kode) == 4 and kode != 'QUOTE':
                    watchlist.append(kode + ".JK")
            
            if not watchlist:
                st.error("Gagal mendeteksi kode saham 4 huruf di Kolom A.")
                st.stop()
                
            st.info(f"🔍 Memulai pemindaian super cepat untuk **{len(watchlist)} saham** secara simultan...")
            
            # Download semua data saham sekaligus (Bulk Request)
            data_bulk = yf.download(watchlist, period="1y", interval="1d", group_by='ticker', progress=False)
            
            hasil_screener = []
            
            # Looping hasil data di memori
            for ticker in watchlist:
                try:
                    if len(watchlist) == 1:
                        df_saham = data_bulk
                    else:
                        df_saham = data_bulk[ticker]
                        
                    df_saham = df_saham.dropna(subset=['Close'])
                    
                    if not df_saham.empty and len(df_saham) >= 50:
                        close_prices = df_saham['Close'].squeeze()
                        sma50_series = close_prices.rolling(window=50).mean()
                        
                        harga_terakhir = float(close_prices.iloc[-1])
                        nilai_sma50 = float(sma50_series.iloc[-1])
                        
                        # Filter Kondisi: Harga Terakhir > SMA 50
                        if harga_terakhir > nilai_sma50:
                            jarak_persen = ((harga_terakhir - nilai_sma
