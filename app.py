import yfinance as yf
import pandas as pd
import numpy as np

# Lista completa de CEDEARs extraída de tu archivo pruebaaaa.py
tickers = [
    'BP.BA', 'BRKB.BA', 'BX.BA', 'C.BA', 'CAT.BA',
    'CCL.BA', 'COPX.BA', 'COIN.BA', 'COST.BA', 'CRM.BA',
    'CVS.BA', 'CVX.BA', 'DAL.BA', 'DE.BA', 'DISN.BA',
    'DIA.BA', 'EFA.BA', 'ETHA.BA', 'GE.BA', 'GOOGL.BA',
    'GS.BA', 'HD.BA', 'HON.BA', 'IBM.BA', 'INTC.BA',
    'JNJ.BA', 'JPM.BA', 'KO.BA', 'LLY.BA', 'MA.BA',
    'MCD.BA', 'META.BA', 'MELI.BA', 'MMM.BA', 'MSFT.BA',
    'NFLX.BA', 'NKE.BA', 'NVDA.BA', 'ORCL.BA', 'PANW.BA',
    'PEP.BA', 'PFE.BA', 'PG.BA', 'PYPL.BA', 'QCOM.BA',
    'QQQ.BA', 'ROKU.BA', 'SHOP.BA', 'SNOW.BA',
    'SONY.BA', 'SPY.BA', 'T.BA', 'TEAM.BA',
    'TGT.BA', 'TSLA.BA', 'TSM.BA', 'TXN.BA', 'UAL.BA',
    'UBER.BA', 'UNH.BA', 'V.BA', 'VZ.BA', 'WFC.BA', 'WMT.BA'
]

print(f"{'CEDEAR':<8} | {'PRECIO':<9} | {'TENDENCIA':<9} | MENSAJE")
print("-" * 60)

# Descargamos los datos de todos los activos juntos para optimizar tiempo y velocidad
# Requerimos 3 meses de historial para que el cálculo de la EMA 50 sea preciso
datos_mercado = yf.download(tickers, period="3mo", interval="1d", progress=False)

for ticker in tickers:
    try:
        # Extraer historial de cierre para el ticker actual eliminando valores nulos
        historial_cierre = datos_mercado['Close'][ticker].dropna()
        if len(historial_cierre) < 50:
            continue
            
        precio_actual = float(historial_cierre.iloc[-1])
        
        # Cálculo matemático exacto de EMA 9 y EMA 50
        ema9 = historial_cierre.ewm(span=9, adjust=False).mean().iloc[-1]
        ema50 = historial_cierre.ewm(span=50, adjust=False).mean().iloc[-1]
        
        # Determinar tendencia en base a la EMA de largo plazo (50)
        tendencia = "ALCISTA" if precio_actual > ema50 else "BAJISTA"
        
        # Umbral de tolerancia de toque (0.5% de cercanía entre el precio y la EMA)
        # Puedes modificar este valor (ej: 0.003 para 0.3%) si deseas más o menos sensibilidad
        umbral = 0.005 
        
        toca_ema9 = abs(precio_actual - ema9) / precio_actual <= umbral
        toca_ema50 = abs(precio_actual - ema50) / precio_actual <= umbral
        
        # SOLUCIÓN AL PROBLEMA: Evaluamos de forma independiente sin usar 'elif'
        mensajes_alerta = []
        if toca_ema9:
            mensajes_alerta.append("TOCA EMA 9")
        if toca_ema50:
            mensajes_alerta.append("TOCA EMA 50")
            
        # Si cumple cualquiera de los dos toques, se imprime en la tabla filtrada
        if mensajes_alerta:
            simbolo_corto = ticker.split('.')[0]
            mensaje_pantalla = " y ".join(mensajes_alerta)
            print(f"{simbolo_corto:<8} | {precio_actual:<9.2f} | {tendencia:<9} | 🟩 {mensaje_pantalla}")
            
    except Exception:
        # Si un ticker falla temporalmente en Yahoo Finance, el script continúa con el siguiente
        continue

print("-" * 60)
print("Análisis completado al 100%.")
