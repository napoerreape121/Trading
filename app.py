import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuración estructural de la interfaz de usuario
st.set_page_config(page_title="Scanner de CEDEARs", page_icon="📈", layout="wide")

st.title("📈 Scanner Automático de CEDEARs")
st.write("Analiza las tendencias y detecta toques en las EMAs 9 y 50 en tiempo real.")

tickers = [
     'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA',
    'AMZN.BA','AAPL.BA','ARM.BA','ARKK.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA',
    'BP.BA','BRKB.BA','BX.BA','C.BA','CAT.BA',
    'CCL.BA','COPX.BA','COIN.BA','COST.BA','CRM.BA',
    'CVS.BA','CVX.BA','DAL.BA','DE.BA','DISN.BA',
    'DIA.BA','EFA.BA','ETHA.BA','GE.BA','GOOGL.BA',
    'GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA',
    'MCD.BA','META.BA','MELI.BA','MMM.BA','MSFT.BA',
    'NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA',
    'PEP.BA','PFE.BA','PG.BA','PYPL.BA','QCOM.BA',
    'QQQ.BA','ROKU.BA','SHOP.BA','SNOW.BA',
    'SONY.BA','SPY.BA','T.BA','TEAM.BA',
    'TGT.BA','TSLA.BA','TSM.BA','TXN.BA','UAL.BA',
    'UBER.BA','UNH.BA','V.BA','VZ.BA','WFC.BA',
    'WMT.BA','XOM.BA'

]

umbral = st.slider("Sensibilidad de toque en EMA (ej: 0.5% = 0.005)", 0.001, 0.020, 0.005, step=0.001)

if st.button("🚀 Ejecutar Análisis de Mercado"):
    with st.spinner("Descargando datos desde Yahoo Finance..."):
        try:
            datos_mercado = yf.download(tickers, period="3mo", interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error al descargar datos del mercado: {e}")
            datos_mercado = None

    if datos_mercado is not None and not datos_mercado.empty:
        resultados = []

        for ticker in tickers:
            try:
                historial_cierre = datos_mercado['Close'][ticker].dropna()
                if len(historial_cierre) < 50:
                    continue
                    
                precio_actual = float(historial_cierre.iloc[-1])
                
                ema9 = historial_cierre.ewm(span=9, adjust=False).mean().iloc[-1]
                ema50 = historial_cierre.ewm(span=50, adjust=False).mean().iloc[-1]
                
                tendencia = "📈 ALCISTA" if precio_actual > ema50 else "📉 BAJISTA"
                
                toca_ema9 = abs(precio_actual - ema9) / precio_actual <= umbral
                toca_ema50 = abs(precio_actual - ema50) / precio_actual <= umbral
                
                mensajes_alerta = []
                if toca_ema9:
                    mensajes_alerta.append("TOCA EMA 9")
                if toca_ema50:
                    mensajes_alerta.append("TOCA EMA 50")
                    
                if mensajes_alerta:
                    # CORRECCIÓN: .split('.')[0] garantiza un string plano y no una lista
                    simbolo_corto = str(ticker.split('.')[0])
                    mensaje_pantalla = " y ".join(mensajes_alerta)
                    resultados.append({
                        "CEDEAR": simbolo_corto,
                        "Precio ($)": round(precio_actual, 2),
                        "Tendencia": tendencia,
                        "Alerta": f"🟩 {mensaje_pantalla}"
                    })
            except Exception:
                continue

        if resultados:
            df_resultados = pd.DataFrame(resultados)
            st.success(f"¡Análisis completado! Se encontraron {len(resultados)} activos bajo los criterios.")
            st.dataframe(df_resultados, use_container_width=True)
        else:
            st.info("No se encontraron CEDEARs tocando las EMAs bajo el umbral actual.")
