# ... (bagian download data sama)

        hasil_screener = []
        # Tambahan: Cek apakah data benar-benar ter-download
        if data_bulk.empty:
            st.error("Data gagal di-download, silakan coba lagi.")
        
        for ticker in watchlist:
            try:
                df = data_bulk[ticker] if len(watchlist) > 1 else data_bulk
                if df.empty or 'Close' not in df.columns: continue
                
                # PENTING: Membersihkan data agar MA selalu bisa dihitung
                df = df.ffill().bfill().dropna()
                
                if len(df) < MA_PERIODE: continue # Skip jika data tidak cukup
                
                close = float(df['Close'].iloc[-1])
                ma_val = float(df['Close'].rolling(MA_PERIODE).mean().iloc[-1])
                
                # Logika filter
                if close > ma_val:
                    # Saham lolos
                    clean_ticker = ticker.replace(".JK", "")
                    hasil_screener.append({"Kode Saham": clean_ticker, "Price": round(close, 2)})
            except Exception as e:
                continue

        # Tampilkan hasil
        if hasil_screener:
            st.dataframe(pd.DataFrame(hasil_screener))
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria. Coba cek apakah MA terhitung (Data mungkin sedang gap).")
