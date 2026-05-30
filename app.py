import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Inspeção de Extintores", layout="wide")
st.title("🧯 Controle e Inspeção de Extintores")

# 1. Conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lendo a aba de cadastros existentes
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
except Exception as e:
    st.error("Erro ao conectar ao Google Sheets. Verifique as credenciais.")
    df_cadastros = pd.DataFrame(columns=["Nº Ext.", "Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"])

# 2. Identificação do Extintor
st.subheader("1. Identificação")
num_extintor = st.text_input("Nº Extintor (Digite e aperte Enter):", key="num_ext")

if num_extintor:
    # Verifica se o extintor já existe no banco de dados
    extintor_existente = df_cadastros[df_cadastros["Nº Ext."].astype(str) == str(num_extintor)]
    
    ja_cadastrado = not extintor_existente.empty
    
    if ja_cadastrado:
        st.success(f"Extintor nº {num_extintor} localizado! Carregando dados...")
        dados_finais = extintor_existente.iloc[0]
    else:
        st.warning(f"Extintor nº {num_extintor} não encontrado. Preencha os dados para o primeiro cadastro.")
        dados_finais = None

    # 3. Formulário de Dados de Cadastro e Inspeção
    st.write("---")
    st.subheader("2. Dados Técnicos e Vistoria")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        localizacao = st.text_input("Localização", value=dados_finais["Localização"] if ja_cadastrado else "")
        tipo = st.selectbox("Tipo", ["Água", "PQS (Pó Químico)", "CO2", "Espuma"], 
                            index=["Água", "PQS (Pó Químico)", "CO2", "Espuma"].index(dados_finais["Tipo"]) if ja_cadastrado else 0)
        carga = st.text_input("Carga (Kg/L)", value=dados_finais["Carga (Kg/L)"] if ja_cadastrado else "")

    with col2:
        # Datas de manutenção (se já existirem, converte para date do python)
        def obter_data(valor, padrao):
            if ja_cadastrado and pd.notna(valor):
                try: return datetime.strptime(str(valor), "%Y-%m-%d").date()
                except: return padrao
            return padrao

        prox_recarga = st.date_input("Próx. Recarga", value=obber_data(dados_finais["Próx. Recarga"] if ja_cadastrado else None, datetime.today().date()))
        prox_teste = st.date_input("Próx. Teste", value=obber_data(dados_finais["Próx. Teste"] if ja_cadastrado else None, datetime.today().date()))

    with col3:
        # Dados exclusivos da inspeção atual
        data_inspecao = st.date_input("Data da Inspeção Atual", value=datetime.today().date())
        pesagem = st.number_input("Pesagem Atual (Kg)", min_value=0.0, step=0.1)
        # Sugere dinamicamente a próxima pesagem para daqui a 3 meses (regra comum)
        sugestao_prox_pesagem = data_inspecao + timedelta(days=90)
        prox_pesagem = st.date_input("Próx. Pesagem", value=sugestao_prox_pesagem)

    # Campo de não conformidades (ocupa a largura total abaixo)
    nao_conformidades = st.text_area("Não Conformidades", value="", placeholder="Ex: Lacre rompido, sem sinalização, manômetro com pressão baixa...")

    # 4. Botão de Salvar
    if st.button("Salvar Inspeção", type="primary"):
        # Aqui entrará a lógica para enviar os dados de volta para o Google Sheets
        st.info("Pronto para gravar no Sheets!")
