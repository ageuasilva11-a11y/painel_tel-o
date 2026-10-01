from datetime import datetime
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


# Função para carregar os dados reais direto do Google Sheets
@st.cache_data(ttl=60)  # Atualiza automaticamente a cada 60 segundos
def carregar_dados_google_sheets():
    try:
        # Lê a folha de cálculo pública ou configurada via st.connection
        # Substitua 'SuaPlanilhaDeOrcamentos' pelo nome exato da aba no Google Sheets
        df = st.conn.read(worksheet="Orcamentos", ttl=60)
        return df
    except Exception as e:
        # Fallback de segurança caso a ligação ainda esteja a ser configurada
        st.warning(
            "A aguardar ligação ao Google Sheets. A exibir dados temporários."
        )
        return pd.DataFrame(
            {
                "Nº Orçamento": ["ORC-2026/01"],
                "Cliente": ["A configurar"],
                "Serviço": ["A ligar ao Google Sheets"],
                "Valor (R$)": [0.0],
                "Status": ["Em Andamento"],
            }
        )


# Alternativamente, para testar rápido com link público do CSV da planilha do Google:
@st.cache_data(ttl=60)
def carregar_dados_csv():
    # Cole aqui o link de publicação em CSV da sua planilha do Google Sheets se preferir método direto
    url_csv = "COLE_AQUI_O_LINK_CSV_DO_GOOGLE_SHEETS_SE_QUISER"
    # return pd.read_csv(url_csv)
    # Por enquanto, mantemos a estrutura pronta para receber os seus dados reais:
    return pd.DataFrame(
        columns=["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)", "Status"]
    )


# Carregando os dados (Pode usar a ligação do Google Sheets do Streamlit)
# Dica: No Streamlit Cloud, configuramos os segredos para ler do Google Sheets de forma privada e segura.
df = (
    carregar_dados_google_sheets()
)  # Ou substitua pela leitura direta do seu ficheiro/Sheets


# Se já tiver os dados a vir da planilha, garantimos que a coluna de valor é numérica:
if not df.empty and "Valor (R$)" in df.columns:
    df["Valor (R$)"] = pd.to_numeric(
        df["Valor (R$)"].astype(str).str.replace("R$", "").str.replace(",", "."),
        errors="coerce",
    ).fillna(0)

# --- MÉTRICAS PRINCIPAIS (KPIs) ---
total_orcamentos = len(df)
valor_total_geral = df["Valor (R$)"].sum() if not df.empty else 0

df_andamento = (
    df[df["Status"].str.contains("Andamento", case=False, na=False)]
    if not df.empty
    else pd.DataFrame()
)
df_concretizado = (
    df[df["Status"].str.contains("Concretizado|Obra", case=False, na=False)]
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
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Nenhum orçamento em andamento registado na planilha.")

with col_tabela2:
    st.subheader("🚀 Obras Concretizadas (Fechadas)")
    if not df_concretizado.empty:
        st.dataframe(
            df_concretizado[["Nº Orçamento", "Cliente", "Serviço", "Valor (R$)"]],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Nenhum orçamento concretizado registado na planilha.")

# Rodapé de atualização automática
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 14px;'>Painel sincronizado com a Base de Dados da Amazon Paisagística Ambiental (Atualização automática a cada 60s).</p>",
    unsafe_allow_html=True,
)