import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="Gestão de Obras e Custos", page_icon="👷", layout="wide")

st.title("👷 Gestão de Obras e Calculadora de Custos")

# Criando abas para organizar as funções
tab_gestao, tab_calculadora = st.tabs(["📋 Gestão de Status e Obras", "🧮 Calculadora de Custos (Hidrossemeadura)"])


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


# ==============================================================================
# TAB 1: GESTÃO DE STATUS E OBRAS
# ==============================================================================
with tab_gestao:
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
            ws_orcamentos = sheet.worksheet("Orcamentos")
        except Exception:
            ws_orcamentos = sheet.get_worksheet(0)

        dados_orcamentos = ws_orcamentos.get_all_records()
        df_orc = pd.DataFrame(dados_orcamentos) if dados_orcamentos else pd.DataFrame()

        try:
            ws_obras = sheet.worksheet("Obras")
        except Exception:
            ws_obras = sheet.add_worksheet(title="Obras", rows="100", cols="20")
            ws_obras.append_row([
                "Nº Orçamento", "Cliente", "Nº Contrato", 
                "Fase da Obra", "Status de Pagamento", "Observações"
            ])

        dados_obras = ws_obras.get_all_records()
        df_obras = pd.DataFrame(dados_obras) if dados_obras else pd.DataFrame(columns=[
            "Nº Orçamento", "Cliente", "Nº Contrato", 
            "Fase da Obra", "Status de Pagamento", "Observações"
        ])

        if not df_orc.empty:
            col_num_orc = "Nº Orçamento" if "Nº Orçamento" in df_orc.columns else df_orc.columns[0]
            col_cliente = "Cliente" if "Cliente" in df_orc.columns else df_orc.columns[1]
            col_status_orc = "Status" if "Status" in df_orc.columns else df_orc.columns[6]

            lista_num_orc = [str(val).strip() for val in df_orc[col_num_orc].tolist()]
            opcoes_status_orc = ["Pendente", "Negociação", "Revisada", "Concretizada"]

            st.subheader("⚙️ Alterar Status do Orçamento na Planilha Principal")
            col_s1, col_s2, col_s3 = st.columns([2, 2, 1])

            with col_s1:
                orc_selecionado_status = st.selectbox(
                    "Selecione o Nº do Orçamento para Mudar Status", 
                    lista_num_orc,
                    key="select_orc_status"
                )

            idx_sel = lista_num_orc.index(orc_selecionado_status)
            status_atual = str(df_orc.iloc[idx_sel][col_status_orc]).strip()

            idx_status_padrao = 0
            for i, opt in enumerate(opcoes_status_orc):
                if opt.lower() == status_atual.lower():
                    idx_status_padrao = i
                    break

            with col_s2:
                novo_status_orc = st.selectbox(
                    "Novo Status do Orçamento", 
                    opcoes_status_orc, 
                    index=idx_status_padrao,
                    key=f"status_select_{orc_selecionado_status}"
                )

            with col_s3:
                st.write(" ")
                st.write(" ")
                if st.button("🔄 Atualizar Status", use_container_width=True):
                    try:
                        linha_sheets = idx_sel + 2
                        col_idx = df_orc.columns.get_loc(col_status_orc) + 1
                        ws_orcamentos.update_cell(linha_sheets, col_idx, novo_status_orc)
                        st.success(f"Status do Orçamento '{orc_selecionado_status}' alterado para '{novo_status_orc}'!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro ao atualizar status: {ex}")

            st.markdown("---")

            st.subheader("📝 Cadastrar / Atualizar Dados da Obra Concretizada")

            df_concretizados = df_orc[df_orc[col_status_orc].astype(str).str.strip().str.lower() == "concretizada"]

            if df_concretizados.empty:
                st.warning("Nenhum orçamento está marcado como 'Concretizada' no momento.")
            else:
                opcoes_concretizados = []
                mapa_clientes = {}
                for _, row in df_concretizados.iterrows():
                    num_o = str(row[col_num_orc]).strip()
                    cli = str(row[col_cliente]).strip() if col_cliente in row else ""
                    rotulo = f"{num_o} - {cli}" if cli else num_o
                    opcoes_concretizados.append(rotulo)
                    mapa_clientes[num_o] = cli

                with st.form("form_obra"):
                    col_a, col_b = st.columns(2)

                    with col_a:
                        selecionado = st.selectbox("Selecione o Orçamento Concretizado", opcoes_concretizados)
                        num_orc_sel = selecionado.split(" - ")[0].strip()
                        cliente_sel = mapa_clientes.get(num_orc_sel, "")

                        registro_existente = {}
                        if not df_obras.empty and "Nº Orçamento" in df_obras.columns:
                            match = df_obras[df_obras["Nº Orçamento"].astype(str).str.strip() == num_orc_sel]
                            if not match.empty:
                                registro_existente = match.iloc[0].to_dict()

                        num_contrato = st.text_input(
                            "Nº do Contrato", 
                            value=str(registro_existente.get("Nº Contrato", ""))
                        )

                    with col_b:
                        fases_opcoes = ["Início / Mobilização", "Execução", "Fase Final / Acabamento", "Concluída", "Pausada"]
                        fase_atual = str(registro_existente.get("Fase da Obra", "Início / Mobilização")).strip()
                        idx_fase = fases_opcoes.index(fase_atual) if fase_atual in fases_opcoes else 0

                        fase_obra = st.selectbox("Fase da Obra", fases_opcoes, index=idx_fase)

                        pag_opcoes = ["Aguardando Sinal", "Parcialmente Pago", "Em Dia", "Atrasado", "Quitado"]
                        pag_atual = str(registro_existente.get("Status de Pagamento", "Aguardando Sinal")).strip()
                        idx_pag = pag_opcoes.index(pag_atual) if pag_atual in pag_opcoes else 0

                        status_pagamento = st.selectbox("Status de Pagamento", pag_opcoes, index=idx_pag)

                    obs = st.text_area(
                        "Observações Gerais / Histórico de Medições", 
                        value=str(registro_existente.get("Observações", ""))
                    )

                    submeter = st.form_submit_button("💾 Salvar Dados da Obra")

                    if submeter:
                        if not num_contrato.strip():
                            st.error("Por favor, informe o Nº do Contrato antes de salvar.")
                        else:
                            try:
                                todas_obras = ws_obras.get_all_records()
                                linha_encontrada = None

                                for idx, row in enumerate(todas_obras, start=2):
                                    if str(row.get("Nº Orçamento")).strip() == num_orc_sel:
                                        linha_encontrada = idx
                                        break

                                dados_novos = [
                                    num_orc_sel,
                                    cliente_sel,
                                    num_contrato.strip(),
                                    fase_obra,
                                    status_pagamento,
                                    obs.strip()
                                ]

                                if linha_encontrada:
                                    ws_obras.update(f"A{linha_encontrada}:F{linha_encontrada}", [dados_novos])
                                    st.success(f"Obra referente ao orçamento '{num_orc_sel}' atualizada com sucesso!")
                                else:
                                    ws_obras.append_row(dados_novos)
                                    st.success(f"Obra referente ao orçamento '{num_orc_sel}' cadastrada com sucesso!")

                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro ao guardar dados no Google Sheets: {ex}")

            st.markdown("---")

            st.subheader("📋 Painel Geral de Acompanhamento das Obras")
            dados_obras_atualizados = ws_obras.get_all_records()
            if dados_obras_atualizados:
                df_painel_obras = pd.DataFrame(dados_obras_atualizados)
                st.dataframe(df_painel_obras, use_container_width=True)
            else:
                st.info("Nenhuma obra cadastrada até ao momento.")

        else:
            st.info("Nenum orçamento encontrado na planilha.")

    except Exception as e:
        st.error(f"Erro ao ligar ao Google Sheets: {e}")


