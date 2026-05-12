import yfinance as yf
import pandas as pd
import ta

# Lista de CEDEARs / acciones
tickers = [
    "AAPL", "ADBE", "AMD", "AMZN", "BA", "BABA", "BBD", "BIDU", "C", "CAT",
    "COIN", "CRM", "CVX", "DIS", "GE", "GOOGL", "GOLD", "HD", "IBM", "INTC",
    "JNJ", "JPM", "KO", "MA", "MCD", "MELI", "META", "MSFT", "NFLX", "NVDA",
    "PFE", "PYPL", "QCOM", "SHOP", "SPOT", "T", "TSLA", "V", "VALE",
    "VZ", "WMT", "XOM", "AAL", "ABEV", "ABT", "ACN", "ARKK", "AMGN", "EBAY"
]

def scanner(ticker):
    # Descargar datos diarios
    data = yf.download(ticker, period="6mo", interval="1d")
    data = data.dropna()

    # Validación: si no hay datos o falta columna Close
    if data.empty or "Close" not in data.columns:
        return None
    
    try:
        # Calcular indicadores
        data["EMA9"] = ta.trend.EMAIndicator(data["Close"], window=9).ema_indicator()
        data["EMA50"] = ta.trend.EMAIndicator(data["Close"], window=50).ema_indicator()
        macd = ta.trend.MACD(data["Close"])
        data["MACD_hist"] = macd.macd_diff()
        data["RSI"] = ta.momentum.RSIIndicator(data["Close"], window=14).rsi()
    except Exception as e:
        print(f"Error calculando indicadores para {ticker}: {e}")
        return None

    # Última vela
    if len(data) < 2:
        return None
    last = data.iloc[-1]
    prev = data.iloc[-2]

    # Condiciones
    tendencia_bajista = last["EMA9"] < last["EMA50"]
    tendencia_alcista = last["EMA9"] > last["EMA50"]
    vela_verde = last["Close"] > last["Open"]
    toca_ema9 = abs(last["Close"] - last["EMA9"]) / last["EMA9"] < 0.005
    toca_ema50 = abs(last["Close"] - last["EMA50"]) / last["EMA50"] < 0.005
    macd_no_cruce = last["MACD_hist"] * prev["MACD_hist"] > 0
    rsi_bajo = last["RSI"] < 50

    if tendencia_bajista and vela_verde and toca_ema9 and macd_no_cruce and rsi_bajo:
        return f"{ticker}: Señal en tendencia bajista tocando EMA9"
    elif tendencia_alcista and vela_verde and (toca_ema9 or toca_ema50) and macd_no_cruce and rsi_bajo:
        return f"{ticker}: Señal en tendencia alcista tocando EMA9/EMA50"
    else:
        return None

# Ejecutar scanner
if __name__ == "__main__":
    for t in tickers:
        señal = scanner(t)
        if señal:
            print(señal)
