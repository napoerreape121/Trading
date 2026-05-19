import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta

# Configuración de la página web de la App
st.set_page_config(page_title="CEDEARs Signal Bot", page_icon="🤖", layout="wide")

st.title("🤖 Panel de Control: Bot de Señales CEDEARs")
st.write("Estrategia algorítmica bajo reglas estrictas y gestión de riesgo del Triángulo de Hierro (2%).")

# ==============================================================================
# CONFIGURACIÓN EN LA BARRA LATERAL (SIDEBAR)
# ==============================================================================
st.sidebar.header("⚙️ Configuración del Capital")
capital_total = st.sidebar.number_input(
    "Capital Total de la Cuenta ($ ARS)", 
    min_value=10000.0, 
    value=1000000.0, 
    step=50000.0,
    format="%.2f"
)

st.sidebar.markdown("---")
st.sidebar.write("**Costos fijos (Balanz):**")
st.sidebar.write("- Arancel: 0.50%")
st.sidebar.write("- Derechos BYMA: 0.05%")
st.sidebar.write("- IVA: 21% s/comisiones")

# Constantes fijas de la estrategia
PORCENTAJE_COMISION = 0.0050
PORCENTAJE_DERECHOS_MERCADO = 0.0005
PORCENTAJE_IVA = 0.21
RIESGO_MAXIMO_POR_OPERACION = 0.02

# Lista oficial de tus 80 CEDEARs
lista_cedears = [
    'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA','AMZN.BA','AAPL.BA','ARM.BA','ARKK.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA','BP.BA','BRKB.BA','BX.BA','C.BA','CAT.BA',
    'CCL.BA','COPX.BA','COIN.BA','COST.BA','CRM.BA','CVS.BA','CVX.BA','DAL.BA','DE.BA','DISN.BA',
    'DIA.BA','EFA.BA','ETHA.BA','GE.BA','GOOGL.BA','GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA','MCD.BA','META.BA','MELI.BA','MMM.BA','MSFT.BA',
    'NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA','PEP.BA','PFE.BA','PG.BA','PYPL.BA','QCOM.BA',
    'QQQ.BA','ROKU.BA','SHOP.BA','SNOW.BA','SONY.BA','SPY.BA','T.BA','TEAM.BA','TGT.BA','TSLA.BA',
    'TSM.BA','TXN.BA','UAL.BA','UBER.BA','UNH.BA','V.BA','VZ.BA','WFC.BA','WMT.BA','XOM.BA'
]

# Botón principal para iniciar el escaneo manual
if st.button("🚀 Iniciar Escaneo de Mercado en Vivo"):
    
    st.info("Escaneando las cotizaciones de BYMA en Yahoo Finanzas. Esto puede demorar un momento...")
    
    # Contenedor para ir mostrando las alertas encontradas
    alertas_encontradas = 0
    
    for ticker in lista_cedears:
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            if df.empty or len(df) < 50:
                continue
                
            df.columns = [col if isinstance(col, tuple) else col for col in df.columns]
            
            # CÁLCULO DE INDICADORES
            df['EMA_9'] = ta.ema(df['Close'], length=9)
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['Volumen_SMA_9'] = ta.sma(df['Volume'], length=9)
            
            macd_df = ta.macd(df['Close'], fast=12, slow=26, signal=9)
            df['MACD_hist'] = macd_df['MACDh_12_26_9']
            
            # Últimas velas cerradas
            ultima_vela = df.iloc[-2]
            vela_previa = df.iloc[-3]
            
            precio_apertura = float(ultima_vela['Open'])
            precio_cierre = float(ultima_vela['Close'])
            volumen_actual = float(ultima_vela['Volume'])
            ema_9_actual = float(ultima_vela['EMA_9'])
            rsi_actual = float(ultima_vela['RSI'])
            atr_actual = float(ultima_vela['ATR'])
            volumen_sma9 = float(ultima_vela['Volumen_SMA_9'])
            macd_hist_actual = float(ultima_vela['MACD_hist'])
            macd_hist_previo = float(vela_previa['MACD_hist'])
            
            # GATILLO DE ENTRADA (TUS REGLAS)
            condicion_1_verde = precio_cierre > precio_apertura
            condicion_2_ema9 = precio_apertura < ema_9_actual < precio_cierre
            condicion_3_macd = macd_hist_actual > macd_hist_previo
            condicion_4_rsi = rsi_actual < 70
            condicion_5_volumen = volumen_actual > volumen_sma9
            
            se_cumplen_todas = (condicion_1_verde and condicion_2_ema9 and 
                                condicion_3_macd and condicion_4_rsi and condicion_5_volumen)
            
            if se_cumplen_todas:
                precio_bruto_entrada = precio_cierre
                
                # Desglose Balanz
                arancel = precio_bruto_entrada * PORCENTAJE_COMISION
                derechos_mercado = precio_bruto_entrada * PORCENTAJE_DERECHOS_MERCADO
                iva = (arancel + derechos_market) * PORCENTAJE_IVA if 'derechos_market' in locals() else (arancel + derechos_mercado) * PORCENTAJE_IVA
                
                precio_neto_entrada = precio_bruto_entrada + arancel + derechos_mercado + iva
                precio_stop_loss = precio_neto_entrada - (2 * atr_actual)
                distancia_sl_pesos = precio_neto_entrada - precio_stop_loss
                
                # Triángulo de Hierro
                dinero_en_riesgo_maximo = capital_total * RIESGO_MAXIMO_POR_OPERACION
                cantidad_nominales = int(dinero_en_riesgo_maximo // distancia_sl_pesos)
                
                capital_requerido = cantidad_nominales * precio_neto_entrada
                if capital_requerido > capital_total:
                    cantidad_nominales = int(capital_total // precio_neto_entrada)
                    capital_requerido = cantidad_nominales * precio_neto_entrada
                
                if cantidad_nominales > 0:
                    alertas_encontradas += 1
                    
                    # Dibujar tarjeta visual de la señal
                    with st.container():
                        st.success(f"🟢 SEÑAL DE COMPRA DETECTADA: **{ticker}**")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Precio Neto Entrada", f"${precio_neto_entrada:,.2f} ARS")
                            st.metric("Stop Loss Sugerido (2*ATR)", f"${precio_stop_loss:,.2f} ARS")
                        with col2:
                            st.metric("CANTIDAD A COMPRAR", f"{cantidad_nominales} nominales")
                            st.metric("Inversión Bruta Requerida", f"${capital_requerido:,.2f} ARS")
                        with col3:
                            st.write(f"📊 **Métricas Técnicas:**")
                            st.write(f"- RSI: {rsi_actual:.2f}")
                            st.write(f"- Hist. MACD: {macd_hist_actual:.4f}")
                        st.markdown("---")
                        
        except Exception as e:
            continue
            
    if alertas_encontradas == 0:
        st.warning("Escaner completo: No se encontraron activos que cumplan el 100% de las condiciones en este momento.")
    else:
        st.balloons()
        st.success(f"¡Escaneo finalizado! Se encontraron {alertas_encontradas} señales activas.")
