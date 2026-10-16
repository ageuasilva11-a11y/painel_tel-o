import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="Painel de Orçamentos", page_icon="📊", layout="wide")

st.title("📊 Painel de Gestão e Acompanhamento de Orçamentos")


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


def ler_worksheet_como_dataframe(worksheet):
    all_values = worksheet.get_all_values()
    if not all_values or len(all_values) < 2:
        return pd.DataFrame()
    
    headers = all_values[0]
    data = all_values[1:]
    
    cleaned_headers = []
    for i, h in enumerate(headers):
        h_str = str(h).strip()
        if not h_str:
            cleaned_headers.append(f"Coluna_{i+1}")
        else:
            cleaned_headers.append(h_str)
            
    return pd.DataFrame(data, columns=cleaned_headers)


try:
    client = obter_conexao_sheets()
    if not client:
        st.error("Não foi possível estabelecer ligação com o Google Sheets.")
        st.stop()

    nome_planilha = "Orcamentos"
    if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
        nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

    sheet = client.open(nome_planilha)
    
    try:
        worksheet = sheet.worksheet("Orcamentos")
    except Exception:
        worksheet = sheet.get_worksheet(0)

    df = ler_worksheet_como_dataframe(worksheet)
    if not df.empty:
        col_status_nome = "Status" if "Status" in df.columns else (df.columns[6] if len(df.columns) > 6 else df.columns[-1])

        df_concretizados = df[df[col_status_nome].astype(str).str.strip().str.lower() == "concretizada"]
        df_em_andamento = df[df[col_status_nome].astype(str).str.strip().str.lower() != "concretizada"]

        # --- TABELA 1: EM ACOMPANHAMENTO ---
        st.subheader("⏳ Orçamentos em Acompanhamento (Pendente / Negociação / Revisada)")
        if not df_em_andamento.empty:
            st.dataframe(df_em_andamento, use_container_width=True)
        else:
            st.info("Nenhum orçamento pendente ou em negociação no momento.")

        st.markdown("---")

        # --- TABELA 2: CONCRETIZADOS ---
        st.subheader("✅ Orçamentos Concretizados")
        if not df_concretizados.empty:
            st.dataframe(df_concretizados, use_container_width=True)
        else:
            st.info("Nenhum orçamento concretizado registado até ao momento.")

        st.markdown("---")

        # --- TABELA 3: PAINEL GERAL DE MEDIÇÃO E OBRAS ---
        st.subheader("📋 Painel Geral de Acompanhamento das Obras")
        try:
            ws_obras = sheet.worksheet("Obras")
            df_obras = ler_worksheet_como_dataframe(ws_obras)
            if not df_obras.empty:
                st.dataframe(df_obras, use_container_width=True)
            else:
                st.info("Nenhuma obra cadastrada até ao momento.")
        except Exception:
            st.info("Nenhuma aba 'Obras' encontrada na planilha ainda.")

    else:
        st.info("Nenhum orçamento encontrado na planilha.")

except Exception as e:
    st.error(f"Erro ao ligar à planilha do Google Sheets: {e}")
