import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
import math
import gspread
import time
import datetime

# --- FUNGSI GOOGLE SHEETS ---
def simpan_trade_ke_gsheet(worksheet_name, data_list):
    try:
        data_clean = [str(item) for item in data_list]
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        
        # Pilih tab berdasarkan nama
        wks = sh.worksheet(worksheet_name)
        
        # Gunakan append_row untuk menambah data ke baris paling bawah
        wks.append_row(data_clean)
        return True, "Sukses"
    except Exception as e:
        return False, str(e)

def tarik_data_dari_gsheet(worksheet_name):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        
        # Ganti sh.sheet1 dengan ini agar spesifik per tab
        worksheet = sh.worksheet(worksheet_name)
        data = worksheet.get_all_values()
        
        if len(data) > 0:
            return pd.DataFrame(data[1:], columns=data[0])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error saat tarik data '{worksheet_name}': {e}")
        return pd.DataFrame()
        
def update_seluruh_gsheet(worksheet_name, df):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        wks = sh.worksheet(worksheet_name)

        df_clean = df.astype(str)
        # Bersihkan tabel & update dengan data dari DataFrame
        wks.clear()
        data_to_upload = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        wks.update(range_name='A1', values=data_to_upload)
      
        return True, "Sukses"
    except Exception as e:
        return False, str(e)
        
def proses_jual_posisi(trade_id, harga_jual, lot_jual, alasan_final):
    try:
        creds_dict = dict(st.secrets["gcp"])
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("NRC Trading Journal")
        
        # Ambil baris data dari memori
        df = st.session_state.df_active
        idx = df.index[df['Trade_ID'] == trade_id].tolist()[0]
        row = df.loc[idx]
        initial_lot = int(row['Initial_Lot'])
        pct_dijual = (int(lot_jual) / initial_lot) * 100
        avg_entry = float(row['Avg_Entry'])
        sl = float(row['SL'])
        harga_jual = float(harga_jual)
        gain_loss_pct = ((harga_jual - avg_entry) / avg_entry) * 100
        profit_loss_rp = (harga_jual - avg_entry) * float(lot_jual) * 100
        result = "Profit" if profit_loss_rp > 0 else ("Loss" if profit_loss_rp < 0 else "BE")
        tanggal_jual = datetime.date.today().strftime('%Y-%m-%d')
        # 2. Hitung Realized R
        risk_per_share = float(row['Avg_Entry']) - float(row['SL'])
        r_val = 0
        realized_r = 0
        if risk_per_share != 0:
            r_val = (float(harga_jual) - float(row['Avg_Entry'])) / risk_per_share 
            
            
        # Siapkan data untuk Jurnal (sesuaikan urutan kolom jurnal Anda)
        data_jurnal = [
            str(row['Trade_ID']),           # A
            str(row['Tanggal']),            # B
            str(row['Ticker']),             # C
            int(lot_jual),                  # D: Lot_Dijual (ANGKA MURNI)
            f"{pct_dijual:.1f}%",           # E: Persen_Lot (KETERANGAN)
            float(row['Avg_Entry']),        # F
            float(harga_jual),              # G
            f"{gain_loss_pct:.2f}%",        # H: Gain/Loss
            profit_loss_rp,                 # I: Profit/Loss (Rp)
            str(row['Grade']),              # J
            str(result),                    # K
            str(row['Initial_R']),      # L
            f"{r_val:.2f}",                # M
            str(tanggal_jual),              # N
            str(alasan_final)               # O
        ]
        
        # Append ke Journal_Final (gunakan fungsi append_row/append_ke_gsheet Anda)
        # Pastikan worksheet "Journal_Final" ada di GSheet Anda
        simpan_trade_ke_gsheet("Journal_Final", data_jurnal)
        
        # Update Sisa Lot di Active_Trades
        sisa_lot = int(row['Lot']) - int(lot_jual)
        
        if sisa_lot > 0:
            st.session_state.df_active.loc[st.session_state.df_active['Trade_ID'] == trade_id, 'Lot'] = sisa_lot
        else:
            st.session_state.df_active = st.session_state.df_active[st.session_state.df_active['Trade_ID'] != trade_id]
            
        # Simpan perubahan ke GSheet (Active_Trades)
        update_seluruh_gsheet("Active_Trades", st.session_state.df_active)
        return True, "Sukses"
    except Exception as e:
        return False, str(e)
        
