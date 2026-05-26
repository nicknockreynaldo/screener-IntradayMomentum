import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==============================================================================
# 1. KONFIGURASI HALAMAN & SIDEBAR INTERAKTIF
# ==============================================================================
st.set_page_config(page_title="IHSG Custom MA Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Custom Moving Average Screener")
st.write("Hubungkan database saham Anda via Google Sheets, lalu atur indikator yang ingin Anda gunakan pada menu di sebelah kiri.")

# --- PANEL ATURAN INPUT DI SEBELAH KIRI (SIDEBAR) ---
st.sidebar.header("⚙️ Pengaturan Parameter")

# Pilihan Timeframe (Dilengkapi jimat proteksi pembatasan data)
TF_PILIHAN = st.sidebar.selectbox(
    "1. Pilih Timeframe (TF)",
    options=["1 Jam (1H)", "Harian (Daily)"],
    index=0
)

# Konversi teks pilihan ke parameter yfinance
if TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"  # 1 bulan sangat aman & cepat untuk data jam-jaman
    label_tf = "1H"
else:
    interval_param = "1d"
    period_param = "1y"   # 1 tahun untuk data harian
    label_tf = "Daily"

# Input Angka Moving Average secara manual
MA_PERIODE = st.sidebar.number_input(
    f"2. Periode Moving Average (MA)",
    min_value=5,
    max_value=200,
    value=50,  # Default awal tetap 50
    step=5
)

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Mulai Pemindaian", use_container_width=True)

# Informasikan parameter aktif di halaman utama
st.info(f"📋 **Kondisi Screener Aktif:** Mencari Saham dengan Harga Terakhir di Atas **SMA {MA_PERIODE}** pada Timeframe **{TF_PILIHAN}**.")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (DYNAMIC BULK DOWNLOAD)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Menghubungkan ke Google Sheets dan memproses data bursa..."):
        try:
            # Ambil kolom pertama saja (Quote)
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])
            
            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()
            
            # Filter kode saham 4 huruf
            watchlist = []
            for kode in watchlist_raw:
                if kode.isalpha() and len(kode) == 4 and kode != 'QUOTE':
                    watchlist.append(kode + ".JK")
            
            if not watchlist:
                st.error("Gagal mendeteksi kode saham 4 huruf di Google Sheets Anda.")
                st.stop()
                
            st.write(f"🔍 Memulai pemindaian massal **{len(watchlist)} saham**...")
            
            # Download data massal secara dinamis berdasarkan input user
            data_bulk = yf.download(
                watchlist, 
                period=period_param, 
                interval=interval_param, 
                group_by='ticker', 
                auto_adjust=False, 
                progress=False
            )
            
            hasil_screener = []
            
            # Looping kalkulasi data di memori
            for ticker in watchlist:
                try:
                    if len(watchlist) == 1:
                        df_saham = data_bulk
                    else:
                        df_saham = data_bulk[ticker]
                        
                    if 'Close' in df_saham.columns:
                        df_saham = df_saham.dropna(subset=['Close'])
                        close_prices = df_saham['Close'].squeeze()
                    else:
                        df_saham = df_saham.dropna(subset=['Adj Close'])
                        close_prices = df_saham['Adj Close'].squeeze()
                    
                    # Pastikan baris data cukup untuk menghitung periode MA yang diinput
                    if not df_saham.empty and len(close_prices) >= MA_PERIODE:
                        # Hitung MA dinamis sesuai input user
                        ma_series = close_prices.rolling(window=MA_PERIODE).mean()
                        
                        harga_terakhir = float(close_prices.iloc[-1])
                        nilai_ma = float(ma_series.iloc[-1])
                        
                        # Filter Kondisi: Close > Custom MA
                        if harga_terakhir > nilai_ma:
                            jarak_persen = ((harga_terakhir - nilai_ma) / nilai_ma) * 100
                            clean_ticker = ticker.replace(".JK", "")
                            
                            hasil_screener.append({
                                "Kode Saham": clean_ticker,
                                "Harga Terakhir": round(harga_terakhir, 2),
                                f"Nilai SMA {MA_PERIODE} ({label_tf})": round(nilai_ma, 2),
                                f"Jarak di Atas SMA{MA_PERIODE}": round(jarak_persen, 2)
                            })
                except:
                    pass
            
            # ==============================================================================
            # 3. TAMPILKAN HASILNYA
            # ==============================================================================
            st.success("🎯 Pemindaian Selesai!")
            
            if hasil_screener:
                df_hasil = pd.DataFrame(hasil_screener)
                # Sort dari yang paling dekat dengan garis MA (Best area untuk Buy on Weakness)
                sort_column = f"Jarak di Atas SMA{MA_PERIODE}"
                df_hasil = df_hasil.sort_values(by=sort_column, ascending=True)
                
                # Format visual persen teks
                df_hasil[sort_column] = df_hasil[sort_column].apply(lambda x: f"+{x}%")
                
                st.metric(label=f"Saham Lolos Filter (> SMA {MA_PERIODE})", value=f"{len(df_hasil)} Saham")
                st.dataframe(df_hasil, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Tidak ada saham dari database Anda yang saat ini berada di atas SMA {MA_PERIODE} ({label_tf}).")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis saat membaca data. Deskripsi Error: {e}")
