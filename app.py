import streamlit as st
import yfinance as yf
import pandas as pd

# Configuración de la página (Modo móvil)
st.set_page_config(page_title="IA Trading Scanner", layout="centered")

st.title("🚀 Scanner Triángulo de Hierro")
st.subheader("Buscando Disparos en Balanz")

# Lista de CEDEARs con volumen
tickers = ["AAPL", "ADBE", "AMZN", "AMD", "BA", "BABA", "DIS", "GOOGL", "KO", "MELI", "MSFT", "NVDA", "TSLA", "V", "WMT"]

def analizar_mercado():
    resultados = []
    bar = st.progress(0)
    for idx, t in enumerate(tickers):
        try:
            data = yf.download(t, period="100d", interval="1d", progress=False)
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            # Indicadores
            c = data['Close']
            ema9 = c.ewm(span=9, adjust=False).mean()
            ema50 = c.ewm(span=50, adjust=False).mean()
            
            h = data.iloc[-1]
            
            # Lógica simplificada de Pivote
            toca_9 = h['Low'] <= ema9.iloc[-1] <= h['High']
            toca_50 = h['Low'] <= ema50.iloc[-1] <= h['High']
            
            if h['Close'] > h['Open']: # Solo velas verdes
                tipo = ""
                if h['Close'] < ema50.iloc[-1] and toca_9: tipo = "📉 PIVOTE EMA 9"
                elif h['Close'] > ema50.iloc[-1] and (toca_9 or toca_50): tipo = "🚀 APOYO TENDENCIA"
                
                if tipo != "":
                    resultados.append({"Activo": t, "Estado": tipo, "Precio": round(float(h['Close']), 2)})
            
        except: continue
        bar.progress((idx + 1) / len(tickers))
    return pd.DataFrame(resultados)

if st.button("ESCANEAR AHORA"):
    df = analizar_mercado()
    if not df.empty:
        st.success("¡Oportunidades encontradas!")
        st.dataframe(df, use_container_width=True) # Tabla ajustable al ancho del celu
    else:
        st.warning("Mercado en calma. No hay señales claras hoy.")
