import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import os

st.set_page_config(page_title="Telão de Orçamentos", page_icon="📊", layout="wide")

st.title("📊 Telão - Gestão de Orçamentos Registados")

# --- CONEXÃO AO GOOGLE SHEETS ---
def obter_conexao_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "google_sheets" in st.secrets:
        creds_dict = dict(st.secrets["google_sheets"])
        if "private_key" in creds_dict:
            pk = creds_dict["private_key"]
            pk = pk.replace("\\n", "\n").replace("\r", "")
            creds_dict["private_key"] = pk
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)
    return None

try:
    client = obter_conexao_sheets()
    nome_planilha = "Orcamentos"
    if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
        nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

    sheet = client.open(nome_planilha)
    try:
        worksheet = sheet.worksheet("Orcamentos")
    except Exception:
        worksheet = sheet.get_worksheet(0)

    dados = worksheet.get_all_records()
    if dados:
        df = pd.DataFrame(dados)
        st.subheader("Todos os Orçamentos Registados")
        
        # Exibição interativa com edição de status se desejar
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Ainda não existem orçamentos registados na planilha.")

except Exception as e:
    st.error(f"Erro ao carregar os dados do Google Sheets: {e}")
