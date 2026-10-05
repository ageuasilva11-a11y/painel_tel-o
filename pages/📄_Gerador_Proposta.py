from datetime import datetime
import io
import os
import sys

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import streamlit as st


# --- FUNÇÃO DE RESOLUÇÃO DE CAMINHO ---
def resolve_path(path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)


# --- FUNÇÃO DE FORMATAÇÃO MONETÁRIA BRASILEIRA ---
def formatar_moeda_br(valor):
    """Formata um float para o padrão brasileiro: R$ 23.500,00"""
    str_val = f"{valor:,.2f}"
    str_val = str_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {str_val}"


# --- FUNÇÃO DE FORMATAÇÃO DE NÚMEROS (ÁREA) ---
def formatar_numero_br(valor):
    """Formata quantidade para o padrão brasileiro: 1.000,00"""
    str_val = f"{valor:,.2f}"
    str_val = str_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return str_val


st.set_page_config(
    page_title="Gerador de Proposta Comercial", page_icon="📄", layout="wide"
)

st.title("📄 Gerador de Proposta Comercial e Registo Automático")
st.markdown(
    "Ajuste os dados do cliente, obra e serviços para gerar a proposta em PDF no modelo oficial e gravá-la no Google Sheets."
)

PRECOS_PADRAO = {
    "Serviço de Recuperação Vegetal por Hidrosemeadura para Taludes": 4.10,
    "Hidromanta Projetada": 22.00,
    "Conformação Manual do Relevo (Microcoveamento)": 1.50,
}

if "proposta" not in st.session_state:
    st.session_state.proposta = [
        {
            "Item": 1,
            "Serviço": "Serviço de Recuperação Vegetal por Hidrosemeadura para Taludes de até 45° (Revestimento Vegetal por Hidrojateamento)",
            "Quantidade (m²)": 118600.0,
            "Preço Unitário (R$)": 4.10,
            "Valor Total (R$)": 486260.00,
        },
    ]

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

def guardar_na_planilha(dados_proposta):
    try:
        client = obter_conexao_sheets()
        if not client:
            return False, "Credenciais não encontradas."
        
        nome_planilha = "Orcamentos"
        if "google_sheets" in st.secrets and "planilha_nome" in st.secrets["google_sheets"]:
            nome_planilha = st.secrets["google_sheets"]["planilha_nome"]

        sheet = client.open(nome_planilha)
        try:
            worksheet = sheet.worksheet("Orcamentos")
        except Exception:
            worksheet = sheet.get_worksheet(0)

        worksheet.append_row(dados_proposta)
        return True, "Proposta registada com sucesso na planilha!"
    except Exception as e:
        return False, str(e)


