import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# Configuración del panel
st.set_page_config(page_title="Asistente Cuantitativo Pro",
                   page_icon="📊", layout="wide")

st.title("[ Asistente de Trading de CEDEARs con Gestión Activa de Portafolio ]")
st.write("Monitoreo Dinámico: El bot analiza tus posiciones abiertas y te ordena ajustar el Stop Loss o cerrar para proteger tus ganancias.")

# Credenciales de Telegram
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

# Base de datos local
ARCHIVO_DB = "portafolio.csv"
if not os.path.exists(ARCHIVO_DB):
    df_inicial = pd.DataFrame(columns=["Ticker", "Cantidad", "PrecioCompra", "StopLoss", "TakeProfit", "FechaEntrada"])
    df_inicial.to_csv(ARCHIVO_DB, index=False)

df_portafolio = pd.read_csv(ARCHIVO_DB)
