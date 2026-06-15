import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

st.warning("⚠️ MODE SANDBOX - Fitur Eksperimental - Jangan untuk Trading")

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Ultimate Power Screener", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

# Inisialisasi Session State
if 'memori_saham' not in st.session_state:
    st.session_state['memori_saham'] = {
        "Manual (Default)": [], "Grade A Setup": [], "Grade B Setup": [], 
        "Grade D (Market Merah Cari Alpha)": [], "Hot Start": []
    }

# Sidebar Parameter
st.sidebar.header("⚙️ Parameter Sensor")
PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)", "Hot Start"])

# Keterangan Preset
if PRESET == "Hot Start":
    st.sidebar.info("Hot Start (Snapshot Pagi):\n\n- Mencari lonjakan volume 30 menit pertama (09.00-09.30) > 2.0x baseline rata-rata volume di jam 09.30.")

FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Prev Daily Close)", ["General", "Intraday Momentum (>0%)"])

# Penyesuaian Otomatis Parameter
if PRESET == "Manual (Default)":
    TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"])
    MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1)
elif PRESET == "Hot Start":
    TF_PILIHAN = "15 Menit (15m)"
    MA_PERIODE = 50
else:
    TF_PILIHAN = "5 Menit (5m)" if PRESET == "Grade D (Market Merah Cari Alpha)" else "Harian (Daily)"
    MA_PERIODE = 50 

tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "1mo"), "15 Menit (15m)": ("15m", "1mo"), "5 Menit (5m)": ("5m", "1mo")}
interval_param, period_param = tf_map[TF_PILIHAN]

URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True)

st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

if MULAI_SCAN:
    with st.spinner("Mengambil data terbaru..."):
        try:
            df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
            watchlist = [k.strip().upper() + ".JK" for k in df_sheet.iloc[:, 0].dropna().astype(str) if len(k.strip()) == 4]
            
            data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=True, progress=False)
            data_daily = yf.download(watchlist, period="2d", interval="1d", group_by='ticker', progress=False)
            
            hasil_screener = []
            daftar_saham_lolos_sekarang = []
            
            for ticker in watchlist:
                df_s = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                df_d = data_daily[ticker] if len(watchlist) > 1 else data_daily
                
                df_s = df_s.sort_index().dropna(subset=['Close', 'Open', 'Volume'])
                if df_s.empty or len(df_s) < 10 or df_d.empty: continue
                
                close = float(df_s['Close'].iloc[-1])
                prev_daily_close = float(df_d['Close'].iloc[-2])
                change_pct = ((close - prev_daily_close) / prev_daily_close) * 100
                
                is_lolos = False
                status_keterangan = "🟢 NEW"
                
                if PRESET == "Hot Start":
                    if len(df_s) >= 2:
                        # 1. Total volume 09.00 - 09.30
                        vol_pagi = df_s['Volume'].iloc[0:2].sum()
                        
                        # 2. Snapshot Rata-rata Volume (Dikunci di jam 09.30)
                        vol_rata = df_s['Volume'].rolling(window=10).mean().iloc[1]
                        
                        # Fallback jika data rata-rata masih kosong
                        if pd.isna(vol_rata): vol_rata = df_s['Volume'].iloc[0]
                        
                        if vol_pagi > (vol_rata * 2.0):
                            is_lolos = True
                            status_keterangan = "🔥 HOT START"
                else:
                    ma10 = float(df_s['Close'].rolling(10).mean().iloc[-1])
                    ma50 = float(df_s['Close'].rolling(50).mean().iloc[-1])
                    if PRESET == "Manual (Default)": is_lolos = True
                    elif PRESET == "Grade A Setup": is_lolos = (close > ma10 and close > ma50)
                    elif PRESET == "Grade B Setup": is_lolos = (close >= (ma10 * 0.95) and close < ma50)
                    elif PRESET == "Grade D (Market Merah Cari Alpha)": is_lolos = (close > ma50)
                    
                    if is_lolos and (clean := ticker.replace(".JK", "")) in st.session_state['memori_saham'][PRESET]:
                        status_keterangan = "🔵 HOLD"

                # Filter Final: Momentum vs Prev Daily Close
                if is_lolos and FILTER_INTRADAY == "Intraday Momentum (>0%)":
                    if close <= prev_daily_close:
                        is_lolos = False

                if is_lolos:
                    clean = ticker.replace(".JK", "")
                    daftar_saham_lolos_sekarang.append(clean)
                    hasil_screener.append({"Kode Saham": clean, "Price": f"Rp{close:,.0f}", "Change %": f"{change_pct:+.2f}%", "Status": status_keterangan})
            
            st.session_state['memori_saham'][PRESET] = daftar_saham_lolos_sekarang
            
            if hasil_screener:
                df_h = pd.DataFrame(hasil_screener).sort_values(by="Kode Saham")
                st.subheader(f"Total: {len(df_h)} Saham")
                st.dataframe(df_h, use_container_width=True, hide_index=True, height=(len(df_h) * 35) + 40)
            else:
                st.warning("Tidak ada saham yang memenuhi kriteria.")
        except Exception as e: st.error(f"Error: {e}")
