import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN & INRESIALISASI SESSION STATE
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Sensor")

# --- TAMBAHAN: DROPDOWN PRESET ---
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)"])

# Menambahkan keterangan di bawah dropdown
if PRESET == "Grade A Setup":
    st.sidebar.caption("Grade A - Price Above DMA 10 AND DMA 50")
elif PRESET == "Grade B Setup":
    st.sidebar.caption("Grade B - Price Above DMA 10 But Below DMA 50")
elif PRESET == "Grade D (Market Merah Cari Alpha)":
    st.sidebar.caption("Grade D - 1H Price Above MA10")

# Logika penentuan nilai default per preset
if PRESET == "Grade D (Market Merah Cari Alpha)":
    d_tf, d_ma, d_trend = "1 Jam (1H)", 20, "General"
elif PRESET == "Grade A Setup" or PRESET == "Grade B Setup":
    d_tf, d_ma, d_trend = "Harian (Daily)", 50, "General"
else:
    d_tf, d_ma, d_trend = "Harian (Daily)", 10, "General"

# --- PARAMETER INTRADAY (TETAP MUNCUL) ---
FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Open)", ["General", "Intraday Momentum (>0%)"], index=0)

# --- PARAMETER LAIN (HANYA MUNCUL DI MODE MANUAL) ---
if PRESET == "Manual (Default)":
    TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1)
    FILTER_TREND = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Power Play Uptrend (Price > DMA 10)"])
else:
    TF_PILIHAN, MA_PERIODE, FILTER_TREND = d_tf, d_ma, d_trend

# Logika Mapping Timeframe
if TF_PILIHAN == "Harian (Daily)":
    interval_param, period_param, label_tf = "1d", "2y", "Daily"
elif TF_PILIHAN == "1 Jam (1H)":
    interval_param, period_param, label_tf = "1h", "1mo", "1H"
elif TF_PILIHAN == "30 Menit (30m)":
    interval_param, period_param, label_tf = "30m", "7d", "30m"
elif TF_PILIHAN == "15 Menit (15m)":
    interval_param, period_param, label_tf = "15m", "7d", "15m"
else:
    interval_param, period_param, label_tf = "5m", "5d", "5m"

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.info(f"📋 **Kondisi Aktif:** Harga > SMA {MA_PERIODE} ({label_tf}) | Intraday: **{FILTER_INTRADAY}** | Tren: **{FILTER_TREND}**")

# ==============================================================================
# 2. LOGIKA UTAMA SCREENER
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Mengunduh data pasar massal secara instan..."):
        try:
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            df_sheet.columns = ['Quote']
            df_sheet = df_sheet.dropna(subset=['Quote'])
            watchlist_raw = df_sheet['Quote'].astype(str).str.strip().str.upper().tolist()
            watchlist = [kode + ".JK" for kode in watchlist_raw if kode.isalpha() and len(kode.strip()) == 4 and kode != 'QUOTE']
            
            if not watchlist:
                st.error("Gagal mendeteksi kode saham yang valid.")
                st.stop()
            
            data_bulk = yf.download(watchlist, period="2y" if interval_param == "1d" else "3mo", interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
            
            hasil_screener = []
            daftar_saham_lolos_sekarang = []
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}"); st.stop()

        for ticker in watchlist:
            try:
                df_saham = data_bulk[ticker] if len(watchlist) == 1 else data_bulk[ticker]
                df_saham = df_saham.dropna(subset=['Close'])
                if df_saham.empty or len(df_saham) < MA_PERIODE: continue
                
                harga_hari_ini = float(df_saham['Close'].iloc[-1])
                ma_hari_ini = float(df_saham['Close'].rolling(window=MA_PERIODE).mean().iloc[-1])
                
                if harga_hari_ini <= ma_hari_ini: continue
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and 'Open' in df_saham.columns and harga_hari_ini < float(df_saham['Open'].iloc[-1]): continue
                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)" and harga_hari_ini < float(df_saham['Close'].rolling(window=10).mean().iloc[-1]): continue

                clean_ticker = ticker.replace(".JK", "")
                daftar_saham_lolos_sekarang.append(clean_ticker)
                status = "🟢 NEW" if clean_ticker not in st.session_state['saham_lolos_sebelumnya'] else "🔵 HOLD"
                
                persen_change = ((harga_hari_ini - float(df_saham['Open'].iloc[-1])) / float(df_saham['Open'].iloc[-1])) * 100 if 'Open' in df_saham.columns else 0.0
                jarak_ma50 = ((harga_hari_ini - ma_hari_ini) / ma_hari_ini) * 100
                
                hasil_screener.append({
                    "Kode Saham": clean_ticker,
                    "% Change": persen_change,
                    "Jarak ke MA 50 (%)": round(jarak_ma50, 2),
                    "Status": status
                })
            except: pass

        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        # ==============================================================================
        # 3. OUTPUT
        # ==============================================================================
        st.success("🎯 Pemindaian Selesai!")
        if hasil_screener:
            df_hasil = pd.DataFrame(hasil_screener)
            df_hasil['is_new'] = df_hasil['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_hasil = df_hasil.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            st.metric("Saham Lolos Kriteria", f"{len(df_hasil)} Saham")
            st.dataframe(df_hasil, use_container_width=True, hide_index=True, column_config={
                "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="+%.2f%%")
            })
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
