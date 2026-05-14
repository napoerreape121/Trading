import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# Configuración del panel de control inteligente en internet
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")
st.title("🤖 Asistente de Trading de CEDEARs con Gestión de Portafolio")
st.write("Carga tus operaciones reales de Balanz. El bot vigilará tus Stop Loss y Take Profit de forma automatizada.")

# Credenciales fijas y verificadas de tu canal de Telegram
TELEGRAM_TOKEN = "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y"
TELEGRAM_CHAT_ID = "6872048498"

def enviar_alerta_telegram(mensaje):
    """Módulo oficial de comunicación en red con la API de Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# BASE DE DATOS LOCAL PERMANENTE: Inicializar o leer el archivo portafolio.csv en el disco duro
ARCHIVO_DB = "portafolio.csv"
if not os.path.exists(ARCHIVO_DB):
    df_inicial = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
    df_inicial.to_csv(ARCHIVO_DB, index=False)

# Leer los datos guardados físicamente en el servidor
df_portafolio = pd.read_csv(ARCHIVO_DB)

# MÓDULO lateral: Carga de Operaciones Reales con Guardado Permanente
st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_real = st.text_input("Ticker del CEDEAR (Ej: AAPL)").upper().strip()
    if ticker_real and not ticker_real.endswith(".BA"):
        ticker_real = f"{ticker_real}.BA"
    
    cant_real = st.number_input("Cantidad de nominales comprados", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra por unidad ($)", min_value=1.0, value=1000.0, step=100.0)
    sl_real = st.number_input("Stop Loss fijado ($)", min_value=0.0, value=900.0, step=100.0)
    tp_real = st.number_input("Take Profit fijado ($)", min_value=0.0, value=1200.0, step=100.0)
    
    boton_guardar = st.form_submit_button(label="💾 Guardar de Forma Permanente")
    
    if boton_guardar and ticker_real:
        nueva_posicion = pd.DataFrame([{
            "Ticker": ticker_real, "Cantidad": int(cant_real), "PrecioCompra": float(precio_real),
            "StopLoss": float(sl_real), "TakeProfit": float(tp_real), "FechaEntrada": datetime.now().strftime('%Y-%m-%d')
        }])
        
        df_actualizado = pd.concat([df_portafolio, nueva_posicion], ignore_index=True)
        df_actualizado.to_csv(ARCHIVO_DB, index=False)
        st.sidebar.success(f"¡{ticker_real} grabado en el disco duro con éxito!")
        st.rerun()

# PANEL PRINCIPAL: Visualización de tus acciones bajo vigilancia permanente
st.subheader("📋 Tus Posiciones Abiertas Actualmente Activas")
if not df_portafolio.empty:
    st.dataframe(df_portafolio, use_container_width=True)
    
    if st.button("🗑️ Vaciar todo el Portafolio (Borrar Base de Datos)"):
        df_limpio = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
        df_limpio.to_csv(ARCHIVO_DB, index=False)
        st.success("¡Base de datos limpiada correctamente!")
        st.rerun()
else:
    st.info("No tienes operaciones cargadas. El portafolio de vigilancia permanente está vacío.")

# Listado de tus 80 CEDEARs para escaneo de compras
tickers_escaner = [
    'AAL.BA','ABT.BA','ACWI.BA','ADBE.BA','AMD.BA','AMZN.BA','AAPL.BA','ARM.BA','ARKK.BA','ASML.BA',
    'AXP.BA','BAC.BA','BA.BA','BABA.BA','BKNG.BA','BP.BA','BRKB.BA','BX.BA','C.BA','CAT.BA',
    'CCL.BA','COPX.BA','COIN.BA','COST.BA','CRM.BA','CVS.BA','CVX.BA','DAL.BA','DE.BA','DISN.BA',
    'DIA.BA','EFA.BA','ETHA.BA','GE.BA','GOOGL.BA','GS.BA','HD.BA','HON.BA','IBM.BA','INTC.BA',
    'JNJ.BA','JPM.BA','KO.BA','LLY.BA','MA.BA','MCD.BA','META.BA','MELI.BA','MMM.BA','MSFT.BA',
    'NFLX.BA','NKE.BA','NVDA.BA','ORCL.BA','PANW.BA','PEP.BA','PFE.BA','PG.BA','PYPL.BA','QCOM.BA',
    'QQQ.BA','ROKU.BA','SHOP.BA','SNOW.BA','SONY.BA','SPY.BA','T.BA','TEAM.BA','TGT.BA','TSLA.BA',
    'TSM.BA','TXN.BA','UAL.BA','UBER.BA','UNH.BA','V.BA','VZ.BA','WFC.BA','WMT.BA','XOM.BA'
]

st.sidebar.header("⚙️ Parámetros del Escáner de Compras")
capital_disponible = st.sidebar.number_input("Tu Capital Total Libre ($ ARS)", min_value=10000, value=158000, step=10000)
riesgo_maximo_ars = capital_disponible * 0.02
ratio_beneficio = st.sidebar.slider("Ratio Recompensa / Riesgo Mínimo", 1.5, 3.5, 2.0, step=0.1)
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)
COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21 

if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    # PARTE 1: ESCANEAR SALIDAS CRÍTICAS DE TUS COMPRAS REALES
    if not df_portafolio.empty:
        st.write("🔍 Verificando estado de tus acciones en cartera...")
        tickers_cartera = df_portafolio["Ticker"].unique().tolist()
        try:
            datos_cartera = yf.download(tickers_cartera, period="5d", interval="1d", progress=False)
            for idx, row in df_portafolio.iterrows():
                tick = row["Ticker"]
                close_vivo = float(datos_cartera['Close'][tick].dropna().iloc[-1])
                low_vivo = float(datos_cartera['Low'][tick].dropna().iloc[-1])
                high_vivo = float(datos_cartera['High'][tick].dropna().iloc[-1])
                
                if low_vivo <= float(row["StopLoss"]):
                    msg_sl = f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n📉 El CEDEAR `{tick}` tocó tu *Stop Loss* de ${row['StopLoss']:,.2f}.\n🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades en Balanz para cortar pérdidas."
                    enviar_alerta_telegram(msg_sl)
                    st.error(f"¡Alerta de Venta Enviada para {tick} por Stop Loss!")
                    
                elif high_vivo >= float(row["TakeProfit"]):
                    msg_tp = f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n📈 El CEDEAR `{tick}` tocó tu *Take Profit* de ${row['TakeProfit']:,.2f}.\n🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades en Balanz y cobrar ganancias netas."
                    enviar_alerta_telegram(msg_tp)
                    st.success(f"¡Alerta de Venta Enviada para {tick} por Ganancia Cumplida!")
        except Exception as e:
            st.warning("No se pudieron verificar las salidas de cartera. Continuando con escaner de compras...")

    # PARTE 2: BUSCAR NUEVAS COMPRAS INTELIGENTES Y EVALUAR RECOMPRAS
    with st.spinner("Buscando las mejores oportunidades según tu capital disponible hoy..."):
        detalles_bloqueo_capital = {}
        
        try:
            datos_mercado = yf.download(tickers_escaner, period="6mo", interval="1d", progress=False)
        except Exception:
            datos_mercado = None
            
        if datos_mercado is not None and not datos_mercado.empty:
            candidatos_validos = []
            for ticker in tickers_escaner:
                try:
                    df_t = pd.DataFrame()
                    df_t['Close'] = datos_mercado['Close'][ticker].dropna()
                    df_t['Open'] = datos_mercado['Open'][ticker].dropna()
                    df_t['Low'] = datos_mercado['Low'][ticker].dropna()
                    df_t['High'] = datos_mercado['High'][ticker].dropna()
                    
                    precio_act = float(df_t['Close'].iloc[-1])
                    precio_ape = float(df_t['Open'].iloc[-1])
                    precio_min = float(df_t['Low'].iloc[-1])
                    
                    ema9 = df_t['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                    ema50 = df_t['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                    
                    high_low = df_t['High'] - df_t['Low']
                    high_close_prev = abs(df_t['High'] - df_t['Close'].shift())
                    low_close_prev = abs(df_t['Low'] - df_t['Close'].shift())
                    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
                    atr14 = true_range.rolling(14).mean().iloc[-1]
                    
                    delta = df_t['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi14 = 100 - (100 / (1 + (gain / loss))).iloc[-1]
                    
                    exp1 = df_t['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = df_t['Close'].ewm(span=26, adjust=False).mean()
                    histograma_macd = (exp1 - exp2 - (exp1 - exp2).ewm(span=9, adjust=False).mean()).iloc[-1]
                    hist_anterior = (exp1 - exp2 - (exp1 - exp2).ewm(span=9, adjust=False).mean()).iloc[-2]
                    
                    es_vela_verde = precio_act > precio_ape
                    tendencia_alcista = precio_act > ema50
                    toca_ema9 = abs(precio_min - ema9) / precio_act <= umbral
                    toca_ema50 = abs(precio_min - ema50) / precio_act <= umbral
                    
                    disparar = False
                    ema_ref = ema50
                    if tendencia_alcista and es_vela_verde and (toca_ema9 or toca_ema50):
                        disparar = True
                        ema_ref = ema50 if toca_ema50 else ema9
                    elif not tendencia_alcista and es_vela_verde and toca_ema9 and rsi14 <= 55:
                        disparar = True
                        ema_ref = ema9
                        
                    if disparar:
                        precio_ent_neto = precio_act * (1 + COSTO_OPERATIVO_TOTAL)
                        sl_g = ema_ref - (2 * atr14)
                        if sl_g >= precio_act * 0.97: 
                            sl_g = precio_act * 0.97
                        precio_sal_sl_neto = sl_g * (1 - COSTO_OPERATIVO_TOTAL)
                        
                        dist_riesgo = (precio_ent_neto - precio_sal_sl_neto) / precio_ent_neto
                        precio_tp = precio_act * (1 + (dist_riesgo * ratio_beneficio))
                        
                        perdida_accion = precio_ent_neto - precio_sal_sl_neto
                        cant_cedears = int(riesgo_maximo_ars // perdida_accion)
                        
                        if cant_cedears <= 0: 
                            continue
                        monto_compra = precio_ent_neto * cant_cedears
                        
                        ticker_limpio = ticker.replace('.BA', '')
                        
                        # EVALUACIÓN ESPECÍFICA DE CAPITAL DISPONIBLE
                        if monto_compra > capital_disponible or precio_ent_neto > capital_disponible: 
                            detalles_bloqueo_capital[ticker_limpio] = {
                                "MontoRequerido": monto_compra,
                                "CantidadSugerida": cant_cedears
                            }
                            continue
                        
                        score = 0
                        if 40 < rsi14 < 60: score += 1
                        if histograma_macd > hist_anterior: score += 1
                        if tendencia_alcista: score += 1
                        
                        candidatos_validos.append({
                            "Ticker": ticker_limpio, "Precio": precio_act, "Neto": precio_ent_neto,
                            "StopLoss": sl_g, "TakeProfit": precio_tp, "Cantidad": cant_cedears,
                            "Total": monto_compra, "Score": score, "PerdidaUnidad": perdida_accion
                        })
                except Exception:
                    continue
            
            # CONSTRUCCIÓN DINÁMICA DEL INVENTARIO ACTUAL DE OPERACIONES REALES
            texto_inventario_completo = ""
            if not df_portafolio.empty:
                texto_inventario_completo = "\n\n📦 *Tu Inventario Actual en Cartera (Balanz):*"
                for idx, row in df_portafolio.iterrows():
                    t_corto = row["Ticker"].replace('.BA', '')
                    texto_inventario_completo += f"\n• `{t_corto}`: {int(row['Cantidad'])} papeles comprados a ${row['PrecioCompra']:,.2f}"
            else:
                texto_inventario_completo = "\n\n📌 *Cartera Actual Abierta:* Ninguna posición activa."
                    
            # DESPACHO DE ENTRADAS VÁLIDAS
            if candidatos_validos:
                df_ops = pd.DataFrame(candidatos_validos).sort_values(by="Score", ascending=False).reset_index(drop=True)
                mejor_opcion = df_ops.iloc[0]
                
                # ------ REGLA REPARADA DEL TRIÁNGULO DE HIERRO EXTREMO ------
                saldo_restante = capital_disponible - mejor_opcion["Total"]
                riesgo_consumido = int(mejor_opcion["Cantidad"]) * mejor_opcion["PerdidaUnidad"]
                riesgo_remanente_permitido = riesgo_maximo_ars - riesgo_consumido
                
                # El límite ya no es la billetera, es el riesgo remanente del 2% estricto
                if riesgo_remanente_permitido >= mejor_opcion["PerdidaUnidad"]:
                    papeles_extras_posibles = int(riesgo_remanente_permitido // mejor_opcion["PerdidaUnidad"])
                    # Doble verificación: que no supere el dinero físico que queda en la cuenta
                    max_por_dinero = int(saldo_restante // mejor_opcion["Neto"])
                    if papeles_extras_posibles > max_por_dinero:
                        papeles_extras_posibles = max_por_dinero
                        
                    if papeles_extras_posibles > 0:
                        texto_estado_billetera = (
                            f"\n\n🛡️ *TRIÁNGULO DE HIERRO (Gestión de Riesgo):*"
                            f"\n✅ *Riesgo controlado:* La operación sugerida consume ${riesgo_consumido:,.2f} de riesgo."
                            f"\n• Saldo remanente proyectado: ${saldo_restante:,.2f}"
                            f"\n• Resguardo de capital: Podrías añadir hasta `{papeles_extras_posibles}` nominales extras de `{mejor_opcion['Ticker']}` sin superar el límite estricto del 2% de riesgo de tu cuenta."
                        )
                    else:
                        texto_estado_billetera = (
                            f"\n\n🛡️ *TRIÁNGULO DE HIERRO (Gestión de Riesgo):*"
                            f"\n🛑 *Límite de riesgo alcanzado:* Comprar más papeles violaría la regla del 2%."
                            f"\n• Aunque te queden ${saldo_restante:,.2f} en efectivo, NO podés comprar más nominales porque aumentarías la pérdida potencial por encima de tu tolerancia máxima."
                        )
                else:
                    texto_estado_billetera = (
                        f"\n\n🛡️ *TRIÁNGULO DE HIERRO (Gestión de Riesgo):*"
                        f"\n🛑 *Límite de riesgo alcanzado:* La orden sugerida de `{int(mejor_opcion['Cantidad'])}` unidades ya ocupa el 100% de tu riesgo permitido."
                        f"\n• NO tenés permitido comprar más nominales de `{mejor_opcion['Ticker']}` para proteger tu capital ante un salto del Stop Loss."
                    )
                # ------------------------------------------------------------------------

                es_recompra = False
                papeles_viejos = 0
                if not df_portafolio.empty and (mejor_opcion["Ticker"] in df_portafolio["Ticker"].str.replace('.BA', '', regex=False).values):
                    es_recompra = True
                    papeles_viejos = int(df_portafolio[df_portafolio["Ticker"].str.replace('.BA', '', regex=False) == mejor_opcion["Ticker"]]["Cantidad"].sum())

                tipo_operacion = f"🔄 *RECOMPRA / REFUERZO DE CARTERA*" if es_recompra else f"🎯 *NUEVO CEDEAR SELECCIONADO*"
                detalle_recompra = f"\n⚠️ *Nota:* Ya tenés `{papeles_viejos}` papeles de este activo. La estrategia valida comprar `{int(mejor_opcion['Cantidad'])}` nominales más porque tenés capital libre." if es_recompra else ""

                st.success("🤖 ¡Análisis de Oportunidades Completado!")
                st.subheader("🎯 Decisión Sugerida por el Cerebro Cuantitativo")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("CEDEAR", mejor_opcion["Ticker"])
                col_a.metric("Nominales Nuevos", int(mejor_opcion["Cantidad"]))
                col_c.metric("Costo Operación", f"$ {mejor_opcion['Total']:,.2f}")
                
                msg_tg = (
                    f"🤖 *¡INFORME DE SEÑALES EN RUEDA VIVO!*\n\n"
                    f"{tipo_operacion}: `{mejor_opcion['Ticker']}`\n"
                    f"🤖 *Cantidad adicional a comprar:* {int(mejor_opcion['Cantidad'])} unidades\n"
                    f"💵 *Precio Pantalla:* ${mejor_opcion['Precio']:,.2f}\n"
                    f"📐 *Precio Entrada Neto:* ${mejor_opcion['Neto']:,.2f}\n"
                    f"🛡️ *ORDEN DE STOP LOSS:* ${mejor_opcion['StopLoss']:,.2f}\n"
                    f"🎯 *ORDEN DE TAKE PROFIT:* ${mejor_opcion['TakeProfit']:,.2f}\n\n"
                    f"💰 *Costo Operación:* ${mejor_opcion['Total']:,.2f}\n"
                    f"🔍 *Score Técnico:* {int(mejor_opcion['Score'])} / 3 Puntos."
                    f"{detalle_recompra}"
                    f"{texto_estado_billetera}"
                    f"{texto_inventario_completo}"
                )
                enviar_alerta_telegram(msg_tg)
                st.dataframe(df_ops.drop(columns=["PerdidaUnidad"]), use_container_width=True)
            
            # MANEJO EXCLUSIVO DE BLOQUEOS POR FALTA DE CAPITAL INICIAL
            else:
                if detalles_bloqueo_capital and not df_portafolio.empty:
                    ticker_bloqueado_cartera = None
                    for tk in detalles_bloqueo_capital.keys():
                        if tk in df_portafolio["Ticker"].str.replace('.BA', '', regex=False).values:
                            ticker_bloqueado_cartera = tk
                            break
                    
                    if ticker_bloqueado_cartera:
                        info_bloqueo = detalles_bloqueo_capital[ticker_bloqueado_cartera]
                        cant_poseida = int(df_portafolio[df_portafolio["Ticker"].str.replace('.BA', '', regex=False) == ticker_bloqueado_cartera]["Cantidad"].sum())
                        falta_dinero = info_bloqueo["MontoRequerido"] - capital_disponible
                        
                        msg_bloqueo = (
                            f"⚠️ *SEÑAL DE RECOMPRA DETENIDA POR CAPITAL* ⚠️\n\n"
                            f"El CEDEAR `{ticker_bloqueado_cartera}` dio señal técnica para comprar más papeles según la estrategia.\n\n"
                            f"📊 *Evaluación de Cartera:*\n"
                            f"• Actualmente tenés: `{cant_poseida}` papeles comprados en Balanz.\n"
                            f"• La estrategia sugiere añadir: `{info_bloqueo['CantidadSugerida']}` nominales.\n"
                            f"• Costo de la operación: ${info_bloqueo['MontoRequerido']:,.2f}\n"
                            f"• Tu capital libre: ${capital_disponible:,.2f}\n"
                            f"❌ *Resultado:* NO se puede ejecutar la recompra. Te faltan `${falta_dinero:,.2f}` de saldo libre para procesar este activo."
                            f"{texto_inventario_completo}"
                        )
                    else:
                        primer_tk = list(detalles_bloqueo_capital.keys())
                        info_bloqueo = detalles_bloqueo_capital[primer_tk]
                        falta_dinero = info_bloqueo["MontoRequerido"] - capital_disponible
                        
                        msg_bloqueo = (
                            f"⚠️ *ALERTA DE LIQUIDEZ BLOQUEADA* ⚠️\n\n"
                            f"Se detectó señal de compra en `{primer_tk}` para adquirir `{info_bloqueo['CantidadSugerida']}` unidades por un total de ${info_bloqueo['MontoRequerido']:,.2f}.\n\n"
                            f"❌ *Resultado:* Tu capital actual de ${capital_disponible:,.2f} no es suficiente para esta operación. Precisás `${falta_dinero:,.2f}` adicionales."
                            f"{texto_inventario_completo}"
                        )
                        
                    enviar_alerta_telegram(msg_bloqueo)
                    st.warning("Señales congeladas por saldo insuficiente. Reporte de balance detallado despachado a Telegram.")
                else:
                    st.info("Ningún CEDEAR reúne las condiciones técnicas en la rueda en vivo de hoy.")
