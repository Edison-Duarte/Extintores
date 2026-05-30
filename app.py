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

# Função para limpar o código do extintor
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
    if not df_cadastros.empty and not df_inspecoes.empty:
        # 1. Pega apenas a última inspeção de cada extintor
        df_ultima_insp = df_inspecoes.sort_values("Data da Inspeção").groupby("Nº Ext.").tail(1)
        
        # 2. Mescla o cadastro com os dados da última inspeção
        df_dashboard = df_cadastros.merge(
            df_ultima_insp[["Nº Ext.", "Próx. Recarga", "Próx. Teste", "Localização", "Tipo", "Carga (Kg/L)"]], 
            on="Nº Ext.", 
            how="left", 
            suffixes=("", "_insp")
        )
        
        # 3. Prioriza os dados da inspeção (se existirem), caso contrário mantém o cadastro
        df_dashboard["Próx. Recarga"] = df_dashboard["Próx. Recarga_insp"].fillna(df_dashboard["Próx. Recarga"])
        df_dashboard["Próx. Teste"] = df_dashboard["Próx. Teste_insp"].fillna(df_dashboard["Próx. Teste"])
        df_dashboard["Localização"] = df_dashboard["Localização_insp"].fillna(df_dashboard["Localização"])
        df_dashboard["Tipo"] = df_dashboard["Tipo_insp"].fillna(df_dashboard["Tipo"])
        df_dashboard["Carga (Kg/L)"] = df_dashboard["Carga (Kg/L)_insp"].fillna(df_dashboard["Carga (Kg/L)"])
        
        # Remove colunas auxiliares
        cols_to_drop = [c for c in df_dashboard.columns if '_insp' in c]
        df_dashboard = df_dashboard.drop(columns=cols_to_drop)

        # Exibe o dashboard atualizado
        st.dataframe(df_dashboard, use_container_width=True)

# --- ABA 2: FORMULÁRIO ---
with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor:", key="f_num").strip()

    if num_extintor:
        ext_data = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
        ja_cadastrado = not ext_data.empty
        dados = ext_data.iloc[0] if ja_cadastrado else None
        num_final = str(dados["Nº Ext."]) if ja_cadastrado else num_extintor

        if ja_cadastrado:
            st.success(f"✅ Equipamento {num_final} localizado.")
        else:
            st.warning(f"🆕 Equipamento {num_final} novo.")

        st.subheader("2. Ficha Técnica")
        c1, c2, c3 = st.columns(3)
        loc = c1.text_input("Localização Física:", value=str(dados["Localização"]) if ja_cadastrado else "")
        carga = c2.text_input("Capacidade de Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
        p_teste = c3.date_input("Vencimento do Teste Hidrostático:", value=datetime.today())
        
        tipo = st.selectbox("Tipo de Carga:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"], index=0)
        p_rec = st.date_input("Vencimento da Recarga:", value=datetime.today())

        st.write("---")
        st.subheader("3. Checklist de Inspeção Mensal")
        i1, i2, i3 = st.columns(3)
        dt_insp = i1.date_input("Data da Inspeção:", value=datetime.today())
        func = i2.text_input("Inspetor / Responsável Técnico:")
        pesagem = i3.number_input("Massa / Pesagem Atual (Kg):", min_value=0.0, step=0.01)
        nc = st.text_area("Registro de Anomalias / Não Conformidades:")

        if st.button("Gravar Informações e Sincronizar", type="primary"):
            # CRUCIAL: Aqui incluímos TODOS os dados no histórico
            row_cad = {"Nº Ext.": num_final, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            row_insp = {
                "Data da Inspeção": str(dt_insp), 
                "Nº Ext.": num_final, 
                "Localização": loc, 
                "Tipo": tipo, 
                "Carga (Kg/L)": carga, 
                "Funcionário": func, 
                "Pesagem": pesagem, 
                "Não Conformidades": nc, 
                "Próx. Recarga": str(p_rec), 
                "Próx. Teste": str(p_teste)
            }
            
            # Atualiza o Cadastro
            if ja_cadastrado: df_cadastros.loc[df_cadastros["Nº Ext."] == num_final, row_cad.keys()] = row_cad.values()
            else: df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
            
            # Adiciona ao Histórico
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
            
            conn.update(worksheet="Cadastros", data=df_cadastros)
            conn.update(worksheet="Inspecoes", data=df_inspecoes)
            st.success("Salvo com sucesso!")
            st.rerun()

# --- ABA 3: HISTÓRICO ---
with aba_hist:
    st.subheader("📋 Histórico Retroativo de Vistorias")
    st.dataframe(df_inspecoes.iloc[::-1], use_container_width=True, hide_index=True)
