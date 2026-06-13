import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

# Inisialisasi Session State
if 'memori_saham' not in st.session_state:
    st.session_state['memori_saham'] = {
        "Manual (Default)": [], "Grade A Setup": [], "Grade B Setup": [], "Grade D (Market Merah Cari Alpha)": []
    }

# Sidebar Parameter
st.sidebar.header("⚙️ Parameter Sensor")
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)"])

# Keterangan Preset
if PRESET == "Grade A Setup":
    st.sidebar.info("Grade A:\n\n- Power Play Uptrend\n- Price Above DMA 10 and 50\n- Swing Play")
elif PRESET == "Grade B Setup":
    st.sidebar.info("Grade B:\n\n- Price Above DMA 10 BUT Below DMA 50\n- Fast Trade Play")
elif PRESET == "Grade D (Market Merah Cari Alpha)":
    st.sidebar.info("Grade D:\n\n- 5min Price Above MA50\n- Scalp Play")

FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Prev Close)", ["General", "Intraday Momentum (>0%)"])

# Penyesuaian Timeframe & MA
if PRESET == "Manual (Default)":
    TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=3) # Default ke 50
    FILTER_TREND = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Power Play Uptrend (Price > DMA 10)"])
else:
    TF_PILIHAN = "5 Menit (5m)" if PRESET == "Grade D (Market Merah Cari Alpha)" else "Harian (Daily)"
    MA_PERIODE = 50 
    FILTER_TREND = "General"

tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "1mo"), "15 Menit (15m)": ("15m", "1mo"), "5 Menit (5m)": ("5m", "1mo")}
interval_param, period_param = tf_map[TF_PILIHAN]

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

if MULAI_SCAN:
    with st.spinner("Menjalankan Analisis Multi-Timeframe..."):
        try:
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            watchlist = [k.strip().upper() + ".JK" for k in df_sheet.iloc[:, 0].dropna().astype(str) if len(k.strip()) == 4]
            
            data_daily = yf.download(watchlist, period="2y", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
            data_intra = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=True, progress=False)
            
            hasil_screener = []
            daftar_saham_lolos_sekarang = []
            
            for ticker in watchlist:
                if ticker not in data_daily.columns.levels[0] or ticker not in data_intra.columns.levels[0]: continue
                
                df_d = data_daily[ticker].sort_index().dropna(subset=['Close'])
                df_i = data_intra[ticker].sort_index().dropna(subset=['Close'])
                if df_d.empty or df_i.empty or len(df_d) < 50: continue
                
                # Kalkulasi Data
                dma10 = float(df_d['Close'].rolling(10).mean().iloc[-1])
                dma50 = float(df_d['Close'].rolling(50).mean().iloc[-1])
                prev_close = float(df_d['Close'].iloc[-2])
                
                close = float(df_i['Close'].iloc[-1])
                change_pct = ((close - prev_close) / prev_close) * 100
                
                # Kalkulasi MA Intraday yang dipilih di Sidebar
                ma_target = float(df_i['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                ma10_intra = float(df_i['Close'].rolling(10).mean().iloc[-1])
                ma20_intra = float(df_i['Close'].rolling(20).mean().iloc[-1])
                ma50_intra = float(df_i['Close'].rolling(50).mean().iloc[-1])
                
                # --- LOGIKA FILTER PEMBENAHAN ---
                is_lolos = True
                
                # 1. Filter Preset
                if PRESET == "Grade A Setup": is_lolos = (close > dma10 and close > dma50)
                elif PRESET == "Grade B Setup": is_lolos = (close >= (dma10 * 0.95) and close < dma50)
                elif PRESET == "Grade D (Market Merah Cari Alpha)": is_lolos = (close > ma50_intra)
                
                # 2. Filter Manual: Harus di atas MA yang dipilih di sidebar
                if PRESET == "Manual (Default)":
                    if close <= ma_target:
                        is_lolos = False
                
                # 3. Filter Momentum & Tren Tambahan
                if FILTER_INTRADAY == "Intraday Momentum (>0%)" and change_pct <= 0: is_lolos = False
                if PRESET == "Manual (Default)" and FILTER_TREND == "Power Play Uptrend (Price > DMA 10)" and close <= dma10: is_lolos = False
                
                if is_lolos:
                    clean_code = ticker.replace(".JK", "")
                    daftar_saham_lolos_sekarang.append(clean_code)
                    hasil_screener.append({
                        "Kode Saham": clean_code,
                        "Price": f"Rp{close:,.0f}",
                        "Change %": f"{change_pct:+.2f}%",
                        "% Jarak ke MA10 (1H)": f"{((close - ma10_intra) / ma10_intra) * 100:.2f}%",
                        "% Jarak ke MA20 (1H)": f"{((close - ma20_intra) / ma20_intra) * 100:.2f}%",
                        "% Jarak ke MA50 (1H)": f"{((close - ma50_intra) / ma50_intra) * 100:.2f}%",
                        "Status": "🟢 NEW" if clean_code not in st.session_state['memori_saham'][PRESET] else "🔵 HOLD"
                    })
            
            st.session_state['memori_saham'][PRESET] = daftar_saham_lolos_sekarang
            if hasil_screener:
                df_h = pd.DataFrame(hasil_screener).sort_values(by="Kode Saham")
                st.success("🎯 Pemindaian Selesai!")
                st.metric("Saham Lolos Kriteria", f"{len(df_h)} Saham")
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else: st.warning("Tidak ada saham yang memenuhi kriteria (coba periksa apakah harga sudah di atas MA yang dipilih).")
        except Exception as e: st.error(f"Error: {e}")
