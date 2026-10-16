import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Dashboard e Boletins de Medição", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Acompanhamento, Medições e NFs")


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
        cleaned_headers.append(h_str if h_str else f"Coluna_{i+1}")
            
    return pd.DataFrame(data, columns=cleaned_headers)


def converter_br_para_float(val_str):
    if not val_str or pd.isna(val_str):
        return 0.0
    s = str(val_str).replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def formatar_moeda_br(valor):
    str_val = f"{valor:,.2f}"
    return f"R$ {str_val.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def formatar_numero_br(valor):
    str_val = f"{valor:,.2f}"
    return str_val.replace(",", "X").replace(".", ",").replace("X", ".")


try:
    client = obter_conexao_sheets()
    if not client:
        st.error("Não foi possível conectar ao Google Sheets.")
        st.stop()

    nome_planilha = "Orcamentos"
    if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
        nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

    sheet = client.open(nome_planilha)

    # Carrega abas de Obras, Medições e NFs
    ws_obras = sheet.worksheet("Obras")
    df_obras = ler_worksheet_como_dataframe(ws_obras)

    # Cria abas auxiliares se não existirem no Google Sheets
    try:
        ws_bms = sheet.worksheet("Boletins_Medicao")
    except Exception:
        ws_bms = sheet.add_worksheet(title="Boletins_Medicao", rows="100", cols="10")
        ws_bms.append_row(["Nº Contrato", "Nº BM", "Data Medição", "Área Medida (m²)", "Valor Medido (R$)", "Observações"])

    try:
        ws_nfs = sheet.worksheet("Notas_Fiscais")
    except Exception:
        ws_nfs = sheet.add_worksheet(title="Notas_Fiscais", rows="100", cols="10")
        ws_nfs.append_row(["Nº Contrato", "Nº NF", "Data Emissão", "Valor NF (R$)", "Data Vencimento", "Status Pagamento", "Comprovante/Obs"])

    df_bms = ler_worksheet_como_dataframe(ws_bms)
    df_nfs = ler_worksheet_como_dataframe(ws_nfs)

    if not df_obras.empty and "Nº Contrato" in df_obras.columns:
        # Seletor de Obras
        lista_contratos = df_obras["Nº Contrato"].unique().tolist()
        
        st.sidebar.header("🔍 Filtro do Dashboard")
        contrato_sel = st.sidebar.selectbox("Selecione a Obra / Contrato:", lista_contratos)

        # Dados da Obra Selecionada
        row_obra = df_obras[df_obras["Nº Contrato"] == contrato_sel].iloc[0]
        cliente_nome = row_obra.get("Cliente", "N/I")
        num_orc = row_obra.get("Nº Orçamento", "N/I")
        
        area_total = converter_br_para_float(row_obra.get("Área Total (m²)", 0))
        area_exec = converter_br_para_float(row_obra.get("Área Executada (m²)", 0))
        area_rest = max(0.0, area_total - area_exec)
        pct_exec = (area_exec / area_total * 100) if area_total > 0 else 0.0

        st.markdown(f"### 🏗️ Obra: **{contrato_sel}** | Cliente: **{cliente_nome}**")
        st.caption(f"Orçamento Origem: {num_orc} | Fase Atual: **{row_obra.get('Fase da Obra', 'Em Execução')}** | Pagamento: **{row_obra.get('Status de Pagamento', 'Em Dia')}**")

        st.markdown("---")

        # --- SEÇÃO 1: CARDS E INDICADORES KPI ---
        c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)

        # Filtrar BMs e NFs desta obra
        bms_obra = df_bms[df_bms["Nº Contrato"] == contrato_sel] if not df_bms.empty and "Nº Contrato" in df_bms.columns else pd.DataFrame()
        nfs_obra = df_nfs[df_nfs["Nº Contrato"] == contrato_sel] if not df_nfs.empty and "Nº Contrato" in df_nfs.columns else pd.DataFrame()

        total_bm_rs = sum([converter_br_para_float(v) for v in bms_obra["Valor Medido (R$)"].tolist()]) if not bms_obra.empty else 0.0
        total_nf_rs = sum([converter_br_para_float(v) for v in nfs_obra["Valor NF (R$)"].tolist()]) if not nfs_obra.empty else 0.0

        c_kpi1.metric("Área Total Contratada", f"{formatar_numero_br(area_total)} m²")
        c_kpi2.metric("Área Executada / Medida", f"{formatar_numero_br(area_exec)} m²", f"{pct_exec:.1f}%")
        c_kpi3.metric("Total em BMs Medidos", formatar_moeda_br(total_bm_rs))
        c_kpi4.metric("Total de NFs Emitidas", formatar_moeda_br(total_nf_rs))

        st.markdown("---")

        # --- SEÇÃO 2: GRÁFICOS VISUAIS ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("📈 Avanço Físico ($m^2$)")
            fig_donut = go.Figure(data=[go.Pie(
                labels=['Executado', 'A Executar'],
                values=[area_exec, area_rest],
                hole=.5,
                marker_colors=['#004d00', '#e0e0e0']
            )])
            fig_donut.update_layout(title_text=f"Progresso da Obra ({pct_exec:.1f}% Concluído)", height=320)
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_g2:
            st.subheader("💵 Comparativo de Faturamento")
            df_chart_fin = pd.DataFrame({
                "Categoria": ["Valor Medido (BMs)", "NFs Emitidas"],
                "Valor (R$)": [total_bm_rs, total_nf_rs]
            })
            fig_bar = px.bar(
                df_chart_fin, x="Categoria", y="Valor (R$)",
                color="Categoria",
                color_discrete_sequence=['#004d00', '#2e7d32'],
                text_auto='.2s'
            )
            fig_bar.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # --- SEÇÃO 3: ABAS DE BOLETIM DE MEDIÇÃO (BM) E NOTAS FISCAIS (NFs) ---
        tab_bm, tab_nf = st.tabs(["📋 Boletins de Medição (BM)", "📄 Notas Fiscais e Pagamentos"])

        # TAB 3.1: BOLETIM DE MEDIÇÃO
        with tab_bm:
            st.subheader("➕ Lançar Novo Boletim de Medição (BM)")
            with st.form("form_bm"):
                col_bm1, col_bm2, col_bm3 = st.columns(3)
                with col_bm1:
                    num_bm = st.text_input("Nº do BM", value=f"BM-0{len(bms_obra)+1 if not bms_obra.empty else 1}")
                    data_bm = st.date_input("Data da Medição", datetime.now())
                with col_bm2:
                    qtd_medida = st.number_input("Área Medida neste BM (m²)", min_value=0.0, step=500.0)
                    val_medido = st.number_input("Valor Correspondente (R$)", min_value=0.0, step=1000.0)
                with col_bm3:
                    obs_bm = st.text_area("Observações da Medição", "Medição quinzenal do trecho executado.")

                btn_salvar_bm = st.form_submit_button("💾 Salvar Boletim de Medição", use_container_width=True)

                if btn_salvar_bm:
                    if qtd_medida <= 0 or val_medido <= 0:
                        st.error("Informe a metragem e o valor medido corretamente.")
                    else:
                        dados_bm_linha = [
                            contrato_sel,
                            num_bm.strip(),
                            data_bm.strftime("%d/%m/%Y"),
                            formatar_numero_br(qtd_medida),
                            formatar_moeda_br(val_medido),
                            obs_bm.strip()
                        ]
                        ws_bms.append_row(dados_bm_linha)
                        st.success(f"Boletim '{num_bm}' salvo com sucesso!")
                        st.rerun()

            st.markdown("##### 📜 Histórico de BMs da Obra")
            if not bms_obra.empty:
                st.dataframe(bms_obra, use_container_width=True)
            else:
                st.info("Nenhum Boletim de Medição lançado para esta obra ainda.")

        # TAB 3.2: NOTAS FISCAIS E PAGAMENTOS
        with tab_nf:
            st.subheader("➕ Lançar Nova Nota Fiscal (NF)")
            with st.form("form_nf"):
                col_nf1, col_nf2, col_nf3 = st.columns(3)
                with col_nf1:
                    num_nf = st.text_input("Nº da Nota Fiscal", "NF-001")
                    data_emissao = st.date_input("Data de Emissão", datetime.now())
                with col_nf2:
                    val_nf = st.number_input("Valor da NF (R$)", min_value=0.0, step=1000.0)
                    data_venc = st.date_input("Data de Vencimento", datetime.now())
                with col_nf3:
                    st_pag = st.selectbox("Status de Pagamento", ["Aguardando Pagamento", "Pago", "Atrasado", "Cancelado"])
                    obs_nf = st.text_input("Observações / Nº do Pedido", "Ref. Medição 01")

                btn_salvar_nf = st.form_submit_button("💾 Registar Nota Fiscal", use_container_width=True)

                if btn_salvar_nf:
                    if val_nf <= 0 or not num_nf.strip():
                        st.error("Informe os dados da Nota Fiscal corretamente.")
                    else:
                        dados_nf_linha = [
                            contrato_sel,
                            num_nf.strip(),
                            data_emissao.strftime("%d/%m/%Y"),
                            formatar_moeda_br(val_nf),
                            data_venc.strftime("%d/%m/%Y"),
                            st_pag,
                            obs_nf.strip()
                        ]
                        ws_nfs.append_row(dados_nf_linha)
                        st.success(f"Nota Fiscal '{num_nf}' cadastrada com sucesso!")
                        st.rerun()

            st.markdown("##### 📜 Histórico de Notas Fiscais e Pagamentos")
            if not nfs_obra.empty:
                st.dataframe(nfs_obra, use_container_width=True)
            else:
                st.info("Nenhuma Nota Fiscal registrada para esta obra ainda.")

    else:
        st.warning("Nenhuma obra cadastrada na planilha de Obras para exibir no Dashboard.")

except Exception as e:
    st.error(f"Erro ao carregar os dados no Dashboard: {e}")
