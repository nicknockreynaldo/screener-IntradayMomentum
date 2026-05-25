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

# --- LINK PERMANEN ANDA ---
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
                            # PERBAIKAN: Rumus matematika dipastikan menutup seluruh tanda kurung dengan benar
                            jarak_persen = ((harga_terakhir - nilai_sma50) / nilai_sma50) * 100
                            clean_ticker = ticker.replace(".JK", "")
                            
                            hasil_screener.append({
                                "Kode Saham": clean_ticker,
                                "Harga Terakhir (Rp)": int(harga_terakhir),
                                "Nilai SMA 50 (Daily)": round(nilai_sma50, 2),
                                "Jarak di Atas SMA50": round(jarak_persen, 2)
                            })
                except:
                    pass  # Lewati jika ada satu saham yang datanya tidak lengkap
            
            # ==============================================================================
            # 3. TAMPILKAN HASILNYA
            # ==============================================================================
            st.success("🎯 Pemindaian Massal Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                # Urutkan dari yang paling dekat dengan garis SMA 50 (potensi Pantulan / Buy on Weakness)
                df_hasil = df_hasil.sort_values(by="Jarak di Atas SMA50", ascending=True)
                
                # Format visual persen
                df_hasil["Jarak di Atas SMA50"] = df_hasil["Jarak di Atas SMA50"].apply(lambda x: f"+{x}%")
                
                st.metric(label="Saham Lolos Filter (Uptrend / di Atas SMA 50)", value=f"{len(df_hasil)} Saham")
                st.dataframe(df_hasil, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada saham dari database Anda yang saat ini berada di atas SMA 50.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis saat membaca data. Deskripsi Error: {e}")
