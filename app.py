import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==============================================================================
# 1. KONFIGURASI HALAMAN & LINK PERMANEN
# ==============================================================================
st.set_page_config(page_title="IHSG SMA 50 Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Intraday SMA 50 Screener")
st.subheader("Timeframe: 1 Jam (1H)")

# --- LINK PERMANEN ANDA ---
# Tempelkan link Google Sheets Anda di bawah ini (Wajib berakhiran /export?format=csv)
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/edit?gid=0#gid=0/export?format=csv"

st.write("Aplikasi telah terhubung secara permanen dengan Google Sheets (Format Rapi). Klik tombol di bawah untuk memulai pemindaian.")

MULAI_SCAN = st.button("🚀 Mulai Pemindaian Market Real-Time", use_container_width=True)

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (FORMAT DATA BERSIH A1/A2)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Menghubungkan ke Google Sheets dan mengunduh data bursa..."):
        try:
            # Karena tabel mulai dari A1, langsung baca secara normal dan rapi
            df_sheet = pd.read_csv(URL_PERMANEN)
            
            # Cek apakah kolom 'Quote' ada di baris pertama
            if 'Quote' not in df_sheet.columns:
                st.error("Gagal mendeteksi kolom dengan nama 'Quote' di baris pertama Google Sheets Anda. Pastikan nama kolom di sel A1 tertulis 'Quote'.")
                st.stop()
                
            # Bersihkan baris kosong di kolom Quote
            df_sheet = df_sheet.dropna(subset=['Quote'])
            
            # Ambil kode saham dari Baris 2 (A2) ke bawah dan tambahkan akhiran .JK secara otomatis
            watchlist = [str(kode).strip().upper() + ".JK" for kode in df_sheet['Quote'].values if len(str(kode).strip()) <= 5]
            
            if not watchlist:
                st.warning("Tidak ditemukan kode saham yang valid di kolom 'Quote'.")
                st.stop()
                
            st.info(f"🔍 Berhasil memuat **{len(watchlist)} saham** dari kolom 'Quote'. Memulai scanning bursa...")
            
            hasil_screener = []
            progress_bar = st.progress(0)
            
            for idx, ticker in enumerate(watchlist):
                try:
                    progress_bar.progress((idx + 1) / len(watchlist))
                    
                    # Tarik data timeframe 1 jam
                    df_1h = yf.download(ticker, period="1y", interval="1h", progress=False)
                    
                    if not df_1h.empty and len(df_1h) >= 50:
                        if isinstance(df_1h.columns, pd.MultiIndex):
                            df_1h.columns = df_1h.columns.get_level_values(0)
                            
                        # Hitung SMA 50
                        df_1h['SMA50'] = df_1h['Close'].rolling(window=50).mean()
                        
                        last_bar = df_1h.iloc[-1]
                        harga_terakhir = last_bar['Close']
                        nilai_sma50 = last_bar['SMA50']
                        
                        # Filter Kondisi: Harga Terakhir > SMA 50
                        if harga_terakhir > nilai_sma50:
                            jarak_persen = ((harga_terakhir - nilai_sma50) / nilai_sma50) * 100
                            clean_ticker = ticker.replace(".JK", "")
                            
                            hasil_screener.append({
                                "Kode Saham": clean_ticker,
                                "Harga Terakhir (Rp)": int(harga_terakhir),
                                "Nilai SMA 50 (1H)": round(nilai_sma50, 2),
                                "Jarak di Atas SMA50": round(jarak_persen, 2)
                            })
                except:
                    pass
            
            # ==============================================================================
            # 3. TAMPILKAN HASILNYA
            # ==============================================================================
            st.success("🎯 Pemindaian Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                # Sort dari yang paling dekat dengan garis SMA 50 (area pantulan potensial)
                df_hasil = df_hasil.sort_values(by="Jarak di Atas SMA50", ascending=True)
                
                # Format visual persen
                df_hasil["Jarak di Atas SMA50"] = df_hasil["Jarak di Atas SMA50"].apply(lambda x: f"+{x}%")
                
                st.metric(label="Saham Lolos Filter (Uptrend Jangka Menengah)", value=f"{len(df_hasil)} Saham")
                st.dataframe(df_hasil, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada saham dari database Anda yang saat ini berada di atas SMA 50 (1H).")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis saat membaca file. Deskripsi Error: {e}")
