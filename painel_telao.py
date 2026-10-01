from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# Configuração da página para ocupar a largura total (ideal para TVs)
st.set_page_config(
    page_title="Painel de Orçamentos - Amazon Paisagística",
    page_icon="🌱",
    layout="wide",
)

# Estilização CSS personalizada para modo "Telão"
st.markdown(
    """
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Cabeçalho do Telão
st.title("🌱 AMAZON PAISAGÍSTICA AMBIENTAL - PAINEL DE OBRAS")
st.markdown(
    f"**Estado Comercial em Tempo Real** | Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
st.markdown("---")


# Função para carregar os dados reais direto do Google Sheets de forma segura
@st.cache_data(ttl=60)  # Atualiza automaticamente a cada 60 segundos
def carregar_dados_google_sheets():
    try:
        # Lê diretamente as credenciais do TOML plano configurado nos segredos
        credentials_dict = dict(st.secrets["gcp_service_account"])

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=scopes
        )
        client = gspread.authorize(creds)

        # Abre a planilha "Orcamentos" e a aba com o mesmo nome
        sheet = client.open("Orcamentos").worksheet("Orcamentos")
        dados = sheet.get_all_records()

        df = pd.DataFrame(dados)
        if df.empty:
            return pd.DataFrame(
                columns=["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)", "Status"]
            )
        return df

    except Exception as e:
        st.error(
            f"Erro ao ligar ao Google Sheets: {e}. Verifique se partilhou a planilha 'Orcamentos' com o e-mail da conta de serviço."
        )
        return pd.DataFrame(
            columns=["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)", "Status"]
        )


# Carrega os dados reais
df = carregar_dados_google_sheets()

# Tratamento e limpeza da coluna de valores para garantir formato numérico
if not df.empty and "Valor (R$)" in df.columns:
    df["Valor (R$)"] = (
        df["Valor (R$)"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce").fillna(0)

# --- MÉTRICAS PRINCIPAIS (KPIs) ---
total_orcamentos = len(df)
valor_total_geral = df["Valor (R$)"].sum() if not df.empty else 0

df_andamento = (
    df[df["Status"].str.contains("Andamento", case=False, na=False)]
    if not df.empty
    else pd.DataFrame()
)
df_concretizado = (
    df[df["Status"].str.contains("Concretizado|Obra|Fechado", case=False, na=False)]
    if not df.empty
    else pd.DataFrame()
)

valor_andamento = df_andamento["Valor (R$)"].sum() if not df_andamento.empty else 0
valor_concretizado = (
    df_concretizado["Valor (R$)"].sum() if not df_concretizado.empty else 0
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="Total de Propostas",
        value=total_orcamentos,
        delta=f"R$ {valor_total_geral:,.2f}",
    )

with kpi2:
    st.metric(
        label="⏳ Em Andamento (Negociação)",
        value=len(df_andamento),
        delta=f"R$ {valor_andamento:,.2f}",
    )

with kpi3:
    st.metric(
        label="✅ Concretizados (Virou Obra)",
        value=len(df_concretizado),
        delta=f"R$ {valor_concretizado:,.2f}",
    )

with kpi4:
    taxa_conversao = (
        (len(df_concretizado) / total_orcamentos * 100)
        if total_orcamentos > 0
        else 0
    )
    st.metric(label="🎯 Taxa de Conversão", value=f"{taxa_conversao:.1f}%")

st.markdown("---")

# --- TABELAS VISUAIS PARA O TELÃO ---
col_tabela1, col_tabela2 = st.columns(2)

with col_tabela1:
    st.subheader("⏳ Propostas em Andamento (Aguardando Resposta)")
    if not df_andamento.empty:
        st.dataframe(
            df_andamento[["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhum orçamento em andamento registado na planilha.")

with col_tabela2:
    st.subheader("🚀 Obras Concretizadas (Fechadas)")
    if not df_concretizado.empty:
        st.dataframe(
            df_concretizado[["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nenhum orçamento concretizado registado na planilha.")

# Rodapé de atualização automática
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 14px;'>Painel sincronizado com a Base de Dados da Amazon Paisagística Ambiental (Atualização automática a cada 60s).</p>",
    unsafe_allow_html=True,
)
