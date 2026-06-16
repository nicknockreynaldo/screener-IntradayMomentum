import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import math

# --- KETERANGAN MODE ---
st.warning("⚠️ MODE SANDBOX WITH GABUNGAN WATCHLIST")

# Pengaturan Halaman
st.set_page_config(page_title="IHSG Screener Suite", page_icon="📈", layout="wide")
warnings.filterwarnings('ignore')

# Inisialisasi Session State untuk Screener
if 'memori_saham' not in st.session_state:
    st.session_state['memori_saham'] = {
        "Manual (Default)": [], "Grade A Setup": [], "Grade B Setup": [], 
        "Grade D (Market Merah Cari Alpha)": [], "Hot Start": []
    }

# --- KONTROL MENU UTAMA (TABS) ---
tab_screener, tab_watchlist = st.tabs(["🚀 Sandbox Ultimate Screener", "📋 Manual Watchlist Monitor (TF: 1H)"])

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
# TAB 2: INJEKSI FITUR MANUAL WATCHLIST MONITOR (TOTAL PASS TANPA FILTER)
# ==============================================================================
with tab_watchlist:
    st.header("📋 Manual Watchlist Monitor (TF: 1 Hour)")
    st.markdown("Pantau pergerakan data teknikal asli tanpa filter eliminasi untuk seluruh saham yang Anda ketik mandiri di bawah ini.")
    
    # Text area untuk menampung input kode-kode saham pilihan harian Anda
    input_watchlist_manual = st.text_area(
        "Masukkan Kode Saham Pilihan Anda (pisahkan dengan koma atau enter):",
        value="BBCA, BMRI, BBNI, UNVR",
        help="Contoh input: BBRI, TLKM, ASII, GOTO",
        key="wl_manual_input"
    )
    
    REFRESH_WATCHLIST = st.button("🔄 Refresh Data Watchlist", use_container_width=True, key="wl_manual_btn")
    
    if REFRESH_WATCHLIST or input_watchlist_manual:
        with st.spinner("Mengunduh data khusus watchlist manual..."):
            try:
                # Parsing string input menjadi list ticker bersih (.JK)
                raw_wl_tokens = [s.strip().upper() for s in input_watchlist_manual.replace("\n", ",").split(",") if s.strip()]
                watchlist_wl = [s + ".JK" if not s.endswith(".JK") else s for s in raw_wl_tokens if len(s.split(".")[0]) == 4]
                
                if watchlist_wl:
                    # Mengunci download data massal khusus ke timeframe 1 Jam (1h)
                    data_bulk_wl = yf.download(watchlist_wl, period="1mo", interval="1h", group_by='ticker', auto_adjust=True, progress=False)
                    hasil_watchlist_manual = []
                    
                    for ticker in watchlist_wl:
                        df_wl_single = data_bulk_wl[ticker] if len(watchlist_wl) > 1 else data_bulk_wl
                        df_wl_single = df_wl_single.sort_index()
                        
                        df_wl_single['Close'] = df_wl_single['Close'].ffill()
                        df_wl_single['Open'] = df_wl_single['Open'].fillna(df_wl_single['Close'])
                        df_wl_single['Volume'] = df_wl_single['Volume'].fillna(0)
                        df_wl_single = df_wl_single.dropna(subset=['Close'])
                        
                        # Pengaman data jika baris saham baru listing kurang dari 50 baris candle 1H
                        if df_wl_single.empty or len(df_wl_single) < 50:
                            hasil_watchlist_manual.append({
                                "Kode Saham": ticker.replace(".JK", ""), "Price": "N/A", "Change %": "N/A",
                                "% Jarak ke MA10 (1H)": "N/A", "% Jarak ke MA20 (1H)": "N/A", "% Jarak ke MA50 (1H)": "N/A",
                                "val_helper": 0
                            })
                            continue
                        
                        close_wl = float(df_wl_single['Close'].iloc[-1])
                        open_wl = float(df_wl_single['Open'].iloc[-1])
                        change_pct_wl = ((close_wl - open_wl) / open_wl) * 100 if open_wl != 0 else 0
                        
                        # Menghitung rolling mean MA Jam-Jaman (1H)
                        ma10_wl = float(df_wl_single['Close'].rolling(10).mean().iloc[-1])
                        ma20_wl = float(df_wl_single['Close'].rolling(20).mean().iloc[-1])
                        ma50_wl = float(df_wl_single['Close'].rolling(50).mean().iloc[-1])
                        
                        # Kalkulasi Nilai Transaksi Jam Terakhir/Hari Ini untuk background sorting
                        hari_ini_wl = df_wl_single.index[-1].date()
                        df_hari_ini_wl = df_wl_single[df_wl_single.index.date == hari_ini_wl]
                        val_transaksi_wl = (df_hari_ini_wl['Close'] * df_hari_ini_wl['Volume']).sum() if not df_hari_ini_wl.empty else close_wl * float(df_wl_single['Volume'].iloc[-1])
                        
                        # MASUKKAN LANGSUNG TANPA ADANYA LOGIKA ELIMINASI IF IS_LOLOS
                        hasil_watchlist_manual.append({
                            "Kode Saham": ticker.replace(".JK", ""),
                            "Price": f"Rp{close_wl:,.0f}",
                            "Change %": f"{change_pct_wl:+.2f}%",
                            "% Jarak ke MA10 (1H)": f"{((close_wl - ma10_wl) / ma10_wl) * 100:+.2f}%",
                            "% Jarak ke MA20 (1H)": f"{((close_wl - ma20_wl) / ma20_wl) * 100:+.2f}%",
                            "% Jarak ke MA50 (1H)": f"{((close_wl - ma50_wl) / ma50_wl) * 100:+.2f}%",
                            "val_helper": val_transaksi_wl
                        })
                    
                    if hasil_watchlist_manual:
                        df_render_wl = pd.DataFrame(hasil_watchlist_manual)
                        # Sorting default otomatis berdasarkan value transaksi terbesar (descending) sesuai sandbox
                        df_render_wl = df_render_wl.sort_values(by="val_helper", ascending=False)
                        df_render_wl = df_render_wl.drop(columns=["val_helper"])
                        
                        st.success(f"🎯 Watchlist Berhasil Dimuat! Memantau {len(df_render_wl)} Saham.")
                        tabel_height_wl = (len(df_render_wl) + 1) * 35
                        st.dataframe(df_render_wl, use_container_width=True, hide_index=True, height=tabel_height_wl)
                    else:
                        st.warning("Tidak ada saham yang berhasil diproses.")
            except Exception as e: st.error(f"Error Watchlist: {e}")
