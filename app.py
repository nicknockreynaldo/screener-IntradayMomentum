import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi halaman
st.set_page_config(page_title="IHSG Power Screener", layout="wide")
st.title("📈 IHSG Ultimate Power Screener")

# Inisialisasi session state
if 'saham_per_parameter' not in st.session_state:
    st.session_state['saham_per_parameter'] = {}

st.sidebar.header("⚙️ Parameter Setup")

# 1. PRESET SELECTOR
PRESET = st.sidebar.selectbox("Pilih Setup:", ["Custom", "Grade A Setup", "Grade B Setup"])

# Logic untuk Auto-fill
def get_preset_values(preset_name):
    if preset_name == "Grade A Setup":
        return {"TF": "Harian (Daily)", "MA": 50, "Intraday": "Intraday Momentum (>0%)"}
    elif preset_name == "Grade B Setup":
        return {"TF": "Harian (Daily)", "MA": 50, "Intraday": "Intraday Momentum (>0%)"}
    return None

defaults = get_preset_values(PRESET)

# 2. DROPDOWN MANUAL (Default mengikuti preset)
tf_options = ["1d", "1h"] # Sesuai kebutuhan Anda
ma_options = [5, 10, 20, 50, 200]
intra_options = ["General", "Intraday Momentum (>0%)"]

TF_PILIHAN = st.sidebar.selectbox("Timeframe:", tf_options, index=0 if not defaults else tf_options.index("1d"))
MA_PERIODE = st.sidebar.selectbox("Periode MA (sebagai referensi):", ma_options, index=3 if not defaults else ma_options.index(defaults["MA"]))
FILTER_INTRADAY = st.sidebar.selectbox("Filter Intraday:", intra_options, index=1 if defaults else 0)

# --- LOGIKA FILTER UTAMA ---
def screening_logic(df, ma_period, preset):
    curr_price = df['Close'].iloc[-1]
    curr_open = df['Open'].iloc[-1]
    
    # Hitung DMA
    dma10 = df['Close'].rolling(10).mean().iloc[-1]
    dma50 = df['Close'].rolling(ma_period).mean().iloc[-1]
    
    # Toleransi 3% dari DMA10
    tolerance = 0.97 * dma10
    
    # Filter Intraday
    if FILTER_INTRADAY == "Intraday Momentum (>0%)" and curr_price <= curr_open:
        return False
    
    # Filter Grade A & B
    if preset == "Grade A Setup":
        # Price > dma50 DAN price > tolerance (3% di bawah dma10)
        return curr_price > dma50 and curr_price >= tolerance
    elif preset == "Grade B Setup":
        # Price < dma50 DAN price > tolerance (3% di bawah dma10)
        return curr_price < dma50 and curr_price >= tolerance
    
    return True # Default untuk Custom

if st.sidebar.button("🚀 Start Screening"):
    st.write(f"Menjalankan: {PRESET}")
    
    # KUNCI UNIK (Agar status NEW stabil)
    kunci = f"{TF_PILIHAN}_{MA_PERIODE}_{FILTER_INTRADAY}_{PRESET}"
    
    # ... Masukkan fungsi download dan screening Anda di sini ...
    # Di dalam loop saham, panggil: 
    # if screening_logic(df_saham, MA_PERIODE, PRESET): ...
    
    st.success("Screening Selesai!")
