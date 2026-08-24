from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.recibos import ReciboCreate, ReciboUpdate
from fpdf import FPDF
import io
import re

router = APIRouter()

MESES = ['', 'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

MESES_ABREV = ['', 'jan.', 'fev.', 'mar.', 'abr.', 'mai.', 'jun.',
               'jul.', 'ago.', 'set.', 'out.', 'nov.', 'dez.']

TARIFA_ENERGISA_FALLBACK = 1.05


def _get_tarifa_energisa(sb) -> float:
    """Busca a tarifa da Energisa configurada em `configuracoes`.
    Usa um valor de fallback se a tabela/linha ainda nao existir."""
    result = (
        sb.table("configuracoes")
        .select("valor")
        .eq("chave", "tarifa_energisa_kwh")
        .execute()
    )
    if result.data:
        try:
            return float(result.data[0]["valor"])
        except (TypeError, ValueError):
            pass
    return TARIFA_ENERGISA_FALLBACK


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

    result = query.order("created_at", desc=True).limit(2000).execute()
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

    # Buscar faturas ja pagas do cliente no mes (recibo documenta pagamento ja recebido,
    # nao marca fatura como paga sozinho - mesma regra do gerar-lote)
    faturas = (
        sb.table("faturas")
        .select("id")
        .eq("cliente_id", req.cliente_id)
        .eq("mes_referencia", str(req.mes_referencia))
        .eq("status", "paga")
        .execute()
    )
    if not faturas.data:
        raise HTTPException(
            status_code=400,
            detail="Marque as faturas como pagas antes de gerar o recibo",
        )

    # Calcular economia
    tarifa = _get_tarifa_energisa(sb)
    economia_mensal = _calcular_economia(sb, req.cliente_id, str(req.mes_referencia), tarifa)
    economia_ano = _calcular_economia_ano(sb, req.cliente_id, req.mes_referencia.year, tarifa)

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
    recibo_id = result.data[0]["id"]

    # Registra os itens do recibo (as faturas que ele cobre) - mesmo mecanismo
    # usado pelo gerar-lote, pra manter consistencia (permite excluir/exportar
    # PDF corretamente mesmo se um dia esse cliente tiver mais de uma fatura no mes)
    itens = [{"recibo_id": recibo_id, "fatura_id": f["id"]} for f in faturas.data]
    sb.table("recibo_itens").insert(itens).execute()

    return result.data[0]


@router.post("/gerar-lote")
async def gerar_recibos_lote(
    mes_referencia: str = Query(...),
    user: dict = Depends(require_permission("recibos", "criar")),
):
    """Gera recibos consolidados por titular para o mes.

    Um titular pode ter varias UCs cadastradas (varios registros de `cliente`,
    um por UC). Agrupa as faturas pagas do mes por titular - mesmo CPF/CNPJ
    (normalizado) dentro da mesma usina - e gera 1 recibo so por titular,
    cobrindo todas as UCs dele, no mesmo formato do recibo usado antes do
    sistema (varias UCs, 1 valor total, 1 economia).
    """
    sb = get_supabase_admin()

    faturas_pagas = (
        sb.table("faturas")
        .select("id, cliente_id, valor_final, kwh_injetado, clientes(cpf_cnpj, usina_id, item)")
        .eq("mes_referencia", mes_referencia)
        .eq("status", "paga")
        .execute()
    )
    if not faturas_pagas.data:
        return {"message": "0 recibo(s) gerado(s)"}

    def titular_key(fatura):
        cliente = fatura.get("clientes") or {}
        cpf_norm = re.sub(r"\D", "", cliente.get("cpf_cnpj") or "")
        usina_id = cliente.get("usina_id")
        # sem CPF cadastrado: nao agrupa com ninguem, fica sozinho no proprio grupo
        return (usina_id, cpf_norm or f"sem-cpf-{fatura['cliente_id']}")

    grupos = {}
    for f in faturas_pagas.data:
        grupos.setdefault(titular_key(f), []).append(f)

    cliente_ids_todos = [f["cliente_id"] for f in faturas_pagas.data]
    ano = int(mes_referencia.split("-")[0])
    tarifa = _get_tarifa_energisa(sb)

    # Verificar quais clientes ja tem recibo no mes (uma unica query em lote)
    existentes = (
        sb.table("recibos")
        .select("cliente_id")
        .in_("cliente_id", cliente_ids_todos)
        .eq("mes_referencia", mes_referencia)
        .execute()
    )
    ja_tem_recibo = {r["cliente_id"] for r in existentes.data or []}

    gerados = 0
    for faturas_grupo in grupos.values():
        cliente_ids_grupo = [f["cliente_id"] for f in faturas_grupo]

        # pula o grupo inteiro se qualquer UC dele ja tiver recibo esse mes
        if any(cid in ja_tem_recibo for cid in cliente_ids_grupo):
            continue

        valor_pago = sum(f["valor_final"] or 0 for f in faturas_grupo)
        economia_mensal = _somar_economia(faturas_grupo, tarifa)

        faturas_ano = (
            sb.table("faturas")
            .select("kwh_injetado, valor_final")
            .in_("cliente_id", cliente_ids_grupo)
            .gte("mes_referencia", f"{ano}-01-01")
            .lte("mes_referencia", f"{ano}-12-01")
            .execute()
        )
        economia_ano = _somar_economia(faturas_ano.data or [], tarifa)

        # cliente representante do grupo pro cabecalho do recibo (menor "item";
        # sem item cadastrado, o de menor id)
        representante = min(
            faturas_grupo,
            key=lambda f: (
                (f.get("clientes") or {}).get("item") is None,
                (f.get("clientes") or {}).get("item") or 0,
                f["cliente_id"],
            ),
        )["cliente_id"]

        recibo = sb.table("recibos").insert({
            "cliente_id": representante,
            "mes_referencia": mes_referencia,
            "data_pagamento": mes_referencia,
            "valor_pago": valor_pago,
            "economia_mensal": economia_mensal,
            "economia_acumulada_ano": economia_ano,
            "forma_pagamento": "PIX",
        }).execute()
        recibo_id = recibo.data[0]["id"]

        itens = [{"recibo_id": recibo_id, "fatura_id": f["id"]} for f in faturas_grupo]
        sb.table("recibo_itens").insert(itens).execute()

        gerados += 1

    return {"message": f"{gerados} recibo(s) gerado(s)"}


@router.delete("/{recibo_id}")
async def delete_recibo(
    recibo_id: int,
    user: dict = Depends(require_permission("recibos", "excluir")),
):
    sb = get_supabase_admin()

    recibo = sb.table("recibos").select("cliente_id, mes_referencia").eq("id", recibo_id).single().execute()
    if not recibo.data:
        raise HTTPException(status_code=404, detail="Recibo nao encontrado")

    itens = sb.table("recibo_itens").select("fatura_id").eq("recibo_id", recibo_id).execute()
    fatura_ids = [i["fatura_id"] for i in itens.data or []]

    sb.table("recibos").delete().eq("id", recibo_id).execute()

    # Reverte pra pendente as faturas que esse recibo tinha marcado como pagas
    if fatura_ids:
        sb.table("faturas").update({"status": "pendente"}).in_("id", fatura_ids).eq("status", "paga").execute()
    else:
        # recibo antigo, gerado antes de existir recibo_itens - comportamento anterior
        sb.table("faturas").update({"status": "pendente"}).eq(
            "cliente_id", recibo.data["cliente_id"]
        ).eq("mes_referencia", recibo.data["mes_referencia"]).eq("status", "paga").execute()

    return {"message": "Recibo excluido"}


@router.get("/pdf/{recibo_id}")
async def exportar_recibo_pdf(
    recibo_id: int,
    user: dict = Depends(require_permission("recibos", "visualizar")),
):
    """Gera PDF do recibo no formato da planilha (LAC Solar)."""
    sb = get_supabase_admin()

    recibo = sb.table("recibos").select("*").eq("id", recibo_id).single().execute()
    if not recibo.data:
        raise HTTPException(status_code=404, detail="Recibo nao encontrado")

    r = recibo.data
    cliente = sb.table("clientes").select("*").eq("id", r["cliente_id"]).single().execute()
    c = cliente.data

    # Recibos gerados apos a consolidacao por titular tem `recibo_itens` -
    # usa exatamente essas faturas (podem ser de varias UCs/clientes). Recibos
    # antigos nao tem: cai no comportamento anterior (faturas do cliente_id no mes).
    itens = sb.table("recibo_itens").select("fatura_id").eq("recibo_id", recibo_id).execute()
    fatura_ids = [i["fatura_id"] for i in itens.data or []]

    faturas_query = sb.table("faturas").select("*, clientes(nome_uc, numero_uc, poste, item)")
    if fatura_ids:
        faturas_query = faturas_query.in_("id", fatura_ids)
    else:
        faturas_query = (
            faturas_query
            .eq("cliente_id", r["cliente_id"])
            .eq("mes_referencia", r["mes_referencia"])
        )
    faturas = faturas_query.execute()

    linhas = sorted(
        faturas.data or [],
        key=lambda f: (
            (f.get("clientes") or {}).get("item") is None,
            (f.get("clientes") or {}).get("item") or 0,
            f["id"],
        ),
    )

    mes_ref = r["mes_referencia"]
    ano = int(mes_ref.split("-")[0])
    mes = int(mes_ref.split("-")[1])
    mes_nome = MESES[mes]
    mes_abrev = MESES_ABREV[mes]

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # === FAIXA DO TOPO: "logo" em texto nos cantos + 4 caixas destacadas ===
    def logo_texto(x):
        pdf.set_xy(x, 8)
        pdf.set_fill_color(255, 193, 7)  # solar-500, cor da marca
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(22, 10, "LAC SOLAR", border=0, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)

    logo_texto(10)
    logo_texto(176)

    caixas = [
        ("Recibo:", f"{mes_abrev}-{str(ano)[2:]}"),
        ("Valor:", f"R$ {r['valor_pago']:.2f}"),
        ("Vencimento:", f"DIA {c.get('dia_vencimento', 5)}"),
        ("Valor (kwh):", f"R$ {c.get('valor_kwh', 0.75):.2f}"),
    ]
    caixa_w = 33
    x = 35
    for label, valor in caixas:
        pdf.set_xy(x, 8)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.cell(caixa_w, 4, label, align="C")
        pdf.set_xy(x, 12)
        pdf.set_fill_color(204, 229, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(caixa_w, 6, valor, border=1, fill=True, align="C")
        x += caixa_w + 2

    pdf.set_y(24)
    pdf.set_line_width(0.2)
    pdf.line(10, 24, 200, 24)

    # === PRODUTOR / RECEBEDOR ===
    pdf.set_y(28)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 4.5, "PRODUTOR ENERGETICO: LAC Solar Ltda", ln=True)
    pdf.cell(0, 4.5, f"RECEBEDOR ENERGETICO: {c.get('nome', '')}", ln=True)
    pdf.cell(0, 4.5, f"CPF: {c.get('cpf_cnpj', '')}", ln=True)
    pdf.ln(3)

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

    # Dados das faturas (1 linha por UC)
    pdf.set_font("Helvetica", "", 6.5)
    total_injetado = 0
    total_saldo = 0
    total_valor = 0

    for f in linhas:
        cliente_uc = f.get("clientes") or {}
        nome_uc = cliente_uc.get("nome_uc") or ""
        poste = cliente_uc.get("poste")
        if poste:
            nome_uc = f"{nome_uc} (poste {poste})"
        numero_uc = cliente_uc.get("numero_uc") or ""
        lei_ini = f"{f['leitura_inicial']:.0f}" if f.get("leitura_inicial") else ""
        lei_fin = f"{f['leitura_final']:.0f}" if f.get("leitura_final") else ""
        consumo = f"{f['consumo_kwh']:.0f}" if f.get("consumo_kwh") else ""
        injetado = f"{f['kwh_injetado']:.0f}" if f.get("kwh_injetado") else "0"
        saldo = f"{f['saldo_kwh']:.0f}" if f.get("saldo_kwh") else "0"
        valor = f"{f['valor_final']:.2f}" if f.get("valor_final") else "0.00"

        total_injetado += f.get("kwh_injetado") or 0
        total_saldo += f.get("saldo_kwh") or 0
        total_valor += f.get("valor_final") or 0

        pdf.cell(cols[0][1], 4.5, nome_uc[:28], border=1)
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


def _somar_economia(faturas, tarifa_energisa):
    """Soma a economia (kwh injetado * tarifa Energisa - valor pago) de uma
    lista de faturas, sem separar por cliente - usada quando o recibo
    consolida varias UCs de um mesmo titular."""
    total = 0
    for f in faturas:
        kwh = f.get("kwh_injetado") or 0
        valor_pago = f.get("valor_final") or 0
        total += kwh * tarifa_energisa - valor_pago
    return round(total, 2)


def _calcular_economia(sb, cliente_id, mes_referencia, tarifa_energisa):
    """Calcula economia do mes (diferenca entre tarifa Energisa e valor pago)."""
    faturas = (
        sb.table("faturas")
        .select("kwh_injetado, valor_final")
        .eq("cliente_id", cliente_id)
        .eq("mes_referencia", mes_referencia)
        .execute()
    )
    return _somar_economia(faturas.data or [], tarifa_energisa)


def _calcular_economia_ano(sb, cliente_id, ano, tarifa_energisa):
    """Calcula economia acumulada no ano."""
    faturas = (
        sb.table("faturas")
        .select("kwh_injetado, valor_final")
        .eq("cliente_id", cliente_id)
        .gte("mes_referencia", f"{ano}-01-01")
        .lte("mes_referencia", f"{ano}-12-01")
        .execute()
    )
    return _somar_economia(faturas.data or [], tarifa_energisa)
