import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Screener", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

# Inisialisasi State untuk status HOLD/NEW
if 'memori_saham' not in st.session_state:
    st.session_state['memori_saham'] = {
        "Manual (Default)": [], "Grade A Setup": [], "Grade B Setup": [], 
        "Grade D (Market Merah Cari Alpha)": [], "Hot Start": []
    }

# Sidebar Parameter
st.sidebar.header("⚙️ Parameter Sensor")
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)", "Hot Start"])

# Konfigurasi UI berdasarkan Preset
if PRESET == "Hot Start":
    st.title("📈 IHSG Ultimate Power Screener")
    MIN_VALUE_M = st.sidebar.number_input("Min. Value Pagi (Miliar Rp)", value=5, step=1)
    MIN_VALUE = MIN_VALUE_M * 1_000_000_000
    st.sidebar.info(f"Filter: Volume 2x Rata-rata & Value >= {MIN_VALUE_M} Miliar")
else:
    st.title("📈 IHSG Multi-Timeframe Ultimate Screener")
    FILTER_TREN = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Bullish (>MA50)"])

FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Prev Daily Close)", ["General", "Intraday Momentum (>0%)"])
TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1)

tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "1mo"), "15 Menit (15m)": ("15m", "1mo"), "5 Menit (5m)": ("5m", "1mo")}
interval_param, period_param = tf_map[TF_PILIHAN]

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"

if st.sidebar.button("🚀 Start Screening", use_container_width=True):
    with st.spinner("Mengolah data..."):
        try:
            watchlist = [k.strip().upper() + ".JK" for k in pd.read_csv(URL_PERMANEN, usecols=[0]).iloc[:, 0].dropna().astype(str)]
            data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', progress=False)
            data_daily = yf.download(watchlist, period="2d", interval="1d", group_by='ticker', progress=False)
            
            hasil = []
            daftar_saham_lolos = []
            
            for ticker in watchlist:
                df_s = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                df_d = data_daily[ticker] if len(watchlist) > 1 else data_daily
                df_s = df_s.sort_index().dropna(subset=['Close', 'Volume'])
                
                if df_s.empty or len(df_s) < 50: continue
                
                close = float(df_s['Close'].iloc[-1])
                prev_close = float(df_d['Close'].iloc[-2])
                ma10 = float(df_s['Close'].rolling(10).mean().iloc[-1])
                ma20 = float(df_s['Close'].rolling(20).mean().iloc[-1])
                ma50 = float(df_s['Close'].rolling(50).mean().iloc[-1])
                
                is_lolos = False
                val_pagi = 0
                status_keterangan = "🟢 NEW"
                
                if PRESET == "Hot Start":
                    hari_ini = df_s.index[-1].date()
                    df_h_ini = df_s[df_s.index.date == hari_ini]
                    if len(df_h_ini) >= 2:
                        vol_pagi = df_h_ini['Volume'].iloc[0:2].sum()
                        val_pagi = vol_pagi * df_h_ini['Close'].iloc[0:2].mean()
                        waktu_kunci = df_h_ini.index[1]
                        vol_rata = df_s['Volume'].rolling(window=10).mean().loc[waktu_kunci]
                        if vol_pagi > (vol_rata * 2.0) and val_pagi >= MIN_VALUE: is_lolos = True
                else:
                    if PRESET == "Manual (Default)": is_lolos = True
                    elif PRESET == "Grade A Setup": is_lolos = (close > ma10 and close > ma50)
                    elif PRESET == "Grade B Setup": is_lolos = (close >= (ma10 * 0.95) and close < ma50)
                    elif PRESET == "Grade D (Market Merah Cari Alpha)": is_lolos = (close > ma50)
                    
                    if FILTER_TREN == "Bullish (>MA50)" and close < ma50: is_lolos = False
                    if is_lolos and (ticker.replace(".JK", "") in st.session_state['memori_saham'][PRESET]):
                        status_keterangan = "🔵 HOLD"

                if is_lolos and FILTER_INTRADAY == "Intraday Momentum (>0%)" and close <= prev_close: is_lolos = False

                if is_lolos:
                    ticker_clean = ticker.replace(".JK", "")
                    daftar_saham_lolos.append(ticker_clean)
                    change = ((close - prev_close) / prev_close) * 100
                    
                    if PRESET == "Hot Start":
                        hasil.append({"Kode Saham": ticker_clean, "Price": f"Rp{close:,.0f}", "Value Pagi (M)": round(val_pagi/1e9, 1), "Change %": f"{change:+.2f}%", "Status": status_keterangan})
                    else:
                        hasil.append({"Kode Saham": ticker_clean, "Price": f"Rp{close:,.0f}", "Change %": f"{change:+.2f}%", "% Jarak ke MA10": f"{(close-ma10)/ma10*100:.2f}%", "% Jarak ke MA20": f"{(close-ma20)/ma20*100:.2f}%", "% Jarak ke MA50": f"{(close-ma50)/ma50*100:.2f}%", "Status": status_keterangan})

            st.session_state['memori_saham'][PRESET] = daftar_saham_lolos
            if hasil:
                df_res = pd.DataFrame(hasil)
                if PRESET == "Hot Start": df_res = df_res.sort_values(by="Value Pagi (M)", ascending=False)
                st.success("Pemindaian Selesai!")
                st.dataframe(df_res, use_container_width=True, hide_index=True)
            else: st.warning("Tidak ada saham yang memenuhi kriteria.")
        except Exception as e: st.error(f"Error: {e}")
