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

# Função para garantir formato BR nas tabelas (DD/MM/AAAA)
def formatar_tabelas(df):
    df_copy = df.copy()
    colunas_data = ['Próx. Recarga', 'Próx. Teste', 'Data da Inspeção']
    for col in colunas_data:
        if col in df_copy.columns:
            # Converte para data e formata como string BR
            df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce').dt.strftime('%d/%m/%Y')
    return df_copy

# Limpeza de código
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
        # Lógica de datas (mantém o formato original para cálculos)
        df_calc = df_cadastros.copy()
        df_calc['dt_rec'] = pd.to_datetime(df_calc['Próx. Recarga']).dt.date
        df_calc['dt_tes'] = pd.to_datetime(df_calc['Próx. Teste']).dt.date
        
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)
        
        vencidos = df_calc[df_calc['dt_rec'] < hoje]
        proximos = df_calc[(df_calc['dt_rec'] >= hoje) & (df_calc['dt_rec'] <= alerta_30)]
        
        cols = st.columns(4)
        cols[0].metric("Total", len(df_cadastros))
        cols[1].metric("Vencidos 🔴", len(vencidos))
        cols[2].metric("30 Dias 🟡", len(proximos))
        
        # Exibição formatada
        st.dataframe(formatar_tabelas(df_cadastros), use_container_width=True)

# --- ABA 2: FORMULÁRIO ---
with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor:").strip()
    
    if num_extintor:
        ext_data = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
        ja_cadastrado = not ext_data.empty
        dados = ext_data.iloc[0] if ja_cadastrado else None
        
        st.subheader("2. Ficha Técnica")
        c1, c2, c3 = st.columns(3)
        loc = c1.text_input("Localização:", value=str(dados["Localização"]) if ja_cadastrado else "")
        p_rec = c2.date_input("Vencimento Recarga:")
        p_teste = c3.date_input("Vencimento Teste Hidro:")
        
        if st.button("Gravar / Atualizar"):
            row = {"Nº Ext.": num_extintor, "Localização": loc, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            # Atualização no banco
            if ja_cadastrado: df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor, row.keys()] = row.values()
            else: df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row])], ignore_index=True)
            conn.update(worksheet="Cadastros", data=df_cadastros)
            st.success("Dados salvos!")
            st.rerun()

# --- ABA 3: HISTÓRICO ---
with aba_hist:
    st.subheader("📋 Histórico Geral")
    st.dataframe(formatar_tabelas(df_inspecoes).iloc[::-1], use_container_width=True)