# ==============================================================================
# TAB 2: CALCULADORA DE CUSTOS DE HIDROSSEMEADURA (SELETOR DE SEMENTES)
# ==============================================================================
with tab_calculadora:
    st.header("🧮 Calculadora de Composição de Custos e Formação de Preço")
    st.markdown("Simule os custos operacionais, escolha a mistura de sementes e insumos, e calcule o preço por m² baseado na metodologia da **Amazon Paisagística**.")

    # BANCO DE DADOS DE INSUMOS E SEMENTES (DA PLANILHA EXCEL)
    BANCO_INSUMOS = {
        "Semente Pensacola": {"preco": 92.00, "base_padrao": 40.0},
        "Semente Batatais": {"preco": 116.67, "base_padrao": 40.0},
        "Sementes Ruzizienses": {"preco": 17.76, "base_padrao": 30.0},
        "Sementes Piatã": {"preco": 15.17, "base_padrao": 30.0},
        "Semente de Painço": {"preco": 48.33, "base_padrao": 20.0},
        "Mulch": {"preco": 4.75, "base_padrao": 210.0},
        "Terra Mulch": {"preco": 9.00, "base_padrao": 200.0},
        "NPK": {"preco": 8.67, "base_padrao": 50.0},
        "Gesso": {"preco": 2.75, "base_padrao": 40.0},
    }

    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        st.subheader("📐 Parâmetros da Obra")
        area_total_m2 = st.number_input("Área Total da Obra (m²)", min_value=100.0, value=15000.0, step=500.0)
        produtividade_dia = st.number_input("Produtividade Diária (m²/dia)", min_value=500.0, value=2000.0, step=500.0)
        dias_estimados = area_total_m2 / produtividade_dia if produtividade_dia > 0 else 1.0
        st.info(f"⏱ **Dias Estimados:** {dias_estimados:.1f} dia(s)")

    with col_p2:
        st.subheader("📊 Lucro & Impostos")
        margem_lucro_pct = st.number_input("Margem de Lucro Desejada (%)", min_value=0.0, max_value=100.0, value=40.0, step=5.0) / 100.0
        imposto_simples_pct = st.number_input("Imposto Simples Nacional (%)", min_value=0.0, max_value=50.0, value=10.0, step=1.0) / 100.0

    with col_p3:
        st.subheader("🚜 Equipe e Veículos")
        mo_diaria = st.number_input("Custo Diário da Equipe (R$/dia)", min_value=0.0, value=1370.91, step=100.0)
        logistica_diaria = st.number_input("Custo Diário Logística/Diesel (R$/dia)", min_value=0.0, value=2779.40, step=100.0)

    st.markdown("---")
    st.subheader("🌱 Seleção da Mistura de Sementes e Insumos (Base: 2.000 m²)")

    # Seletor multi-escolha dos insumos/sementes desejados
    insumos_selecionados = st.multiselect(
        "Selecione as sementes e insumos para esta composição:",
        options=list(BANCO_INSUMOS.keys()),
        default=["Semente Pensacola", "Mulch", "NPK", "Gesso"]
    )

    # Monta a tabela editável dinamicamente com base nas escolhas do usuário
    dados_tabela = []
    for item in insumos_selecionados:
        info = BANCO_INSUMOS[item]
        dados_tabela.append({
            "Item": item,
            "Base (kg)": info["base_padrao"],
            "Preço R$/kg": info["preco"]
        })

    if dados_tabela:
        df_insumos_edit = st.data_editor(
            pd.DataFrame(dados_tabela),
            num_rows="dynamic",
            use_container_width=True,
            key="editor_insumos_dinamico"
        )

        fator_escala = area_total_m2 / 2000.0
        df_insumos_edit["Qtd Necessária (kg)"] = df_insumos_edit["Base (kg)"] * fator_escala
        df_insumos_edit["Total (R$)"] = df_insumos_edit["Qtd Necessária (kg)"] * df_insumos_edit["Preço R$/kg"]
        total_insumos_rs = df_insumos_edit["Total (R$)"].sum()
    else:
        st.warning("Selecione pelo menos uma semente ou insumo para realizar o cálculo.")
        total_insumos_rs = 0.0

    # Cálculo dos Custos Totais Diretos
    total_mo_rs = mo_diaria * dias_estimados
    total_logistica_rs = logistica_diaria * dias_estimados
    custo_direto_total = total_insumos_rs + total_mo_rs + total_logistica_rs

    # Formação do Preço com Markup
    fator_divisor = (1.0 - margem_lucro_pct - imposto_simples_pct)
    preco_venda_total = custo_direto_total / fator_divisor if fator_divisor > 0 else custo_direto_total * 2.0
    preco_por_m2 = preco_venda_total / area_total_m2 if area_total_m2 > 0 else 0.0
    imposto_rs = preco_venda_total * imposto_simples_pct
    lucro_bruto_rs = preco_venda_total - custo_direto_total - imposto_rs

    st.markdown("---")
    st.subheader("📈 Resumo da Composição Financeira")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("Custo Direto Total", f"R$ {custo_direto_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col_r2.metric("Preço de Venda Sugerido", f"R$ {preco_venda_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col_r3.metric("Preço por m²", f"R$ {preco_por_m2:,.2f}/m²".replace(",", "X").replace(".", ",").replace("X", "."))
    col_r4.metric("Lucro Bruto Previsto", f"R$ {lucro_bruto_rs:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Detalhamento em tabela
    df_resumo = pd.DataFrame([
        {"Categoria": "Insumos e Sementes Selecionadas", "Valor Total (R$)": total_insumos_rs, "Custo/m²": total_insumos_rs / area_total_m2 if area_total_m2 > 0 else 0},
        {"Categoria": "Mão de Obra (Equipe + Encargos)", "Valor Total (R$)": total_mo_rs, "Custo/m²": total_mo_rs / area_total_m2 if area_total_m2 > 0 else 0},
        {"Categoria": "Logística & Diesel", "Valor Total (R$)": total_logistica_rs, "Custo/m²": total_logistica_rs / area_total_m2 if area_total_m2 > 0 else 0},
        {"Categoria": "Imposto (Simples Nacional)", "Valor Total (R$)": imposto_rs, "Custo/m²": imposto_rs / area_total_m2 if area_total_m2 > 0 else 0},
        {"Categoria": "Lucro Líquido Previsto", "Valor Total (R$)": lucro_bruto_rs, "Custo/m²": lucro_bruto_rs / area_total_m2 if area_total_m2 > 0 else 0},
    ])

    st.table(df_resumo.style.format({
        "Valor Total (R$)": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "Custo/m²": lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    }))
