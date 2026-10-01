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
    """
    Autentica no Google Sheets via st.secrets (Nuvem) ou arquivo local.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # 1. Tenta autenticar usando os Secrets do Streamlit Cloud
    if "google_sheets" in st.secrets:
        creds_dict = dict(st.secrets["google_sheets"])
        # Garante que as quebras de linha da chave privada fiquem corretas
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)

    # 2. Caso contrário, tenta usar o arquivo local (desenvolvimento local)
    elif os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)

    # 3. Se nenhum método estiver disponível, gera um erro informativo
    else:
        st.error(
            "Credenciais do Google Sheets não encontradas! "
            "Configure os Secrets no Streamlit Cloud ou mantenha 'service_account.json' localmente."
        )
        st.stop()

# -----------------------------------------------------------------------------
# FUNÇÃO PARA CARREGAR DADOS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    """
    Lê os dados da planilha 'Orcamentos' do Google Sheets.
    """
    try:
        client = conectar_google_sheets()
        
        # Obtém o nome da planilha (padrão: "Orcamentos")
        nome_planilha = "Orcamentos"
        if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
            nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

        sheet = client.open(nome_planilha)

        # Tenta selecionar a aba "Orcamentos", senão pega a primeira aba disponível
        try:
            worksheet = sheet.worksheet("Orcamentos")
        except Exception:
            worksheet = sheet.get_worksheet(0)

        dados = worksheet.get_all_records()
        df = pd.DataFrame(dados)

        if df.empty:
            return pd.DataFrame()

        return df

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

    # Botão para atualizar os dados manualmente
    col_top1, col_top2 = st.columns([4, 1])
    with col_top2:
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

    # Carrega os dados
    with st.spinner("A carregar dados do Google Sheets..."):
        df = carregar_dados()

    if df.empty:
        st.warning("Nenhum dado encontrado na planilha ou erro de ligação.")
        return

    # -------------------------------------------------------------------------
    # INDICADORES / METRICAS (KPIs)
    # -------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    total_orcamentos = len(df)
    col1.metric("Total de Orçamentos", total_orcamentos)

    # Tenta calcular o valor total se existir a coluna 'Valor' ou 'Valor (R$)'
    coluna_valor = None
    for col in df.columns:
        if "valor" in col.lower():
            coluna_valor = col
            break

    if coluna_valor:
        # Trata valores numéricos em texto (ex: R$ 1.500,00 -> 1500.00)
        df['valor_limpo'] = (
            df[coluna_valor]
            .astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        df['valor_limpo'] = pd.to_numeric(df['valor_limpo'], errors='coerce').fillna(0)
        valor_total = df['valor_limpo'].sum()
        col2.metric("Valor Total", f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Tenta exibir métricas de Status se existir a coluna 'Status'
    coluna_status = None
    for col in df.columns:
        if "status" in col.lower():
            coluna_status = col
            break

    if coluna_status:
        aprovados = len(df[df[coluna_status].astype(str).str.lower().str.contains("aprovad")])
        pendentes = len(df[df[coluna_status].astype(str).str.lower().str.contains("pendent")])
        col3.metric("Aprovados", aprovados)
        col4.metric("Pendentes", pendentes)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # FILTROS NA BARRA LATERAL
    # -------------------------------------------------------------------------
    st.sidebar.header("🔍 Filtros")
    df_filtrado = df.copy()

    # Remove a coluna temporária do filtro de exibição
    if 'valor_limpo' in df_filtrado.columns:
        df_display = df_filtrado.drop(columns=['valor_limpo'])
    else:
        df_display = df_filtrado.copy()

    if coluna_status:
        opcoes_status = ["Todos"] + list(df[coluna_status].astype(str).unique())
        status_selecionado = st.sidebar.selectbox("Filtrar por Status", opcoes_status)
        if status_selecionado != "Todos":
            df_display = df_display[df_display[coluna_status].astype(str) == status_selecionado]

    # Busca por texto genérica
    busca = st.sidebar.text_input("Buscar por Cliente ou Serviço")
    if busca:
        mask = df_display.astype(str).apply(lambda row: row.str.contains(busca, case=False).any(), axis=1)
        df_display = df_display[mask]

    # -------------------------------------------------------------------------
    # TABELA DE DADOS
    # -------------------------------------------------------------------------
    st.subheader("📋 Registos de Orçamentos")
    st.dataframe(df_display, use_container_width=True)


if __name__ == "__main__":
    main()
