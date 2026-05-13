import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Configuración de la página en internet
st.set_page_config(page_title="Asistente Cuantitativo CEDEARs", page_icon="🤖", layout="wide")

st.title("🤖 Asistente Consultivo de Trading de CEDEARs")
st.write("Estrategia algorítmica pura: EMAs, Volatilidad ATR, Gestión del 2% y Costos Balanz desglosados.")

# Credenciales de Telegram (Fijas y Verificadas)
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"

def enviar_alerta_telegram(mensaje):
    """Función de red corregida para despachar notificaciones directas a tu celular"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# Listado completo de CEDEARs configurados
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

# Menú lateral para controlar tu billetera y el algoritmo sin tocar código
st.sidebar.header("🧮 Gestión de Billetera")
capital_total = st.sidebar.number_input("Capital Total Disponible ($ ARS)", min_value=10000, value=1000000, step=50000)
riesgo_maximo_ars = capital_total * 0.02

st.sidebar.markdown(f"**Tu riesgo máximo permitido (2%):** ${riesgo_maximo_ars:,.2f}")

st.sidebar.header("⚙️ Parámetros de Sensibilidad")
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)

# Estructura del Triángulo de Hierro (Costos fijos Balanz deducidos matemáticamente)
ARANCEL_BALANZ = 0.0050   # 0.50%
DERECHOS_BYMA = 0.0005    # 0.05%
IVA_FACTOR = 1.21         # 21% sobre comisiones
COSTO_OPERATIVO_TOTAL = (ARANCEL_BALANZ + DERECHOS_BYMA) * IVA_FACTOR  # Aprox 0.6655%

# BOTÓN DE PRUEBA DE CONEXIÓN
if st.sidebar.button("🔔 Probar Conexión de Telegram"):
    exito = enviar_alerta_telegram("✨ ¡Conexión Exitosa! Tu bot de asistencia ya puede enviarte alertas de CEDEARs al celular.")
    if exito:
        st.sidebar.success("¡Mensaje de prueba enviado! Revisa tu Telegram.")
    else:
        st.sidebar.error("Error al enviar. Verifica el Token o Chat ID.")

if st.button("🚀 Ejecutar Escáner y Despachar Alertas"):
    with st.spinner("Analizando datos históricos y estructuras de gráficos..."):
        try:
            # Requerimos 6 meses de historial diario para calcular EMA 50, MACD y el ATR 14
            datos_mercado = yf.download(tickers, period="6mo", interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error de conexión con los servidores de mercado: {e}")
            datos_mercado = None

    if datos_mercado is not None and not datos_mercado.empty:
        # SOLUCIÓN AL ERROR: La lista se declara AFUERA del bucle para acumular todas las oportunidades
        ordenes_del_dia = []

        for ticker in tickers:
            try:
                df_ticker = pd.DataFrame()
                df_ticker['Close'] = datos_mercado['Close'][ticker].dropna()
                df_ticker['Open'] = datos_mercado['Open'][ticker].dropna()
                df_ticker['Low'] = datos_mercado['Low'][ticker].dropna()
                df_ticker['High'] = datos_mercado['High'][ticker].dropna()
                
                if len(df_ticker) < 50:
                    continue
                
                precio_actual = float(df_ticker['Close'].iloc[-1])
                precio_apertura = float(df_ticker['Open'].iloc[-1])
                precio_minimo = float(df_ticker['Low'].iloc[-1])
                
                # Indicadores técnicos
                ema9 = df_ticker['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                ema50 = df_ticker['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                
                high_low = df_ticker['High'] - df_ticker['Low']
                high_close_prev = abs(df_ticker['High'] - df_ticker['Close'].shift())
                low_close_prev = abs(df_ticker['Low'] - df_ticker['Close'].shift())
                true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                atr14 = true_range.rolling(14).mean().iloc[-1]
                
                delta = df_ticker['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi14 = 100 - (100 / (1 + rs)).iloc[-1]
                
                exp1 = df_ticker['Close'].ewm(span=12, adjust=False).mean()
                exp2 = df_ticker['Close'].ewm(span=26, adjust=False).mean()
                macd_line = exp1 - exp2
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histograma_macd = (macd_line - signal_line).iloc[-1]
                hist_anterior = (macd_line - signal_line).iloc[-2]
                
                # Reglas de la estrategia
                es_vela_verde = precio_actual > precio_apertura
                tendencia_alcista = precio_actual > ema50
                
                toca_ema9 = abs(precio_minimo - ema9) / precio_actual <= umbral
                toca_ema50 = abs(precio_minimo - ema50) / precio_actual <= umbral
                
                disparar_estrategia = False
                ema_referencia = ema50
                contexto_txt = ""
                
                if tendencia_alcista and es_vela_verde and (toca_ema9 or toca_ema50):
                    disparar_estrategia = True
                    ema_referencia = ema50 if toca_ema50 else ema9
                    contexto_txt = "Estructura Alcista + Confirmación Vela Verde + Toque de Soporte."
                elif not tendencia_alcista and es_vela_verde and toca_ema9:
                    if rsi14 <= 55:
                        disparar_estrategia = True
                        ema_referencia = ema9
                        contexto_txt = "Rebote Técnico Bajista (Vela Verde en EMA 9) con espacio en RSI."

                if disparar_estrategia:
                    precio_entrada_neto = precio_actual * (1 + COSTO_OPERATIVO_TOTAL)
                    stop_loss_grafico = ema_referencia - (2 * atr14)
                    if stop_loss_grafico >= precio_actual: 
                        stop_loss_grafico = precio_actual * 0.97
                    
                    precio_salida_stop_neto = stop_loss_grafico * (1 - COSTO_OPERATIVO_TOTAL)
                    perdida_por_accion = precio_entrada_neto - precio_salida_stop_neto
                    
                    cantidad_cedears = int(riesgo_maximo_ars // perdida_por_accion)
                    if cantidad_cedears <= 0:
                        continue
                        
                    monto_total_compra = precio_entrada_neto * cantidad_cedears
                    
                    puntos_score = 0
                    if rsi14 > 40 and rsi14 < 65: puntos_score += 1
                    if histograma_macd > hist_anterior: puntos_score += 1
                    
                    if puntos_score == 2: score_txt = "⭐ PREMIUM"
                    elif puntos_score == 1: score_txt = "⚡ REGULAR"
                    else: score_txt = "⚠️ NEUTRAL"
                    
                    simbolo_limpio = str(ticker.split('.')[0])
                    
                    # Añadir a la lista colectiva sin borrar los anteriores
                    ordenes_del_dia.append({
                        "CEDEAR": simbolo_limpio,
                        "Precio Mercado": f"$ {precio_actual:,.2f}",
                        "Precio Neto (Balanz)": f"$ {precio_entrada_neto:,.2f}",
                        "Stop Loss Dinámico": f"$ {stop_loss_grafico:,.2f}",
                        "Cantidad a Comprar": cantidad_cedears,
                        "Capital Requerido": f"$ {monto_total_compra:,.2f}",
                        "Argumentación Score": score_txt
                    })
                    
                    msg_telegram = (
                        f"🤖 *¡ALERTA DE TRADING OBJETIVA!*\n\n"
                        f"📈 *Activo:* `{simbolo_limpio}`\n"
                        f"🟢 *Orden:* COMPRAR\n"
                        f"🧮 *Cantidad Estricta:* {cantidad_cedears} unidades\n\n"
                        f"💵 *Precio Entrada:* ${precio_actual:,.2f}\n"
                        f"📐 *Precio Entrada Neto:* ${precio_entrada_neto:,.2f}\n"
                        f"🛡️ *Stop Loss (Análisis Gráfico):* ${stop_loss_grafico:,.2f}\n"
                        f"📊 *Riesgo:* Cubierto bajo la regla del 2%\n\n"
                        f"🔍 *Score Técnico:* {score_txt}\n"
                        f"📝 *Motivo:* {contexto_txt}"
                    )
                    enviar_alerta_telegram(msg_telegram)

            except Exception:
                continue

        # Renderizar la tabla con todas las oportunidades juntas
        if ordenes_del_dia:
            df_final = pd.DataFrame(ordenes_del_dia)
            st.success("🤖 ¡Análisis completado! Las órdenes válidas han sido enviadas a tu Telegram.")
            st.dataframe(df_final, use_container_width=True)
        else:
            st.info("Mercado escaneado. Ningún activo cumple con los criterios técnicos estrictos hoy.")
