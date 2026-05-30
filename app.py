import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página - Layout focado em Gestão Corporativa
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização CSS para métricas ficarem com cores de alerta
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 40px; }
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

# --- FUNÇÕES DE PADRONIZAÇÃO ---
def limpar_codigo(df):
    if not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

def formatar_data_br(v):
    if pd.isna(v) or str(v).strip() in ["", "None", "NaN"]: return ""
    try:
        if isinstance(v, (datetime, pd.Timestamp)): return v.strftime("%d/%m/%Y")
        return datetime.strptime(str(v).split()[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return str(v)

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# 2. ABAS DO SISTEMA
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard de Gestão", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD (O DIFERENCIAL COMERCIAL) ---
with aba_dash:
    st.subheader("Torre de Controle - Status de Conformidade")
    
    if df_cadastros.empty:
        st.info("Aguardando os primeiros cadastros para gerar indicadores.")
    else:
        # Cálculos de Datas
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)

        # Converter colunas para datetime para cálculo
        df_cadastros['dt_recarga'] = pd.to_datetime(df_cadastros['Próx. Recarga']).dt.date
        df_cadastros['dt_teste'] = pd.to_datetime(df_cadastros['Próx. Teste']).dt.date

        # Métricas Recarga
        recarga_vencida = df_cadastros[df_cadastros['dt_recarga'] < hoje]
        recarga_alerta = df_cadastros[(df_cadastros['dt_recarga'] >= hoje) & (df_cadastros['dt_recarga'] <= alerta_30)]

        # Métricas Teste Hidrostático
        teste_vencido = df_cadastros[df_cadastros['dt_teste'] < hoje]

        # Exibição de Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Extintores", len(df_cadastros))
        m2.metric("Recargas Vencidas", len(recarga_vencida), delta_color="inverse")
        m3.metric("Recargas Próx. 30 dias", len(recarga_alerta))
        m4.metric("Teste Hidro. Vencido", len(teste_vencido))

        st.write("---")
        
        # Tabela de Ação Imediata
        if len(recarga_vencida) > 0 or len(teste_vencido) > 0:
            st.error("⚠️ Atenção: Equipamentos fora de conformidade encontrados!")
            acoes = pd.concat([recarga_vencida, teste_vencido]).drop_duplicates().copy()
            
            # Formatar para exibição
            for col in ["Próx. Recarga", "Próx. Teste"]:
                acoes[col] = acoes[col].apply(formatar_data_br)
            
            st.dataframe(acoes[["Nº Ext.", "Localização", "Tipo", "Próx. Recarga", "Próx. Teste"]], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Todos os equipamentos estão dentro do prazo de validade.")

# --- ABA 2: FORMULÁRIO (A OPERAÇÃO) ---
with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor (ex: 02):", key="f_num").strip()

    if num_extintor:
        # Busca inteligente (trata 02 como 2)
        try:
            num_int = int(float(num_extintor))
            def try_int(x):
                try: return int(float(x))
                except: return -1
            df_cadastros["_tmp"] = df_cadastros["Nº Ext."].apply(try_int)
            ext_data = df_cadastros[df_cadastros["_tmp"] == num_int]
        except:
            ext_data = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]

        ja_cadastrado = not ext_data.empty
        dados = ext_data.iloc[0] if ja_cadastrado else None
        num_final = str(dados["Nº Ext."]) if ja_cadastrado else num_extintor

        st.write("---")
        if ja_cadastrado: st.success(f"Equipamento {num_final} carregado.")
        else: st.warning(f"Equipamento {num_final} não cadastrado.")

        st.subheader("2. Ficha Técnica")
        c1, c2, c3 = st.columns(3)
        with c1:
            loc = st.text_input("Localização:", value=str(dados["Localização"]) if ja_cadastrado else "")
            tipo_sel = st.selectbox("Tipo:", ["Água", "PQS", "CO2", "Espuma"], index=0)
        with c2:
            carga = st.text_input("Carga:", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
            p_rec = st.date_input("Próx. Recarga:", format="DD/MM/YYYY", value=pd.to_datetime(dados["Próx. Recarga"]).date() if ja_cadastrado else datetime.today().date())
        with c3:
            p_teste = st.date_input("Próx. Teste Hidro.:", format="DD/MM/YYYY", value=pd.to_datetime(dados["Próx. Teste"]).date() if ja_cadastrado else datetime.today().date())

        st.subheader("3. Inspeção Mensal (Vistoria)")
        i1, i2, i3 = st.columns(3)
        with i1:
            dt
