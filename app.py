import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta

# =====================================================================
# 🛠️ CONFIGURACIÓN DE LA PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Simulador Cuantitativo: Alto Rendimiento", 
    page_icon="🚀", 
    layout="wide"
)

st.title("🚀 Simulador Cuantitativo: Motor Dinámico de Alta Rotación")
st.markdown("Estrategia optimizada para generar mayor volumen de operaciones, buscando capturar tendencias dinámicas en CEDEARs.")

# =====================================================================
# 📋 UNIVERSO DE ACTIVOS (CEDEARs)
# =====================================================================
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

# =====================================================================
# 🎛️ PANEL LATERAL (PARÁMETROS)
# =====================================================================
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

COSTO_OPERATIVO = (0.0050 + 0.0005) * 1.21
VOLUMEN_MINIMO = 3000 # Umbral accesible para no filtrar de más

if "diccionario_precios_historicos" not in st.session_state:
    st.session_state.diccionario_precios_historicos = {}

# =====================================================================
# 🚀 MOTOR DE BACKTESTING DINÁMICO
# =====================================================================
if st.button(f"🚀 Ejecutar Simulación Dinámica ({opcion_tiempo})"):
    with st.spinner(f"Descargando datos y procesando rotación de activos..."):
        try:
            full_tickers = tickers + ['SPY.BA']
            datos_globales = yf.download(full_tickers, period=periodo_download, interval="1d", progress=False)
        except Exception as e:
            st.error(f"Error al descargar datos: {e}")
            datos_globales = None

    if datos_globales is not None and not datos_globales.empty:
        st.session_state.diccionario_precios_historicos = {}
        
        try:
            spy_df = pd.DataFrame()
            spy_df['Close'] = datos_globales['Close']['SPY.BA'].dropna()
            spy_df['EMA_20'] = ta.trend.ema_indicator(spy_df['Close'], window=20)
            spy_df = spy_df.dropna()
            spy_df.index = pd.to_datetime(spy_df.index).normalize()
        except Exception:
            spy_df = pd.DataFrame()

        lista_fechas_totales = []
        
        for ticker in tickers:
            try:
                df = pd.DataFrame()
                df['Close'] = datos_globales['Close'][ticker].dropna()
                df['Open'] = datos_globales['Open'][ticker].dropna()
                df['Low'] = datos_globales['Low'][ticker].dropna()
                df['High'] = datos_globales['High'][ticker].dropna()
                df['Volume'] = datos_globales['Volume'][ticker].dropna()
                
                if len(df) < 50:
                    continue
                
                df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
                df['RSI_5'] = ta.momentum.rsi(df['Close'], window=5) # RSI equilibrado
                df['ATR_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
                df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
                
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
                
                permite_compras_mercado = True
                if not spy_df.empty and fecha_hoy in spy_df.index:
                    if spy_df.loc[fecha_hoy, 'Close'] < spy_df.loc[fecha_hoy, 'EMA_20']:
                        permite_compras_mercado = False
                
                capital_liberado_hoy = 0
                tickers_a_cerrar = []
                
                # ==========================================
                # 1. EVALUAR VENTAS
                # ==========================================
                for t_activo, pos in list(posiciones_activas.items()):
                    df_activo = st.session_state.diccionario_precios_historicos[t_activo]
                    
                    if fecha_manana in df_activo.index:
                        row_m = df_activo.loc[fecha_manana]
                        p_open = float(row_m["Open"])
                        p_low = float(row_m["Low"])
                        p_high = float(row_m["High"])
                        
                        cerrar = False
                        resultado_str = ""
                        precio_salida_bruto = 0
                        
                        if p_low <= pos["StopLoss"]:
                            cerrar = True
                            precio_salida_bruto = min(pos["StopLoss"], p_open)
                            resultado_str = "🔴 STOP LOSS"
                        elif p_high >= pos["TakeProfit"]: 
                            cerrar = True
                            precio_salida_bruto = max(pos["TakeProfit"], p_open)
                            resultado_str = "🎯 TAKE PROFIT"
                        
                        if cerrar:
                            precio_salida_neto = precio_salida_bruto * (1 - COSTO_OPERATIVO)
                            monto_recuperado = precio_salida_neto * pos["Cantidad"]
                            monto_invertido = pos["PrecioCompraNeto"] * pos["Cantidad"]
                            ganancia_pesos = monto_recuperado - monto_invertido
                            
                            capital_liberado_hoy += monto_recuperado
                            rend = ((precio_salida_neto - pos["PrecioCompraNeto"]) / pos["PrecioCompraNeto"]) * 100
                            
                            historial_trades.append({
                                "Fecha Compra": pos["FechaEntrada"],
                                "Fecha Venta": fecha_manana,
                                "CEDEAR": t_activo,
                                "Resultado": resultado_str,
                                "Rendimiento (%)": round(rend, 2),
                                "Cantidad Nominales": pos["Cantidad"],
                                "Ganancia Neta Trade ($)": ganancia_pesos,
                                "Precio Compra ($)": pos["PrecioCompraNeto"],
                                "Precio Salida ($)": precio_salida_neto,
                                "SL Inicial": pos["StopLoss"],
                                "TP Inicial": pos["TakeProfit"]
                            })
                            tickers_a_cerrar.append(t_activo)
                
                for t in tickers_a_cerrar:
                    posiciones_activas.pop(t)
                
                efectivo += capital_liberado_hoy
                tickers_en_cartera = set(posiciones_activas.keys())
                
                # ==========================================
                # 2. EVALUAR COMPRAS (Más dinámicas y frecuentes)
                # ==========================================
                for tick, df_activo in st.session_state.diccionario_precios_historicos.items():
                    if tick in tickers_en_cartera:
                        continue
                    
                    if fecha_hoy in df_activo.index:
                        row_hoy = df_activo.loc[fecha_hoy]
                        
                        p_close = float(row_hoy["Close"])
                        ema_20 = float(row_hoy["EMA_20"])
                        rsi_5 = float(row_hoy["RSI_5"])
                        vol = float(row_hoy["Volume"])
                        vol_sma20 = float(row_hoy["Vol_SMA_20"])
                        atr = float(row_hoy["ATR_14"])
                        
                        # Filtros dinámicos orientados a mayor rotación
                        cond_tendencia = (p_close > ema_20)
                        cond_momentum = rsi_5 < 30 # Umbral más flexible para captar correcciones comunes
                        cond_volumen = (vol > 0.9 * vol_sma20) and (vol_sma20 > VOLUMEN_MINIMO) 
                        
                        if permite_compras_mercado and cond_tendencia and cond_momentum and cond_volumen:
                            p_neto_compra = p_close * (1 + COSTO_OPERATIVO)
                            
                            # Relación 1.2 ATR de riesgo vs 2.5 ATR de objetivo (alta rotación)
                            stop_loss = p_neto_compra - (1.2 * atr) 
                            take_profit = p_neto_compra + (2.5 * atr)
                            
                            riesgo_por_accion = p_neto_compra - stop_loss
                            if stop_loss <= 0 or riesgo_por_accion <= 0:
                                continue
                            
                            capital_total_actual = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
                            riesgo_max_ars = capital_total_actual * 0.02 # 2% de riesgo por operación
                            
                            cantidad = int(riesgo_max_ars // riesgo_por_accion)
                            if cantidad <= 0:
                                continue
                            
                            costo_total = p_neto_compra * cantidad
                            if costo_total > efectivo:
                                continue
                            
                            efectivo -= costo_total
                            posiciones_activas[tick] = {
                                "PrecioCompraNeto": p_neto_compra,
                                "StopLoss": stop_loss,
                                "TakeProfit": take_profit,
                                "Cantidad": cantidad,
                                "FechaEntrada": fecha_hoy
                            }
            
            capital_final = efectivo + sum(p["PrecioCompraNeto"] * p["Cantidad"] for p in posiciones_activas.values())
            
            if historial_trades:
                st.session_state.df_trades_global = pd.DataFrame(historial_trades).sort_values(by=["Fecha Venta", "CEDEAR"]).reset_index(drop=True)
                st.session_state.capital_final_total_global = capital_final
            else:
                st.session_state.df_trades_global = None

# =====================================================================
# 📊 VISUALIZACIÓN DE RESULTADOS E INSPECTOR VISUAL
# =====================================================================
if "df_trades_global" in st.session_state and st.session_state.df_trades_global is not None:
    df_trades = st.session_state.df_trades_global.copy()
    
    balances = [capital_inicial]
    acc = capital_inicial
    for _, row in df_trades.iterrows():
        acc += row["Ganancia Neta Trade ($)"]
        balances.append(acc)
    
    total_t = len(df_trades)
    ganados = len(df_trades[df_trades['Resultado'].str.contains("TAKE PROFIT")])
    winrate = (ganados / total_t) * 100 if total_t > 0 else 0
    ganancia_neta_ars = st.session_state.capital_final_total_global - capital_inicial
    rendimiento_pct = (ganancia_neta_ars / capital_inicial) * 100
    
    df_bal = pd.DataFrame({
        "Fecha": [df_trades.iloc[0]["Fecha Compra"]] + list(df_trades["Fecha Venta"]),
        "Balance": balances
    }).drop_duplicates(subset=["Fecha"]).set_index("Fecha")
    
    df_bal['Max_Balance'] = df_bal['Balance'].cummax()
    df_bal['Drawdown'] = (df_bal['Balance'] - df_bal['Max_Balance']) / df_bal['Max_Balance']
    max_dd = df_bal['Drawdown'].min() * 100
    
    st.success("✅ ¡Simulación Dinámica ejecutada con éxito!")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Operaciones Totales", total_t)
    col2.metric("Efectividad (Win Rate)", f"{winrate:.1f}%")
    col3.metric("Ganancia Neta ($)", f"$ {ganancia_neta_ars:,.2f}")
    col4.metric("Rendimiento Total", f"{rendimiento_pct:+.2f}%")
    col5.metric("Máxima Caída (Max DD)", f"{max_dd:.2f}%", delta_color="inverse")
    
    st.line_chart(df_bal["Balance"], use_container_width=True)
    
    c_tab1, c_tab2 = st.columns(2)
    with c_tab1:
        st.subheader("📋 Historial de Operaciones")
        df_view = df_trades.copy()
        df_view["Fecha Compra"] = df_view["Fecha Compra"].dt.strftime('%Y-%m-%d')
        df_view["Fecha Venta"] = df_view["Fecha Venta"].dt.strftime('%Y-%m-%d')
        df_view["Ganancia Neta Trade ($)"] = df_view["Ganancia Neta Trade ($)"].apply(lambda x: f"$ {x:+,.2f}")
        st.dataframe(df_view[["Fecha Compra", "Fecha Venta", "CEDEAR", "Resultado", "Rendimiento (%)", "Ganancia Neta Trade ($)"]], use_container_width=True)
        
    with c_tab2:
        st.subheader("🔍 Inspector Visual de Trades")
        opciones = [
            f"ID {i} | {row['Fecha Compra'].strftime('%Y-%m-%d')} | {row['CEDEAR']} -> {row['Resultado']}"
            for i, row in df_trades.iterrows()
        ]
        elegido = st.selectbox("Seleccioná un trade para auditar:", opciones)
        
        if elegido:
            idx_t = int(elegido.split("|")[0].replace("ID ", "").strip())
            t_info = df_trades.iloc[idx_t]
            tick_aud = t_info["CEDEAR"]
            
            if tick_aud in st.session_state.diccionario_precios_historicos:
                df_h = st.session_state.diccionario_precios_historicos[tick_aud]
                f_c = t_info["Fecha Compra"]
                f_v = t_info["Fecha Venta"]
                
                df_rec = df_h[(df_h.index >= f_c - pd.Timedelta(days=15)) & (df_h.index <= f_v + pd.Timedelta(days=15))]
                
                if not df_rec.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df_rec.index, open=df_rec['Open'], high=df_rec['High'],
                        low=df_rec['Low'], close=df_rec['Close'], name=tick_aud
                    ))
                    fig.add_trace(go.Scatter(x=df_rec.index, y=df_rec['EMA_20'], line=dict(color='orange', width=2), name="EMA 20"))
                    
                    fig.add_trace(go.Scatter(x=[f_c, f_v], y=[t_info["SL Inicial"], t_info["SL Inicial"]], line=dict(color='red', dash='dash'), name="Stop Loss"))
                    fig.add_trace(go.Scatter(x=[f_c, f_v], y=[t_info["TP Inicial"], t_info["TP Inicial"]], line=dict(color='green', dash='dash'), name="Take Profit"))
                    
                    fig.add_annotation(x=f_c, y=t_info["Precio Compra ($)"], text="📥 COMPRA", showarrow=True, arrowhead=2, arrowcolor="blue", bgcolor="blue", font=dict(color="white"))
                    fig.add_annotation(x=f_v, y=t_info["Precio Salida ($)"], text=f"📤 {t_info['Resultado']}", showarrow=True, arrowhead=2, arrowcolor="purple", bgcolor="purple", font=dict(color="white"))
                    
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
elif "df_trades_global" in st.session_state:
    st.info("No se registraron operaciones bajo los parámetros dinámicos.")