def load_journal_data():
    # 1. Tarik data
    df = tarik_data_dari_gsheet("Journal_Final")
    
    if df.empty:
        return df

    # 2. Pastikan kolom numerik benar-benar angka (mengatasi TypeError)
    # Gunakan errors='coerce' agar data non-angka berubah jadi NaN, lalu isi dengan 0
    numeric_cols = ['Lot', 'Initial_Lot', 'Profit/Loss (Rp)', 'Lot_Pct', 'Initial_R'] 
    
    for col in numeric_cols:
        if col in df.columns:
            # 1. Ubah jadi string
            # 2. Ganti '-' atau 'N/A' menjadi '' (kosong)
            # 3. Konversi ke angka
            df[col] = df[col].astype(str).str.replace('-', '').str.replace('N/A', '')
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
    # 3. Handle 'Realized R' dengan aman (mengatasi KeyError)
    if 'Realized_R' in df.columns:
        df['Realized_R'] = pd.to_numeric(df['Realized_R'].astype(str).str.replace('R', '', regex=False), errors='coerce').fillna(0)
    else:
        # Jika kolom tidak ada, buat kolom 0 agar aplikasi tidak crash
        df['Realized_R'] = 0.0
        
    # 4. Handle 'Alasan_Final'
    if 'Alasan_Final' in df.columns:
        # Menggunakan split yang aman
        split_data = df['Alasan_Final'].astype(str).str.split(' - ', n=1, expand=True)
        df['Kategori'] = split_data[0]
        df['Catatan_Detail'] = split_data[1] if 1 in split_data.columns else ""
    else:
        df['Kategori'] = "N/A"
        df['Catatan_Detail'] = ""
    
    return df

