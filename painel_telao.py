import os
import json
import base64
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

    # 1. Método Base64 (Inviolável no Streamlit Cloud - sem erros de quebra de linha)
    if "GCP_JSON_B64" in st.secrets:
        b64_data = st.secrets["GCP_JSON_B64"]
        creds_json = base64.b64decode(b64_data).decode("utf-8")
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)

    # 2. Método local no seu PC (service_account.json)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)

    else:
        st.error("Credenciais do Google Sheets não encontradas nos Secrets!")
        st.stop()

# -----------------------------------------------------------------------------
# FUNÇÃO PARA CARREGAR DADOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        client = conectar_google_sheets()

        nome_planilha = "Orcamentos"
        if "planilha_nome" in st.secrets:
            nome_planilha = st.secrets["planilha_nome"]

        sheet = client.open(nome_planilha)

        try:
            worksheet = sheet.worksheet("Orcamentos")
        except Exception:
            worksheet = sheet.get_worksheet(0)

        dados = worksheet.get_all_records()
        return pd.DataFrame(dados)

    except Exception as e:
        st.error(f"Erro ao ligar ao Google Sheets: {e}")
        st.info("Verifique se partilhou a planilha do Google Drive com o e-mail: orca-451@telao-510314.iam.gserviceaccount.com")
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

    st.metric("Total de Orçamentos", len(df))
    st.markdown("---")
    st.subheader("📋 Registos de Orçamentos")
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
