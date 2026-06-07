import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN & INRESIALISASI SESSION STATE (MEMORI SCREENER)
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")
st.write("Saring momentum saham andalan Anda berdasarkan kombinasi Timeframe, Moving Average, dan pergerakan Intraday.")

# Mengamankan memori lintas klik untuk melacak saham mana yang BARU LOLOS FILTER
if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Sensor")

# --- DROPDOWN 1: FILTER INTRADAY MOMENTUM VS OPEN ---
FILTER_INTRADAY = st.sidebar.selectbox(
    "1. Filter Pergerakan Hari Ini (Vs Open)",
    options=["General", "Intraday Momentum (>0%)"],
    index=0
)

# --- DROPDOWN 2: TIMEFRAME EKSEKUSI ---
TF_PILIHAN = st.sidebar.selectbox(
    "2. Pilih Timeframe Eksekusi",
    options=["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"],
    index=0
)

if TF_PILIHAN == "Harian (Daily)":
    interval_param = "1d"
    period_param = "2y"
    label_tf = "Daily"
elif TF_PILIHAN == "1 Jam (1H)":
    interval_param = "1h"
    period_param = "1mo"
    label_tf = "1H"
elif TF_PILIHAN == "30 Menit (30m)":
    interval_param = "30m"
    period_param = "7d"
    label_tf = "30m"
elif TF_PILIHAN == "15 Menit (15m)":
    interval_param = "15m"
    period_param = "7d"
    label_tf = "15m"
else:
    interval_param = "5m"
    period_param = "5d"
    label_tf = "5m"

# --- DROPDOWN 3: PERIODE MA KUSTOM ---
MA_PERIODE = st.sidebar.selectbox(
    "3. Periode Moving Average (MA) Eksekusi",
    options=[5, 10, 20, 50, 200],
    index=1  # Default langsung ke MA 10 agar pas pertama buka langsung match dengan col10 GSheet Anda
)

# --- DROPDOWN 4: FILTER TREN UTAMA ---
FILTER_TREND = st.sidebar.selectbox(
    "4. Filter Tren Utama (Akselerasi)",
    options=["General", "Power Play Uptrend (Price > DMA 10)"],
    index=0
)

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Intraday: **{FILTER_INTRADAY}** | Tren: **{FILTER_TREND}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER (TOTAL AMAN & AMBIL DATA TOLERAN)
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Mengunduh data pasar massal secara instan..."):
        try:
            # Ambil sheet kol_10
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])
            
            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()
            
            watchlist = []
            for kode in watchlist_raw:
                if kode.isalpha() and len(kode) == 4 and kode != 'QUOTE':
                    watchlist.append(kode + ".JK")
            
            if not watchlist:
                st.error("Gagal mendeteksi kode saham yang valid di Google Sheets Anda.")
                st.stop()
                
            st.write(f"🔍 Memproses data untuk **{len(watchlist)} saham**...")
            
            # Unduh data historis dasar secara aman tanpa perataan otomatis (auto_adjust=False)
            data_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "3mo", interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
            
            hasil_screener = []
            daftar_saham_lolos_sekarang = []
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengunduh data: {e}")
            st.stop()

        # Perulangan analisa per saham
        for ticker in watchlist:
            try:
                # Ambil sub-dataframe individual saham secara aman
                if len(watchlist) == 1:
                    df_saham = data_bulk.copy()
                else:
                    if ticker not in data_bulk.columns.levels[0]:
                        continue
                    df_saham = data_bulk[ticker].copy()
                
                # Gunakan kolom 'Close' murni untuk mencocokkan harga penutupan teknikal
                if 'Close' not in df_saham.columns:
                    continue
                    
                df_saham = df_saham.dropna(subset=['Close'])
                if df_saham.empty or len(df_saham) < MA_PERIODE:
                    continue
                
                # Dapatkan nilai harga terakhir dan runtun MA
                harga_hari_ini = float(df_saham['Close'].iloc[-1])
                ma_series = df_saham['Close'].rolling(window=MA_PERIODE).mean()
                ma_hari_ini = float(ma_series.iloc[-1])
                
                # --- FILTER UTAMA BERDASARKAN INPUT FILTER SIDEBAR ---
                # Kondisi Lolos 1: Harga > MA yang Anda pilih di Sidebar
                if harga_hari_ini <= ma_hari_ini:
                    continue
                
                # Kondisi Lolos 2: Filter Intraday (Hanya dijalankan jika user memilih "Intraday Momentum")
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and 'Open' in df_saham.columns:
                    open_hari_ini = float(df_saham['Open'].iloc[-1])
                    if harga_hari_ini < open_hari_ini:
                        continue
                
                # Kondisi Lolos 3: Filter Tren Utama
                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)":
                    ma_10_check = df_saham['Close'].rolling(window=10).mean()
                    if harga_hari_ini < float(ma_10_check.iloc[-1]):
                        continue

                # JIKA LOLOS SEMUA KRITERIA FILTER AKTIF SIDEBAR DI ATAS, MASUKKAN KE TABEL:
                clean_ticker = ticker.replace(".JK", "")
                daftar_saham_lolos_sekarang.append(clean_ticker)
                
                # --- LOGIKA SAKRAL STATUS NEW VIA SESSION STATE ---
                if clean_ticker not in st.session_state['saham_lolos_sebelumnya']:
                    status = "🟢 NEW"
                else:
                    status = "🔵 HOLD"
                
                # Hitung Persentase Perubahan Tampilan
                if 'Open' in df_saham.columns and pd.notna(df_saham['Open'].iloc[-1]):
                    persen_change = ((harga_hari_ini - float(df_saham['Open'].iloc[-1])) / float(df_saham['Open'].iloc[-1])) * 100
                else:
                    persen_change = 0.0
                    
                jarak_ma50 = ((harga_hari_ini - ma_hari_ini) / ma_hari_ini) * 100
                
                hasil_screener.append({
                    "Kode Saham": clean_ticker,
                    "% Change": persen_change,
                    "Jarak ke MA 50 (%)": round(jarak_ma50, 2),
                    "Status": status
                })
            except:
                pass

        # Perbarui memori session state dengan hasil filter klik barusan
        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        # ==============================================================================
        # 3. OUTPUT DAN PENAMPILAN DATA TABEL
        # ==============================================================================
        st.success("🎯 Pemindaian Selesai!")
        
        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            
            # Kelompokkan status NEW otomatis di bagian atas tabel agar mudah dilacak
            df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_hasil = df_hasil.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            
            st.metric(label="Saham Lolos Kriteria", value=f"{len(df_hasil)} Saham")
            
            st.dataframe(
                df_hasil,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                    "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="+%.2f%%")
                }
            )
        else:
            st.warning("Tidak ada saham dari database Anda yang memenuhi kriteria filter aktif saat ini.")
