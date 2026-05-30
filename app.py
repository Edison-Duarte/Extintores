import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 36px; font-weight: bold; }
    div.stButton > button:first-child { background-color: #d32f2f; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏙️ Sistema de Gestão e Auditoria de Extintores")

# Conexão Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro de conexão.")
    st.stop()

# --- ABAS ---
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard", "📝 Nova Inspeção", "📋 Histórico"])

with aba_dash:
    # ... (mantenha sua lógica de cálculo de datas aqui) ...
    
    # Substitua os gráficos Plotly por estes nativos:
    st.subheader("📈 Análise Visual")
    g1, g2 = st.columns(2)
    
    with g1:
        st.write("Status dos Equipamentos")
        # Gráfico nativo estável
        st.bar_chart(df_calc["Status"].value_counts())
        
    with g2:
        st.write("Inventário por Tipo")
        # Gráfico nativo estável
        st.bar_chart(df_calc["Tipo"].value_counts())

# ... (restante do seu código inalterado) ...
