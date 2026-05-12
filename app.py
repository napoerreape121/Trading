import yfinance as yf
import pandas as pd
import ta
import streamlit as st

# Lista de CEDEARs / acciones
tickers = [
    "AAPL", "ADBE", "AMD", "AMZN", "BA", "BABA", "BBD", "BIDU", "C", "CAT",
    "COIN", "CRM", "CVX", "DIS", "GE", "GOOGL", "GOLD", "HD", "IBM", "INTC",
    "JNJ", "JPM", "KO", "MA", "MCD", "MELI", "META", "MSFT", "NFLX", "NVDA",
    "PFE", "PYPL", "QCOM", "SHOP", "SPOT", "T", "TSLA", "V", "VALE",
    "VZ", "WMT", "XOM", "AAL", "ABEV", "ABT", "ACN", "ARKK", "AMGN", "EBAY"
]

def scanner(ticker):
    data = yf.download(ticker, period="6mo", interval="1d").dropna()
    if data.empty or "Close" not in data.columns or len(data) < 2:
        return None
    
    try:
        data["EMA9"] = ta.trend.EMAIndicator(data["Close"], window=9).ema_indicator()
        data["EMA50"] = ta.trend.EMAIndicator(data["Close"], window=50).ema_indicator()
    except Exception:
        return None
    
    last, prev = data.iloc[-1], data.iloc[-2]
    tendencia_bajista = last["EMA9"] < last["EMA50"]
    tendencia_alcista = last["EMA9"] > last["EMA50"]
    vela_verde = last["Close"] > last["Open"]
    toca_ema9 = abs(last["Close"] - last["EMA9"]) / last["EMA9"] < 0.005
    toca_ema50 = abs(last["Close"] - last["EMA50"]) / last["EMA50"] < 0.005

    if tendencia_bajista and vela_verde and toca_ema9:
        return f"{ticker}: Señal en tendencia bajista tocando EMA9"
    elif tendencia_alcista and vela_verde and (toca_ema9 or toca_ema50):
        return f"{ticker}: Señal en tendencia alcista tocando EMA9/EMA50"
    return None

# Interfaz Streamlit
st.title("Scanner de CEDEARs con EMA")

resultados = []
for t in tickers:
    señal = scanner(t)
    if señal:
        resultados.append(señal)

if resultados:
    st.subheader("Señales detectadas:")
    for r in resultados:
        st.write(r)
else:
    st.write("No se detectaron señales en este momento.")
