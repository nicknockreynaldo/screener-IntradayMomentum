import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==============================================================================
# 1. KONFIGURASI HALAMAN APLIKASI
# ==============================================================================
st.set_page_config(page_title="IHSG SMA 50 Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Intraday Screener")
st.subheader("Menyaring Saham di Atas SMA 50 (Timeframe 1 Jam)")
st.write("Aplikasi ini otomatis membaca watchlist dari Google Sheets Anda dan melakukan pemindaian tren secara real-time.")

# Sidebar untuk Input Link Google Sheets agar fleksibel
st.sidebar.header("Konfigurasi Sumber Data")
input_url = st.sidebar.text_input(
    "Masukkan Link CSV Google Sheets Anda:",
    placeholder="https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/edit?gid=0#gid=0/export?format=csv"
)

# Tombol untuk trigger scanning
MULAI_SCAN = st.sidebar.button("🚀 Jalankan Screener")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER
# ==============================================================================
if MULAI_SCAN:
    if not input_url:
        st.error("Silakan masukkan URL Google Sheets Anda terlebih dahulu di sidebar kiri!")
    else:
        with st.spinner("Sedang mengunduh watchlist dan menganalisis data bursa... Mohon tunggu."):
            try:
                # Membaca sheet (melompati 12 baris pertama)
                df_sheet = pd.read_csv(input_url, skiprows=12)
                df_sheet = df_sheet.dropna(subset=['Quote'])
                watchlist = [str(kode).strip() + ".JK" for kode in df_sheet['Quote'].values]
                
                st.info(f"Berhasil memuat {len(watchlist)} saham dari Google Sheets Anda. Memulai pemindaian...")
                
                hasil_screener = []
                
                # Progress bar visual untuk aplikasi
                progress_bar = st.progress(0)
                
                for idx, ticker in enumerate(watchlist):
                    try:
                        # Update progress bar
                        progress_bar.progress((idx + 1) / len(watchlist))
                        
                        # Tarik data 1H
                        df_1h = yf.download(ticker, period="1y", interval="1h", progress=False)
                        
                        if not df_1h.empty and len(df_1h) >= 50:
                            if isinstance(df_1h.columns, pd.MultiIndex):
                                df_1h.columns = df_1h.columns.get_level_values(0)
                                
                            df_1h['SMA50'] = df_1h['Close'].rolling(window=50).mean()
                            
                            last_bar = df_1h.iloc[-1]
                            harga_terakhir = last_bar['Close']
                            nilai_sma50 = last_bar['SMA50']
                            
                            # Kondisi Utama
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
                # 3. MENAMPILKAN HASIL KE DASHBOARD APLIKASI
                # ==============================================================================
                st.success("🎯 Pemindaian Selesai!")
                
                if hasil_screener:
                    df_hasil = pd.DataFrame(hasil_screener)
                    # Urutkan berdasarkan jarak terdekat ke SMA 50
                    df_hasil = df_hasil.sort_values(by="Jarak di Atas SMA50", ascending=True)
                    
                    # Formatting tampilan kolom persentase agar rapi di dashboard
                    df_hasil["Jarak di Atas SMA50"] = df_hasil["Jarak di Atas SMA50"].apply(lambda x: f"+{x}%")
                    
                    # Tampilkan metrik total saham yang lolos
                    st.metric(label="Total Saham Lolos Filter (Uptrend)", value=f"{len(df_hasil)} Saham")
                    
                    # Tampilkan tabel interaktif (Bisa di-sort dan di-search langsung oleh pengguna)
                    st.dataframe(df_hasil, use_container_width=True, hide_index=True)
                else:
                    st.warning("Tidak ditemukan saham yang berada di atas SMA 50 pada timeframe 1 Jam saat ini.")
                    
            except Exception as e:
                st.error(f"Gagal memproses Google Sheets. Pastikan format tautan benar dan aksesnya sudah publik! Error: {e}")