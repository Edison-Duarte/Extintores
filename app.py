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

def tratar_data_calculo(v):
    if pd.isna(v) or str(v).strip() in ["", "None", "NaN"]: 
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(v).strip().split()[0], formato).date()
        except ValueError:
            continue
    return None

def formatar_data_br(v):
    dt = tratar_data_calculo(v)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return str(v) if pd.notna(v) else ""

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# 2. SISTEMA DE ABAS
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard de Gestão", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD ---
with aba_dash:
    st.subheader("Painel de Controle e Conformidade Tecnológica")
    if df_cadastros.empty:
        st.info("Aguardando os primeiros cadastros para gerar os indicadores.")
    else:
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)
        df_calc = df_cadastros.copy()
        df_calc['dt_recarga_limpa'] = df_calc['Próx. Recarga'].apply(tratar_data_calculo)
        df_calc['dt_teste_limpa'] = df_calc['Próx. Teste'].apply(tratar_data_calculo)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(df_cadastros))
        m2.metric("Recarga Vencida 🔴", len(df_calc[df_calc['dt_recarga_limpa'] < hoje]))
        m3.metric("Vencem em 30d 🟡", len(df_calc[(df_calc['dt_recarga_limpa'] >= hoje) & (df_calc['dt_recarga_limpa'] <= alerta_30)]))
        m4.metric("Teste Hidro. Vencido ❌", len(df_calc[df_calc['dt_teste_limpa'] < hoje]))

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
            # --- FUNÇÃO DE EXCLUSÃO ---
            with st.expander("⚠️ Área de Gerenciamento"):
                if st.button(f"🗑️ Excluir Extintor {num_final}"):
                    df_cadastros = df_cadastros[df_cadastros["Nº Ext."] != num_final]
                    conn.update(worksheet="Cadastros", data=df_cadastros)
                    st.rerun()
        else: 
            st.warning(f"🆕 Equipamento {num_final} não encontrado.")

        # Campos do Formulário
        c1, c2, c3 = st.columns(3)
        with c1:
            loc = st.text_input("Localização:", value=str(dados["Localização"]) if ja_cadastrado else "")
            tipo_sel = st.selectbox("Tipo:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"], index=0)
        with c2:
            carga = st.text_input("Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
            p_rec = st.date_input("Vencimento Recarga:", value=datetime.today())
        with c3:
            p_teste = st.date_input("Vencimento Teste:", value=datetime.today())

        dt_insp = st.date_input("Data da Inspeção:", value=datetime.today())
        func = st.text_input("Inspetor:")
        pesagem = st.number_input("Pesagem (Kg):", value=0.0)
        nao_conf = st.text_area("Anomalias:")

        if st.button("Gravar / Sincronizar", type="primary"):
            row_cad = {"Nº Ext.": num_final, "Localização": loc, "Tipo": tipo_sel, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            row_insp = {"Data da Inspeção": str(dt_insp), "Nº Ext.": num_final, "Funcionário": func, "Pesagem": pesagem, "Não Conformidades": nao_conf}
            
            if ja_cadastrado:
                df_cadastros.loc[df_cadastros["Nº Ext."] == num_final, row_cad.keys()] = row_cad.values()
            else:
                df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
            
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
            conn.update(worksheet="Cadastros", data=df_cadastros)
            conn.update(worksheet="Inspecoes", data=df_inspecoes)
            st.success("Dados salvos!")
            st.rerun()

# --- ABA 3: HISTÓRICO ---
with aba_hist:
    st.dataframe(df_inspecoes.iloc[::-1], use_container_width=True)