# --- PAINEL LATERAL ---
with st.sidebar:
    st.header("🏢 Dados do Cliente e Obra")
    num_proposta = st.text_input("Nº da Proposta", "0028092026-LCM")
    cliente_nome = st.text_input("Empresa Contratante", "LCM Construção e Comércio S.A.")
    cliente_cnpj = st.text_input("CNPJ Cliente", "19.758.842/0023-40")
    cliente_atencao = st.text_input("A/C (Atenção)", "Jacqueline Carvalho (Equipe de Compras)")
    cliente_email = st.text_input("E-mail Cliente", "jacqueline.carvalho@lcmconstrucao.com.br")
    cliente_fone = st.text_input("Telefone Cliente", "(92) 3085-5885")
    local_obra = st.text_input("Local da Obra", "KM 319 - Careiro Castanho/AM")

    st.markdown("---")
    st.header("⏱ Prazos e Condicionantes")
    prazo_mobilizacao = st.text_input("Prazo de Mobilização", "07 (SETE) dias após assinatura do contrato")
    prazo_execucao = st.text_input("Prazo de Execução", "Conforme cronograma operacional aprovado para a frente de obra")
    prazo_germinacao = st.text_input("Prazo de Germinação", "Iniciada entre 15 a 30 dias. Fechamento total em até 60 dias.")
    garantia_obra = st.text_input("Garantia", "03 (três) meses, contados da data da conclusão do(s) serviço(s).")
    irrigacao_resp = st.text_input("Responsabilidade Irrigação", "Inteira responsabilidade da CONTRATANTE (não inclusos custos com caminhão-pipa ou mangueiras).")

    st.markdown("---")
    st.header("📋 Adicionar Serviço")
    servico_sel = st.selectbox("Serviço", list(PRECOS_PADRAO.keys()) + ["Outro"])
    if servico_sel == "Outro":
        nome_servico = st.text_input("Nome do Serviço")
        preco_padrao = 0.0
    else:
        nome_servico = servico_sel
        preco_padrao = PRECOS_PADRAO[servico_sel]

    qtd_m2 = st.number_input("Área (m²)", min_value=0.0, value=118600.0, step=100.0)
    preco_unit = st.number_input("Preço Unitário (R$/m²)", min_value=0.0, value=preco_padrao, step=0.10)

    if st.button("➕ Adicionar Serviço", use_container_width=True):
        if nome_servico and qtd_m2 > 0 and preco_unit > 0:
            st.session_state.proposta.append({
                "Item": len(st.session_state.proposta) + 1,
                "Serviço": nome_servico,
                "Quantidade (m²)": qtd_m2,
                "Preço Unitário (R$)": preco_unit,
                "Valor Total (R$)": qtd_m2 * preco_unit,
            })
            st.rerun()

    if st.button("🗑️ Limpar Tudo", type="secondary", use_container_width=True):
        st.session_state.proposta = []
        st.rerun()

