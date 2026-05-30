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
    div.stButton > button { width: 100%; height: 60px; }
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
        hidro = df_calc[df_calc['dt_tes'] < hoje]

        cols = st.columns(4)
        if cols[0].button(f"Total\n{len(df_cadastros)}"): st.session_state.filtro = "Todos"
        if cols[1].button(f"Vencidos 🔴\n{len(vencidos)}"): st.session_state.filtro = "Vencidos"
        if cols[2].button(f"30 Dias 🟡\n{len(proximos)}"): st.session_state.filtro = "Proximos"
        if cols[3].button(f"Teste Hidro ❌\n{len(hidro)}"): st.session_state.filtro = "Hidro"

        filtro = getattr(st.session_state, 'filtro', 'Todos')
        if filtro == "Vencidos": st.dataframe(vencidos, use_container_width=True)
        elif filtro == "Proximos": st.dataframe(proximos, use_container_width=True)
        elif filtro == "Hidro": st.dataframe(hidro, use_container_width=True)
        else: st.dataframe(df_cadastros, use_container_width=True)

# --- ABA 2: FORMULÁRIO (Layout Original + Pesagem) ---
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
                if st.button("🗑️ Excluir este equipamento"):
                    df_cadastros = df_cadastros[df_cadastros["Nº Ext."] != num_final]
                    conn.update(worksheet="Cadastros", data=df_cadastros)
                    st.rerun()
        else:
            st.warning(f"🆕 Equipamento {num_final} não encontrado.")

        st.subheader("2. Ficha Técnica do Equipamento")
        c1, c2, c3 = st.columns(3)
        with c1:
            loc = st.text_input("Localização Física:", value=str(dados["Localização"]) if ja_cadastrado else "")
            tipo = st.selectbox("Tipo de Carga:", ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"], index=0)
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
            p_pesagem = dt_insp + timedelta(days=90)
            st.info(f"📆 Próxima Pesagem: {p_pesagem.strftime('%d/%m/%Y')}")
        with i3:
            nc = st.text_area("Registro de Anomalias / Não Conformidades:")

        if st.button("Gravar Informações e Sincronizar", type="primary"):
            row_cad = {"Nº Ext.": num_final, "Localização": loc, "Tipo": tipo, "Carga (Kg/L)": carga, "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            row_insp = {"Data da Inspeção": str(dt_insp), "Nº Ext.": num_final, "Funcionário": func, "Pesagem": pesagem, "Não Conformidades": nc, "Próx. Pesagem": str(p_pesagem), "Próx. Recarga": str(p_rec), "Próx. Teste": str(p_teste)}
            
            if ja_cadastrado: df_cadastros.loc[df_cadastros["Nº Ext."] == num_final, row_cad.keys()] = row_cad.values()
            else: df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
            
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
            conn.update(worksheet="Cadastros", data=df_cadastros)
            conn.update(worksheet="Inspecoes", data=df_inspecoes)
            st.success("Salvo com sucesso!")
            st.rerun()

# --- ABA 3: HISTÓRICO COM FILTROS COMPLETOS ---
with aba_hist:
    st.subheader("📋 Histórico Retroativo de Vistorias")
    f1, f2, f3 = st.columns(3)
    with f1: 
        filtro_num = st.text_input("🔍 Busca por Nº Extintor:")
        filtro_loc = st.multiselect("📍 Localização:", df_inspecoes["Localização"].unique())
    with f2: 
        filtro_tipo = st.multiselect("🔥 Tipo de Carga:", df_inspecoes["Tipo"].unique())
        filtro_func = st.selectbox("👤 Inspetor:", ["Todos"] + list(df_inspecoes["Funcionário"].unique()))
    with f3: 
        filtro_nc = st.text_input("⚠️ Busca em Não Conformidades:")
        status_v = st.selectbox("📅 Prazo", ["Todos", "Vencidos", "Próximos (30d)"])

    df_view = df_inspecoes.copy()
    if filtro_num: df_view = df_view[df_view["Nº Ext."].astype(str).str.contains(filtro_num, case=False)]
    if filtro_loc: df_view = df_view[df_view["Localização"].isin(filtro_loc)]
    if filtro_tipo: df_view = df_view[df_view["Tipo"].isin(filtro_tipo)]
    if filtro_func != "Todos": df_view = df_view[df_view["Funcionário"] == filtro_func]
    if filtro_nc: df_view = df_view[df_view["Não Conformidades"].astype(str).str.contains(filtro_nc, case=False)]
    
    if status_v != "Todos":
        df_view["dt_rec"] = pd.to_datetime(df_view["Próx. Recarga"]).dt.date
        hoje = datetime.today().date()
        if status_v == "Vencidos": df_view = df_view[df_view["dt_rec"] < hoje]
        else: df_view = df_view[(df_view["dt_rec"] >= hoje) & (df_view["dt_rec"] <= hoje + timedelta(30))]
    
    st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)

# --- ASSINATURA FINALIZADA COM FONTE GABRIOLA ---
st.markdown("---")

st.markdown(
    """
    <div style='text-align: center; margin-top: 100px;'>
        <p style='margin-bottom: -8px; font-family: "Gabriola", serif; font-style: italic; font-size: 18px; color: #0056b3;'>
            Developed by:
        </p>
        <p style='font-family: "Gabriola", serif; font-size: 20px; font-weight: 100; color: #1e7044;'>
            Edison Duarte Filho®
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
