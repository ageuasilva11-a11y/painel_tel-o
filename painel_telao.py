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

    # 1. Autenticação via Secrets do Streamlit Cloud
    if "google_sheets" in st.secrets:
        creds_dict = dict(st.secrets["google_sheets"])
        
        # Tratamento rigoroso e automático da chave privada (PEM)
        if "private_key" in creds_dict:
            pk = creds_dict["private_key"]
            pk = pk.replace("\\n", "\n")
            lines = [line.strip() for line in pk.split("\n") if line.strip()]
            creds_dict["private_key"] = "\n".join(lines) + "\n"

        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)

    # 2. Autenticação via ficheiro local
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)

    else:
        st.error("Credenciais do Google Sheets não encontradas!")
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
        st.info("Verifique se partilhou a planilha do Google Drive com o e-mail da conta de serviço com acesso de Leitor/Editor.")
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

    # Indicadores
    col1, col2 = st.columns(2)
    col1.metric("Total de Orçamentos", len(df))

    st.markdown("---")
    st.subheader("📋 Registos de Orçamentos")
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
