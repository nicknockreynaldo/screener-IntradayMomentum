import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

# ... (Bagian Konfigurasi & Preset Sidebar tetap sama seperti sebelumnya) ...

# ==============================================================================
# 2. LOGIKA UTAMA
# ==============================================================================
if MULAI_SCAN:
    with st.spinner("Memproses data..."):
        try:
            # ... (Proses download watchlist tetap sama) ...
            
            # Kita perlu data 1 Jam (1H) untuk perhitungan MA 10, 20, 50 secara konsisten
            data_1h = yf.download(watchlist, period="1mo", interval="1h", group_by='ticker', auto_adjust=False, progress=False)

            hasil_screener = []
            for ticker in watchlist:
                df_s = data_1h[ticker] if len(watchlist) > 1 else data_1h
                df_s = df_s.dropna(subset=['Close'])
                if df_s.empty or len(df_s) < 50: continue
                
                close = float(df_s['Close'].iloc[-1])
                # Menghitung MA pada timeframe 1H
                ma10 = float(df_s['Close'].rolling(10).mean().iloc[-1])
                ma20 = float(df_s['Close'].rolling(20).mean().iloc[-1])
                ma50 = float(df_s['Close'].rolling(50).mean().iloc[-1])
                
                # ... (Logika filter is_lolos tetap sama) ...

                if is_lolos:
                    clean = ticker.replace(".JK", "")
                    # Menghitung persentase jarak
                    jarak_ma10 = ((close - ma10) / ma10) * 100
                    jarak_ma20 = ((close - ma20) / ma20) * 100
                    jarak_ma50 = ((close - ma50) / ma50) * 100
                    
                    hasil_screener.append({
                        "Kode Saham": clean,
                        "% Change": ((close - float(df_s['Open'].iloc[-1])) / float(df_s['Open'].iloc[-1])) * 100,
                        "Jarak ke MA 10 (%)": jarak_ma10,
                        "Jarak ke MA 20 (%)": jarak_ma20,
                        "Jarak ke MA 50 (%)": jarak_ma50,
                        "Status": "🟢 NEW" if clean not in st.session_state['memori_saham'][PRESET] else "🔵 HOLD"
                    })
            
            # ... (Update memori tetap sama) ...

            # ==============================================================================
            # 3. OUTPUT DENGAN FORMAT PERSENTASE
            # ==============================================================================
            if hasil_screener:
                df_h = pd.DataFrame(hasil_screener)
                # ... (Sorting logic) ...
                
                st.success(f"🎯 Pemindaian Selesai! | Data per: {waktu_str}")
                st.metric("Saham Lolos Kriteria", f"{len(df_h)} Saham")
                
                # Menggunakan column_config untuk memastikan format %
                st.dataframe(df_h, use_container_width=True, hide_index=True, column_config={
                    "% Change": st.column_config.NumberColumn("% Change", format="%+.2f%%"),
                    "Jarak ke MA 10 (%)": st.column_config.NumberColumn("Jarak ke MA 10 (%)", format="%+.2f%%"),
                    "Jarak ke MA 20 (%)": st.column_config.NumberColumn("Jarak ke MA 20 (%)", format="%+.2f%%"),
                    "Jarak ke MA 50 (%)": st.column_config.NumberColumn("Jarak ke MA 50 (%)", format="%+.2f%%")
                })
