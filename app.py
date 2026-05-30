import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 38px; font-weight: bold; }
    div.stButton > button:first-child { background-color: #d32f2f; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏙️ Sistema de Gestão e Auditoria de Extintores")

# 1. Conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro de conexão. Verifique os Secrets e a Planilha.")
    st.stop()

# --- FUNÇÕES DE LIMPEZA ---
def limpar_codigo(df):
    if df is not None and not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# 2. SISTEMA DE ABAS
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard de Gestão", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD ---
with aba_dash:
    st.subheader("Painel de Controle e Conformidade Tecnológica")
    if not df_cadastros.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Equipamentos", len(df_cadastros))
        m2.metric("Recarga Vencida 🔴", "Verificar") 
        m3.metric("Vencem em 30d 🟡", "Verificar")
        m4.metric("Teste Hidro. Vencido ❌", "Verificar")

# --- ABA 2: FORMULÁRIO COM EXCLUSÃO ---
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
            with st.expander("⚠️ Área de Gerenciamento"):
                if st.button(f"🗑️ Excluir Extintor {num_final}", type="secondary"):
                    df_cadastros = df_cadastros[df_cadastros["Nº Ext."] != num_final]
                    conn.update(worksheet="Cadastros", data=df_cadastros)
                    st.rerun()
        else:
            st.warning(f"🆕 Equipamento {num_final} não encontrado.")

        st.subheader("2. Ficha Técnica do Equipamento")
        c1, c2, c3 = st.columns(3)
        with c1:
            loc = st.text_input("Localização Física:", value=str(dados["Localização"]) if ja_cadastrado else "")
            tipo_sel = st.selectbox("Tipo de Carga:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"], index=0)
        with c2:
            carga = st.text_input("Capacidade de Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
            p_rec = st.date_input("Vencimento da Recarga:", value=datetime.today())
        with c3:
            p_teste = st.date_input("Vencimento do Teste Hidrostático:", value=datetime.today())

        st.write("---")
        st.subheader("3. Checklist de Inspeção Mensal")
        i1, i2, i3 = st.columns(3)
        with i1:
            dt_insp = st.date_input("Data da Inspeção:", value=datetime.today())
            func = st.text_input("Inspetor / Responsável Técnico:")
        with i2:
            pesagem = st.number_input("Massa / Pesagem Atual (Kg):", min_value=0.0, step=0.01)
        with i3:
            nao_conf = st.text_area("Registro de Anomalias / Não Conformidades:")

        if st.button("Gravar Informações e Sincronizar", type="primary"):
            row_cad = {"Nº Ext.": num_final, "Localização": loc, "Tipo": tipo_sel, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            row_insp = {"Data da Inspeção": str(dt_insp), "Nº Ext.": num_final, "Funcionário": func, "Pesagem": pesagem, "Não Conformidades": nao_conf, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            
            if ja_cadastrado:
                df_cadastros.loc[df_cadastros["Nº Ext."] == num_final, row_cad.keys()] = row_cad.values()
            else:
                df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
            
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
            conn.update(worksheet="Cadastros", data=df_cadastros)
            conn.update(worksheet="Inspecoes", data=df_inspecoes)
            st.success("Dados salvos com sucesso!")
            st.rerun()

# --- ABA 3: HISTÓRICO COM FILTROS AVANÇADOS ---
with aba_hist:
    st.subheader("📋 Histórico Retroativo de Vistorias")
    
    if not df_inspecoes.empty:
        f1, f2, f3 = st.columns(3)
        with f1:
            filtro_num = st.text_input("🔍 Busca por Nº Extintor:")
            filtro_loc = st.multiselect("📍 Localização:", df_inspecoes["Localização"].unique())
        with f2:
            filtro_tipo = st.multiselect("🔥 Tipo de Carga:", df_inspecoes["Tipo"].unique())
            filtro_func = st.selectbox("👤 Inspetor:", ["Todos"] + list(df_inspecoes["Funcionário"].unique()))
        with f3:
            filtro_nc = st.text_input("⚠️ Busca em Não Conformidades:")
            status_vencimento = st.selectbox("📅 Status de Prazo:", ["Todos", "🔴 Vencidos (Recarga)", "🟡 Próximos ao Vencimento (30d)"])

        df_view = df_inspecoes.copy()
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)

        # Filtros
        if filtro_num: df_view = df_view[df_view["Nº Ext."].astype(str).str.contains(filtro_num, case=False)]
        if filtro_loc: df_view = df_view[df_view["Localização"].isin(filtro_loc)]
        if filtro_tipo: df_view = df_view[df_view["Tipo"].isin(filtro_tipo)]
        if filtro_func != "Todos": df_view = df_view[df_view["Funcionário"] == filtro_func]
        if filtro_nc: df_view = df_view[df_view["Não Conformidades"].astype(str).str.contains(filtro_nc, case=False)]
        
        # Filtro de Status de Vencimento
        if status_vencimento != "Todos":
            df_view["dt_rec"] = pd.to_datetime(df_view["Próx. Recarga"]).dt.date
            if status_vencimento == "🔴 Vencidos (Recarga)":
                df_view = df_view[df_view["dt_rec"] < hoje]
            else:
                df_view = df_view[(df_view["dt_rec"] >= hoje) & (df_view["dt_rec"] <= alerta_30)]
        
        st.write(f"Exibindo {len(df_view)} registros:")
        st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro histórico disponível.")
