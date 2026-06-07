# 1. Install/Update library yfinance versi terbaru secara senyap
!pip install yfinance -q

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

# Matikan notifikasi peringatan/warning agar output tabel bersih rapi
warnings.filterwarnings('ignore', category=FutureWarning)

# --- LINK PERMANEN GOOGLE SHEETS ANDA ---
URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

print("⏳ Langkah 1: Mengambil database saham dari Google Sheets...")

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
        print("❌ Gagal mendeteksi kode saham yang valid di Kolom A.")
    else:
        print(f"🔍 Langkah 2: Berhasil memuat {len(watchlist)} saham.")
        print("⚡ Langkah 3: Memulai BULK DOWNLOAD data Intraday 1 Jam (1H)...")

        # TRIK UTAMA UTK COLAB: Tembak semua saham sekaligus (Bulk Request)
        # auto_adjust=False dipasang untuk mengunci kestabilan data intraday (.JK)
        data_bulk = yf.download(watchlist, period="1mo", interval="1h", group_by='ticker', auto_adjust=False, progress=True)

        hasil_screener = []

        # Proses pengolahan data SMA 50 Jam langsung dari memori Colab
        for ticker in watchlist:
            try:
                if len(watchlist) == 1:
                    df_saham = data_bulk.copy()
                else:
                    df_saham = data_bulk[ticker].copy()

                # Pastikan data esensial OHLC tidak kosong
                df_saham = df_saham.dropna(subset=['Close', 'Open', 'High', 'Low'])

                if not df_saham.empty and len(df_saham) >= 50:
                    
                    # 1. AMBIL SERI HARGA CLOSE STANDAR (SQUEEZE UNTUK KESTABILAN KODE)
                    close_prices = df_saham['Close'].squeeze()
                    
                    # 2. KALKULASI SMA 50 JAM BERDASARKAN CLOSE STANDAR
                    df_saham['SMA50'] = close_prices.rolling(window=50).mean()

                    # Ambil data poin live/terakhir berbasis HARGA CLOSE STANDAR
                    harga_terakhir_close = float(close_prices.iloc[-1])
                    nilai_sma50 = float(df_saham['SMA50'].iloc[-1])
                    open_price = float(df_saham['Open'].iloc[-1])
                    
                    # 3. METRIK % CHANGE INTRADAY (Current Close / Open Price)
                    persen_change = ((harga_terakhir_close - open_price) / open_price) * 100

                    # Kondisi Seleksi Utama: Close Terakhir > SMA 50
                    if harga_terakhir_close > nilai_sma50:
                        jarak_persen = ((harga_terakhir_close - nilai_sma50) / nilai_sma50) * 100
                        clean_ticker = ticker.replace(".JK", "")

                        # --- LOGIKA PRICE ACTION ADAPTIF (POLA X ANTM) ---
                        # Candle -2 (Dua jam lalu): Low sempat menguji/berada di bawah SMA 50
                        low_2_lalu = float(df_saham['Low'].iloc[-3])
                        ma_2_lalu = float(df_saham['SMA50'].iloc[-3])
                        
                        # Candle -1 (Satu jam lalu): Batas tertinggi lokal (Garis Horizontal)
                        high_1_lalu = float(df_saham['High'].iloc[-2])

                        # Penentuan Status secara Dinamis berbasis kombinasi Price Action & Garis SMA
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
                pass # Abaikan jika ada satu saham baru yang datanya belum genap 50 jam

        # ==============================================================================
        # PRINT REKAPITULASI HASIL SCREENER
        # ==============================================================================
        print("\n" + "="*85)
        print(f"🎯 PEMINDAIAN TIMEFRAME 1 JAM (1H) SELESAI | WAKTU: {datetime.now().strftime('%H:%M:%S')} WIB")
        print("="*85)

        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            
            # Tambahkan kolom sorting bayangan agar status "🟢 NEW" selalu diprioritaskan di paling atas
            df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_hasil = df_hasil.sort_values(by=["is_new", "Jarak ke SMA50"], ascending=[False, True]).drop(columns=['is_new'])
            
            # Rapikan format tampilan kolom jarak agar memiliki tanda persen
            df_hasil['Jarak ke SMA50'] = df_hasil['Jarak ke SMA50'].apply(lambda x: f"+{x}%")
            
            # Reset nomor urut indeks tabel
            df_hasil.index = range(1, len(df_hasil) + 1)

            print(f"Total Saham Lolos Filter: {len(df_hasil)} Saham\n")
            # Tampilkan tabel interaktif di Google Colab
            display(df_hasil)
        else:
            print("ℹ️ Tidak ada saham yang saat ini bergerak di atas SMA 50 (1H).")

except Exception as e:
    print(f"❌ Terjadi kesalahan teknis: {e}")
