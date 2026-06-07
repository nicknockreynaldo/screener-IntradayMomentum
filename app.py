import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import warnings
from datetime import datetime

# Set Konfigurasi Halaman Web Streamlit Anda
st.set_page_config(
    page_title="IHSG Intraday Momentum",
    page_icon="📈",
    layout="wide"
)

# Matikan notifikasi peringatan/warning agar output tabel bersih rapi
warnings.filterwarnings('ignore', category=FutureWarning)

st.title("📈 IHSG Intraday Momentum Screener")
st.subheader("Live State-Tracking Architecture (NEW vs HOLD)")

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

# Tombol Pemicu Scanning di Aplikasi Web
if st.button("🚀 Mulai Scanning Market Live", use_container_width=True):
    with st.spinner("Mengambil database saham dari GSheet & mendownload data Live dari Yahoo Finance..."):
        try:
            # Membaca hanya Kolom A (Quote) saja dari format tabel A1/A2 Anda
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])

            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()

            # Filter validasi kode saham 4 huruf
            watchlist = []
            for kode in watchlist_raw:
                if kode.isalpha() and len(kode) == 4 and kode != 'QUOTE':
                    watchlist.append(kode + ".JK")

            if not watchlist:
                st.error("❌ Gagal mendeteksi kode saham yang valid di Kolom A Google Sheets.")
            else:
                # BULK DOWNLOAD data Intraday 1 Jam (1H)
                data_bulk = yf.download(watchlist, period="1mo", interval="1h", group_by='ticker', auto_adjust=False, progress=False)

                hasil_screener = []

                # Proses pengolahan data SMA 50 Jam
                for ticker in watchlist:
                    try:
                        if len(watchlist) == 1:
                            df_saham = data_bulk.copy()
                        else:
                            df_saham = data_bulk[ticker].copy()

                        # Pastikan data esensial OHLC tidak kosong
                        df_saham = df_saham.dropna(subset=['Close', 'Open', 'High', 'Low'])

                        if not df_saham.empty and len(df_saham) >= 50:
                            
                            # 1. AMBIL SERI HARGA CLOSE STANDAR
                            close_prices = df_saham['Close'].squeeze()
                            
                            # 2. KALKULASI SMA 50 JAM BERDASARKAN CLOSE STANDAR
                            df_saham['SMA50'] = close_prices.rolling(window=50).mean()

                            # Ambil data poin live/terakhir berbasis HARGA CLOSE STANDAR
                            harga_terakhir_close = float(close_prices.iloc[-1])
                            nilai_ma_sekarang = float(df_saham['SMA50'].iloc[-1])
                            open_price = float(df_saham['Open'].iloc[-1])
                            
                            # 3. METRIK % CHANGE INTRADAY (Current Close / Open Price)
                            persen_change = ((harga_terakhir_close - open_price) / open_price) * 100

                            # Kondisi Seleksi Utama: Close Terakhir > SMA 50
                            if harga_terakhir_close > nilai_ma_sekarang:
                                jarak_persen = ((harga_terakhir_close - nilai_ma_sekarang) / nilai_ma_sekarang) * 100
                                clean_ticker = ticker.replace(".JK", "")

                                # --- LOGIKA PRICE ACTION ADAPTIF (POLA X ANTM) ---
                                low_2_lalu = float(df_saham['Low'].iloc[-3])
                                ma_2_lalu = float(df_saham['SMA50'].iloc[-3])
                                high_1_lalu = float(df_saham['High'].iloc[-2])

                                # Penentuan Status secara Dinamis
                                if low_2_lalu <= ma_2_lalu and harga_terakhir_close > high_1_lalu:
                                    status = "🟢 NEW"
                                    keterangan = "🎯 Valid Memantul (Pola X) & Breakout High Lokal"
                                else:
                                    status = "🔵 HOLD"
                                    keterangan = "Tren bertahan kokoh di atas SMA 50"

                                hasil_screener.append({
                                    "Kode Saham": clean_ticker,
                                    "% Change": f"{persen_change:+.2f}%",
                                    "Jarak ke SMA50": round(jarak_persen, 2),
                                    "Status": status,
                                    "Keterangan Setup": keterangan
                                })
                    except:
                        pass 

                # ==============================================================================
                # TAMPILKAN REKAPITULASI HASIL DI STREAMLIT
                # ==============================================================================
                waktu_scan = datetime.now().strftime('%H:%M:%S')
                
                if hasil_screener:
                    df_hasil = pd.DataFrame(hasil_screener)
                    
                    # Urutkan agar status "🟢 NEW" selalu berada di baris paling atas
                    df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
                    df_hasil = df_hasil.sort_values(by=["is_new", "Jarak ke SMA50"], ascending=[False, True]).drop(columns=['is_new'])
                    
                    df_hasil['Jarak ke SMA50'] = df_hasil['Jarak ke SMA50'].apply(lambda x: f"+{x}%")
                    df_hasil.index = range(1, len(df_hasil) + 1)

                    st.success(f"🎯 Pemindaian Selesai! Waktu Scan: {waktu_scan} WIB | Total: {len(df_hasil)} Saham Lolos")
                    
                    # Tampilkan tabel interaktif bawaan Streamlit secara penuh
                    st.dataframe(df_hasil, use_container_width=True)
                else:
                    st.info(f"ℹ️ Tidak ada saham yang saat ini bergerak di atas SMA 50 (1H). Waktu Scan: {waktu_scan} WIB")

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan teknis: {e}")
else:
    st.write("👈 Klik tombol di atas untuk memulai pemindaian momentum intraday.")
