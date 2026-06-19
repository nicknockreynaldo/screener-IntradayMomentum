import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import math
import gspread
import time

# --- FUNGSI GOOGLE SHEETS ---

def simpan_trade_ke_gsheet(worksheet_name, dataframe):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        
        data_to_append = dataframe.values.tolist()
        wks.append_rows(data_to_append)
        return True, "Sukses"
    except Exception as e:
        return False, str(e)

def tarik_data_dari_gsheet(nama_tab):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        
        # Ganti sh.sheet1 dengan ini agar spesifik per tab
        wks = sh.worksheet("Active_Trades") 
        
        data = wks.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Gagal tarik data dari sheet {nama_tab}: {e}")
        return pd.DataFrame()
        
def append_ke_gsheet(worksheet_name, dataframe_row):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        wks = sh.worksheet(worksheet_name)
        
        # Mengubah baris dataframe menjadi list untuk di-append
        data_to_append = dataframe_row.values.tolist()[0]
        
        wks.append_row(data_to_append)
        return True, "Sukses"
    except Exception as e:
        return False, str(e)


# --- KETERANGAN MODE ---
st.warning("⚠️ MODE SANDBOX WITH GABUNGAN WATCHLIST")

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Screener Suite", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

if 'my_trades' not in st.session_state:
    st.session_state['my_trades'] = pd.DataFrame(columns=[
        "Trade_ID","Tanggal", "Ticker", "Lot", "Entry", "SL", "Jarak SL", "Target", "R-Ratio", "Grade", "Action"
    ])

# Inisialisasi Session State untuk Screener
if 'memori_saham' not in st.session_state:
    st.session_state['memori_saham'] = {
        "Manual (Default)": [], "Grade A Setup": [], "Grade B Setup": [], 
        "Grade D (Market Merah Cari Alpha)": [], "Hot Start": []
    }

# --- KONTROL MENU UTAMA (TABS) ---
# DITAMBAHKAN tab_calc
tab_screener, tab_watchlist, tab_calc, tab_active_trade = st.tabs(["🚀 Screener", "📋 Watchlist", "🧮 Calculator", "📊 Portfolio"])

