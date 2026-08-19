from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.recibos import ReciboCreate, ReciboUpdate
from fpdf import FPDF
import io

router = APIRouter()

MESES = ['', 'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


@router.get("/")
async def list_recibos(
    mes_referencia: str = Query(None),
    cliente_id: int = Query(None),
    user: dict = Depends(require_permission("recibos", "visualizar")),
):
    """Lista recibos com filtros."""
    sb = get_supabase_admin()
    query = sb.table("recibos").select("*, clientes(nome, celular, usina_id, usinas(nome))")

    if mes_referencia:
        query = query.eq("mes_referencia", mes_referencia)
    if cliente_id:
        query = query.eq("cliente_id", cliente_id)

    result = query.order("created_at", desc=True).execute()
    return result.data or []


@router.post("/")
async def create_recibo(
    req: ReciboCreate,
    user: dict = Depends(require_permission("recibos", "criar")),
):
    """Cria recibo para um cliente no mes, consolidando todas as faturas."""
    sb = get_supabase_admin()

    # Verificar se ja existe recibo
    existente = (
        sb.table("recibos")
        .select("id")
        .eq("cliente_id", req.cliente_id)
        .eq("mes_referencia", str(req.mes_referencia))
        .execute()
    )
    if existente.data:
        raise HTTPException(status_code=400, detail="Ja existe recibo para este cliente neste mes")

    # Buscar todas as faturas do cliente no mes
    faturas = (
        sb.table("faturas")
        .select("*")
        .eq("cliente_id", req.cliente_id)
        .eq("mes_referencia", str(req.mes_referencia))
        .execute()
    )

    # Marcar faturas como pagas
    for f in faturas.data or []:
        sb.table("faturas").update({"status": "paga"}).eq("id", f["id"]).execute()

    # Calcular economia
    economia_mensal = _calcular_economia(sb, req.cliente_id, str(req.mes_referencia))
    economia_ano = _calcular_economia_ano(sb, req.cliente_id, req.mes_referencia.year)

    data = {
        "cliente_id": req.cliente_id,
        "mes_referencia": str(req.mes_referencia),
        "data_pagamento": str(req.data_pagamento),
        "valor_pago": req.valor_pago,
        "economia_mensal": economia_mensal,
        "economia_acumulada_ano": economia_ano,
        "forma_pagamento": req.forma_pagamento,
        "observacoes": req.observacoes,
    }

    result = sb.table("recibos").insert(data).execute()
    return result.data[0]


@router.post("/gerar-lote")
async def gerar_recibos_lote(
    mes_referencia: str = Query(...),
    user: dict = Depends(require_permission("recibos", "criar")),
):
    """Gera recibos para todos os clientes que tem faturas pagas no mes."""
    sb = get_supabase_admin()

    faturas_pagas = (
        sb.table("faturas")
        .select("cliente_id, valor_final")
        .eq("mes_referencia", mes_referencia)
        .eq("status", "paga")
        .execute()
    )

    # Agrupar por cliente
    clientes_valores = {}
    for f in faturas_pagas.data or []:
        cid = f["cliente_id"]
        if cid not in clientes_valores:
            clientes_valores[cid] = 0
        clientes_valores[cid] += f["valor_final"] or 0

    gerados = 0
    for cliente_id, valor_total in clientes_valores.items():
        # Verificar se ja tem recibo
        existente = (
            sb.table("recibos")
            .select("id")
            .eq("cliente_id", cliente_id)
            .eq("mes_referencia", mes_referencia)
            .execute()
        )
        if existente.data:
            continue

        ano = int(mes_referencia.split("-")[0])
        economia_mensal = _calcular_economia(sb, cliente_id, mes_referencia)
        economia_ano = _calcular_economia_ano(sb, cliente_id, ano)

        sb.table("recibos").insert({
            "cliente_id": cliente_id,
            "mes_referencia": mes_referencia,
            "data_pagamento": mes_referencia,
            "valor_pago": valor_total,
            "economia_mensal": economia_mensal,
            "economia_acumulada_ano": economia_ano,
            "forma_pagamento": "PIX",
        }).execute()
        gerados += 1

    return {"message": f"{gerados} recibo(s) gerado(s)"}


@router.delete("/{recibo_id}")
async def delete_recibo(
    recibo_id: int,
    user: dict = Depends(require_permission("recibos", "excluir")),
):
    sb = get_supabase_admin()
    sb.table("recibos").delete().eq("id", recibo_id).execute()
    return {"message": "Recibo excluido"}


@router.get("/pdf/{recibo_id}")
async def exportar_recibo_pdf(
    recibo_id: int,
    user: dict = Depends(require_permission("recibos", "visualizar")),
):
    """Gera PDF do recibo no formato da planilha."""
    sb = get_supabase_admin()

    recibo = sb.table("recibos").select("*").eq("id", recibo_id).single().execute()
    if not recibo.data:
        raise HTTPException(status_code=404, detail="Recibo nao encontrado")

    r = recibo.data
    cliente = sb.table("clientes").select("*").eq("id", r["cliente_id"]).single().execute()
    c = cliente.data

    # Buscar todas as faturas do cliente no mes
    faturas = (
        sb.table("faturas")
        .select("*, clientes(nome_uc, numero_uc, poste)")
        .eq("cliente_id", r["cliente_id"])
        .eq("mes_referencia", r["mes_referencia"])
        .order("id")
        .execute()
    )

    # Buscar saldo ACM de cada fatura
    # Para simplificar, usamos saldo_kwh da fatura
    mes_ref = r["mes_referencia"]
    ano = int(mes_ref.split("-")[0])
    mes = int(mes_ref.split("-")[1])

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # === CABECALHO ===
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "LAC Solar Ltda", ln=True, align="C")
    pdf.ln(4)

    # === DUAS COLUNAS: Dados do Cliente | Dados do Recibo ===
    y_start = pdf.get_y()
    col_w = 95

    # --- Coluna esquerda: Dados do cliente ---
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(col_w, 5, f"Nome: {c.get('nome', '')}")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(col_w, 4.5, f"CPF/CNPJ: {c.get('cpf_cnpj', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Identidade: {c.get('identidade', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Celular: {c.get('celular', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"E-mail: {c.get('email', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Endereco: {c.get('endereco', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Data da Contratacao: {c.get('data_contratacao', '')}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Valor do Kwh/mes: R$ {c.get('valor_kwh', 0.75):.2f}")
    pdf.ln()
    pdf.cell(col_w, 4.5, f"Data de Vencimento: DIA {c.get('dia_vencimento', 5):02d}")
    pdf.ln()

    y_after_left = pdf.get_y()

    # --- Coluna direita: Dados do recibo ---
    pdf.set_y(y_start)
    pdf.set_x(105)
    pdf.set_font("Helvetica", "B", 8)

    mes_nome = MESES[mes]
    vencimento = f"{c.get('dia_vencimento', 5):02d}/{mes:02d}/{ano}"
    pdf.cell(col_w, 5, f"Recibo: {mes_nome}/{ano}     Valor: R$ {r['valor_pago']:.2f}")
    pdf.ln()
    pdf.set_x(105)
    pdf.cell(col_w, 5, f"Vencimento: {vencimento}")
    pdf.ln()
    pdf.set_x(105)
    pdf.ln()
    pdf.set_x(105)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(col_w, 4.5, "PRODUTOR ENERGETICO: LAC Solar Ltda")
    pdf.ln()
    pdf.set_x(105)
    pdf.cell(col_w, 4.5, f"RECEBEDOR ENERGETICO: {c.get('nome', '')}")
    pdf.ln()
    pdf.set_x(105)
    pdf.cell(col_w, 4.5, f"CPF/CNPJ: {c.get('cpf_cnpj', '')}")
    pdf.ln()
    pdf.set_x(105)
    pdf.cell(col_w, 4.5, f"Valor (kwh): R$ {c.get('valor_kwh', 0.75):.2f}")

    pdf.set_y(max(y_after_left, pdf.get_y()) + 6)

    # === TABELA DE UCs ===
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(240, 240, 240)

    cols = [
        ("Nome da UC", 40),
        ("Numero UC", 22),
        ("Inicial", 18),
        ("Final", 18),
        ("Consumo", 18),
        ("KwH Injetado", 20),
        ("Saldo ACM", 20),
        ("Valor Total", 22),
    ]

    # Cabecalho da tabela
    pdf.cell(cols[0][1] + cols[1][1], 5, "Objeto da Contratacao", border=1, fill=True, align="C")
    pdf.cell(cols[2][1] + cols[3][1] + cols[4][1], 5, "Dados da Leitura", border=1, fill=True, align="C")
    pdf.cell(cols[5][1], 5, "KwH injetado", border=1, fill=True, align="C")
    pdf.cell(cols[6][1], 5, "Saldo ACM(Kwh)", border=1, fill=True, align="C")
    pdf.cell(cols[7][1], 5, "Valor Total", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "B", 6)
    for label, w in cols:
        pdf.cell(w, 5, label, border=1, fill=True, align="C")
    pdf.ln()

    # Dados das faturas
    pdf.set_font("Helvetica", "", 6.5)
    total_injetado = 0
    total_saldo = 0
    total_valor = 0

    for f in faturas.data or []:
        nome_uc = f.get("clientes", {}).get("nome_uc") or ""
        numero_uc = f.get("clientes", {}).get("numero_uc") or ""
        lei_ini = f"{f['leitura_inicial']:.0f}" if f.get("leitura_inicial") else ""
        lei_fin = f"{f['leitura_final']:.0f}" if f.get("leitura_final") else ""
        consumo = f"{f['consumo_kwh']:.0f}" if f.get("consumo_kwh") else ""
        injetado = f"{f['kwh_injetado']:.0f}" if f.get("kwh_injetado") else "0"
        saldo = f"{f['saldo_kwh']:.0f}" if f.get("saldo_kwh") else "0"
        valor = f"{f['valor_final']:.2f}" if f.get("valor_final") else "0.00"

        total_injetado += f.get("kwh_injetado") or 0
        total_saldo += f.get("saldo_kwh") or 0
        total_valor += f.get("valor_final") or 0

        pdf.cell(cols[0][1], 4.5, nome_uc[:25], border=1)
        pdf.cell(cols[1][1], 4.5, numero_uc, border=1, align="C")
        pdf.cell(cols[2][1], 4.5, lei_ini, border=1, align="R")
        pdf.cell(cols[3][1], 4.5, lei_fin, border=1, align="R")
        pdf.cell(cols[4][1], 4.5, consumo, border=1, align="R")
        pdf.cell(cols[5][1], 4.5, injetado, border=1, align="R")
        pdf.cell(cols[6][1], 4.5, saldo, border=1, align="R")
        pdf.cell(cols[7][1], 4.5, f"R$ {valor}", border=1, align="R")
        pdf.ln()

    # Linha de totais
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.cell(cols[0][1] + cols[1][1] + cols[2][1] + cols[3][1] + cols[4][1], 5, "", border=1)
    pdf.cell(cols[5][1], 5, f"{total_injetado:.0f}", border=1, align="R")
    pdf.cell(cols[6][1], 5, f"{total_saldo:.0f}", border=1, align="R")
    pdf.cell(cols[7][1], 5, f"R$ {total_valor:.2f}", border=1, align="R")
    pdf.ln()

    # Economia
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 7)
    economia_mensal = r.get("economia_mensal") or 0
    economia_ano = r.get("economia_acumulada_ano") or 0
    pdf.cell(0, 4.5, f"Economia produzida no mes: R$ {economia_mensal:.2f}", ln=True)
    pdf.cell(0, 4.5, f"No Ano ({ano}): R$ {economia_ano:.2f}", ln=True)

    # Dados para quitacao
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 7)
    pdf.cell(0, 4.5, "Dados para quitacao:", ln=True)
    pdf.set_font("Helvetica", "", 7)
    if c.get("dados_pagamento"):
        pdf.cell(0, 4.5, c["dados_pagamento"], ln=True)
    if c.get("pix"):
        pdf.cell(0, 4.5, c["pix"], ln=True)

    # Assinatura
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4.5, f"Cuiaba-MT, {mes_nome}/{ano}", ln=True, align="R")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "Luiz Antonio de Carvalho", ln=True, align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4.5, "PRODUTOR ENERGETICO", ln=True, align="C")

    # Gerar bytes
    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    nome_arquivo = f"recibo_{c.get('nome', 'cliente').replace(' ', '_')}_{mes_nome}_{ano}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )


def _calcular_economia(sb, cliente_id, mes_referencia):
    """Calcula economia do mes (diferenca entre tarifa Energisa e valor pago)."""
    faturas = (
        sb.table("faturas")
        .select("kwh_injetado, valor_final")
        .eq("cliente_id", cliente_id)
        .eq("mes_referencia", mes_referencia)
        .execute()
    )
    economia = 0
    tarifa_energisa = 1.05  # tarifa media Energisa
    for f in faturas.data or []:
        kwh = f.get("kwh_injetado") or 0
        valor_pago = f.get("valor_final") or 0
        valor_energisa = kwh * tarifa_energisa
        economia += valor_energisa - valor_pago
    return round(economia, 2)


def _calcular_economia_ano(sb, cliente_id, ano):
    """Calcula economia acumulada no ano."""
    faturas = (
        sb.table("faturas")
        .select("kwh_injetado, valor_final")
        .eq("cliente_id", cliente_id)
        .gte("mes_referencia", f"{ano}-01-01")
        .lte("mes_referencia", f"{ano}-12-01")
        .execute()
    )
    economia = 0
    tarifa_energisa = 1.05
    for f in faturas.data or []:
        kwh = f.get("kwh_injetado") or 0
        valor_pago = f.get("valor_final") or 0
        valor_energisa = kwh * tarifa_energisa
        economia += valor_energisa - valor_pago
    return round(economia, 2)