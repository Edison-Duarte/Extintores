import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

st.markdown("""<style>[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; } div.stButton > button { width: 100%; height: 75px; }</style>""", unsafe_allow_html=True)
st.title("🏙️ Sistema de Gestão e Auditoria de Extintores")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro de conexão com o Google Sheets.")
    st.stop()

def limpar_codigo(df):
    if df is not None and not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard Interativo", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

with aba_dash:
    st.subheader("Painel de Controle")
    if not df_cadastros.empty and not df_inspecoes.empty:
        # Unifica dados para mostrar o status mais recente
        df_ultima_insp = df_inspecoes.sort_values("Data da Inspeção").groupby("Nº Ext.").tail(1)
        df_dashboard = df_cadastros.merge(df_ultima_insp[["Nº Ext.", "Próx. Recarga", "Próx. Teste", "Localização", "Tipo", "Carga (Kg/L)"]], on="Nº Ext.", how="left", suffixes=("", "_insp"))
        df_dashboard["Próx. Recarga"] = df_dashboard["Próx. Recarga_insp"].fillna(df_dashboard["Próx. Recarga"])
        df_dashboard["Próx. Teste"] = df_dashboard["Próx. Teste_insp"].fillna(df_dashboard["Próx. Teste"])
        
        hoje = datetime.today().date()
        df_dashboard['dt_rec'] = pd.to_datetime(df_dashboard['Próx. Recarga']).dt.date
        df_dashboard['dt_tes'] = pd.to_datetime(df_dashboard['Próx. Teste']).dt.date
        
        vencidos = df_dashboard[df_dashboard['dt_rec'] < hoje]
        st.dataframe(df_dashboard, use_container_width=True)

with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor:", key="f_num").strip()
    if num_extintor:
        ext_data = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
        ja_cadastrado = not ext_data.empty
        dados = ext_data.iloc[0] if ja_cadastrado else None
        
        loc = st.text_input("Localização Física:", value=str(dados["Localização"]) if ja_cadastrado else "")
        tipo = st.selectbox("Tipo de Carga:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"], index=0)
        carga = st.text_input("Capacidade de Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
        p_rec = st.date_input("Vencimento da Recarga:")
        p_teste = st.date_input("Vencimento do Teste Hidrostático:")
        func = st.text_input("Inspetor / Responsável Técnico: *")
        
        if st.button("Gravar Informações"):
            if not func: st.error("⚠️ Campo 'Inspetor' é obrigatório!")
            else:
                row_cad = {"Nº Ext.": num_extintor, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
                row_insp = {"Data da Inspeção": str(datetime.today().date()), "Nº Ext.": num_extintor, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Funcionário": func, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
                
                if ja_cadastrado: df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor, row_cad.keys()] = row_cad.values()
                else: df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
                
                df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
                conn.update(worksheet="Cadastros", data=df_cadastros)
                conn.update(worksheet="Inspecoes", data=df_inspecoes)
                st.success("Salvo!")
                st.rerun()

with aba_hist:
    st.subheader("📋 Histórico Retroativo")
    st.dataframe(df_inspecoes.iloc[::-1], use_container_width=True)
