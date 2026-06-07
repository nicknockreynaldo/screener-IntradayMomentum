import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi
st.title("🔍 Data Debugger")

if st.button("Lihat Data Mentah (Debugging)"):
    URL_PERMANEN = "https://docs.google.com/spreadsheets/d/16FBTNzXHRELk3NINhzk8XEymE_m34OLo4dpWldm9nKw/export?format=csv"
    df_sheet = pd.read_csv(URL_PERMANEN, usecols=[0], nrows=200)
    watchlist = [kode.strip().upper() + ".JK" for kode in df_sheet.iloc[:, 0].dropna().astype(str) if len(kode.strip()) == 4]
    
    # Ambil 5 sampel saja agar cepat
    data = yf.download(watchlist[:5], period="5d", interval="1h", group_by='ticker', auto_adjust=True, progress=False)
    
    debug_list = []
    for ticker in watchlist[:5]:
        try:
            df = data[ticker] if len(watchlist) > 1 else data
            df = df.ffill().bfill().dropna()
            
            close = float(df['Close'].iloc[-1])
            ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
            
            debug_list.append({
                "Ticker": ticker,
                "Price": close,
                "MA 20": round(ma20, 2),
                "Apakah Price > MA?": close > ma20
            })
        except:
            continue
            
    st.table(pd.DataFrame(debug_list))
