import os
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Painel de Orçamentos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# FUNÇÃO DE AUTENTICAÇÃO COM GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_resource
def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # 1. Autenticação via Streamlit Cloud Secrets (Bloco [google_sheets])
    if "google_sheets" in st.secrets:
        creds_dict = dict(st.secrets["google_sheets"])
        
        # Tratamento sanitizado para a chave privada (PEM)
        if "private_key" in creds_dict:
            pk = creds_dict["private_key"]
            pk = pk.replace("\\n", "\n").replace("\r", "")
            creds_dict["private_key"] = pk

        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)

    # 2. Autenticação Local (ficheiro service_account.json na raiz)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)

    else:
        st.error("Credenciais do Google Sheets não encontradas! Verifique o Secrets no Streamlit Cloud ou o arquivo local.")
        st.stop()

# -----------------------------------------------------------------------------
# FUNÇÃO PARA CARREGAR DADOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        client = conectar_google_sheets()
        
        nome_planilha = "Orcamentos"
        if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
            nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

        sheet = client.open(nome_planilha)

        try:
            worksheet = sheet.worksheet("Orcamentos")
        except Exception:
            worksheet = sheet.get_worksheet(0)

        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)

    except Exception as e:
        st.error(f"Erro ao ligar ao Google Sheets: {e}")
        st.info("Verifique se partilhou a planilha do Google Drive com o e-mail da conta de serviço com acesso de Editor/Leitor.")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
def main():
    st.title("📊 Painel de Orçamentos")
    st.markdown("---")

    col_top1, col_top2 = st.columns([4, 1])
    with col_top2:
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("A carregar dados do Google Sheets..."):
        df = carregar_dados()

    if df.empty:
        st.warning("Nenhum dado encontrado na planilha ou erro de ligação.")
        return

    # Indicador Geral
    st.metric("Total de Registos", len(df))
    st.markdown("---")

    # -------------------------------------------------------------------------
    # SECÇÃO: OBRAS CONCRETIZADAS (FECHADAS)
    # -------------------------------------------------------------------------
    st.subheader("🚀 Obras Concretizadas (Fechadas)")

    # Tenta identificar automaticamente colunas de status/situação na planilha
    colunas_possiveis = ["Status", "Situação", "Situacao", "Estado", "Fechado"]
    coluna_status = next((col for col in colunas_possiveis if col in df.columns), None)

    if coluna_status:
        # Filtra linhas onde o status contenha termos indicativos de concretizado/fechado
        termos_sucesso = ["fechado", "concretizado", "concluído", "concluido", "aprovado", "ganho"]
        df_fechadas = df[
            df[coluna_status].astype(str).str.lower().str.contains("|".join(termos_sucesso), na=False)
        ]
    else:
        df_fechadas = pd.DataFrame()

    if not df_fechadas.empty:
        st.success(f"Encontradas {len(df_fechadas)} obras concretizadas.")
        st.dataframe(df_fechadas, use_container_width=True)
    else:
        st.info("Nenhum orçamento concretizado registado na planilha.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # TABELA COMPLETA DE REGISTOS
    # -------------------------------------------------------------------------
    st.subheader("📋 Todos os Orçamentos Registados")
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
