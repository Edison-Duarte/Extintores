import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    div.stButton > button { width: 100%; height: 75px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏙️ Sistema de Gestão e Auditoria de Extintores")

# Conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro de conexão com o Google Sheets.")
    st.stop()

# Funções Auxiliares
def limpar_codigo(df):
    if df is not None and not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# Abas
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard Interativo", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD ---
with aba_dash:
    st.subheader("Painel de Controle")
    if not df_cadastros.empty:
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)
        
        df_calc = df_cadastros.copy()
        df_calc['dt_rec'] = pd.to_datetime(df_calc['Próx. Recarga']).dt.date
        df_calc['dt_tes'] = pd.to_datetime(df_calc['Próx. Teste']).dt.date

        vencidos = df_calc[df_calc['dt_rec'] < hoje]
        proximos = df_calc[(df_calc['dt_rec'] >= hoje) & (df_calc['dt_rec'] <= alerta_30)]
        hidro_vencido = df_calc[df_calc['dt_tes'] < hoje]
        hidro_proximo = df_calc[(df_calc['dt_tes'] >= hoje) & (df_calc['dt_tes'] <= alerta_30)]

        # COLUNAS EXIBIDAS NO DASHBOARD (Sem Pesagem, Próx. Pesagem e Não Conformidades)
        colunas_dash = ["Nº Ext.", "Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"]

        cols = st.columns(5)
        if cols[0].button(f"Total\n{len(df_cadastros)}"): st.session_state.filtro = "Todos"
        if cols[1].button(f"Vencidos 🔴\n{len(vencidos)}"): st.session_state.filtro = "Vencidos"
        if cols[2].button(f"Prox. ao Vencimento 🟡\n{len(proximos)}"): st.session_state.filtro = "Proximos"
        if cols[3].button(f"Hidro Vencido ❌\n{len(hidro_vencido)}"): st.session_state.filtro = "HidroVencido"
        if cols[4].button(f"Hidro Prox ao Vencimento ⚠️\n{len(hidro_proximo)}"): st.session_state.filtro = "HidroProx"

        filtro = getattr(st.session_state, 'filtro', 'Todos')
        if filtro == "Vencidos": df_resultado = vencidos[colunas_dash].copy()
        elif filtro == "Proximos": df_resultado = proximos[colunas_dash].copy()
