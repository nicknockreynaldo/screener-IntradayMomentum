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

st.write("Aplikasi telah terhubung secara permanen dengan Google Sheets Anda. Klik tombol di bawah untuk memulai pemindaian.")

MULAI_SCAN = st.button("🚀 Mulai Pemindaian Market Real-Time", use_container_width=True)

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (ABSULUT BARIS 13 KE BAWAH)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Menghubungkan ke Google Sheets dan mengunduh data bursa..."):
        try:
            # Baca sheet tanpa header, skip bad lines agar kebal error kolom
            df_raw = pd.read_csv(URL_PERMANEN, header=None, on_bad_lines='skip')
            
            # KUNCI ABSOLUT: Berdasarkan gambar Anda, data tabel mulai dari Baris 13 (Indeks Python: 12)
            # Kita langsung ambil dari baris ke-14 (Indeks 13) ke bawah untuk daftar sahamnya
            start_idx = 12
            
            if len(df_raw) <= start_idx:
                st.error("Google Sheets Anda kekurangan baris data atau kosong.")
                st.stop()
                
            # Ambil khusus Kolom A (Indeks 0) dari baris setelah header ke bawah
            kode_saham_raw = df_raw.iloc[start_idx+1:, 0].dropna().tolist()
            
            watchlist = []
            for kode in kode_saham_raw:
                kode_clean = str(kode).strip().upper()
                # Filter agar yang diambil hanya kode saham yang valid (biasanya 4-5 karakter huruf)
                if kode_clean and kode_clean != 'NAN' and kode_clean != 'QUOTE' and len(kode_clean) <= 6:
                    # Antisipasi jika di sheet tidak sengaja tertulis angka atau teks aneh
                    if kode_clean.isalpha():
                        watchlist.append(kode_clean + ".JK")
            
            if not watchlist:
                st.error("Gagal membaca kode saham dari Baris 14 ke bawah pada Kolom A. Pastikan kode saham ditulis di Kolom A.")
                st.stop()
                
            st.info(f"🔍 Memindai **{len(watchlist)} saham** dari database Google Sheets Anda...")
            
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
                        
                        # Filter Kondisi Harga > SMA 50
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
                # Sort dari yang paling dekat dengan garis SMA 50
                df_hasil = df_hasil.sort_values(by="Jarak di Atas SMA50", ascending=True)
                
                # Format visual persen
                df_hasil["Jarak di Atas SMA50"] = df_hasil["Jarak di Atas SMA50"].apply(lambda x: f"+{x}%")
                
                st.metric(label="Saham Lolos Filter (Uptrend Jangka Menengah)", value=f"{len(df_hasil)} Saham")
                st.dataframe(df_hasil, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada saham dari database Anda yang saat ini berada di atas SMA 50 (1H).")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan teknis saat membaca file. Deskripsi Error: {e}")