# --- KETERANGAN MODE ---
st.warning("⚠️ MODE SANDBOX")

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
tab_screener, tab_watchlist, tab_calc, tab_active_trade, tab_journal = st.tabs([
    "🚀 Screener", 
    "📋 Watchlist", 
    "🧮 Risk & Sizing", 
    "📊 Portfolio", 
    "📚 Journal"
])
# ==============================================================================
# TAB 1: SCREENER 
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
    
    # CSS Injection (Tetap sama)
    st.markdown("""
        <style>
            table { text-align: center !important; }
            th { text-align: center !important; }
            td { text-align: center !important; }
            [data-testid="stDataEditor"] { text-align: center !important; }
            [data-testid="stDataEditor"] div[data-testid="stText"] { text-align: center !important; }
            [data-testid="stDataEditor"] .st-emotion-cache-1vt4y4j { justify-content: center !important; }
            /* CSS untuk Border Form (Hanya Top & Bottom) */
            [data-testid="stForm"] {
                border-left: none !important;
                border-right: none !important;
                border-top: 1px solid #e0e0e0 !important;
                border-bottom: 1px solid #e0e0e0 !important;
                border-radius: 0 !important;
                background-color: transparent !important;
            }
        </style>
    """, unsafe_allow_html=True)

    if 'my_trades' not in st.session_state:
        st.session_state['my_trades'] = pd.DataFrame(columns=[
            "Trade_ID", "Tanggal", "Ticker", "Lot", "Entry", "SL", "Jarak SL", "Target", "R-Ratio", "Grade", "Action"
        ])

    c_g1, c_g2 = st.columns(2)
    grade_in = c_g1.selectbox("Setup Grade", ["A", "B", "C", "D"], index=1)
    risk_map = {"A": 1.5, "B": 1.0, "C": 0.5, "D": 0.2}
    RISK_PCT = c_g2.slider("Risk per Trade (%)", 0.1, 5.0, value=risk_map[grade_in], step=0.1) / 100

    with st.container():
        c1, c2 = st.columns(2)
        MODAL = c1.number_input("Modal Trading (Rp)", value=10_000_000, step=1_000_000)
        c1.caption(f"Modal: Rp {f'{MODAL:,.0f}'.replace(',', '.')}")
        col_in1, col_in2, col_in3, col_in4 = st.columns(4)
        ticker_in = col_in1.text_input("Ticker", "BBCA").upper()
        entry_in = col_in2.number_input("Entry Price", value=6000)
        sl_in = col_in3.number_input("Stop Loss Price", value=5800)
        manual_tp = col_in4.number_input("Target Manual", value=6300, step=1, format="%d")

    # 2. LOGIKA KALKULASI & VALIDASI SL < ENTRY dan TP harus > entry
    risk_amount, lot_max, risk_dist_pct, r_manual = 0, 0, 0, 0
    risk_per_share = 0
    
    if sl_in >= entry_in:
        st.error("⚠️ Stop Loss harus di bawah Entry Price!")
        risk_amount, lot_max, risk_dist_pct, r_manual = 0, 0, 0, 0
    elif manual_tp <= entry_in:
        st.error("⚠️ Target Manual harus di atas Entry Price!")
    else:
        risk_amount = MODAL * RISK_PCT
        risk_per_share = entry_in - sl_in
        risk_dist_pct = (risk_per_share / entry_in) * 100
        r_manual = (manual_tp - entry_in) / risk_per_share
        lot_max = math.floor((risk_amount / risk_per_share) / 100)
    
    st.markdown("---")  
    # --- METRICS & SISA KODE (TETAP DI LUAR FORM) ---
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

    st.markdown("""
        <style>
            /* Mengurangi spasi setelah Metrics Pink */
            div[data-testid="column"] { padding-bottom: 0px !important; }
            
            /* Mengurangi spasi sebelum subheader Risk Multiple */
            h3 { margin-top: -10px !important; margin-bottom: 5px !important; }
            
            /* Jika ada garis pemisah (horizontal rule), buat lebih tipis spasinya */
            hr { margin-top: 5px !important; margin-bottom: 5px !important; }
        </style>
    """, unsafe_allow_html=True)


    st.subheader("🎯 Risk Multiple")
    col_tabel1, col_tabel2 = st.columns([3, 1]) # [3, 1] berarti tabel hanya menempati 3/4 lebar layar
    
    with col_tabel1:
        if risk_per_share > 0:
            df_target_ringkas = pd.DataFrame({
                "1.5R": [f"{entry_in + (risk_per_share * 1.5):,.0f}"],
                "2R": [f"{entry_in + (risk_per_share * 2):,.0f}"],
                "3R": [f"{entry_in + (risk_per_share * 3):,.0f}"],
                "Manual TP": [f"{manual_tp:,.0f} ({r_manual:.2f})"]
            })
        else:
            df_target_ringkas = pd.DataFrame({"1.5R": ["-"], "2R": ["-"], "3R": ["-"], "Manual TP": ["-"]})
        st.table(df_target_ringkas)

     # 3. FORM (Hanya untuk tombol submit)
    with st.form("input_form", clear_on_submit=False):
        submitted = st.form_submit_button("➕ Tambah ke Daftar Pre-Trade")
        if submitted:
            if sl_in >= entry_in:
                st.error("Input tidak valid!")
            else:
                new_row = pd.DataFrame([{
                    "Tanggal": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    "Ticker": ticker_in,
                    "Lot": lot_max,
                    "Entry": entry_in,
                    "SL": sl_in,
                    "Jarak SL": f"{risk_dist_pct:.2f}%",
                    "Target": manual_tp,
                    "R-Ratio": f"{r_manual:.2f}",
                    "Grade": grade_in,
                    "Action": False
                }])
                st.session_state['my_trades'] = pd.concat([st.session_state['my_trades'], new_row], ignore_index=True)
                st.rerun()
    
    st.subheader("📋 Daftar Pre-Trade")
    edited_df = st.data_editor(
        st.session_state['my_trades'],
           column_config={
                "Trade_ID": st.column_config.TextColumn("Trade ID", disabled=True),
                "Tanggal": st.column_config.TextColumn("Tanggal", disabled=True),
                "Ticker": st.column_config.TextColumn("Ticker", disabled=True),
                "Lot": st.column_config.NumberColumn("Lot", disabled=True),
                "Entry": st.column_config.NumberColumn("Entry", disabled=True),
                "SL": st.column_config.NumberColumn("SL", disabled=True),
                "Jarak SL": st.column_config.TextColumn("Jarak SL", disabled=True),
                "Target": st.column_config.NumberColumn("Target", disabled=True),
                "R-Ratio": st.column_config.TextColumn("R-Ratio", disabled=True),
                "Grade": st.column_config.TextColumn("Grade", disabled=True),
            },
    )
    
    c_act1, c_act2 = st.columns(2)
    if c_act1.button("🚀 Confirm Trade"):
        if not st.session_state['my_trades'].empty:
            for _, row in st.session_state['my_trades'].iterrows():
                trade_id = f"{int(time.time())}.{row['Ticker']}"
                data_list_pre = [trade_id, row['Tanggal'], row['Ticker'], row['Lot'], row['Entry'], row['SL'], row['Jarak SL'], row['Target'], row['R-Ratio'], row['Grade']]
                data_list_active = data_list_pre + [row['Lot']]
                simpan_trade_ke_gsheet("Plan_PreTrade", data_list_pre)
                simpan_trade_ke_gsheet("Active_Trades", data_list_active)
            st.success("Trade berhasil dikonfirmasi!")
            st.session_state['my_trades'] = pd.DataFrame(columns=["Tanggal", "Ticker", "Lot", "Entry", "SL", "Jarak SL", "Target", "R-Ratio", "Grade", "Action"])
            st.rerun()

    if c_act2.button("🗑️ Hapus Baris Terpilih"):
        st.session_state['my_trades'] = edited_df[edited_df["Action"] == False]
        st.rerun()
