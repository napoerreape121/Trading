import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta

# Configuración de la interfaz web
st.set_page_config(
    page_title="Simulador Multitemporal Avanzado", 
    page_icon="🧪", 
    layout="wide"
)
st.title("🧪 Simulador Histórico con Capital Limitado y Estrategia de Confluencias")
st.write("Sistema Cuantitativo Estricto: Tendencia (EMA 200), Momentum (MACD + RSI 40-65), Gatillo de Volumen y Control de Capital Real ($1.000.000 ARS iniciales).")

# Universo de CEDEARs bajo vigilancia
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

# Configuración inicial de la simulación en la barra lateral
st.sidebar.header("💰 Parámetros Financieros")
capital_inicial = st.sidebar.number_input("Capital Inicial ($ ARS)", min_value=100000, value=1000000, step=50000)

st.sidebar.header("📅 Período de la Simulación")
opcion_tiempo = st.sidebar.radio("Horizonte temporal a testear:", ("1 Año", "2 Años", "3 Años"), index=0)

if opcion_tiempo == "1 Año":
    periodo_download = "18mo"
    ruedas_recorte = 250
elif opcion_tiempo == "2 Años":
    periodo_download = "30mo"
    ruedas_recorte = 500
else:
    periodo_download = "42mo"
    ruedas_recorte = 750

# Estructura de aranceles (Balanz + Derechos + IVA)
COSTO_OPERATIVO = (0.0050 + 0.0005) * 1.21 

if "diccionario_precios_historicos" not in st.session_state:
    st.session_state.diccionario_precios_historicos = {}