# --- CORPO DA PÁGINA ---
if st.session_state.proposta:
    df = pd.DataFrame(st.session_state.proposta)
    valor_total = df["Valor Total (R$)"].sum()
    
    # Condições de pagamento fixas (30%, 60%, 10%)
    val_30 = valor_total * 0.30
    val_60 = valor_total * 0.60
    val_10 = valor_total * 0.10

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Proposta Nº {num_proposta} - {cliente_nome}")
        st.dataframe(df, use_container_width=True)
    with col2:
        st.info(f"**Local da Obra:** {local_obra}")
        st.success(f"**Valor Global:** {formatar_moeda_br(valor_total)}\n\n• **30% Sinal:** {formatar_moeda_br(val_30)}\n• **60% Execução:** {formatar_moeda_br(val_60)}\n• **10% Final:** {formatar_moeda_br(val_10)}")

    def gerar_pdf():
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=20, bottomMargin=25)
        elements = []
        styles = getSampleStyleSheet()

        style_title = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=10, leading=12, alignment=1, textColor=colors.HexColor("#004d00"))
        style_header_sub = ParagraphStyle("HeaderSub", parent=styles["Normal"], fontSize=7.5, leading=9.5, alignment=1)
        style_section = ParagraphStyle("SecStyle", parent=styles["Heading2"], fontSize=8.5, leading=10.5, textColor=colors.HexColor("#004d00"), spaceBefore=5, spaceAfter=2)
        style_body = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=7.5, leading=9.5)
        style_bold = ParagraphStyle("BoldStyle", parent=styles["Normal"], fontSize=7.5, leading=9.5, fontName="Helvetica-Bold")
        style_direita = ParagraphStyle("DireitaStyle", parent=styles["Normal"], fontSize=7.5, leading=9.5, alignment=2)
        style_centro = ParagraphStyle("CentroStyle", parent=styles["Normal"], fontSize=7.5, leading=9.5, alignment=1)

        # Cabeçalho Oficial
        logo_path = resolve_path("AMAZON.jpg")
        texto_cabecalho = [
            Paragraph("<b>AMAZON HIDROSSEMEADURA</b>", style_title),
            Paragraph("<b>AMAZON PAISAGISTICA AMBIENTAL</b>", style_bold),
            Paragraph("CNPJ n. 44.246.097/0001-92 | Insc. Municipal: 52393501<br/>Rua Patrai, 385-SI 04-Nova Cidade | CEP: 69.097-305 - Manaus/AM<br/>Fone: +55 92 3085-5885 | 99190-6445 | e-mail: amazonpaisagistica@gmail.com", style_header_sub),
        ]

        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=0.9 * inch, height=0.9 * inch)
            tbl_header = Table([[logo_img, texto_cabecalho]], colWidths=[1.0 * inch, 6.5 * inch])
            tbl_header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER")]))
            elements.append(tbl_header)
        else:
            for item in texto_cabecalho:
                elements.append(item)

        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"<b>PROPOSTA COMERCIAL - N° {num_proposta}</b>", style_title))
        elements.append(Spacer(1, 3))

        # Bloco de Informações do Cliente
        data_atual_str = datetime.now().strftime("%d de %B de %Y")
        dados_cliente = f"""
        <b>Cliente:</b> {cliente_nome}<br/>
        <b>CNPJ:</b> {cliente_cnpj}<br/>
        <b>Att.:</b> {cliente_atencao}<br/>
        <b>Local da Obra:</b> {local_obra}<br/>
        <b>Data:</b> {data_atual_str}<br/>
        <b>E-mail:</b> {cliente_email}
        """
        elements.append(Paragraph(dados_cliente, style_body))
        elements.append(Spacer(1, 4))

        # Tabela de Serviços
        elements.append(Paragraph("<b>RESUMO FINAL / COMPOSIÇÃO DOS SERVIÇOS</b>", style_section))
        table_data = [["Item", "Descrição dos Serviços", "Área (m²)", "Vlr. Unit. (R$)", "Total (R$)"]]
        for row in st.session_state.proposta:
            table_data.append([
                str(row["Item"]),
                row["Serviço"],
                formatar_numero_br(row["Quantidade (m²)"]),
                formatar_moeda_br(row["Preço Unitário (R$)"]),
                formatar_moeda_br(row["Valor Total (R$)"])
            ])
        table_data.append(["", "VALOR GLOBAL DA PROPOSTA", "", "", formatar_moeda_br(valor_total)])

        t = Table(table_data, colWidths=[25, 335, 65, 80, 95])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004d00")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e6ffe6")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 4))

        # Etapas de Execução
        elements.append(Paragraph("<b>ETAPAS DA EXECUÇÃO DOS SERVIÇOS (HIDROSEMEADURA)</b>", style_section))
        etapas_texto = """
        1. Preparação / acerto das áreas.<br/>
        2. Picoteamento / coveamento das áreas.<br/>
        3. Correção do solo com calcário dolomítico.<br/>
        4. Hidrojateamento com revestimento vegetal (lançamento de sementes adaptadas para a região).
        """
        elements.append(Paragraph(etapas_texto, style_body))
        elements.append(Spacer(1, 4))

        # Condições de Pagamento (Fixas: 30%, 60%, 10%)
        elements.append(Paragraph("<b>CONDIÇÕES DE PAGAMENTO E VALORES</b>", style_section))
        pag_texto = f"""
        <b>VALOR TOTAL DA PROPOSTA:</b> {formatar_moeda_br(valor_total)}.<br/>
        • <b>30% do valor total ({formatar_moeda_br(val_30)})</b> na assinatura do contrato para mobilização de funcionários, insumos e equipamentos. (via PIX - CNPJ: 44.246.097/0001-92 - MJ GOMES DE MORAES).<br/>
        • <b>60% do valor total ({formatar_moeda_br(val_60)})</b> na aplicação dos serviços através de emissão de Nota Fiscal Eletrônica e pagamento via Boleto Bancário.<br/>
        • <b>10% do valor total ({formatar_moeda_br(val_10)})</b> no fechamento / medição final através de emissão de Nota Fiscal Eletrônica e pagamento via Boleto Bancário.
        """
        elements.append(Paragraph(pag_texto, style_body))
        elements.append(Spacer(1, 4))

        # Prazos, Condicionantes e Garantia
        elements.append(Paragraph("<b>PRAZOS, CONDICIONANTES E GARANTIA</b>", style_section))
        prazos_tabela_dados = [
            [
                Paragraph(f"<b>Prazo de Mobilização:</b> {prazo_mobilizacao}", style_body),
                Paragraph(f"<b>Prazo de Germinação:</b> {prazo_germinacao}", style_body)
            ],
            [
                Paragraph(f"<b>Prazo de Execução:</b> {prazo_execucao}", style_body),
                Paragraph(f"<b>Garantia:</b> {garantia_obra}", style_body)
            ],
            [
                Paragraph(f"<b>Irrigação:</b> {irrigacao_resp}", style_body),
                Paragraph("<b>Documentação:</b> Enviar Cartão CNPJ, Contrato Social, documentos do representante legal e procuração (se aplicável).", style_body)
            ]
        ]
        t_prazos = Table(prazos_tabela_dados, colWidths=[250, 250])
        t_prazos.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_prazos)
        elements.append(Spacer(1, 6))

        # Aviso de Confidencialidade
        aviso_confidencial = "<font size=6.5><i>Alertamos que o conteúdo da presente Proposta Comercial é CONFIDENCIAL e direcionado única e exclusivamente à empresa acima discriminada, sendo vetada a divulgação, publicação e outros usos desta Proposta Comercial, ou de qualquer parte do seu conteúdo, sem a devida autorização.</i></font>"
        elements.append(Paragraph(aviso_confidencial, style_body))
        elements.append(Spacer(1, 6))

        # Bloco de Assinatura
        bloco_assinatura = [
            Paragraph(f"Manaus/AM, {datetime.now().strftime('%d de %B de %Y')}.", style_direita),
            Spacer(1, 10),
            Paragraph("<b>ASSINADO DIGITALMENTE</b><br/><b>MJ GOMES DE MORAES</b>", style_centro),
            Paragraph("<font size=6 color=grey>A conformidade com a assinatura pode ser verificada em https://serpro.gov.br/assinador-digital</font>", style_centro),
            Spacer(1, 5),
            Paragraph("__________________________________________________<br/><b>AMAZON PAISAGISTICA AMBIENTAL</b><br/>Departamento Comercial / Técnico", style_centro)
        ]
        elements.append(KeepTogether(bloco_assinatura))

        # Função de Rodapé por página
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.drawString(25, 12, "AMAZON PAISAGISTICA AMBIENTAL - Proposta Comercial")
            canvas.drawRightString(595 - 25, 12, f"Página {doc.page} de 1")
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        buffer.seek(0)
        return buffer

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        pdf_bytes = gerar_pdf()
        st.download_button(
            label="📥 Baixar Proposta Comercial em PDF",
            data=pdf_bytes,
            file_name=f"Proposta_{num_proposta}_{cliente_nome.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col_btn2:
        if st.button("🚀 Registar Proposta na Planilha", use_container_width=True):
            data_atual = datetime.now().strftime("%d/%m/%Y")
            
            servicos_str = ", ".join([s["Serviço"] for s in st.session_state.proposta])
            valor_formatado_br = formatar_moeda_br(valor_total)
            
            linha_dados = [
                str(num_proposta),
                str(cliente_nome),
                str(cliente_cnpj),
                str(local_obra),
                str(servicos_str),
                valor_formatado_br,
                "Pendente",
                data_atual
            ]
            
            sucesso, mensagem = guardar_na_planilha(linha_dados)
            if sucesso:
                st.success(mensagem)
            else:
                st.error(f"Erro ao guardar na planilha: {mensagem}")
else:
    st.warning("Adicione pelo menos um serviço na barra lateral para gerar a proposta.")
