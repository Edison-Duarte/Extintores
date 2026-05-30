import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página do Streamlit
st.set_page_config(page_title="Controle de Extintores", page_icon="🧯", layout="centered")

st.title("🧯 Controle e Inspeção de Extintores")
st.write("Insira o número do extintor para realizar o cadastro ou uma nova inspeção.")

# 1. Conexão com o Google Sheets utilizando os Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê as duas abas da planilha
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro ao conectar à planilha. Verifique se as credenciais nos Secrets estão corretas e se a planilha foi compartilhada com o e-mail da conta de serviço.")
    st.stop()

# Limpando possíveis valores nulos ou formatos estranhos para garantir a busca
df_cadastros["Nº Ext."] = df_cadastros["Nº Ext."].astype(str).str.strip()

# 2. Identificação do Extintor
st.subheader("1. Identificação")
num_extintor = st.text_input("Nº Extintor:", key="num_ext_input").strip()

if num_extintor:
    # Verifica se o número digitado já existe na aba de Cadastros
    extintor_existente = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
    ja_cadastrado = not extintor_existente.empty

    st.write("---")
    if ja_cadastrado:
        st.success(f"✅ Extintor Nº {num_extintor} localizado! Carregando dados do último registro...")
        dados_finais = extintor_existente.iloc[0]
    else:
        st.warning(f"🆕 Extintor Nº {num_extintor} não encontrado. Preencha os campos para realizar o primeiro cadastro.")
        dados_finais = None

    # 3. Formulário de Dados
    st.subheader("2. Informações do Equipamento")
    
    # Campos que ficam pré-preenchidos se o extintor já existir
    localizacao = st.text_input("Localização:", value=str(dados_finais["Localização"]) if ja_cadastrado else "")
    
    lista_tipos = ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"]
    index_tipo = lista_tipos.index(dados_finais["Tipo"]) if ja_cadastrado and dados_finais["Tipo"] in lista_tipos else 0
    tipo = st.selectbox("Tipo:", lista_tipos, index=index_tipo)
    
    carga = st.text_input("Carga (Kg/L):", value=str(dados_finais["Carga (Kg/L)"]) if ja_cadastrado else "")

    # Tratamento de datas para o formulário
    def converter_data(valor_data):
        if ja_cadastrado and pd.notna(valor_data) and valor_data != "":
            try:
                return datetime.strptime(str(valor_data), "%Y-%m-%d").date()
            except:
                return datetime.today().date()
        return datetime.today().date()

    col1, col2 = st.columns(2)
    with col1:
        prox_recarga = st.date_input("Próxima Recarga:", value=converter_data(dados_finais["Próx. Recarga"] if ja_cadastrado else None))
    with col2:
        prox_teste = st.date_input("Próximo Teste (Hidrostático):", value=converter_data(dados_finais["Próx. Teste"] if ja_cadastrado else None))

    st.write("---")
    st.subheader("3. Dados da Inspeção Atual")
    
    # Campos dinâmicos que mudam a cada nova inspeção
    data_inspecao = st.date_input("Data da Inspeção Atual:", value=datetime.today().date())
    pesagem = st.number_input("Pesagem Atual (Kg):", min_value=0.0, step=0.05, value=0.0)
    
    # Sugestão automática de próxima pesagem (padrão 3 meses a partir da inspeção atual)
    sugestao_pesagem = data_inspecao + timedelta(days=90)
    prox_pesagem = st.date_input("Próxima Pesagem:", value=sugestao_pesagem)
    
    nao_conformidades = st.text_area("Não Conformidades:", placeholder="Se houver, descreva aqui (ex: lacre rompido, manômetro descalibrado, sem sinalização...)")

    # 4. Botão para Salvar as Informações
    if st.button("Salvar Registro", type="primary"):
        with st.spinner("Salvando dados na planilha..."):
            
            # Criando os dicionários com os novos dados digitados
            novo_cadastro = {
                "Nº Ext.": str(num_extintor),
                "Localização": str(localizacao),
                "Tipo": str(tipo),
                "Carga (Kg/L)": str(carga),
                "Próx. Recarga": str(prox_recarga),
                "Próx. Teste": str(prox_teste)
            }
            
            nova_inspecao = {
                "Data da Inspeção": str(data_inspecao),
                "Nº Ext.": str(num_extintor),
                "Pesagem": float(pesagem),
                "Próx. Pesagem": str(prox_pesagem),
                "Não Conformidades": str(nao_conformidades)
            }
            
            # --- LÓGICA DA ABA 'CADASTROS' ---
            # Se já existir, precisamos atualizar a linha existente, se não, adicionamos uma nova
            if ja_cadastrado:
                df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor, ["Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"]] = [
                    str(localizacao), str(tipo), str(carga), str(prox_recarga), str(prox_teste)
                ]
            else:
                df_cadastros = pd.concat([df_cadastros, pd.DataFrame([novo_cadastro])], ignore_index=True)
            
            # --- LÓGICA DA ABA 'INSPECOES' ---
            # Sempre adiciona uma linha nova para gerar o histórico temporal
            df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([nova_inspecao])], ignore_index=True)
            
            # Atualiza de fato o Google Sheets
            try:
                conn.update(worksheet="Cadastros", data=df_cadastros)
                conn.update(worksheet="Inspecoes", data=df_inspecoes)
                st.success(f"Dados do Extintor {num_extintor} salvos com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao gravar os dados na planilha: {e}")