# ==============================================================================
# TAB 4: ACTIVE TRADE
# ==============================================================================

with tab_active_trade:
    st.header("⚡ Trading Portfolio")

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
                'SL', 'Jarak SL', 'Target', 'Initial_R', 'Grade'
            ])

    # 2. Sembunyikan kolom kalkulasi dari UI tampilan
    df_temp = st.session_state.df_active.copy()

    # Paksa konversi ke numerik dan tangani nilai kosong (NaN)
    df_temp['Lot'] = pd.to_numeric(df_temp['Lot'], errors='coerce').fillna(0)
    df_temp['Initial_Lot'] = pd.to_numeric(df_temp['Initial_Lot'], errors='coerce').fillna(1) 
    
    # Lakukan kalkulasi hanya setelah data dipastikan angka
    df_temp['Remaining %'] = ((df_temp['Lot'] / df_temp['Initial_Lot']) * 100).round(0).astype(int)
    
    cols_to_hide = ['Jarak SL', 'Initial_R', 'Initial_Lot']
    cols_to_show = [c for c in df_temp.columns if c not in cols_to_hide]
    df_clean = df_temp[cols_to_show]

    # Inisialisasi key dinamis untuk data_editor
    dynamic_key = f"active_trade_editor_v_{st.session_state.editor_version}"
    
    # 3. Data Editor
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
            "Grade": st.column_config.TextColumn("Grade", disabled=True),
            "Remaining %": st.column_config.NumberColumn("Remaining %", format="%d%%", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key=dynamic_key
    )

    # 4. Layout Tombol di bawah tabel (Refresh kiri, Sync kanan)
    c_btn_left, c_btn_mid, c_btn_right = st.columns([1, 4, 1])

    # Tombol Refresh di kolom paling kiri
    if c_btn_left.button("🔄 Refresh Data", use_container_width=True):
        if 'df_active' in st.session_state:
            del st.session_state.df_active
        st.rerun()

    # Tombol Sync di kolom paling kanan
    if c_btn_right.button("💾 Sync & Save Changes", use_container_width=True):
        updated_data = edited_df
        
        # Gabungkan ke master_df
        master_df = st.session_state.df_active.copy()
        for col in ['Lot', 'Avg_Entry']:
            if col in updated_data.columns:
                master_df[col] = updated_data[col]
                
        master_df['Initial_Lot'] = master_df['Lot']
        master_df = master_df.fillna("")
        
        if 'Remaining %' in master_df.columns:
            master_df = master_df.drop(columns=['Remaining %'])
            
        # Kirim data ke GSheet
        success, msg = update_seluruh_gsheet("Active_Trades", master_df)
        if success:
            st.session_state.df_active = master_df
            st.session_state.editor_version += 1
            st.success("Data berhasil di-sync!")
            st.rerun() 
        else:
            st.error(f"Gagal simpan ke GSheet: {msg}")

    st.markdown("---")
    with st.expander("💸 Close/Sell Position"):
        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1.5])
        
        trade_list = st.session_state.df_active['Trade_ID'].tolist()
        selected_trade = col1.selectbox("Pilih Trade ID", trade_list)
        # Ambil lot maksimal berdasarkan Trade ID yang dipilih
        row_data = st.session_state.df_active.loc[st.session_state.df_active['Trade_ID'] == selected_trade].iloc[0]
        
        initial_lot = int(row_data['Initial_Lot']) 
        current_lot = int(row_data['Lot'])
        default_avg = int(float(row_data['Avg_Entry']))
        
        sell_price = col2.number_input("Harga Jual", step=50, value=default_avg, min_value=1)
        persen_slider = col3.slider("Persentase Jual (%)", 0, 100, 25, step=5)
        sell_lot = int(initial_lot * (persen_slider / 100))
        if sell_lot == 0 and persen_slider > 0: sell_lot = 1
        sell_lot = min(sell_lot, current_lot) # Safety check
        col3.caption(f"Jual: {sell_lot} lot ({persen_slider}%)")
        col4.write("")
        col4.write("")

        st.divider()
        c_r1, c_r2 = st.columns([1, 2])
        kategori = c_r1.selectbox("Alasan Jual:", ["TP", "SL", "Trailing Stop", "BEP", "Manual Exit", "Lainnya"])
        catatan = c_r2.text_input("Catatan Detail (Opsional):")
        alasan_final = f"{kategori} - {catatan}" if catatan else kategori
        
        if col4.button("🚀 Execute Sell", use_container_width=True):
            if sell_lot > current_lot:
                st.error("Lot yang ingin dijual melebihi sisa lot!")
            else:
                success, msg = proses_jual_posisi(selected_trade, sell_price, sell_lot,alasan_final)
                if success:
                    st.session_state.editor_version += 1 
                    st.success(f"Trade {selected_trade} terjual {sell_lot} lot!")
                    st.rerun()
                else:
                    st.error(f"Gagal: {msg}")
