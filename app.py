import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Configuração da página - Foco em Gestão Corporativa e Executiva
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização para os cards e botões ficarem destacados e profissionais
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 36px; font-weight: bold; }
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

# --- FUNÇÕES DE PADRONIZAÇÃO E LIMPEZA ---
def limpar_codigo(df):
    if df is not None and not df.empty and "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

def tratar_data_calculo(v):
    """Garante que qualquer formato de data vire um objeto datetime.date para cálculos precisos"""
    if pd.isna(v) or str(v).strip() in ["", "None", "NaN"]: 
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(v).strip().split()[0], formato).date()
        except ValueError:
            continue
    return None

def formatar_data_br(v):
    """Formata datas para exibição visual amigável na tabela (DD/MM/AAAA)"""
    dt_objeto = tratar_data_calculo(v)
    if dt_objeto:
        return dt_objeto.strftime("%d/%m/%Y")
    return str(v) if pd.notna(v) else ""

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# 2. SISTEMA DE ABAS
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard de Gestão", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD (COM GRÁFICOS INTERATIVOS) ---
with aba_dash:
    st.subheader("Painel de Controle e Conformidade Tecnológica")
    
    if df_cadastros is None or df_cadastros.empty:
        st.info("Aguardando os primeiros cadastros para gerar os indicadores comerciais.")
    else:
        hoje = datetime.today().date()
        alerta_30 = hoje + timedelta(days=30)

        # Criando colunas temporárias de cálculo seguras (não afetam a planilha)
        df_calc = df_cadastros.copy()
        df_calc['dt_recarga_limpa'] = df_calc['Próx. Recarga'].apply(tratar_data_calculo)
        df_calc['dt_teste_limpa'] = df_calc['Próx. Teste'].apply(tratar_data_calculo)

        # Filtros de Alertas
        recarga_vencida = df_calc[df_calc['dt_recarga_limpa'] < hoje]
        recarga_alerta = df_calc[(df_calc['dt_recarga_limpa'] >= hoje) & (df_calc['dt_recarga_limpa'] <= alerta_30)]
        teste_vencido = df_calc[df_calc['dt_teste_limpa'] < hoje]

        # Renderização dos Cards Visuais
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Equipamentos", len(df_cadastros))
        m2.metric("Recarga Vencida 🔴", len(recarga_vencida))
        m3.metric("Vence em até 30 dias 🟡", len(recarga_alerta))
        m4.metric("Teste Hidro. Vencido ❌", len(teste_vencido))

        st.write("---")
        
        # --- SEÇÃO DE GRÁFICOS ---
        st.subheader("📈 Análise Visual da Distribuição e Prazos")
        g1, g2 = st.columns(2)
        
        with g1:
            # Geração do Status para o gráfico de Rosca
            def categorizar_status(row):
                if row['dt_recarga_limpa'] and row['dt_recarga_limpa'] < hoje: return "🔴 Recarga Vencida"
                if row['dt_teste_limpa'] and row['dt_teste_limpa'] < hoje: return "❌ Teste Hidro. Vencido"
                if row['dt_recarga_limpa'] and row['dt_recarga_limpa'] <= alerta_30: return "🟡 Próximo ao Vencimento (30d)"
                return "✅ Em Conformidade"

            df_calc["Status Visão Geral"] = df_calc.apply(categorizar_status, axis=1)
            df_status_count = df_calc["Status Visão Geral"].value_counts().reset_index()
            df_status_count.columns = ["Status", "Quantidade"]
            
            # Mapa de cores corporativas fixas para o gráfico
            cores_status = {
                "✅ Em Conformidade": "#2e7d32",
                "🟡 Próximo ao Vencimento (30d)": "#f9a825",
                "🔴 Recarga Vencida": "#c62828",
                "❌ Teste Hidro. Vencido": "#e53935"
            }
            
            fig_donut = px.pie(
                df_status_count, 
                values="Quantidade", 
                names="Status", 
                hole=0.5,
                title="Status Geral da Incolumidade (AVCB)",
                color="Status",
                color_discrete_map=cores_status
            )
            fig_donut.update_traces(textinfo='value+percent')
            st.plotly_chart(fig_donut, use_container_width=True)

        with g2:
            # Gráfico de barras por tipo de agente extintor
            df_tipo_count = df_calc["Tipo"].value_counts().reset_index()
            df_tipo_count.columns = ["Tipo de Agente", "Qtd"]
            
            fig_bar = px.bar(
                df_tipo_count, 
                x="Tipo de Agente", 
                y="Qtd", 
                title="Inventário de Equipamentos por Tipo",
                text="Qtd",
                color="Tipo de Agente",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(showlegend=False, yaxis_title="Quantidade", xaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.write("---")
        
        # Grid de Ação Preventiva (Tabela)
        df_alertas = df_calc[
            (df_calc['dt_recarga_limpa'] < hoje) | 
            (df_calc['dt_teste_limpa'] < hoje) | 
            ((df_calc['dt_recarga_limpa'] >= hoje) & (df_calc['dt_recarga_limpa'] <= alerta_30))
        ].copy()

        if not df_alertas.empty:
            st.subheader("⚠️ Plano de Ação - Equipamentos que Exigem Atenção Imediata")
            
            df_alertas["Próx. Recarga"] = df_alertas["Próx. Recarga"].apply(formatar_data_br)
            df_alertas["Próx. Teste"] = df_alertas["Próx. Teste"].apply(formatar_data_br)
            
            df_alertas["Status Auditoria"] = df_alertas.apply(lambda r: "🔴 Recarga Vencida" if r['dt_recarga_limpa'] < hoje else ("❌ Teste Hidro. Vencido" if r['dt_teste_limpa'] < hoje else "🟡 Próximo ao Vencimento"), axis=1)
            
            colunas_dash = ["Nº Ext.", "Localização", "Tipo", "Próx. Recarga", "Próx. Teste", "Status Auditoria"]
            st.dataframe(df_alertas[colunas_dash], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Excelente! Todos os extintores da instalação estão 100% em conformidade com as normas vigentes.")

# --- ABA 2: FORMULÁRIO ---
with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor (ex: 02):", key="f_num").strip()

    if num_extintor:
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
        if ja_cadastrado: st.success(f"✅ Equipamento {num_final} localizado na base de dados.")
        else: st.warning(f"🆕 Equipamento {num_final} não encontrado. Iniciando ficha técnica para primeiro cadastro.")

        st.subheader("2. Ficha Técnica do Equipamento")
        c1, c2, c3 = st.columns(3)
        with c1:
            loc = st.text_input("Localização Física (Ex: Hangar 1):", value=str(dados["Localização"]) if ja_cadastrado else "")
            lista_tipos = ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"]
            idx_tipo = lista_tipos.index(dados["Tipo"]) if ja_cadastrado and dados["Tipo"] in lista_tipos else 0
            tipo_sel = st.selectbox("Tipo de Carga:", lista_tipos, index=idx_tipo)
        with c2:
            carga = st.text_input("Capacidade de Carga (Kg/L):", value=str(dados["Carga (Kg/L)"]) if ja_cadastrado else "")
            dt_rec_inicial = tratar_data_calculo(dados["Próx. Recarga"]) if ja_cadastrado else datetime.today().date()
            p_rec = st.date_input("Vencimento da Recarga:", format="DD/MM/YYYY", value=dt_rec_inicial if dt_rec_inicial else datetime.today().date())
        with c3:
            dt_test_inicial = tratar_data_calculo(dados["Próx. Teste"]) if ja_cadastrado else datetime.today().date()
            p_teste = st.date_input("Vencimento do Teste Hidrostático:", format="DD/MM/YYYY", value=dt_test_inicial if dt_test_inicial else datetime.today().date())

        st.write("---")
        st.subheader("3. Checklist de Inspeção Mensal (Vistoria)")
        i1, i2, i3 = st.columns(3)
        with i1:
            dt_insp
