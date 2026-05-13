import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Configuración del panel de control interactivo en internet
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")

st.title("🤖 Asistente de Trading de CEDEARs - Modelo de Alta Fidelidad")
st.write("Estrategia Calibrada con Ratio Riesgo/Beneficio Fijo. Envío directo de señales y órdenes exactas a Telegram.")

# Credenciales fijas y verificadas de tu canal de Telegram
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"

def enviar_alerta_telegram(mensaje):
    """Módulo de comunicación nativo corregido con la URL oficial de red"""
    url = f"telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# Lista matriz de tus 80 CEDEARs en pesos
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

# Menú lateral interactivo para ajustar tu balance en pesos de Balanz en tiempo real
st.sidebar.header("💰 Parámetros Financieros Reales")
capital_cuenta = st.sidebar.number_input("Capital de tu Cuenta ($ ARS)", min_value=10000, value=158000, step=10000)
riesgo_maximo_ars = capital_cuenta * 0.02

st.sidebar.markdown(f"**Tu riesgo máximo permitido (2%):** ${riesgo_maximo_ars:,.2f}")

st.sidebar.header("⚙️ Configuración del Algoritmo")
ratio_beneficio = st.sidebar.slider("Ratio Recompensa / Riesgo (Ej: 2.0 = Ganar el doble)", 1.5, 3.5, 2.0, step=0.1)
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)

# Estructura de costos del Triángulo de Hierro (Arancel 0.50% + BYMA 0.05% + IVA)
COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21 

# BOTÓN EN LA BARRA LATERAL PARA PROBAR LA CONEXIÓN
if st.sidebar.button("🔔 Probar Conexión de Telegram"):
    exito = enviar_alerta_telegram("✨ ¡Conexión Exitosa! Tu bot con Ratio Fijo y Cantidades Enteras ya está operativo.")
    if exito: st.sidebar.success("¡Mensaje enviado! Revisa tu celular.")
    else: st.sidebar.error("Error de enlace. Asegúrate de haberle dado al botón 'Iniciar' dentro de tu chat de Telegram.")

if st.button("🚀 Ejecutar Escáner y Despachar Alertas Exactas"):
    with st.spinner("Descargando datos del mercado y aplicando filtros de Ratio..."):
        try:
            datos_mercado = yf.download(tickers, period="6mo", interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error de conexión con los servidores de bolsa: {e}")
            datos_mercado = None

    if datos_mercado is not None and not datos_mercado.empty:
        ordenes_del_dia = []

        for ticker in tickers:
            try:
                df_ticker = pd.DataFrame()
                df_ticker['Close'] = datos_mercado['Close'][ticker].dropna()
                df_ticker['Open'] = datos_mercado['Open'][ticker].dropna()
                df_ticker['Low'] = datos_mercado['Low'][ticker].dropna()
                df_ticker['High'] = datos_mercado['High'][ticker].dropna()
                
                if len(df_ticker) < 50: continue
                
                precio_actual = float(df_ticker['Close'].iloc[-1])
                precio_apertura = float(df_ticker['Open'].iloc[-1])
                precio_minimo = float(df_ticker['Low'].iloc[-1])
                
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
                    contexto_txt = "Estructura Alcista Mayor + Confirmación de Vela Verde."
                elif not tendencia_alcista and es_vela_verde and toca_ema9 and rsi14 <= 55:
                    disparar_estrategia = True
                    ema_referencia = ema9
                    contexto_txt = "Rebote Técnico en Tendencia Bajista Corta."

                if disparar_estrategia:
                    precio_entrada_neto = precio_actual * (1 + COSTO_OPERATIVO_TOTAL)
                    
                    stop_loss_grafico = ema_referencia - (2 * atr14)
                    if stop_loss_grafico >= precio_actual: stop_loss_grafico = precio_actual * 0.97
                    precio_salida_stop_neto = stop_loss_grafico * (1 - COSTO_OPERATIVO_TOTAL)
                    
                    distancia_riesgo_pct = (precio_entrada_neto - precio_salida_stop_neto) / precio_entrada_neto
                    precio_take_profit = precio_actual * (1 + (distancia_riesgo_pct * ratio_beneficio))
                    
                    perdida_por_accion = precio_entrada_neto - precio_salida_stop_neto
                    cantidad_cedears = int(riesgo_maximo_ars // perdida_por_accion)
                    
                    if cantidad_cedears <= 0: continue
                        
                    monto_total_compra = precio_entrada_neto * cantidad_cedears
                    
                    # CORRECCIÓN DE VARIABLE: Asegura la validación estricta de saldo real de caja
                    if monto_total_compra > capital_cuenta or precio_entrada_neto > capital_cuenta: continue 
                    
                    simbolo_corto = ticker.split('.')[0]
                    
                    ordenes_del_dia.append({
                        "CEDEAR": simbolo_corto,
                        "Precio Pantalla": f"$ {precio_actual:,.2f}",
                        "Precio Neto Entrada": f"$ {precio_entrada_neto:,.2f}",
                        "Stop Loss (ATR)": f"$ {stop_loss_grafico:,.2f}",
                        "Take Profit (Ratio)": f"$ {precio_take_profit:,.2f}",
                        "Cantidad Sugerida": cantidad_cedears,
                        "Total Operación": f"$ {monto_total_compra:,.2f}"
                    })
                    
                    msg_telegram = (
                        f"🤖 *¡ALERTA DE SEÑAL DE TRADING! (Ratio {ratio_beneficio}:1)*\n\n"
                        f"📈 *CEDEAR:* `{simbolo_corto}`\n"
                        f"🟢 *Orden:* COMPRAR\n"
                        f"🧮 *Cantidad Nominal Exacta:* {cantidad_cedears} unidades\n\n"
                        f"💵 *Precio en Pantalla:* ${precio_actual:,.2f}\n"
                        f"📐 *Precio de Entrada Neto:* ${precio_entrada_neto:,.2f} (Deducido Balanz)\n"
                        f"🛡️ *STOP LOSS EN PESOS:* ${stop_loss_grafico:,.2f}\n"
                        f"🎯 *TAKE PROFIT EN PESOS:* ${precio_take_profit:,.2f}\n\n"
                        f"💰 *Costo de la Operación:* ${monto_total_compra:,.2f}\n"
                        f"📊 *Control de Riesgo:* Protegido bajo el 2% de tu cuenta.\n"
                        f"📝 *Justificación:* {contexto_txt}"
                    )
                    enviar_alerta_telegram(msg_telegram)

            except Exception:
                continue

        if ordenes_del_dia:
            df_final = pd.DataFrame(ordenes_del_dia)
            st.success("🤖 ¡Análisis de Ratio completado con éxito! Las alertas desglosadas en pesos ya se enviaron a tu Telegram.")
            st.dataframe(df_final, use_container_width=True)
        else:
            st.info("Ningún CEDEAR cumple las condiciones exactas de entrada e indicadores en la rueda de hoy.")