# ==============================================================================
# TAB 5: JOURNAL (Versi Agregasi/Opsi 1)
# ==============================================================================

with tab_journal:
    st.header("📋 Trading Journal")
    
    df_raw = tarik_data_dari_gsheet("Journal_Final")
    
    if not df_raw.empty:
        # 1. Konversi Tipe Data (PENTING: Harus dilakukan di awal)
        df_raw['Tanggal'] = pd.to_datetime(df_raw['Tanggal'])
        df_raw['Bulan_Key'] = df_raw['Tanggal'].dt.to_period('M')
        # Bersihkan Realized R (Hapus 'R')
        df_raw['Realized_R'] = df_raw['Realized_R'].astype(str).str.replace('R', '', regex=False).astype(float)
        
        # Konversi ke Numerik agar tidak terjadi string concatenation
        df_raw['Lot'] = pd.to_numeric(df_raw['Lot'], errors='coerce').fillna(0)
        df_raw['Profit/Loss (Rp)'] = pd.to_numeric(df_raw['Profit/Loss (Rp)'], errors='coerce').fillna(0)

        # 2. Filter Bulan
        df_raw['Bulan_Display'] = df_raw['Tanggal'].dt.strftime('%B-%Y')
        pilihan_bulan = sorted(df_raw['Bulan_Display'].unique(), reverse=True)
        
        col1, _ = st.columns([1, 3])
        selected_month_display = col1.selectbox("Pilih Bulan", options=pilihan_bulan)
        
        # Mapping untuk filter balik ke key (karena drop-down string)
        selected_key = df_raw[df_raw['Bulan_Display'] == selected_month_display]['Bulan_Key'].iloc[0]
        df_filtered = df_raw[df_raw['Bulan_Key'] == selected_key].copy()

        st.write("Daftar kolom yang ada di data:", df_filtered.columns.tolist())
        # 3. AGREGASI (Gunakan kolom yang sudah numerik)
        df_agg = df_filtered.groupby('Trade_ID').agg({
            'Ticker': 'first',
            'Lot': 'sum',
            'Gain/Loss (%)': 'first',   
            'Profit/Loss (Rp)': 'sum',
            'Initial_R': 'first',
            'Realized_R': 'sum',
            'Grade': 'first',
            'Alasan_Final': 'first'    
        })

        # === Kalkulasi ===
        sum_r = df_agg['Realized_R'].sum()
        total_lot = df_agg['Lot'].sum()
        weighted_r = (df_agg['Realized_R'] * df_agg['Lot']).sum() / total_lot if total_lot != 0 else 0
        avg_r = df_agg['Realized_R'].mean()

        
        win_trades = df_agg[df_agg['Realized_R'] > 0]
        loss_trades = df_agg[df_agg['Realized_R'] < 0]

        total_trades = len(df_agg)
        win_rate = (len(win_trades) / total_trades) * 100 if total_trades > 0 else 0
        avg_win = win_trades['Realized_R'].mean() if not win_trades.empty else 0
        avg_loss = abs(loss_trades['Realized_R'].mean()) if not loss_trades.empty else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        sum_win_r = win_trades['Realized_R'].sum()
        sum_loss_r = abs(loss_trades['Realized_R'].sum())
        profit_factor = sum_win_r / sum_loss_r if sum_loss_r != 0 else (float('inf') if sum_win_r > 0 else 0)
        profit_factor_display = "∞" if sum_loss_r == 0 and sum_win_r > 0 else f"{sum_win_r / sum_loss_r:.2f}" if sum_loss_r != 0 else "0.00"
        
        # Baris 1
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Win Rate", f"{win_rate:.1f}%")
        col_m2.metric("Profit Factor", f"{profit_factor_display:.2f}")
        col_m3.metric("Sum R", f"{sum_r:.2f}")

        # Baris 2
        col_m4, col_m5, col_m6 = st.columns(3)
        col_m4.metric("Avg R", f"{avg_r:.2f}")
        col_m5.metric("Expectancy", f"{expectancy:.2f}")
        col_m6.metric("Weighted R", f"{weighted_r:.2f}")
        
        st.markdown("---")

        st.subheader("Summary per Trade")
        
        # Tampilkan tabel utama
        cols_order = ['Ticker', 'Lot', 'Gain/Loss (%)', 'Profit/Loss (Rp)', 'Initial_R', 'Realized_R', 'Grade', 'Alasan_Final']
        
       
        event = st.dataframe(
            df_display.style.format({
                'Lot': '{:.0f}', 
                'Profit/Loss (Rp)': '{:,.0f}', 
                'Realized_R': '{:.2f}R',
                'Initial_R': '{:.2f}R',
                'Gain/Loss (%)': '{:.2f}%'
            }), 
            use_container_width=True, 
            selection_mode="single-row", 
            on_select="rerun"
        )
        
        # 4. Detail Transaksi
        if event.selection['rows']:
            selected_row_idx = event.selection['rows'][0]
            selected_trade_id = df_agg.index[selected_row_idx]
            
            st.divider()
            st.subheader(f"Detail Transaksi: {selected_trade_id}")
            
            detail = df_filtered[df_filtered['Trade_ID'] == selected_trade_id]
            
            # Menampilkan kolom detail termasuk 'Realized R'
            st.dataframe(
                detail[['Tanggal', 'Avg_Entry', 'Sell Price', 'Lot', 'Profit/Loss (Rp)', 'Realized_R']].style.format({
                    'Profit/Loss (Rp)': '{:,.0f}'
                }),
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Klik pada salah satu baris di tabel ringkasan untuk melihat detail transaksi.")

    else:
        st.info("Data jurnal belum tersedia.")

