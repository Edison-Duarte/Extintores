import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página do Streamlit
st.set_page_config(page_title="Controle de Extintores", page_icon="🧯", layout="wide")

st.title("🧯 Controle e Inspeção de Extintores")

# 1. Conexão com o Google Sheets utilizando os Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cadastros = conn.read(worksheet="Cadastros", ttl=0)
    df_inspecoes = conn.read(worksheet="Inspecoes", ttl=0)
except Exception as e:
    st.error("Erro ao conectar à planilha. Verifique as credenciais.")
    st.stop()

# Garantir que não haja problemas com espaços nos números de extintor
df_cadastros["Nº Ext."] = df_cadastros["Nº Ext."].astype(str).str.strip()
if not df_inspecoes.empty:
    df_inspecoes["Nº Ext."] = df_inspecoes["Nº Ext."].astype(str).str.strip()

# Criando abas de navegação no topo do app para organizar visualmente
aba_inserir, aba_historico = st.tabs(["📝 Nova Inspeção / Cadastro", "📊 Histórico de Inspeções"])

# --- ABA 1: INSERIR OU ATUALIZAR INSPEÇÃO ---
with aba_inserir:
    st.subheader("1. Identificação")
    num_extintor = st.text_input("Nº Extintor:", key="num_ext_input").strip()

    if num_extintor:
        extintor_existente = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]
        ja_cadastrado = not extintor_existente.empty

        st.write("---")
        if ja_cadastrado:
            st.success(f"✅ Extintor Nº {num_extintor} localizado! Carregando dados do último registro...")
            dados_finais = extintor_existente.iloc[0]
        else:
            st.warning(f"🆕 Extintor Nº {num_extintor} não encontrado. Preencha os campos para realizar o primeiro cadastro.")
            dados_finais = None

        st.subheader("2. Informações do Equipamento")
        
        localizacao = st.text_input("Localização:", value=str(dados_finais["Localização"]) if ja_cadastrado else "")
        lista_tipos = ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"]
        index_tipo = lista_tipos.index(dados_finais["Tipo"]) if ja_cadastrado and dados_finais["Tipo"] in lista_tipos else 0
        tipo = st.selectbox("Tipo:", lista_tipos, index=index_tipo)
        carga = st.text_input("Carga (Kg/L):", value=str(dados_finais["Carga (Kg/L)"]) if ja_cadastrado else "")

        def converter_data(valor_data):
            if ja_cadastrado and pd.notna(valor_data) and valor_data != "":
                try: return datetime.strptime(str(valor_data), "%Y-%m-%d").date()
                except: return datetime.today().date()
            return datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            prox_recarga = st.date_input("Próxima Recarga:", value=converter_data(dados_finais["Próx. Recarga"] if ja_cadastrado else None))
        with col2:
            prox_teste = st.date_input("Próximo Teste (Hidrostático):", value=converter_data(dados_finais["Próx. Teste"] if ja_cadastrado else None))

        st.write("---")
        st.subheader("3. Dados da Inspeção Atual")
        
        col_insp1, col_insp2 = st.columns(2)
        with col_insp1:
            data_inspecao = st.date_input("Data da Inspeção Atual:", value=datetime.today().date())
            pesagem = st.number_input("Pesagem Atual (Kg):", min_value=0.0, step=0.05, value=0.0)
            # Novo campo solicitado:
            funcionario = st.text_input("Funcionário / Responsável:", placeholder="Digite seu nome completo")
        
        with col_insp2:
            sugestao_pesagem = data_inspecao + timedelta(days=90)
            prox_pesagem = st.date_input("Próxima Pesagem:", value=sugestao_pesagem)
            nao_conformidades = st.text_area("Não Conformidades:", placeholder="Se houver, descreva aqui...")

        if st.button("Salvar Registro", type="primary"):
            if not funcionario.strip():
                st.error("⚠️ Por favor, preencha o campo 'Funcionário / Responsável' antes de salvar.")
            else:
                with st.spinner("Salvando dados na planilha..."):
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
                        "Não Conformidades": str(nao_conformidades),
                        "Funcionário": str(funcionario) # Gravando o funcionário
                    }
                    
                    if ja_cadastrado:
                        df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor, ["Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"]] = [
                            str(localizacao), str(tipo), str(carga), str(prox_recarga), str(prox_teste)
                        ]
                    else:
                        df_cadastros = pd.concat([df_cadastros, pd.DataFrame([novo_cadastro])], ignore_index=True)
                    
                    df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([nova_inspecao])], ignore_index=True)
                    
                    try:
                        conn.update(worksheet="Cadastros", data=df_cadastros)
                        conn.update(worksheet="Inspecoes", data=df_inspecoes)
                        st.success(f"Dados do Extintor {num_extintor} salvos com sucesso!")
                        st.rerun() # Atualiza a tela para redefinir os dados e mostrar o histórico novo
                    except Exception as e:
                        st.error(f"Erro ao gravar os dados na planilha: {e}")

# --- ABA 2: VISUALIZAR O HISTÓRICO COMPLETO ---
with aba_historico:
    st.subheader("📋 Histórico Completo de Inspeções Realizadas")
    
    if df_inspecoes.empty:
        st.info("Nenhuma inspeção foi registrada ainda.")
    else:
        # Filtro opcional na tela para buscar por um extintor específico no histórico
        filtro_extintor = st.text_input("Filtrar histórico por Nº do Extintor (Deixe em branco para ver todos):", value="").strip()
        
        df_exibicao = df_inspecoes.copy()
        
        # Se o usuário digitou algo no filtro, aplicamos a busca
        if filtro_extintor:
            df_exibicao = df_exibicao[df_exibicao["Nº Ext."] == filtro_extintor]
            
        if df_exibicao.empty:
            st.warning(f"Nenhum registro encontrado para o extintor Nº {filtro_extintor}.")
        else:
            # Ordena as inspeções mais recentes para aparecerem no topo
            if "Data da Inspeção" in df_exibicao.columns:
                try:
                    df_exibicao["Data da Inspeção"] = pd.to_datetime(df_exibicao["Data da Inspeção"]).dt.date
                    df_exibicao = df_exibicao.sort_values(by="Data da Inspeção", ascending=False)
                except:
                    pass
            
            # Exibe os dados formatados em uma tabela interativa na tela
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
