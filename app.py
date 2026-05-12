import yfinance as yf
import pandas as pd
import warnings
import time

warnings.filterwarnings("ignore")

# Lista de CEDEARs más importantes
tickers = [
    "AAPL", "ADBE", "AMD", "AMZN", "BA", "BABA", "BBD", "BIDU", "C", "CAT",
    "COIN", "CRM", "CVX", "DIS", "GE", "GOOGL", "GOLD", "HD", "IBM", "INTC",
    "JNJ", "JPM", "KO", "MA", "MCD", "MELI", "META", "MSFT", "NFLX", "NVDA",
    "PFE", "PYPL", "QCOM", "SHOP", "SPOT", "T", "TSLA", "V", "VALE",
    "VZ", "WMT", "XOM", "AAL", "ABEV", "ABT", "ACN", "ARKK", "AMGN", "EBAY"
]

def scanner_pro_v4():
    print("\n" + "="*75)
    print("   IA SCANNER: ESTRATEGIA DE PIVOTE (VERSIÓN REPARADA)")
    print("="*75)
    encontrados = 0

    for t in tickers:
        try:
            # 1. Descarga y Limpieza Quirúrgica (Lo que acabamos de arreglar)
            raw_data = yf.download(t, period="100d", interval="1d", progress=False)
            if raw_data.empty: continue
            
            data = raw_data.copy()
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # 2. Indicadores (EMA 9, 50, MACD, RSI)
            c = data['Close']
            data['EMA9'] = c.ewm(span=9, adjust=False).mean()
            data['EMA50'] = c.ewm(span=50, adjust=False).mean()
            
            exp1, exp2 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
            data['Hist'] = (exp1 - exp2) - (exp1 - exp2).ewm(span=9, adjust=False).mean()
            
            delta = c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            data['RSI'] = 100 - (100 / (1 + (gain / loss)))

            h, a = data.iloc[-1], data.iloc[-2]

            # 3. Aplicación de tus Reglas
            vela_verde = float(h['Close']) > float(h['Open'])
            rsi_ok = float(h['RSI']) < 55
            no_cruce = (float(h['Hist']) > 0 and float(a['Hist']) > 0) or (float(h['Hist']) < 0 and float(a['Hist']) < 0)

            # Zona de toque (Margen 1%)
            def en_zona(val, ema): return abs(float(val) - float(ema)) / float(ema) <= 0.01
            toca_9 = en_zona(h['Low'], h['EMA9']) or (float(h['Low']) <= float(h['EMA9']) <= float(h['High']))
            toca_50 = en_zona(h['Low'], h['EMA50']) or (float(h['Low']) <= float(h['EMA50']) <= float(h['High']))

            if vela_verde and rsi_ok and no_cruce:
                if float(h['Close']) < float(h['EMA50']) and toca_9:
                    print(f"📉 [BAJISTA] {t:<6} | Pivote EMA 9  | RSI: {float(h['RSI']):.1f}")
                    encontrados += 1
                elif float(h['Close']) > float(h['EMA50']) and (toca_9 or toca_50):
                    tipo = "EMA 9" if toca_9 else "EMA 50"
                    print(f"🚀 [ALCISTA] {t:<6} | Apoyo en {tipo:<6} | RSI: {float(h['RSI']):.1f}")
                    encontrados += 1
            
            time.sleep(0.1)
        except: continue

    if encontrados == 0:
        print("\nNo se detectan apoyos claros en este momento.")
    
    print("\n" + "="*75)
    input("Presioná ENTER para cerrar...")

if __name__ == "__main__":
    scanner_pro_v4()