# ==============================================================================
# TAB 1: CODE ASLI SANDBOX (DIPERTAHANKAN SEPENUHNYA)
# ==============================================================================
with tab_screener:
    # Sidebar Parameter (Khusus untuk Tab Screener)
    st.sidebar.header("⚙️ Parameter Sensor")
    PRESET = st.sidebar.selectbox("Pilih Preset Setup:", ["Manual (Default)", "Grade A Setup", "Grade B Setup", "Grade D (Market Merah Cari Alpha)", "Hot Start"], key="scr_preset")

    # KETERANGAN PRESET
    if PRESET == "Grade A Setup":
        st.sidebar.markdown("""
        <div style="background-color: #d4edda; padding: 10px; border-radius: 5px; color: #155724;">
        <strong>Grade A:</strong><br>
        <ul>
        <li>Power Play Uptrend</li>
        <li>Price Above DMA 10 and 50</li>
        <li>Swing Play</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    elif PRESET == "Grade B Setup":
        st.sidebar.markdown("""
        <div style="background-color: #d1ecf1; padding: 10px; border-radius: 5px; color: #0c5460;">
        <strong>Grade B:</strong><br>
        <ul>
        <li>Price Above DMA 10 BUT Below DMA 50</li>
        <li>Fast Trade Play</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    elif PRESET == "Grade D (Market Merah Cari Alpha)":
        st.sidebar.markdown("""
        <div style="background-color: #f8d7da; padding: 10px; border-radius: 5px; color: #721c24;">
        <strong>Grade D:</strong><br>
        <ul>
        <li>5min Price Above MA50</li>
        <li>Scalp Play</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    elif PRESET == "Hot Start":
        st.sidebar.info("Hot Start (Snapshot Pagi Terkunci):\n\n- Membandingkan volume 30 menit pertama HARI INI > 2x lipat dari rata-rata volume 10 candle terakhir (terkunci di jam 09.30).")
        MIN_VALUE_M = st.sidebar.number_input("Min. Value Pagi (Miliar Rp)", value=5, step=1, key="scr_min_val_m")
        MIN_VALUE = MIN_VALUE_M * 1_000_000_000

    FILTER_INTRADAY = st.sidebar.selectbox("1. Filter Pergerakan Hari Ini (Vs Open)", ["General", "Intraday Momentum (>0%)"], key="scr_filter_intraday")

    # Penyesuaian Otomatis Parameter
    if PRESET == "Manual (Default)":
        TF_PILIHAN = st.sidebar.selectbox("2. Pilih Timeframe Eksekusi", ["Harian (Daily)", "1 Jam (1H)", "30 Menit (30m)", "15 Menit (15m)", "5 Menit (5m)"], key="scr_tf")
        MA_PERIODE = st.sidebar.selectbox("3. Periode Moving Average (MA) Eksekusi", [5, 10, 20, 50, 200], index=1, key="scr_ma")
        FILTER_TREND = st.sidebar.selectbox("4. Filter Tren Utama (Akselerasi)", ["General", "Power Play Uptrend (Price > DMA 10)"], key="scr_trend")
    elif PRESET == "Hot Start":
        TF_PILIHAN = "15 Menit (15m)"
        MA_PERIODE = 50
        FILTER_TREND = "General"
    else:
        TF_PILIHAN = "5 Menit (5m)" if PRESET == "Grade D (Market Merah Cari Alpha)" else "Harian (Daily)"
        MA_PERIODE = 50 
        FILTER_TREND = "General"

    tf_map = {"Harian (Daily)": ("1d", "2y"), "1 Jam (1H)": ("1h", "1mo"), "30 Menit (30m)": ("30m", "1mo"), "15 Menit (15m)": ("15m", "1mo"), "5 Menit (5m)": ("5m", "1mo")}
    interval_param, period_param = tf_map[TF_PILIHAN]

    URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
    MULAI_SCAN = st.sidebar.button("🚀 Start Screening", use_container_width=True, key="scr_btn")

    # JUDUL DINAMIS
    if PRESET == "Hot Start":
        st.title("📈 IHSG Ultimate Power Screener")
    else:
        st.title("📈 IHSG Multi-Timeframe Ultimate Screener")

    if MULAI_SCAN:
        with st.spinner("Mengambil data terbaru..."):
            try:
                df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
                watchlist = [k.strip().upper() + ".JK" for k in df_sheet.iloc[:, 0].dropna().astype(str) if len(k.strip()) == 4]
                
                # 1. Download Data Utama (Sesuai Timeframe Eksekusi No. 2)
                data_bulk = yf.download(watchlist, period=period_param, interval=interval_param, group_by='ticker', auto_adjust=True, progress=False)
                
                # 2. Download Data Harian terpisah untuk menjamin ekstraksi nilai "Daily MA 50" yang valid
                data_daily_bulk = None
                if TF_PILIHAN != "Harian (Daily)":
                    data_daily_bulk = yf.download(watchlist, period="6mo", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
                
                # 3. Download Data 1 JAM terpisah khusus untuk isi kolom display jangkauan (1H)
                data_1h_bulk = None
                if PRESET != "Hot Start":
                    if TF_PILIHAN == "1 Jam (1H)":
                        data_1h_bulk = data_bulk
                    else:
                        data_1h_bulk = yf.download(watchlist, period="1mo", interval="1h", group_by='ticker', auto_adjust=True, progress=False)

                hasil_screener = []
                daftar_saham_lolos_sekarang = []
                
                for ticker in watchlist:
                    df_s = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                    df_s = df_s.sort_index()
                    
                    # SINKRONISASI DATA UTAMA
                    df_s['Close'] = df_s['Close'].ffill()
                    df_s['Open'] = df_s['Open'].fillna(df_s['Close'])
                    df_s['Volume'] = df_s['Volume'].fillna(0)
                    df_s = df_s.dropna(subset=['Close'])
                    
                    # Cek batas candle minimal secara dinamis agar kalkulasi MA tidak error
                    min_candle = MA_PERIODE if PRESET == "Manual (Default)" else 50
                    if df_s.empty or len(df_s) < min_candle: continue
                    
                    is_lolos = False
                    status_keterangan = "🟢 NEW"
                    val_pagi = 0
                    
                    close = float(df_s['Close'].iloc[-1])
                    open_price = float(df_s['Open'].iloc[-1])
                    change_pct = ((close - open_price) / open_price) * 100 if open_price != 0 else 0
                    
                    # Menghitung Moving Averages Utama Internal (Sesuai TF Eksekusi)
                    ma10_internal = float(df_s['Close'].rolling(10).mean().iloc[-1])
                    ma50_internal = float(df_s['Close'].rolling(50).mean().iloc[-1])
                    ma_eksekusi_dinamis = float(df_s['Close'].rolling(window=MA_PERIODE).mean().iloc[-1])
                    
                    # --- LOGIKA EKSTRAKSI DAN KALKULASI DATA HARIAN (AUDIT JANGKAR) ---
                    if TF_PILIHAN == "Harian (Daily)":
                        daily_ma50 = ma50_internal
                        dma10_kunci = ma10_internal
                        d_close = close
                    else:
                        df_d = data_daily_bulk[ticker] if len(watchlist) > 1 else data_daily_bulk
                        df_d = df_d.sort_index()
                        df_d['Close'] = df_d['Close'].ffill()
                        df_d = df_d.dropna(subset=['Close'])
                        
                        # Hitung Nilai Rata-rata 50 Harian yang sesungguhnya
                        if not df_d.empty and len(df_d) >= 50:
                            daily_ma50 = float(df_d['Close'].rolling(50).mean().iloc[-1])
                        else:
                            daily_ma50 = None
                            
                        # Komponen untuk Filter Power Play Uptrend
                        if not df_d.empty and len(df_d) >= 10:
                            dma10_kunci = float(df_d['Close'].rolling(10).mean().iloc[-1])
                            d_close = float(df_d['Close'].iloc[-1])
                        else:
                            dma10_kunci = ma10_internal
                            d_close = close
                    
                    # Hitung Nilai Transaksi Hari Ini untuk keperluan Sorting Latar Belakang
                    hari_ini = df_s.index[-1].date()
                    df_hari_ini = df_s[df_s.index.date == hari_ini]
                    if not df_hari_ini.empty:
                        val_transaksi_sekarang = (df_hari_ini['Close'] * df_hari_ini['Volume']).sum()
                    else:
                        val_transaksi_sekarang = close * float(df_s['Volume'].iloc[-1])
                    
                    # Logic Hot Start
                    if PRESET == "Hot Start":
                        if df_s.index[-1].date() < pd.Timestamp.now().date(): continue
                        
                        df_hari_ini = df_s[df_s.index.date == hari_ini]
                        if len(df_hari_ini) >= 2:
                            vol_pagi = df_hari_ini['Volume'].iloc[0:2].sum()
                            val_pagi = vol_pagi * df_hari_ini['Close'].iloc[0:2].mean()
                            waktu_kunci = df_hari_ini.index[1]
                            vol_rata = df_s['Volume'].rolling(window=10).mean().loc[waktu_kunci]
                            
                            if pd.isna(vol_rata) or vol_rata == 0: vol_rata = df_hari_ini['Volume'].iloc[0]
                            
                            if vol_pagi > (vol_rata * 2.0) and val_pagi >= MIN_VALUE:
                                is_lolos = True
                                status_keterangan = "🔥 HOT START"
                    
                    # Logic Preset Berbasis Multi-Timeframe & Manual Setup
                    else:
                        if PRESET == "Manual (Default)": 
                            # --- KONSEP NESTED IF SELEKSI BERLAPIS ---
                            # IF 1: Validasi Filter No. 3 (Price wajib >= MA Eksekusi pada TF pilihan saat ini)
                            if close >= ma_eksekusi_dinamis:
                                # IF 2: Validasi Filter No. 4 (Filter Tren Utama / Akselerasi)
                                if FILTER_TREND == "Power Play Uptrend (Price > DMA 10)":
                                    # Jika harga memenuhi ambang batas toleransi 3% DMA10 harian, nyatakan lolos
                                    if d_close >= (dma10_kunci * 0.97):
                                        is_lolos = True
                                else:
                                    # Jika Filter Tren Utama adalah "General", otomatis lolos karena IF 1 terpenuhi
                                    is_lolos = True
                                
                        elif PRESET == "Grade A Setup": is_lolos = (close > ma10_internal and close > ma50_internal)
                        elif PRESET == "Grade B Setup": is_lolos = (close >= (ma10_internal * 0.95) and close < ma50_internal)
                        elif PRESET == "Grade D (Market Merah Cari Alpha)": is_lolos = (close > ma50_internal)
                        
                        if is_lolos and (clean := ticker.replace(".JK", "")) in st.session_state['memori_saham'][PRESET]:
                            status_keterangan = "🔵 HOLD"

                    # Filter Intraday Momentum terhadap Harga Open Hari Ini
                    if is_lolos and FILTER_INTRADAY == "Intraday Momentum (>0%)" and change_pct <= 0:
                        is_lolos = False

                    if is_lolos:
                        clean = ticker.replace(".JK", "")
                        daftar_saham_lolos_sekarang.append(clean)
                        
                        # Pembuatan Matriks Display Baris Tabel
                        item_data = {
                            "Kode Saham": clean, 
                            "Price": f"Rp{close:,.0f}", 
                            "Change %": f"{change_pct:+.2f}%",
                            "Daily MA 50": f"Rp{daily_ma50:,.0f}" if daily_ma50 is not None else "N/A" # KOLOM BARU AUDIT
                        }
                        
                        # LOGIKA JANGKAR 1H MURNI UNTUK MATRIKS DISPLAY TABEL
                        if PRESET != "Hot Start":
                            df_1h = data_1h_bulk[ticker] if len(watchlist) > 1 else data_1h_bulk
                            df_1h = df_1h.sort_index()
                            df_1h['Close'] = df_1h['Close'].ffill()
                            df_1h = df_1h.dropna(subset=['Close'])
                            
                            if not df_1h.empty and len(df_1h) >= 50:
                                ma10_1h = float(df_1h['Close'].rolling(10).mean().iloc[-1])
                                ma20_1h = float(df_1h['Close'].rolling(20).mean().iloc[-1])
                                ma50_1h = float(df_1h['Close'].rolling(50).mean().iloc[-1])
                                
                                item_data.update({
                                    "% Jarak ke MA10 (1H)": f"{((close - ma10_1h) / ma10_1h) * 100:+.2f}%",
                                    "% Jarak ke MA20 (1H)": f"{((close - ma20_1h) / ma20_1h) * 100:+.2f}%",
                                    "% Jarak ke MA50 (1H)": f"{((close - ma50_1h) / ma50_1h) * 100:+.2f}%"
                                })
                            else:
                                item_data.update({
                                    "% Jarak ke MA10 (1H)": "N/A",
                                    "% Jarak ke MA20 (1H)": "N/A",
                                    "% Jarak ke MA50 (1H)": "N/A"
                                })
                            
                        item_data.update({
                            "Status": status_keterangan,
                            "val_helper": val_pagi if PRESET == "Hot Start" else val_transaksi_sekarang
                        })
                        hasil_screener.append(item_data)
                
                st.session_state['memori_saham'][PRESET] = daftar_saham_lolos_sekarang
                
                if hasil_screener:
                    df_h = pd.DataFrame(hasil_screener)
                    
                    # LOGIKA SORTING BERDASARKAN VALUE TRANSAKSI TERBESAR (DESCENDING)
                    df_h = df_h.sort_values(by="val_helper", ascending=False)
                    df_h = df_h.drop(columns=["val_helper"])
                    
                    st.success("🎯 Pemindaian Selesai!")
                    st.metric("Saham Lolos Kriteria", f"{len(df_h)} Saham")
                    
                    tabel_height = (len(df_h) + 1) * 35
                    st.dataframe(df_h, use_container_width=True, hide_index=True, height=tabel_height)
                else:
                    st.warning("Tidak ada saham yang memenuhi kriteria.")
            except Exception as e: st.error(f"Error: {e}")

# ==============================================================================
# TAB 2: WATCHLIST MONITOR (SUPER & INTRADAY)
# ==============================================================================
with tab_watchlist:
    # 1. Mengembalikan Header Utama
    st.header("🚀 Super Watchlist")
    
    URL_WL = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv&gid=720440950"
    
    # Ambil data dari sheet (Default)
    if 'default_wl' not in st.session_state:
        try:
            df_wl_raw = pd.read_csv(URL_WL, header=None)
            full_content = []
            for col in df_wl_raw.columns:
                vals = df_wl_raw[col].dropna().astype(str).tolist()
                full_content.extend(vals)
            st.session_state['default_wl'] = ", ".join(full_content)
        except:
            st.session_state['default_wl'] = "BBCA, BMRI, BBNI, UNVR"
            
    input_watchlist_manual = st.text_area(
        "Super Watchlist (Input Manual atau dari Google Sheet):",
        value=st.session_state['default_wl'],
        help="Input otomatis ditarik dari Google Sheet Tab WL (Sel A1)",
        key="wl_manual_input"
    )
    
    # 2. Tombol dibuat pendek (Tanpa use_container_width)
    REFRESH_WATCHLIST = st.button("🚀 Refresh Super Watchlist", key="wl_manual_btn")
    
    if REFRESH_WATCHLIST or input_watchlist_manual:
        with st.spinner("Mengunduh data Super Watchlist..."):
            try:
                raw_wl_tokens = [s.strip().upper() for s in input_watchlist_manual.replace("\n", ",").split(",") if s.strip()]
                watchlist_wl = [s + ".JK" if not s.endswith(".JK") else s for s in raw_wl_tokens if len(s.split(".")[0]) == 4]
                
                if watchlist_wl:
                    # Download 1H untuk MA dan 1D untuk Daily MA
                    data_1h = yf.download(watchlist_wl, period="1mo", interval="1h", group_by='ticker', auto_adjust=True, progress=False)
                    data_1d = yf.download(watchlist_wl, period="3mo", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
                    
                    hasil_watchlist_manual = []
                    
                    for ticker in watchlist_wl:
                        df_1h = data_1h[ticker] if len(watchlist_wl) > 1 else data_1h
                        df_1d = data_1d[ticker] if len(watchlist_wl) > 1 else data_1d
                        
                        df_1h = df_1h.dropna(subset=['Close'])
                        df_1d = df_1d.dropna(subset=['Close'])
                        
                        if df_1h.empty or df_1d.empty: continue
                        
                        close = float(df_1h['Close'].iloc[-1])
                        ma10_1h = float(df_1h['Close'].rolling(10).mean().iloc[-1])
                        ma20_1h = float(df_1h['Close'].rolling(20).mean().iloc[-1])
                        ma50_1h = float(df_1h['Close'].rolling(50).mean().iloc[-1])
                        ma10_daily = float(df_1d['Close'].rolling(10).mean().iloc[-1])
                        
                        hasil_watchlist_manual.append({
                            "Kode Saham": ticker.replace(".JK", ""),
                            "Price": f"Rp{close:,.0f}",
                            "% Dist to Daily MA 10": f"{((close - ma10_daily) / ma10_daily) * 100:+.2f}%",
                            "% Dist to MA10 (1H)": f"{((close - ma10_1h) / ma10_1h) * 100:+.2f}%",
                            "% Jarak ke MA20 (1H)": f"{((close - ma20_1h) / ma20_1h) * 100:+.2f}%",
                            "% Jarak ke MA50 (1H)": f"{((close - ma50_1h) / ma50_1h) * 100:+.2f}%"
                        })
                    
                    if hasil_watchlist_manual:
                        st.dataframe(pd.DataFrame(hasil_watchlist_manual), use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Error: {e}")

    st.markdown("---")

    # --- 2. INTRADAY MOMENTUM WATCHLIST (TF: 5m) ---
    st.subheader("⚡ Intraday Momentum Watchlist")
    input_intra = st.text_area("Input Watchlist Intraday Manual:", value="", key="input_intra")
    btn_intra = st.button("⚡ Refresh Intraday Watchlist", key="btn_intra")

    if btn_intra and input_intra:
        with st.spinner("Loading Intraday Data..."):
            try:
                tokens = [s.strip().upper() for s in input_intra.replace("\n", ",").split(",") if s.strip()]
                wl = [s + ".JK" if not s.endswith(".JK") else s for s in tokens if len(s.split(".")[0]) == 4]
                
                data_1h = yf.download(wl, period="1mo", interval="1h", group_by='ticker', auto_adjust=True, progress=False)
                data_1d = yf.download(wl, period="3mo", interval="1d", group_by='ticker', auto_adjust=True, progress=False)
                data_5m = yf.download(wl, period="1d", interval="5m", group_by='ticker', auto_adjust=True, progress=False)
                
                hasil = []
                for ticker in wl:
                    # Menggunakan .xs (cross-section) agar struktur kolom selalu flat (Open, Close, Volume)
                    # baik untuk 1 ticker maupun banyak ticker
                    df_1h = data_1h.xs(ticker, axis=1, level=0, drop_level=True)
                    df_1d = data_1d.xs(ticker, axis=1, level=0, drop_level=True)
                    df_5m = data_5m.xs(ticker, axis=1, level=0, drop_level=True)
                    
                    df_1h = df_1h.dropna(subset=['Close'])
                    df_1d = df_1d.dropna(subset=['Close'])
                    df_5m = df_5m.dropna(subset=['Close', 'Volume'])
                    
                    if df_1h.empty or df_1d.empty or df_5m.empty: continue
                    
                    close = float(df_1h['Close'].iloc[-1])
                    ma10_1h = float(df_1h['Close'].rolling(10).mean().iloc[-1])
                    ma20_1h = float(df_1h['Close'].rolling(20).mean().iloc[-1])
                    ma50_1h = float(df_1h['Close'].rolling(50).mean().iloc[-1])
                    ma10_daily = float(df_1d['Close'].rolling(10).mean().iloc[-1])
                    
                   
                  # Ganti logika perhitungan vwap menjadi OHLC/4 (sesuai preferensi profesional)
                    ohlc_avg = (df_5m['Open'] + df_5m['High'] + df_5m['Low'] + df_5m['Close']) / 4
                    vwap = (ohlc_avg * df_5m['Volume']).sum() / df_5m['Volume'].sum()
                                                            
                    hasil.append({
                        "Kode Saham": ticker.replace(".JK", ""),
                        "Price": f"Rp{close:,.0f}",
                        "% Dist to Daily MA 10": f"{((close - ma10_daily) / ma10_daily) * 100:+.2f}%",
                        "% Dist to MA10 (1H)": f"{((close - ma10_1h) / ma10_1h) * 100:+.2f}%",
                        "% Jarak ke MA20 (1H)": f"{((close - ma20_1h) / ma20_1h) * 100:+.2f}%",
                        "% Jarak ke MA50 (1H)": f"{((close - ma50_1h) / ma50_1h) * 100:+.2f}%",
                        "VWAP Intraday": f"Rp{vwap:,.0f}",
                        "Dist to VWAP %": f"{((close - vwap) / vwap) * 100:+.2f}%"
                    })
                if hasil: st.dataframe(pd.DataFrame(hasil), use_container_width=True, hide_index=True)
            except Exception as e: st.error(f"Error: {e}")
# ==============================================================================
# TAB 3: RISK CALCULATOR
# ==============================================================================
with tab_calc:
    st.header("🧮 Position Sizing & Risk Management")
    # --- INFORMASI TARGET (Tabel Ringkas Horizontal) ---
    
    # CSS Injection untuk Center Alignment (Mencakup st.table dan st.data_editor)
    st.markdown("""
        <style>
            /* Untuk st.table */
            table { text-align: center !important; }
            th { text-align: center !important; }
            td { text-align: center !important; }
            
            /* Untuk st.data_editor */
            [data-testid="stDataEditor"] {
                text-align: center !important;
            }
            [data-testid="stDataEditor"] div[data-testid="stText"] {
                text-align: center !important;
            }
            /* Memaksa isi sel di data editor rata tengah */
            [data-testid="stDataEditor"] .st-emotion-cache-1vt4y4j {
                justify-content: center !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
  
    # Pastikan urutan kolom di sini SAMA PERSIS dengan di new_row
    if 'my_trades' not in st.session_state:
        st.session_state['my_trades'] = pd.DataFrame(columns=[
            "Trade_ID", "Tanggal", "Ticker", "Lot", "Entry", "SL", "Jarak SL", "Target", "R-Ratio", "Grade", "Action"
        ])

    # --- INPUT SECTION ---
    c1, c2 = st.columns(2)
    MODAL = c1.number_input("Modal Trading (Rp)", value=100_000_000, step=1_000_000)
    c1.caption(f"Modal: Rp {f'{MODAL:,.0f}'.replace(',', '.')}")
    
    # Penambahan Setup Grade
    grade_in = c2.selectbox("Setup Grade", ["A", "B", "C", "D"], index=1)
    risk_map = {"A": 1.5, "B": 1.0, "C": 0.5, "D": 0.2}
    
    # Slider dengan nilai default mengikuti Grade
    RISK_PCT = c2.slider("Risk per Trade (%)", 0.1, 5.0, risk_map[grade_in], step=0.1) / 100
    
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    ticker_in = col_in1.text_input("Ticker", "BBCA").upper()
    entry_in = col_in2.number_input("Entry Price", value=6000)
    sl_in = col_in3.number_input("Stop Loss Price", value=5800)
    manual_tp = col_in4.number_input("Target Manual", value=6300, step=1, format="%d")
    
    # --- KALKULASI ---
    risk_amount = MODAL * RISK_PCT
    risk_per_share = entry_in - sl_in
    risk_dist_pct = (risk_per_share / entry_in) * 100
    r_manual = (manual_tp - entry_in) / risk_per_share if risk_per_share != 0 else 0
    lot_max = math.floor((risk_amount / risk_per_share) / 100) if risk_per_share != 0 else 0

    # --- METRICS PINK BACKGROUND ---
    def style_metric_pink(label, value):
        st.markdown(f"""
            <div style="background-color: #ffe6e6; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #ffcccc;">
                <div style="font-size: 14px; color: #555;">{label}</div>
                <div style="font-size: 24px; font-weight: bold; color: #000;">{value}</div>
            </div>
        """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    with m1: style_metric_pink("Risk Amount", f"Rp{int(risk_amount):,.0f}")
    with m2: style_metric_pink("Max Lot", f"{lot_max} Lot")
    with m3: style_metric_pink("Jarak SL", f"{risk_dist_pct:.2f}%")

    st.markdown("---")

    # --- TARGET PRICE MULTIPLE ---
    st.subheader("🎯 Risk Multiple")
    df_target_ringkas = pd.DataFrame({
        "1.5R": [f"{entry_in + (risk_per_share * 1.5):,.0f}"],
        "2R": [f"{entry_in + (risk_per_share * 2):,.0f}"],
        "3R": [f"{entry_in + (risk_per_share * 3):,.0f}"],
        "Manual TP": [f"{manual_tp:,.0f} ({r_manual:.2f}R)"]
    })
    st.table(df_target_ringkas)

    # --- BUTTON TAMBAH ---
    if st.button("➕ Tambah ke Daftar Pre-Trade"):
        new_row = pd.DataFrame([{
            "Tanggal": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "Ticker": ticker_in,
            "Lot": lot_max,
            "Entry": entry_in,
            "SL": sl_in,
            "Jarak SL": f"{risk_dist_pct:.2f}%",
            "Target": manual_tp,
            "R-Ratio": f"{r_manual:.2f}R",
            "Grade": grade_in,
            "Action": False
        }])
        st.session_state['my_trades'] = pd.concat([st.session_state['my_trades'], new_row], ignore_index=True)
        st.rerun()

    # --- DAFTAR PRE-TRADE ---
    st.subheader("📋 Daftar Pre-Trade")
    edited_df = st.data_editor(
        st.session_state['my_trades'],
        column_config={
            "Action": st.column_config.CheckboxColumn("Action", default=False)
        },
        use_container_width=True,
        hide_index=True
    )
    
    c_act1, c_act2 = st.columns(2)
  # Confirm Trade
    if c_act1.button("🚀 Confirm Trade"):
        for _, row in st.session_state['my_trades'].iterrows():
            # Generate Trade_ID unik: [Waktu Detik].[Ticker]
            # Contoh: 1718695200.BBCA
            trade_id = f"{int(time.time())}.{row['Ticker']}"
            
            # Kirim ke GSheet dengan Trade_ID sebagai kolom pertama (kolom A)
            df_to_send = pd.DataFrame([{
                "Trade_ID": trade_id,
                "Tanggal": row['Tanggal'],
                "Ticker": row['Ticker'],
                "Lot": row['Lot'],
                "Avg_Entry": row['Entry'],
                "SL": row['SL'],
                "Jarak SL": row['Jarak SL'],
                "Target": row['Target'],
                "Risk Multiple": row['R-Ratio'],
                "Grade": row['Grade']
            }])

            # 1. Kirim ke sheet Pre Trade (10 Kolom)
            simpan_trade_ke_gsheet("Pre_Trades", df_to_send)
        
            # 2. Kirim ke sheet Active Trade (10 Kolom - Sama persis!)
            simpan_trade_ke_gsheet("Active_Trades", df_to_send)
            
        st.success("Trade berhasil dikonfirmasi!")
        # Reset list
        st.session_state['my_trades'] = pd.DataFrame(columns=[
            "Tanggal", "Ticker", "Lot", "Entry", "SL", "Jarak SL", "Target", "R-Ratio", "Grade", "Action"
        ])
        st.rerun()
    

    # Hapus Baris
    if c_act2.button("🗑️ Hapus Baris Terpilih"):
        # Filter menggunakan kolom 'Action'
        st.session_state['my_trades'] = edited_df[edited_df["Action"] == False]
        st.rerun()
        
# ==============================================================================
# TAB 4: ACTIVE TRADE
# ==============================================================================

with tab_active_trade:
    st.header("⚡ Active Trade Management")

    # --- 1. SOLUSI ANTI-MEMBAL: Inisialisasi nomor versi key editor ---
    if 'editor_version' not in st.session_state:
        st.session_state.editor_version = 0

    # Proteksi pembersihan memori jika tipe data salah
    if 'df_active' in st.session_state:
        if not isinstance(st.session_state.df_active, pd.DataFrame):
            del st.session_state.df_active

    # Tarik data asli dari Google Sheets
    if 'df_active' not in st.session_state:
        raw_data = tarik_data_dari_gsheet("Active_Trades")
        if isinstance(raw_data, pd.DataFrame):
            st.session_state.df_active = raw_data
        elif isinstance(raw_data, list) and len(raw_data) > 0:
            st.session_state.df_active = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        else:
            st.session_state.df_active = pd.DataFrame(columns=[
                'Trade_ID', 'Tanggal', 'Ticker', 'Lot', 'Avg_Entry', 
                'SL', 'Jarak SL', 'Target', 'Risk Multiple', 'Grade'
            ])

    # 2. Sembunyikan kolom kalkulasi dari UI tampilan
    df_temp = st.session_state.df_active.copy()
    cols_to_hide = ['Jarak SL', 'Risk Multiple', 'Grade']
    cols_to_show = [c for c in df_temp.columns if c not in cols_to_hide]
    df_clean = df_temp[cols_to_show]

    st.subheader("📝 Live Position Monitor")

    # 3. Form Editor dengan Key Versi Dinamis
    with st.form("editor_form"):
        # Kita buat nama key berubah setiap kali berhasil sync (misal: v_0, v_1, v_2)
        # Cara ini otomatis menghapus cache memori lama dengan aman tanpa memicu StreamlitAPIException
        dynamic_key = f"active_trade_editor_v_{st.session_state.editor_version}"
        
        edited_df = st.data_editor(
            df_clean,
            column_config={
                "Trade_ID": st.column_config.TextColumn("Trade ID", disabled=True),
                "Tanggal": st.column_config.TextColumn("Tanggal", disabled=True),
                "Ticker": st.column_config.TextColumn("Ticker", disabled=True),
                "SL": st.column_config.NumberColumn("SL", disabled=True),
                "Target": st.column_config.NumberColumn("Target", disabled=True),
                "Lot": st.column_config.NumberColumn("Total Lot"),
                "Avg_Entry": st.column_config.NumberColumn("Avg Entry", format="Rp %d"),
            },
            hide_index=True,
            use_container_width=True,
            key=dynamic_key
        )
        
        submitted = st.form_submit_button("💾 Sync & Save Changes")
        
        if submitted:
            # Ambil data langsung dari variabel tabel
            updated_data = edited_df
            
            # Gabungkan ke master_df agar kolom tersembunyi tidak ikut hilang
            master_df = st.session_state.df_active.copy()
            for col in ['Lot', 'Avg_Entry']:
                if col in updated_data.columns:
                    master_df[col] = updated_data[col]
            
            master_df = master_df.fillna("")

            # Kirim data ke GSheet
            success, msg = simpan_trade_ke_gsheet("Active_Trades", master_df)
            if success:
                # Update memori lokal data master
                st.session_state.df_active = master_df
                
                # NAIKKAN VERSI KEY: Trik utama untuk mereset cache editor tanpa error
                st.session_state.editor_version += 1
                
                st.success("Data berhasil di-sync!")
                st.rerun() # Refresh halaman dengan key baru yang bersih total
            else:
                st.error(f"Gagal simpan ke GSheet: {msg}")
