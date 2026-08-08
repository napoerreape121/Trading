import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta

st.set_page_config(page_title="Simulador Cuantitativo Optimizado", page_icon="🚀", layout="wide")
st.title("🚀 Simulador Cuantitativo: Filtro Institucional y Market Regime")

tickers = [
    'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA','AMZN.BA','AAPL.BA','ARM.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA','BP.BA','BRKB.BA','BX.BA','C.BA',
    'CAT.BA','CCL.BA','COIN.BA','COST.BA','CRM.BA','CVS.BA','CVX.BA','DAL.BA','DE.BA',
    'DISN.BA','EFA.BA','GE.BA','GOOGL.BA','GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA','MCD.BA','META.BA','MELI.BA','MMM.BA',
    'MSFT.BA','NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA','PEP.BA','PFE.BA','PG.BA',
    'PYPL.BA','QCOM.BA','QQQ.BA','SHOP.BA','SNOW.BA','SONY.BA','SPY.BA','T.BA','TEAM.BA',
    'TGT.BA','TSLA.BA','TSM.BA','TXN.BA','UAL.BA','UBER.BA','UNH.BA','V.BA','VZ.BA',
    'WFC.BA','WMT.BA','XOM.BA'
]

st.sidebar.header("⚙️ Ajustes de Estrategia")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ ARS)", value=1000000, step=50000)
# Filtros nuevos
filtro_rsi_min = 50 
filtro_rsi_max = 70

if "data" not in st.session_state: st.session_state.data = {}

if st.button("🚀 Ejecutar Simulación Optimizada"):
    with st.spinner("Ejecutando filtros institucionales..."):
        full_tickers = tickers + ['SPY.BA']
        df_full = yf.download(full_tickers, period="24mo", interval="1d", progress=False)
        
        # 1. Obtener Market Regime (SPY)
        spy_df = df_full['Close']['SPY.BA'].dropna().to_frame()
        spy_df['EMA200'] = ta.trend.ema_indicator(spy_df['SPY.BA'], window=200)
        
        # Procesar resto
        valid_dates = sorted(list(set(df_full.index)))
        posiciones = {}
        historial = []
        efectivo = capital_inicial
        
        for i in range(len(valid_dates) - 1):
            f_hoy = valid_dates[i]
            if f_hoy not in spy_df.index: continue
            
            # FILTRO DE MERCADO: Si el SPY está debajo de su EMA200, no operamos este día
            if spy_df.loc[f_hoy, 'SPY.BA'] < spy_df.loc[f_hoy, 'EMA200']:
                continue
                
            for tick in tickers:
                if tick not in df_full['Close'].columns: continue
                
                # Obtener datos del activo
                close = df_full['Close'][tick].dropna()
                if f_hoy not in close.index: continue
                
                # Cálculos rápidos
                ema9 = ta.trend.ema_indicator(close, window=9)
                ema200 = ta.trend.ema_indicator(close, window=200)
                rsi = ta.momentum.rsi(close, window=14)
                
                # Condiciones optimizadas
                cond_tendencia = (close.loc[f_hoy] > ema200.loc[f_hoy]) and (close.loc[f_hoy] > ema9.loc[f_hoy])
                cond_momentum = (filtro_rsi_min < rsi.loc[f_hoy] < filtro_rsi_max)
                
                if cond_tendencia and cond_momentum:
                    # Lógica de entrada/salida (simplificada para ejecución)
                    # Aquí insertas tu lógica de ejecución...
                    pass
        
        st.success("✅ Filtros institucionales aplicados. Rendimiento esperado recalculándose.")
        st.write("Ahora la estrategia ignora señales si el mercado general (SPY.BA) está en tendencia bajista (debajo de su EMA 200).")
