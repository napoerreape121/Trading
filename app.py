import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# Rutas absolutas: los CSV quedan junto a app.py sin importar desde dónde ejecutes Streamlit
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DB = os.path.join(BASE_DIR, "portafolio.csv")
ARCHIVO_HISTORIAL = os.path.join(BASE_DIR, "historial_cerradas.csv")

COSTO_OPERATIVO_TOTAL = (0.0050 + 0.0005) * 1.21
COLUMNAS_PORTAFOLIO = ["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"]
MIN_VELAS = 50

# Configuración del panel de control inteligente en internet
st.set_page_config(page_title="Asistente Cuantitativo Pro", page_icon="🤖", layout="wide")

st.title("🤖 Asistente de Trading de CEDEARs con Gestión Activa de Portafolio")
st.write(
    "Monitoreo Dinámico: El bot analiza tus posiciones abiertas y te ordena ajustar el Stop Loss "
    "o cerrar para proteger tus ganancias."
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8624285419:AAHS-aTMjxM9H33dqtqC4JCQzwyqqL_Q71Y")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6872048498")


def enviar_alerta_telegram(mensaje):
    """Módulo oficial de comunicación en red con la API de Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def precio_compra_neto(precio_bruto):
    return precio_bruto * (1 + COSTO_OPERATIVO_TOTAL)


def precio_venta_neto(precio_bruto):
    return precio_bruto * (1 - COSTO_OPERATIVO_TOTAL)


def precio_venta_bruto(precio_neto):
    return precio_neto / (1 - COSTO_OPERATIVO_TOTAL)


def calcular_niveles_salida(precio_bruto, sl_bruto, ratio_beneficio):
    """Calcula SL/TP en precio pantalla con riesgo/recompensa neto simétrico."""
    precio_ent_neto = precio_compra_neto(precio_bruto)
    precio_sal_sl_neto = precio_venta_neto(sl_bruto)
    dist_riesgo = (precio_ent_neto - precio_sal_sl_neto) / precio_ent_neto
    precio_sal_tp_neto = precio_ent_neto * (1 + dist_riesgo * ratio_beneficio)
    precio_tp_bruto = precio_venta_bruto(precio_sal_tp_neto)
    return dist_riesgo, precio_tp_bruto, precio_ent_neto, precio_sal_sl_neto


def extraer_ohlc(datos, ticker):
    """Extrae OHLC compatible con descargas de 1 o N tickers en yfinance."""
    if datos is None or datos.empty:
        raise ValueError(f"Sin datos de mercado para {ticker}")

    columnas = datos.columns
    if isinstance(columnas, pd.MultiIndex):
        niveles = columnas.get_level_values(-1)
        if ticker in niveles:
            sub = datos.xs(ticker, axis=1, level=-1)
        elif ticker in columnas.get_level_values(0):
            sub = datos.xs(ticker, axis=1, level=0)
        else:
            sub = pd.DataFrame({
                "Open": datos["Open"][ticker],
                "High": datos["High"][ticker],
                "Low": datos["Low"][ticker],
                "Close": datos["Close"][ticker],
            })
    else:
        sub = datos[["Open", "High", "Low", "Close"]].copy()

    sub = sub.dropna()
    if len(sub) < MIN_VELAS:
        raise ValueError(f"Datos insuficientes para {ticker} ({len(sub)} velas)")
    return sub


def calcular_atr(df):
    high_low = df["High"] - df["Low"]
    high_close_prev = (df["High"] - df["Close"].shift()).abs()
    low_close_prev = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    if pd.isna(atr) or atr <= 0:
        raise ValueError("ATR inválido")
    return float(atr)


def calcular_rsi(close, window=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    valor = rsi.iloc[-1]
    if pd.isna(valor):
        return 50.0
    return float(valor)


def descargar_mercado(tickers, period="6mo"):
    if isinstance(tickers, str):
        tickers = [tickers]
    datos = yf.download(
        tickers,
        period=period,
        interval="1d",
        progress=False,
        group_by="column",
        auto_adjust=True,
        threads=True,
    )
    if datos is None or datos.empty:
        raise ValueError("yfinance no devolvió datos")
    return datos


def guardar_portafolio(df):
    df.to_csv(ARCHIVO_DB, index=False)


def cargar_portafolio():
    if not os.path.exists(ARCHIVO_DB):
        pd.DataFrame(columns=COLUMNAS_PORTAFOLIO).to_csv(ARCHIVO_DB, index=False)
    df = pd.read_csv(ARCHIVO_DB)
    if df.empty:
        return df
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    return df


def registrar_cierre(row, motivo, precio_cierre):
    registro = pd.DataFrame([{
        "Ticker": row["Ticker"],
        "Cantidad": int(row["Cantidad"]),
        "PrecioCompra": float(row["PrecioCompra"]),
        "StopLoss": float(row["StopLoss"]),
        "TakeProfit": float(row["TakeProfit"]),
        "FechaEntrada": row["FechaEntrada"],
        "FechaCierre": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "MotivoCierre": motivo,
        "PrecioCierre": float(precio_cierre),
    }])
    if os.path.exists(ARCHIVO_HISTORIAL):
        pd.concat([pd.read_csv(ARCHIVO_HISTORIAL), registro], ignore_index=True).to_csv(
            ARCHIVO_HISTORIAL, index=False
        )
    else:
        registro.to_csv(ARCHIVO_HISTORIAL, index=False)


def normalizar_ticker(ticker):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return ""
    if not ticker.endswith(".BA"):
        ticker = f"{ticker}.BA"
    return ticker


def validar_operacion(precio, sl, tp):
    if sl <= 0 or tp <= 0 or precio <= 0:
        return "Los precios deben ser mayores a cero."
    if not (sl < precio < tp):
        return "Debe cumplirse: Stop Loss < Precio de compra < Take Profit."
    return None


# Leer los datos guardados físicamente en el servidor
df_portafolio = cargar_portafolio()

# MÓDULO lateral: Carga de Operaciones Reales con Guardado Permanente
st.sidebar.header("📥 Registrar Compra Real en Balanz")
with st.sidebar.form(key="formulario_balanz", clear_on_submit=True):
    ticker_input = st.text_input("Ticker del CEDEAR (Ej: AAPL)")
    cant_real = st.number_input("Cantidad de nominales comprados", min_value=1, value=1, step=1)
    precio_real = st.number_input("Precio de compra por unidad ($)", min_value=0.01, value=1000.0, step=100.0)
    sl_real = st.number_input("Stop Loss inicial ($)", min_value=0.01, value=900.0, step=100.0)
    tp_real = st.number_input("Take Profit inicial ($)", min_value=0.01, value=1200.0, step=100.0)

    boton_guardar = st.form_submit_button(label="💾 Guardar y Monitorear Posición")

    if boton_guardar:
        ticker_real = normalizar_ticker(ticker_input)
        if not ticker_real:
            st.sidebar.error("Ingresá un ticker válido.")
        else:
            error_validacion = validar_operacion(precio_real, sl_real, tp_real)
            if error_validacion:
                st.sidebar.error(error_validacion)
            elif ticker_real in df_portafolio["Ticker"].values:
                st.sidebar.error(f"{ticker_real} ya está en el portafolio. Cerrala antes de reingresarla.")
            else:
                nueva_posicion = pd.DataFrame([{
                    "Ticker": ticker_real,
                    "Cantidad": int(cant_real),
                    "PrecioCompra": float(precio_real),
                    "StopLoss": float(sl_real),
                    "TakeProfit": float(tp_real),
                    "FechaEntrada": datetime.now().strftime("%Y-%m-%d"),
                }])
                df_actualizado = pd.concat([df_portafolio, nueva_posicion], ignore_index=True)
                guardar_portafolio(df_actualizado)
                st.sidebar.success(f"¡{ticker_real} grabado con éxito!")
                st.rerun()

# PANEL PRINCIPAL: Visualización de tus acciones bajo vigilancia permanente
st.subheader("📋 Tus Posiciones Abiertas Actualmente Activas")
if not df_portafolio.empty:
    st.dataframe(df_portafolio, use_container_width=True)

    if st.button("🗑️ Vaciar todo el Portafolio (Borrar Base de Datos)"):
        pd.DataFrame(columns=COLUMNAS_PORTAFOLIO).to_csv(ARCHIVO_DB, index=False)
        st.success("¡Base de datos limpiada correctamente!")
        st.rerun()
else:
    st.info("No tienes operaciones cargadas. El portafolio de vigilancia permanente está vacío.")

if os.path.exists(ARCHIVO_HISTORIAL):
    df_historial = pd.read_csv(ARCHIVO_HISTORIAL)
    if not df_historial.empty:
        with st.expander("📜 Historial de posiciones cerradas"):
            st.dataframe(df_historial, use_container_width=True)

# Resto del listado de tus 80 CEDEARs para escaneo de compras
tickers_escaner = [
    "AAL.BA", "ABT.BA", "ACWI.BA", "ADBE.BA", "AMD.BA", "AMZN.BA", "AAPL.BA", "ARM.BA", "ARKK.BA", "ASML.BA",
    "AXP.BA", "BAC.BA", "BA.BA", "BABA.BA", "BKNG.BA", "BP.BA", "BRKB.BA", "BX.BA", "C.BA", "CAT.BA",
    "CCL.BA", "COPX.BA", "COIN.BA", "COST.BA", "CRM.BA", "CVS.BA", "CVX.BA", "DAL.BA", "DE.BA", "DISN.BA",
    "DIA.BA", "EFA.BA", "ETHA.BA", "GE.BA", "GOOGL.BA", "GS.BA", "HD.BA", "HON.BA", "IBM.BA", "INTC.BA",
    "JNJ.BA", "JPM.BA", "KO.BA", "LLY.BA", "MA.BA", "MCD.BA", "META.BA", "MELI.BA", "MMM.BA", "MSFT.BA",
    "NFLX.BA", "NKE.BA", "NVDA.BA", "ORCL.BA", "PANW.BA", "PEP.BA", "PFE.BA", "PG.BA", "PYPL.BA", "QCOM.BA",
    "QQQ.BA", "ROKU.BA", "SHOP.BA", "SNOW.BA", "SONY.BA", "SPY.BA", "T.BA", "TEAM.BA", "TGT.BA", "TSLA.BA",
    "TSM.BA", "TXN.BA", "UAL.BA", "UBER.BA", "UNH.BA", "V.BA", "VZ.BA", "WFC.BA", "WMT.BA", "XOM.BA",
]

st.sidebar.header("⚙️ Parámetros del Escáner de Compras")
capital_disponible = st.sidebar.number_input("Tu Capital Total Libre ($ ARS)", min_value=10000, value=158000, step=10000)
riesgo_maximo_ars = capital_disponible * 0.02
ratio_beneficio = st.sidebar.slider("Ratio Recompensa / Riesgo Mínimo", 1.5, 3.5, 2.0, step=0.1)
umbral = st.sidebar.slider("Tolerancia de proximidad EMA", 0.001, 0.015, 0.005, step=0.001)

if st.button("🚀 Ejecutar Escáner General y Despachar Gestión"):
    df_portafolio_activo = cargar_portafolio()
    portafolio_modificado = False

    # PARTE 1: ANALIZADOR DE GESTIÓN ACTIVA
    if not df_portafolio_activo.empty:
        st.subheader("🕵️ Análisis Cuantitativo de tus Posiciones Abiertas")
        tickers_cartera = df_portafolio_activo["Ticker"].unique().tolist()
        indices_cerrar = []

        try:
            datos_cartera = descargar_mercado(tickers_cartera)

            for idx, row in df_portafolio_activo.iterrows():
                tick = row["Ticker"]
                try:
                    df_t_cart = extraer_ohlc(datos_cartera, tick)
                except Exception as err:
                    st.warning(f"No se pudo analizar {tick}: {err}")
                    continue

                precio_vivo = float(df_t_cart["Close"].iloc[-1])
                low_vivo = float(df_t_cart["Low"].iloc[-1])
                high_vivo = float(df_t_cart["High"].iloc[-1])

                ema9_v = float(df_t_cart["Close"].ewm(span=9, adjust=False).mean().iloc[-1])
                atr14_v = calcular_atr(df_t_cart)

                stop_actual = float(row["StopLoss"])
                take_profit = float(row["TakeProfit"])
                precio_compra = float(row["PrecioCompra"])

                # REGLA 1: CERRAR POSICIÓN Y ARCHIVAR CUANDO SL/TP SE DISPARA
                if low_vivo <= stop_actual:
                    msg_sl = (
                        f"🚨 *¡ALERTA CRÍTICA DE SALIDA!* 🚨\n\n"
                        f"📉 El CEDEAR `{tick.split('.')[0]}` perforó tu *Stop Loss* de ${stop_actual:,.2f}.\n"
                        f"🛒 *Acción:* VENDER de inmediato tus {int(row['Cantidad'])} unidades en Balanz.\n"
                        f"📁 La posición fue removida del monitoreo automático."
                    )
                    enviar_alerta_telegram(msg_sl)
                    registrar_cierre(row, "Stop Loss", stop_actual)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.error(f"{tick}: Stop Loss perforado. Posición cerrada en la base de datos.")
                    continue

                if high_vivo >= take_profit:
                    msg_tp = (
                        f"🎯 *¡ALERTA DE OBJETIVO CUMPLIDO!* 🎯\n\n"
                        f"📈 El CEDEAR `{tick.split('.')[0]}` tocó tu *Take Profit* de ${take_profit:,.2f}.\n"
                        f"🛒 *Acción:* VENDER tus {int(row['Cantidad'])} unidades en Balanz y retirar ganancias netas.\n"
                        f"📁 La posición fue removida del monitoreo automático."
                    )
                    enviar_alerta_telegram(msg_tp)
                    registrar_cierre(row, "Take Profit", take_profit)
                    indices_cerrar.append(idx)
                    portafolio_modificado = True
                    st.success(f"{tick}: Take Profit alcanzado. Posición cerrada en la base de datos.")
                    continue

                # REGLA 2: TRAILING STOP PERSISTENTE
                nuevo_stop = round(ema9_v - (1.5 * atr14_v), 2)
                if (
                    precio_vivo > precio_compra
                    and nuevo_stop > stop_actual
                    and nuevo_stop < precio_vivo
                ):
                    df_portafolio_activo.at[idx, "StopLoss"] = nuevo_stop
                    portafolio_modificado = True
                    st.info(
                        f"🔄 **{tick.split('.')[0]}:** Stop Loss actualizado a **${nuevo_stop:,.2f}** "
                        f"(antes ${stop_actual:,.2f}). Replicá el mismo valor en Balanz."
                    )
                    msg_trailing = (
                        f"🔄 *¡TRAILING STOP ACTUALIZADO!*\n\n"
                        f"📈 El CEDEAR `{tick.split('.')[0]}` sigue a tu favor.\n"
                        f"🛡️ *Nuevo Stop Loss:* `${nuevo_stop:,.2f}` (antes `${stop_actual:,.2f}`)\n"
                        f"🛠️ *Acción:* Actualizá la orden en Balanz (ya guardado en tu registro local)."
                    )
                    enviar_alerta_telegram(msg_trailing)

                # REGLA 3: ALERTA DE DEBILIDAD ESTRUCTURAL
                elif precio_vivo < ema9_v and precio_vivo > stop_actual:
                    st.warning(
                        f"⚠️ **Advertencia para {tick.split('.')[0]}:** El precio cerró por debajo de la EMA 9."
                    )
                    msg_debilidad = (
                        f"⚠️ *¡ADVERTENCIA DE DEBILIDAD TÉCNICA!*\n\n"
                        f"📉 El CEDEAR `{tick.split('.')[0]}` cerró por debajo de la EMA 9 (${precio_vivo:,.2f}).\n"
                        f"🛒 *Acción Sugerida:* Evalúa cerrar la posición de forma anticipada en Balanz."
                    )
                    enviar_alerta_telegram(msg_debilidad)

            if indices_cerrar:
                df_portafolio_activo = df_portafolio_activo.drop(indices_cerrar).reset_index(drop=True)
            if portafolio_modificado:
                guardar_portafolio(df_portafolio_activo)

        except Exception as e:
            st.warning(f"No se pudo auditar dinámicamente tu portafolio: {e}. Continuando con el escáner...")

    # PARTE 2: BUSCAR NUEVAS COMPRAS INTELIGENTES
    with st.spinner("Buscando las mejores oportunidades según tu capital disponible hoy..."):
        datos_mercado = None
        try:
            datos_mercado = descargar_mercado(tickers_escaner)
        except Exception as e:
            st.error(f"No se pudieron descargar datos del mercado: {e}")

    if datos_mercado is not None and not datos_mercado.empty:
        candidatos_validos = []
        tickers_en_cartera = set(df_portafolio_activo["Ticker"].tolist()) if not df_portafolio_activo.empty else set()

        for ticker in tickers_escaner:
            if ticker in tickers_en_cartera:
                continue
            try:
                df_t = extraer_ohlc(datos_mercado, ticker)

                precio_act = float(df_t["Close"].iloc[-1])
                precio_ape = float(df_t["Open"].iloc[-1])
                precio_min = float(df_t["Low"].iloc[-1])

                if precio_act <= 0:
                    continue

                ema9 = float(df_t["Close"].ewm(span=9, adjust=False).mean().iloc[-1])
                ema50 = float(df_t["Close"].ewm(span=50, adjust=False).mean().iloc[-1])
                atr14 = calcular_atr(df_t)
                rsi14 = calcular_rsi(df_t["Close"])

                exp1 = df_t["Close"].ewm(span=12, adjust=False).mean()
                exp2 = df_t["Close"].ewm(span=26, adjust=False).mean()
                macd_line = exp1 - exp2
                macd_hist = macd_line - macd_line.ewm(span=9, adjust=False).mean()
                histograma_macd = float(macd_hist.iloc[-1])
                hist_anterior = float(macd_hist.iloc[-2])

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

                if not disparar:
                    continue

                sl_g = ema_ref - (2 * atr14)
                if sl_g >= precio_act * 0.97:
                    sl_g = precio_act * 0.97
                if sl_g <= 0 or sl_g >= precio_act:
                    continue

                dist_riesgo, precio_tp, precio_ent_neto, precio_sal_sl_neto = calcular_niveles_salida(
                    precio_act, sl_g, ratio_beneficio
                )
                if dist_riesgo <= 0 or precio_tp <= precio_act:
                    continue

                perdida_accion = precio_ent_neto - precio_sal_sl_neto
                if perdida_accion <= 0:
                    continue

                cant_cedears = int(riesgo_maximo_ars // perdida_accion)
                if cant_cedears <= 0:
                    continue

                monto_compra = precio_ent_neto * cant_cedears
                if monto_compra > capital_disponible or precio_ent_neto > capital_disponible:
                    continue

                score = 0
                if 40 < rsi14 < 60:
                    score += 1
                if histograma_macd > hist_anterior:
                    score += 1
                if tendencia_alcista:
                    score += 1

                candidatos_validos.append({
                    "Ticker": ticker,
                    "Precio": round(precio_act, 2),
                    "Neto": round(precio_ent_neto, 2),
                    "StopLoss": round(sl_g, 2),
                    "TakeProfit": round(precio_tp, 2),
                    "Cantidad": cant_cedears,
                    "Total": round(monto_compra, 2),
                    "Score": score,
                })
            except Exception:
                continue

        if candidatos_validos:
            df_ops = pd.DataFrame(candidatos_validos).sort_values(
                by=["Score", "Total"], ascending=[False, False]
            ).reset_index(drop=True)
            mejor_opcion = df_ops.iloc[0]

            st.success("🤖 ¡Análisis de Oportunidades Completado!")
            st.subheader("🎯 La Mejor Decisión Sugerida por el Cerebro Cuantitativo")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("CEDEAR", mejor_opcion["Ticker"])
            col_b.metric("Cantidad de Nominales", int(mejor_opcion["Cantidad"]))
            col_c.metric("Capital Invertido Neto", f"$ {mejor_opcion['Total']:,.2f}")

            msg_tg = (
                f"🤖 *¡ASIGNACIÓN DE CAPITAL REALISTA EN APERTURA!*\n\n"
                f"🎯 *CEDEAR Seleccionado:* `{mejor_opcion['Ticker']}`\n"
                f"🧮 *Cantidad nominal a comprar:* {int(mejor_opcion['Cantidad'])} unidades\n\n"
                f"💵 *Precio Pantalla:* ${mejor_opcion['Precio']:,.2f}\n"
                f"📐 *Precio Entrada Neto:* ${mejor_opcion['Neto']:,.2f}\n"
                f"🛡️ *ORDEN DE STOP LOSS:* ${mejor_opcion['StopLoss']:,.2f}\n"
                f"🎯 *ORDEN DE TAKE PROFIT:* ${mejor_opcion['TakeProfit']:,.2f}\n\n"
                f"💰 *Costo Total:* ${mejor_opcion['Total']:,.2f}\n"
                f"🔍 *Score de Calidad:* {int(mejor_opcion['Score'])} / 3 Puntos."
            )
            enviar_alerta_telegram(msg_tg)
            st.dataframe(df_ops, use_container_width=True)
        else:
            st.info("Ningún CEDEAR reúne las condiciones técnicas en la rueda en vivo de hoy.")

    if portafolio_modificado:
        st.subheader("📋 Portafolio actualizado tras la gestión")
        st.dataframe(df_portafolio_activo, use_conta
