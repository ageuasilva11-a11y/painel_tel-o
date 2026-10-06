import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="Acompanhamento de Obras", page_icon="👷", layout="wide")

st.title("👷 Gestão de Obras Concretizadas e Pagamentos")


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
    if not client:
        st.error("Não foi possível estabelecer ligação com o Google Sheets.")
        st.stop()

    nome_planilha = "Orcamentos"
    if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
        nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

    sheet = client.open(nome_planilha)

    # 1. Carrega aba de Orçamentos
    try:
        ws_orcamentos = sheet.worksheet("Orcamentos")
    except Exception:
        ws_orcamentos = sheet.get_worksheet(0)

    dados_orcamentos = ws_orcamentos.get_all_records()
    df_orc = pd.DataFrame(dados_orcamentos) if dados_orcamentos else pd.DataFrame()

    # 2. Carrega ou cria a aba "Obras" no Google Sheets
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

    # Filtrar orçamentos concretizados
    if not df_orc.empty:
        col_status = "Status" if "Status" in df_orc.columns else df_orc.columns[6]
        col_num_orc = "Nº Orçamento" if "Nº Orçamento" in df_orc.columns else df_orc.columns[0]
        col_cliente = "Cliente" if "Cliente" in df_orc.columns else df_orc.columns[1]

        df_concretizados = df_orc[df_orc[col_status].astype(str).str.strip().str.lower() == "concretizada"]

        if df_concretizados.empty:
            st.warning("Nenhum orçamento concretizado foi encontrado na planilha.")
        else:
            # Lista de orçamentos concretizados para seleção
            opcoes_concretizados = []
            mapa_clientes = {}
            for _, row in df_concretizados.iterrows():
                num_orc = str(row[col_num_orc]).strip()
                cli = str(row[col_cliente]).strip() if col_cliente in row else ""
                rotulo = f"{num_orc} - {cli}" if cli else num_orc
                opcoes_concretizados.append(rotulo)
                mapa_clientes[num_orc] = cli

            st.subheader("📝 Cadastrar / Atualizar Status da Obra")

            with st.form("form_obra"):
                col_a, col_b = st.columns(2)

                with col_a:
                    selecionado = st.selectbox("Selecione o Orçamento Concretizado", opcoes_concretizados)
                    num_orc_sel = selecionado.split(" - ")[0].strip()
                    cliente_sel = mapa_clientes.get(num_orc_sel, "")

                    # Verificar se já existe registo desta obra na aba "Obras"
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
                            # Atualizar se já existir ou inserir nova linha
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
                                # Atualiza linha existente
                                ws_obras.update(f"A{linha_encontrada}:F{linha_encontrada}", [dados_novos])
                                st.success(f"Obra referente ao orçamento '{num_orc_sel}' atualizada com sucesso!")
                            else:
                                # Adiciona nova linha
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
                st.info("Nenhuma obra cadastrada até o momento.")

    else:
        st.info("Nenhum dado encontrado na planilha de orçamentos.")

except Exception as e:
    st.error(f"Erro ao ligar ao Google Sheets: {e}")
