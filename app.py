import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

if 'saham_lolos_sebelumnya' not in st.session_state:
    st.session_state['saham_lolos_sebelumnya'] = []

st.sidebar.header("⚙️ Parameter Sensor")

# --- INPUT PRESET ---
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)"])

# Box Biru Gede sebagai keterangan
if PRESET == "Grade A Setup":
    st.sidebar.info("Grade A: Price > DMA 10 AND Price > DMA 50")
elif PRESET == "Grade B Setup":
    st.sidebar.info("Grade B: Price >= (DMA 10 * 0.97) AND Price < DMA 50")
elif PRESET == "Grade D (Market Merah Cari Alpha)":
    st.sidebar.info("Grade D: 1H Price > MA 20")

# --- PARAMETER INTRADAY ---
FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Open)", ["General", "Intraday Momentum (>0%)"])

# --- PARAMETER MANUAL ---
if PRESET == "Manual (Default)":
    TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1)
    FILTER_TREND = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Power Play Uptrend (Price > DMA 10)"])
else:
    TF_PILIHAN = "1 Jam (1H)" if PRESET == "Grade D (Market Merah Cari Alpha)" else "Harian (Daily)"
    MA_PERIODE = 20
    FILTER_TREND = "General"

tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "7d"), "15 Menit (15m)": ("15m", "7d"), "5 Menit (5m)": ("5m", "5d")}
interval_param, period_param = tf_map[TF_PILIHAN]

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

# ==============================================================================
# 2. LOGIKA UTAMA
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Memproses data..."):
        try:
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            watchlist = [k.strip().upper() + ".JK" for k in df_sheet.iloc[:, 0].dropna().astype(str) if len(k.strip()) == 4]
            data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=False, progress=False)
            
            hasil_screener = []
            daftar_saham_lolos_sekarang = []

            for ticker in watchlist:
                df_s = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                df_s = df_s.dropna(subset=['Close'])
                if df_s.empty or len(df_s) < 50: continue
                
                close = float(df_s['Close'].iloc[-1])
                ma10 = float(df_s['Close'].rolling(10).mean().iloc[-1])
                ma20 = float(df_s['Close'].rolling(20).mean().iloc[-1])
                ma50 = float(df_s['Close'].rolling(50).mean().iloc[-1])
                
                # --- LOGIKA FILTER BERDASARKAN PRESET ---
                is_lolos = False
                if PRESET == "Grade A Setup":
                    is_lolos = (close > ma10 and close > ma50)
                elif PRESET == "Grade B Setup":
                    is_lolos = (close >= (ma10 * 0.97) and close < ma50)
                elif PRESET == "Grade D (Market Merah Cari Alpha)":
                    is_lolos = (close > ma20) # Sesuai request baru
                else: # Manual
                    is_lolos = (close > float(df_s['Close'].rolling(MA_PERIODE).mean().iloc[-1]))
                
                # Filter Intraday
                if is_lolos and FILTER_INTRADAY == "Intraday Momentum (>0%)" and 'Open' in df_s.columns:
                    if close < float(df_s['Open'].iloc[-1]): is_lolos = False
                
                if is_lolos:
                    clean = ticker.replace(".JK", "")
                    daftar_saham_lolos_sekarang.append(clean)
                    status = "🟢 NEW" if clean not in st.session_state['saham_lolos_sebelumnya'] else "🔵 HOLD"
                    hasil_screener.append({
                        "Kode Saham": clean,
                        "% Change": ((close - float(df_s['Open'].iloc[-1])) / float(df_s['Open'].iloc[-1])) * 100,
                        "Jarak ke MA 50 (%)": ((close - ma50) / ma50) * 100,
                        "Status": status
                    })
        except Exception as e: st.error(f"Error: {e}")

        st.session_state['saham_lolos_sebelumnya'] = daftar_saham_lolos_sekarang

        # ==============================================================================
        # 3. OUTPUT
        # ==============================================================================
        if hasil_screener:
            df_h = pd.DataFrame(hasil_screener)
            df_h['is_new'] = df_h['Status'].apply(lambda x: 1 if "NEW" in x else 0)
            df_h = df_h.sort_values(by=["is_new", "Kode Saham"], ascending=[False, True]).drop(columns=['is_new'])
            
            st.success("🎯 Pemindaian Selesai!")
            st.metric(label="Saham Lolos Kriteria", value=f"{len(df_h)} Saham")
            
            st.dataframe(df_h, use_container_width=True, hide_index=True, column_config={
                "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="+%.2f%%")
            })
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria.")
