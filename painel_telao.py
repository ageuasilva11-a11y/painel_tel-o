import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="Painel de Orçamentos", page_icon="📊", layout="wide")

st.title("📊 Telão - Acompanhamento de Orçamentos")


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

        # Garantir coluna de Status padronizada
        col_status_nome = "Status" if "Status" in df.columns else df.columns[6]

        # Filtragem das duas tabelas
        df_concretizados = df[df[col_status_nome].str.strip().str.lower() == "concretizada"]
        df_em_andamento = df[df[col_status_nome].str.strip().str.lower() != "concretizada"]

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

        # --- BLOCO DE ATUALIZAÇÃO DE STATUS ---
        st.subheader("⚙️ Alterar Status de um Orçamento")

        col1, col2, col3 = st.columns([2, 2, 1])
        
        col_orcamento = "Nº Orçamento" if "Nº Orçamento" in df.columns else df.columns[0]
        lista_propostas = [str(val) for val in df[col_orcamento].tolist()]
        
        with col1:
            prop_selecionada = st.selectbox("Selecione o Nº do Orçamento", lista_propostas)
        
        with col2:
            novo_status = st.selectbox("Novo Status", ["Pendente", "Negociação", "Revisada", "Concretizada"])

        with col3:
            st.write(" ")
            st.write(" ")
            if st.button("🔄 Atualizar Status", use_container_width=True):
                try:
                    idx_linha = lista_propostas.index(prop_selecionada) + 2
                    col_status_idx = df.columns.get_loc(col_status_nome) + 1
                    
                    worksheet.update_cell(idx_linha, col_status_idx, novo_status)
                    st.success(f"Status do Orçamento '{prop_selecionada}' atualizado para '{novo_status}'!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Erro ao atualizar status: {ex}")
    else:
        st.info("Nenhum orçamento encontrado na planilha.")

except Exception as e:
    st.error(f"Erro ao ligar à planilha do Google Sheets: {e}")
