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

# --- FUNÇÃO DE LIMPEZA E PADRONIZAÇÃO ---
def limpar_codigo_extintor(df):
    if "Nº Ext." in df.columns:
        df["Nº Ext."] = df["Nº Ext."].astype(str).str.strip()
        df["Nº Ext."] = df["Nº Ext."].apply(lambda x: x[:-2] if x.endswith(".0") else x)
    return df

df_cadastros = limpar_codigo_extintor(df_cadastros)
df_inspecoes = limpar_codigo_extintor(df_inspecoes)

# --- FUNÇÃO PARA FORMATAR DATAS PARA O PADRÃO BRASILEIRO (DD/MM/AAAA) ---
def formatar_data_br(v):
    if pd.isna(v) or str(v).strip() in ["", "None", "NaN"]:
        return ""
    try:
        # Se já for um objeto de data/datetime
        if isinstance(v, (datetime, pd.Timestamp)):
            return v.strftime("%d/%m/%Y")
        # Se for string no formato YYYY-MM-DD
        return datetime.strptime(str(v).split()[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        try:
            # Se já estiver no formato DD/MM/AAAA por engano
            return datetime.strptime(str(v).split()[0], "%d/%m/%Y").strftime("%d/%m/%Y")
        except:
            return str(v)

# Abas de navegação
aba_inserir, aba_historico = st.tabs(["📝 Nova Inspeção / Cadastro", "📊 Histórico de Inspeções"])

# --- ABA 1: INSERIR OU ATUALIZAR INSPEÇÃO ---
with aba_inserir:
    st.subheader("1. Identificação")
    num_extintor = st.text_input("Nº Extintor:", key="num_ext_input").strip()

    if num_extintor:
        # Lógica de busca inteligente (02, 2, 002 como iguais)
        try:
            num_digitado_int = int(float(num_extintor))
            def converter_para_int_seguro(x):
                try: return int(float(x))
                except: return -1
            df_cadastros["_busca_int"] = df_cadastros["Nº Ext."].apply(converter_para_int_seguro)
            extintor_existente = df_cadastros[df_cadastros["_busca_int"] == num_digitado_int]
        except ValueError:
            extintor_existente = df_cadastros[df_cadastros["Nº Ext."] == num_extintor]

        ja_cadastrado = not extintor_existente.empty

        st.write("---")
        if ja_cadastrado:
            st.success(f"✅ Extintor Nº {num_extintor} localizado! Carregando dados do último registro...")
            dados_finais = extintor_existente.iloc[0]
            num_extintor_salvamento = str(dados_finais["Nº Ext."])
        else:
            st.warning(f"🆕 Extintor Nº {num_extintor} não encontrado. Preencha os campos para realizar o primeiro cadastro.")
            dados_finais = None
            num_extintor_salvamento = num_extintor

        st.subheader("2. Informações do Equipamento")
        
        localizacao = st.text_input("Localização:", value=str(dados_finais["Localização"]) if ja_cadastrado else "")
        lista_tipos = ["Água", "PQS (Pó Químico)", "CO2", "Espuma Mecânica"]
        index_tipo = lista_tipos.index(dados_finais["Tipo"]) if ja_cadastrado and dados_finais["Tipo"] in lista_tipos else 0
        tipo = st.selectbox("Tipo:", lista_tipos, index=index_tipo)
        carga = st.text_input("Carga (Kg/L):", value=str(dados_finais["Carga (Kg/L)"]) if ja_cadastrado else "")

        def converter_data_para_input(valor_data):
            if ja_cadastrado and pd.notna(valor_data) and str(valor_data).strip() not in ["", "None"]:
                for formato in ("%Y-%m-%d", "%d/%m/%Y"):
                    try: 
                        return datetime.strptime(str(valor_data).split()[0], formato).date()
                    except ValueError: 
                        continue
            return datetime.today().date()

        col1, col2 = st.columns(2)
        with col1:
            prox_recarga = st.date_input("Próxima Recarga:", value=converter_data_para_input(dados_finais["Próx. Recarga"] if ja_cadastrado else None))
        with col2:
            prox_teste = st.date_input("Próximo Teste (Hidrostático):", value=converter_data_para_input(dados_finais["Próx. Teste"] if ja_cadastrado else None))

        st.write("---")
        st.subheader("3. Dados da Inspeção Atual")
        
        col_insp1, col_insp2 = st.columns(2)
        with col_insp1:
            data_inspecao = st.date_input("Data da Inspeção Atual:", value=datetime.today().date())
            pesagem = st.number_input("Pesagem Atual (Kg):", min_value=0.0, step=0.05, value=0.0)
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
                    if "_busca_int" in df_cadastros.columns:
                        df_cadastros = df_cadastros.drop(columns=["_busca_int"])

                    # Salvamos no formato padrão do banco (YYYY-MM-DD) para manter a consistência da planilha
                    novo_cadastro = {
                        "Nº Ext.": str(num_extintor_salvamento),
                        "Localização": str(localizacao),
                        "Tipo": str(tipo),
                        "Carga (Kg/L)": str(carga),
                        "Próx. Recarga": str(prox_recarga),
                        "Próx. Teste": str(prox_teste)
                    }
                    
                    nova_inspecao = {
                        "Data da Inspeção": str(data_inspecao),
                        "Nº Ext.": str(num_extintor_salvamento),
                        "Localização": str(localizacao),
                        "Tipo": str(tipo),
                        "Carga (Kg/L)": str(carga),
                        "Próx. Recarga": str(prox_recarga),
                        "Próx. Teste": str(prox_teste),
                        "Pesagem": float(pesagem),
                        "Próx. Pesagem": str(prox_pesagem),
                        "Não Conformidades": str(nao_conformidades),
                        "Funcionário": str(funcionario)
                    }
                    
                    if ja_cadastrado:
                        df_cadastros.loc[df_cadastros["Nº Ext."] == num_extintor_salvamento, ["Localização", "Tipo", "Carga (Kg/L)", "Próx. Recarga", "Próx. Teste"]] = [
                            str(localizacao), str(tipo), str(carga), str(prox_recarga), str(prox_teste)
                        ]
                    else:
                        df_cadastros = pd.concat([df_cadastros, pd.DataFrame([novo_cadastro])], ignore_index=True)
                    
                    df_inspecoes = pd.concat([df_inspecoes, pd.DataFrame([nova_inspecao])], ignore_index=True)
                    
                    df_cadastros = limpar_codigo_extintor(df_cadastros)
                    df_inspecoes = limpar_codigo_extintor(df_inspecoes)
                    
                    try:
                        conn.update(worksheet="Cadastros", data=df_cadastros)
                        conn.update(worksheet="Inspecoes", data=df_inspecoes)
                        st.success(f"Dados do Extintor {num_extintor_salvamento} salvos com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao gravar os dados na planilha: {e}")

# --- ABA 2: VISUALIZAR O HISTÓRICO COMPLETO ---
with aba_historico:
    st.subheader("📋 Histórico Completo de Inspeções Realizadas")
    
    if df_inspecoes.empty:
        st.info("Nenhuma inspeção foi registrada ainda.")
    else:
        filtro_extintor = st.text_input("Filtrar histórico por Nº do Extintor (Deixe em branco para ver todos):", value="", key="filtro_hist").strip()
        
        df_exibicao = df_inspecoes.copy()
        
        if filtro_extintor:
            try:
                filtro_int = int(float(filtro_extintor))
                def converter_para_int_seguro(x):
                    try: return int(float(x))
                    except: return -1
                df_exibicao["_filtro_int"] = df_exibicao["Nº Ext."].apply(converter_para_int_seguro)
                df_exibicao = df_exibicao[df_exibicao["_filtro_int"] == filtro_int]
                df_exibicao = df_exibicao.drop(columns=["_filtro_int"])
            except ValueError:
                df_exibicao = df_exibicao[df_exibicao["Nº Ext."] == filtro_extintor]
            
        if df_exibicao.empty:
            st.warning(f"Nenhum registro encontrado para o extintor Nº {filtro_extintor}.")
        else:
            # Ordenação garantida antes de mudar a exibição para texto brasileiro
            if "Data da Inspeção" in df_exibicao.columns:
                try:
                    df_exibicao["_data_sort"] = pd.to_datetime(df_exibicao["Data da Inspeção"])
                    df_exibicao = df_exibicao.sort_values(by="_data_sort", ascending=False).drop(columns=["_data_sort"])
                except:
                    pass
            
            # --- CONVERSÃO VISUAL DAS DATAS PARA DD/MM/AAAA ---
            colunas_data = ["Data da Inspeção", "Próx. Recarga", "Próx. Teste", "Próx. Pesagem"]
            for col in colunas_data:
                if col in df_exibicao.columns:
                    df_exibicao[col] = df_exibicao[col].apply(formatar_data_br)
            
            # Reorganização opcional para deixar a visualização amigável na tela
            ordem_colunas = [
                "Data da Inspeção", "Nº Ext.", "Funcionário", "Localização", "Tipo", 
                "Carga (Kg/L)", "Pesagem", "Próx. Pesagem", "Próx. Recarga", "Próx. Teste", "Não Conformidades"
            ]
            colunas_existentes = [c for c in ordem_colunas if c in df_exibicao.columns]
            df_exibicao = df_exibicao[colunas_existentes]

            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
