import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

st.title("🏙️ Sistema de Gestão e Auditoria de Extintores")

# Conexão
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro de conexão.")
    st.stop()

def limpar_codigo(df):
    if df is not None and not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard Interativo", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD (Apenas Dados Técnicos) ---
with aba_dash:
    st.subheader("Painel de Controle")
    if not df_cadastros.empty:
        colunas_permitidas = ["Nº Ext.", "Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"]
        st.dataframe(df_cadastros[colunas_permitidas], use_container_width=True)

# --- ABA 2: FORMULÁRIO (Gravação Completa) ---
with aba_form:
    num_extintor = st.text_input("Digite o Nº do Extintor:").strip()
    if num_extintor:
        ext_data = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
        ja_cadastrado = not ext_data.empty
        dados = ext_data.iloc[0] if ja_cadastrado else None
        
        c1, c2, c3 = st.columns(3)
        loc = c1.text_input("Localização:", value=str(dados["Localização"]) if ja_cadastrado else "")
        tipo = c2.selectbox("Tipo:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma"], index=0)
        carga = c3.text_input("Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
        
        p_rec = st.date_input("Vencimento Recarga:")
        p_teste = st.date_input("Vencimento Teste:")
        
        func = st.text_input("Inspetor / Responsável Técnico:")
        pesagem = st.number_input("Pesagem (Kg):", step=0.01)
        nc = st.text_area("Não Conformidades:")

        if st.button("Gravar / Atualizar"):
            row_cad = {"Nº Ext.": num_extintor, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            row_insp = {"Data da Inspeção": str(datetime.today().date()), "Nº Ext.": num_extintor, "Pesagem": pesagem, "Próx. Pesagem": str(datetime.today() + timedelta(90)), "Não Conformidades": nc, "Funcionário": func, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            
            if ja_cadastrado: df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor, row_cad.keys()] = row_cad.values()
            else: df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
            
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
            conn.update(worksheet="Cadastros", data=df_cadastros)
            conn.update(worksheet="Inspecoes", data=df_inspecoes)
            st.rerun()

# --- ABA 3: HISTÓRICO (Com Filtros) ---
with aba_hist:
    st.subheader("📋 Histórico Retroativo de Vistorias")
    f1, f2, f3 = st.columns(3)
    busca = f1.text_input("Busca por Nº Extintor:")
    
    df_view = df_inspecoes.copy()
    if busca: df_view = df_view[df_view["Nº Ext."].astype(str).str.contains(busca)]
    
    st.dataframe(df_view.iloc[::-1], use_container_width=True)