# =====================================================================
# 🚀 MOTOR DE SIMULACIÓN HISTÓRICA CON CONFLUENCIAS Y CAPITAL REAL
# =====================================================================
if st.button(f"🧪 Iniciar Simulación con Capital Limitado ({opcion_tiempo})"):
    with st.spinner(f"Descargando historiales de {opcion_tiempo} de Yahoo Finance..."):
        try:
            datos_globales = yf.download(tickers, period=periodo_download, interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error al descargar historial: {e}")
            datos_globales = None

    if datos_globales is not None and not datos_globales.empty:
        st.session_state.diccionario_precios_historicos = {}
        lista_fechas_totales = []
        
        for ticker in tickers:
            try:
                df = pd.DataFrame()
                df['Close'] = datos_globales['Close'][ticker].dropna()
                df['Open'] = datos_globales['Open'][ticker].dropna()
                df['Low'] = datos_globales['Low'][ticker].dropna()
                df['High'] = datos_globales['High'][ticker].dropna()
                df['Volume'] = datos_globales['Volume'][ticker].dropna()
                
                if len(df) < 200: 
                    continue
                
                # Indicadores de la Estrategia Estricta
                df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
                df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
                df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
                df['MACD_Hist'] = ta.trend.MACD(df['Close']).macd_diff()
                df['ATR_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
                df['Vol_SMA_9'] = df['Volume'].rolling(window=9).mean()
                
                df = df.dropna()
                df.index = pd.to_datetime(df.index).normalize()
                
                st.session_state.diccionario_precios_historicos[ticker] = df.copy()
                
                df_recortado = df.tail(ruedas_recorte)
                lista_fechas_totales.extend(df_recortado.index.tolist())
            except Exception:
                continue

        fechas_unicas = sorted(list(set(lista_fechas_totales)))
        
        if fechas_unicas and st.session_state.diccionario_precios_historicos:
            posiciones_activas = {}
            historial_trades = []
            efectivo = capital_inicial
            
            total_fechas = len(fechas_unicas)
            
            for f in range(total_fechas - 1):
                fecha_hoy = fechas_unicas[f]
                fecha_manana = fechas_unicas[f+1]
                
                capital_liberado_hoy = 0
                tickers_a_cerrar = []
                
                # FASE A: Auditar posiciones abiertas (SL, TP y Trailing dinámico)
                for t_activo, pos in list(posiciones_activas.items()):
                    df_activo = st.session_state.diccionario_precios_historicos[t_activo]
                    
                    if fecha_manana in df_activo.index:
                        row_m = df_activo.loc[fecha_manana]
                        prox_low = float(row_m["Low"])
                        prox_high = float(row_m["High"])
                        prox_close = float(row_m["Close"])
                        ema9_m = float(row_m["EMA_9"])
                        atr_m = float(row_m["ATR_14"])
                        
                        cerrar = False
                        resultado_str = ""
                        precio_salida_bruto = 0
                        
                        # 1. Comprobar Stop Loss
                        if prox_low <= pos["StopLoss"]:
                            cerrar = True
                            precio_salida_bruto = pos["StopLoss"]
                            resultado_str = "🔴 STOP LOSS"
                        # 2. Comprobar Take Profit (Ratio 1:2)
                        elif prox_high >= pos["TakeProfit"]:
                            cerrar = True
                            precio_salida_bruto = pos["TakeProfit"]
                            resultado_str = "🎯 TAKE PROFIT"
                        
                        if cerrar:
                            precio_salida_neto = precio_salida_bruto * (1 - COSTO_OPERATIVO)
                            monto_recuperado = precio_salida_neto * pos["Cantidad"]
                            monto_invertido_inicial = pos["PrecioCompraNeto"] * pos["Cantidad"]
                            ganancia_pura_pesos = monto_recuperado - monto_invertido_inicial
                            
                            capital_liberado_hoy += monto_recuperado
                            rend_trade = ((precio_salida_neto - pos["PrecioCompraNeto"]) / pos["PrecioCompraNeto"]) * 100
                            
                            historial_trades.append({
                                "Fecha Compra": pos["FechaEntrada"],
                                "Fecha Venta": fecha_manana,
                                "CEDEAR": t_activo, 
                                "Resultado": resultado_str, 
                                "Rendimiento (%)": round(rend_trade, 2),
                                "Cantidad Nominales": pos["Cantidad"], 
                                "Monto Neto Recuperado": monto_recuperado,
                                "Ganancia Neta Trade ($)": ganancia_pura_pesos,
                                "Precio Compra ($)": pos["PrecioCompraNeto"],
                                "Precio Salida ($)": precio_salida_neto,
                                "SL Inicial": pos["StopLoss"],
                                "TP Inicial": pos["TakeProfit"]
                            })
                            tickers_a_cerrar.append(t_activo)
                        else:
                            # Actualización de Trailing Stop dinámico basado en EMA9 y ATR
                            nuevo_stop = round(ema9_m - (1.5 * atr_m), 2)
                            if prox_close > pos["PrecioCompraNeto"] and nuevo_stop > pos["StopLoss"] and nuevo_stop < prox_close:
                                pos["StopLoss"] = nuevo_stop
                
                for t in tickers_a_cerrar:
                    posiciones_activas.pop(t)
                
                efectivo += capital_liberado_hoy
                
                # FASE B: Buscar señales de compra al cierre de HOY
                tickers_en_cartera = set(posiciones_activas.keys())
                
                for tick, df_activo in st.session_state.diccionario_precios_historicos.items():
                    if tick in tickers_en_cartera: 
                        continue
                    
                    if (fecha_hoy in df_activo.index) and (fecha_manana in df_activo.index):
                        row_hoy = df_activo.loc[fecha_hoy]
                        prev_idx = df_activo.index.get_loc(fecha_hoy) - 1
                        if prev_idx < 0:
                            continue
                        row_prev = df_activo.iloc[prev_idx]
                        
                        p_close = float(row_hoy["Close"])
                        p_open = float(row_hoy["Open"])
                        ema_200 = float(row_hoy["EMA_200"])
                        ema_9 = float(row_hoy["EMA_9"])
                        rsi = float(row_hoy["RSI_14"])
                        macd_hist = float(row_hoy["MACD_Hist"])
                        prev_macd_hist = float(row_prev["MACD_Hist"])
                        vol = float(row_hoy["Volume"])
                        vol_sma9 = float(row_hoy["Vol_SMA_9"])
                        atr = float(row_hoy["ATR_14"])
                        
                        # Filtros estrictos de la estrategia
                        cond_tendencia = p_close > ema_200
                        cond_momentum = (p_close > ema_9) and (macd_hist > prev_macd_hist) and (40 < rsi < 65)
                        cond_gatillo = (p_close > p_open) and (vol > vol_sma9)
                        
                        if cond_tendencia and cond_momentum and cond_gatillo:
                            row_manana = df_activo.loc[fecha_manana]
                            p_open_manana = float(row_manana["Open"])
                            
                            p_neto_entrada = p_open_manana * (1 + COSTO_OPERATIVO)
                            stop_loss = p_neto_entrada - (2 * atr)
                            target = p_neto_entrada + ((p_neto_entrada - stop_loss) * 2)
                            
                            riesgo_por_accion = p_neto_entrada - stop_loss
                            if stop_loss <= 0 or riesgo_por_accion <= 0:
                                continue
                            
                            # Cálculo de capital total actual (Efectivo + Valor nominal actual en cartera)
                            capital_total_actual = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
                            riesgo_maximo_ars = capital_total_actual * 0.02  # Arriesgar máximo 2% del capital total por trade
                            
                            cantidad = int(riesgo_maximo_ars // riesgo_por_accion)
                            if cantidad <= 0:
                                continue
                            
                            costo_total = p_neto_entrada * cantidad
                            
                            # RESTRICCIÓN DE DINERO REAL: Si no hay efectivo suficiente, no se ejecuta la compra
                            if costo_total > efectivo:
                                continue
                            
                            efectivo -= costo_total
                            posiciones_activas[tick] = {
                                "PrecioCompraNeto": p_neto_entrada,
                                "StopLoss": stop_loss,
                                "TakeProfit": target,
                                "Cantidad": cantidad,
                                "FechaEntrada": fecha_manana
                            }
            
            capital_final_total = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
            
            if historial_trades:
                st.session_state.df_trades_global = pd.DataFrame(historial_trades).sort_values(by=["Fecha Venta", "CEDEAR"]).reset_index(drop=True)
                st.session_state.capital_final_total_global = capital_final_total
            else:
                st.session_state.df_trades_global = None

# =====================================================================
# 📊 VISUALIZACIÓN DE RESULTADOS
# =====================================================================
if "df_trades_global" in st.session_state and st.session_state.df_trades_global is not None:
    df_trades = st.session_state.df_trades_global.copy()
    
    balance_acumulado = capital_inicial
    lista_balances = []
    for idx, row in df_trades.iterrows():
        balance_acumulado += row["Ganancia Neta Trade ($)"]
        lista_balances.append(balance_acumulado)
    df_trades["Balance Puro Numero"] = lista_balances
    
    total_trades = len(df_trades)
    ganados = len(df_trades[df_trades['Resultado'] == "🎯 TAKE PROFIT"])
    efectividad = (ganados / total_trades) * 100 if total_trades > 0 else 0
    ganancia_pesos = st.session_state.capital_final_total_global - capital_inicial
    rend_cuenta = (ganancia_pesos / capital_inicial) * 100
    
    st.success("📊 ¡Simulación con Capital Limitado Completada con Éxito!")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Operaciones Totales", total_trades)
    c2.metric("Efectividad (Win Rate)", f"{efectividad:.1f}%")
    c3.metric("Ganancia Acumulada ($)", f"$ {ganancia_pesos:,.2f}")
    c4.metric("Rendimiento Neto Real", f"{rend_cuenta:+.2f}%")
    
    st.line_chart(df_trades.set_index("Fecha Venta")["Balance Puro Numero"], use_container_width=True)
    
    col_tabla1, col_tabla2 = st.columns(2)
    with col_tabla1:
        st.subheader("📋 Historial Cronológico")
        df_visual = df_trades.copy()
        df_visual["Fecha Compra"] = df_visual["Fecha Compra"].dt.strftime('%Y-%m-%d')
        df_visual["Fecha Venta"] = df_visual["Fecha Venta"].dt.strftime('%Y-%m-%d')
        df_visual["Ganancia Neta Trade ($)"] = df_visual["Ganancia Neta Trade ($)"].apply(lambda x: f"$ {x:+,.2f}")
        st.dataframe(df_visual[["Fecha Compra", "Fecha Venta", "CEDEAR", "Resultado", "Rendimiento (%)", "Ganancia Neta Trade ($)"]], use_container_width=True)
        
    with col_tabla2:
        st.subheader("🔍 Inspector Visual")
        opciones_select = [
            f"ID {i} | {row['Fecha Compra'].strftime('%Y-%m-%d')} | {row['CEDEAR']} -> {row['Resultado']}"
            for i, row in df_trades.iterrows()
        ]
        trade_seleccionado = st.selectbox("Elige el Trade a auditar:", opciones_select)
        
        if trade_seleccionado:
            partes_texto = trade_seleccionado.split("|")
            id_segmento = partes_texto[0]
            id_limpio = id_segmento.replace("ID ", "").strip()
            idx_trade = int(id_limpio)
            
            trade_info = df_trades.iloc[idx_trade]
            ticker_auditar = trade_info["CEDEAR"]
            
            if ticker_auditar in st.session_state.diccionario_precios_historicos:
                df_hist = st.session_state.diccionario_precios_historicos[ticker_auditar]
                
                f_compra = trade_info["Fecha Compra"]
                f_venta = trade_info["Fecha Venta"]
                
                df_recorte_foto = df_hist[(df_hist.index >= f_compra - pd.Timedelta(days=15)) & (df_hist.index <= f_venta + pd.Timedelta(days=15))]
                
                if not df_recorte_foto.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df_recorte_foto.index, 
                        open=df_recorte_foto['Open'], high=df_recorte_foto['High'],
                        low=df_recorte_foto['Low'], close=df_recorte_foto['Close'], name=f"Precio {ticker_auditar}"
                    ))
                    fig.add_trace(go.Scatter(x=df_recorte_foto.index, y=df_recorte_foto['EMA_9'], line=dict(color='blue', width=1.5), name="EMA 9"))
                    fig.add_trace(go.Scatter(x=df_recorte_foto.index, y=df_recorte_foto['EMA_200'], line=dict(color='orange', width=2), name="EMA 200"))
                    
                    fig.add_trace(go.Scatter(x=[f_compra, f_venta], y=[trade_info["SL Inicial"], trade_info["SL Inicial"]], line=dict(color='red', dash='dash'), name="Stop Loss"))
                    if not pd.isna(trade_info["TP Inicial"]):
                        fig.add_trace(go.Scatter(x=[f_compra, f_venta], y=[trade_info["TP Inicial"], trade_info["TP Inicial"]], line=dict(color='green', dash='dash'), name="Take Profit"))
                    
                    fig.add_annotation(x=f_compra, y=trade_info["Precio Compra ($)"], text="📥 COMPRA", showarrow=True, arrowhead=2, arrowcolor="blue", xref="x", yref="y", bgcolor="blue", font=dict(color="white"))
                    fig.add_annotation(x=f_venta, y=trade_info["Precio Salida ($)"], text=f"📤 {trade_info['Resultado']}", showarrow=True, arrowhead=2, arrowcolor="purple", xref="x", yref="y", bgcolor="purple", font=dict(color="white"))
                    
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
elif "df_trades_global" in st.session_state:
    st.info("Ninguna operación pudo abrirse bajo las restricciones de capital y confluencias en este período.")
