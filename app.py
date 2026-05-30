import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página - Foco em Gestão Corporativa e Executiva
st.set_page_config(page_title="Gestão de Extintores SP", page_icon="📊", layout="wide")

# Estilização para os cards ficarem destacados e profissionais
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
    dt = tratar_data_calculo(v)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return str(v) if pd.notna(v) else ""

df_cadastros = limpar_codigo(df_cadastros)
df_inspecoes = limpar_codigo(df_inspecoes)

# 2. SISTEMA DE ABAS
aba_dash, aba_form, aba_hist = st.tabs(["📊 Dashboard de Gestão", "📝 Nova Inspeção / Cadastro", "📋 Histórico Geral"])

# --- ABA 1: DASHBOARD (A TORRE DE CONTROLE) ---
with aba_dash:
    st.subheader("Painel de Controle e Conformidade Tecnológica")
    
    if df_cadastros.empty:
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
        
        # Grid de Ação Preventiva
        df_alertas = df_calc[
            (df_calc['dt_recarga_limpa'] < hoje) | 
            (df_calc['dt_teste_limpa'] < hoje) | 
            ((df_calc['dt_recarga_limpa'] >= hoje) & (df_calc['dt_recarga_limpa'] <= alerta_30))
        ].copy()

        if not df_alertas.empty:
            st.subheader("⚠️ Plano de Ação - Equipamentos que Exigem Atenção Imediata")
            
            # Formata apenas visualmente para o padrão brasileiro antes de exibir
            df_alertas["Próx. Recarga"] = df_alertas["Próx. Recarga"].apply(formatar_data_br)
            df_alertas["Próx. Teste"] = df_alertas["Próx. Teste"].apply(formatar_data_br)
            
            # Adiciona coluna de Status customizada para auditoria
            def definir_status(row):
                if row['dt_recarga_limpa'] and row['dt_recarga_limpa'] < hoje: return "🔴 Recarga Vencida"
                if row['dt_teste_limpa'] and row['dt_teste_limpa'] < hoje: return "❌ Teste Hidro. Vencido"
                return "🟡 Próximo ao Vencimento"
                
            df_alertas["Status Auditoria"] = df_alertas.apply(definir_status, axis=1)
            
            colunas_dash = ["Nº Ext.", "Localização", "Tipo", "Próx. Recarga", "Próx. Teste", "Status Auditoria"]
            st.dataframe(df_alertas[colunas_dash], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Excelente! Todos os extintores da instalação estão 100% em conformidade com as normas vigentes.")

# --- ABA 2: FORMULÁRIO (CORRIGIDO) ---
with aba_form:
    st.subheader("1. Identificação do Equipamento")
    num_extintor = st.text_input("Digite o Nº do Extintor (ex: 02):", key="f_num").strip()

    if num_extintor:
        # Busca flexível inteligente (trata 02, 2 e 002 como iguais)
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
            dt_insp = st.date_input("Data da Inspeção Atual:", format="DD/MM/YYYY", value=datetime.today().date())
            func = st.text_input("Inspetor / Responsável Técnico:")
        with i2:
            pesagem = st.number_input("Massa / Pesagem Atual (Kg):", min_value=0.0, step=0.01, value=0.0)
            # REPARO DO ERRO: Utilizando corretamente a variável dt_insp para projetar a data técnica
            p_pesagem = dt_insp + timedelta(days=90)
            st.info(f"📆 Agendamento Automático da Próxima Pesagem: {p_pesagem.strftime('%d/%m/%Y')}")
        with i3:
            nao_conf = st.text_area("Registro de Anomalias / Não Conformidades:", placeholder="Lacre rompido, manômetro sem pressão, ausência de sinalização...")

        if st.button("Gravar Informações e Sincronizar", type="primary"):
            if not func.strip(): 
                st.error("⚠️ Erro de validação: O nome do Inspetor/Responsável é obrigatório para fins de auditoria.")
            else:
                with st.spinner("Registrando dados criptografados na base em nuvem..."):
                    if "_tmp" in df_cadastros.columns: 
                        df_cadastros = df_cadastros.drop(columns=["_tmp"])
                    
                    row_cad = {
                        "Nº Ext.": num_final, 
                        "Localização": loc, 
                        "Tipo": tipo_sel, 
                        "Carga (Kg/L)": carga, 
                        "Próx. Recarga": str(p_rec), 
                        "Próx. Teste": str(p_teste)
                    }
                    
                    row_insp = {
                        "Data da Inspeção": str(dt_insp),
                        "Nº Ext.": num_final,
                        "Localização": loc,
                        "Tipo": tipo_sel,
                        "Carga (Kg/L)": carga,
                        "Pesagem": pesagem,
                        "Próx. Pesagem": str(p_pesagem),
                        "Próx. Recarga": str(p_rec),
                        "Próx. Teste": str(p_teste),
                        "Não Conformidades": nao_conf,
                        "Funcionário": func
                    }

                    if ja_cadastrado:
                        df_cadastros.loc[df_cadastros["Nº Ext."] == num_final, row_cad.keys()] = row_cad.values()
                    else:
                        df_cadastros = pd.concat([df_cadastros, pd.DataFrame([row_cad])], ignore_index=True)
                    
                    df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([row_insp])], ignore_index=True)
                    
                    try:
                        conn.update(worksheet="Cadastros", data=df_cadastros)
                        conn.update(worksheet="Inspecoes", data=df_inspecoes)
                        st.success(f"Sucesso! Dados do Extintor {num_final} salvos e integrados.")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro crítico de gravação: {e}")

# --- ABA 3: HISTÓRICO GERAL ---
with aba_hist:
    st.subheader("Histórico Retroativo de Vistorias")
    if not df_inspecoes.empty:
        df_view = df_inspecoes.copy()
        
        # Garante a formatação visual correta de todas as colunas de datas no histórico
        colunas_datas_hist = ["Data da Inspeção", "Próx. Pesagem", "Próx. Recarga", "Próx. Teste"]
        for col in colunas_datas_hist:
            if col in df_view.columns: 
                df_view[col] = df_view[col].apply(formatar_data_br)
        
        # Ordenação inteligente pelo mais recente
        st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro histórico disponível nesta unidade.")
