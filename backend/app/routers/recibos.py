from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.recibos import ReciboCreate, ReciboUpdate
from fpdf import FPDF
import io
import re
import tempfile
import os
import zipfile
import shutil

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
    """Gera recibo PPTX a partir do template e retorna PDF ou PPTX."""
    sb = get_supabase_admin()

    recibo = sb.table("recibos").select("*").eq("id", recibo_id).single().execute()
    if not recibo.data:
        raise HTTPException(status_code=404, detail="Recibo nao encontrado")

    r = recibo.data
    cliente = sb.table("clientes").select("*").eq("id", r["cliente_id"]).single().execute()
    c = cliente.data

    # Buscar faturas do recibo
    itens = sb.table("recibo_itens").select("fatura_id").eq("recibo_id", recibo_id).execute()
    fatura_ids = [i["fatura_id"] for i in itens.data or []]

    faturas_query = sb.table("faturas").select("*, clientes(nome_uc, numero_uc, poste, item)")
    if fatura_ids:
        faturas_query = faturas_query.in_("id", fatura_ids)
    else:
        faturas_query = faturas_query.eq("cliente_id", r["cliente_id"]).eq("mes_referencia", r["mes_referencia"])
    faturas = faturas_query.execute()

    linhas = sorted(
        faturas.data or [],
        key=lambda f: ((f.get("clientes") or {}).get("item") is None, (f.get("clientes") or {}).get("item") or 0, f["id"]),
    )

    mes_ref = r["mes_referencia"]
    ano = int(mes_ref.split("-")[0])
    mes = int(mes_ref.split("-")[1])

    MESES_CURTO = ['', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
    MESES_EXTENSO = ['', 'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho',
                     'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    valor_pago = r.get("valor_pago") or 0
    valor_kwh = c.get("valor_kwh") or 0.75
    dia_venc = c.get("dia_vencimento") or 5

    f1 = linhas[0] if linhas else {}
    cli1 = f1.get("clientes") or {}
    total_injetado = sum(f.get("kwh_injetado") or 0 for f in linhas)

    nome_uc_tabela = cli1.get("nome_uc") or c.get("nome_uc") or c.get("nome", "")
    if cli1.get("poste"):
        nome_uc_tabela = nome_uc_tabela + " (poste " + str(cli1["poste"]) + ")"

    # Historico ultimos 6 meses
    historico = []
    for i in range(5, -1, -1):
        m = mes - i
        a = ano
        if m <= 0:
            m += 12
            a -= 1
        ref = str(a) + "-" + str(m).zfill(2) + "-01"
        fat = sb.table("faturas").select("kwh_injetado").eq("cliente_id", r["cliente_id"]).eq("mes_referencia", ref).execute()
        kwh = sum(f.get("kwh_injetado") or 0 for f in fat.data or [])
        historico.append({"mes": MESES_CURTO[m], "kwh": int(kwh)})

    # Montar dados de substituicao
    valor_fmt = "R$ " + "{:,.2f}".format(valor_pago).replace(",", "X").replace(".", ",").replace("X", ".")
    valor_kwh_fmt = "R$ " + "{:.2f}".format(valor_kwh).replace(".", ",")

    substituicoes = {
        "Mauro Nascimento Braga (poste 3)": str(nome_uc_tabela),
        "Mauro Nascimento Braga": str(c.get("nome", "")),
        "000000126": str(recibo_id).zfill(9),
        "AGO/26": MESES_CURTO[mes] + "/" + str(ano)[2:],
        "05/09/2026": str(dia_venc).zfill(2) + "/" + str(mes).zfill(2) + "/" + str(ano),
        "01/08/2026": "01/" + str(mes).zfill(2) + "/" + str(ano),
        "R$ 177,80": valor_fmt,
        "CPF: 110.190.771-15 End.: Av. das Torres, 456 Poste 3 Cuiab\u00e1/MT - CEP: 78000-000": "CPF: " + str(c.get("cpf_cnpj", "")) + " End.: " + str(c.get("endereco", "")),
        "R$ 0,70": valor_kwh_fmt,
        ">254<": ">" + str(int(total_injetado)) + "<",
        "6/4754860-7": str(cli1.get("numero_uc") or c.get("numero_uc") or ""),
        ">868<": ">" + (("{:.0f}".format(f1["leitura_inicial"])) if f1.get("leitura_inicial") else "") + "<",
        "1.122": ("{:.0f}".format(f1["leitura_final"])) if f1.get("leitura_final") else "",
        "2.807": ("{:.0f}".format(f1["saldo_kwh"])) if f1.get("saldo_kwh") else "0",
        ">198<": ">" + str(historico[0]["kwh"]) + "<",
        ">MAR<": ">" + historico[0]["mes"] + "<",
        ">215<": ">" + str(historico[1]["kwh"]) + "<",
        ">ABR<": ">" + historico[1]["mes"] + "<",
        ">230<": ">" + str(historico[2]["kwh"]) + "<",
        ">MAI<": ">" + historico[2]["mes"] + "<",
        ">245<": ">" + str(historico[3]["kwh"]) + "<",
        ">JUN<": ">" + historico[3]["mes"] + "<",
        ">260<": ">" + str(historico[4]["kwh"]) + "<",
        ">JUL<": ">" + historico[4]["mes"] + "<",
        ">AGO<": ">" + historico[5]["mes"] + "<",
        "01 de agosto de 2026": "01 de " + MESES_EXTENSO[mes] + " de " + str(ano),
    }

    # Descompactar template
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "recibo_template.pptx")
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "recibo.pptx")
    unpacked_dir = os.path.join(temp_dir, "unpacked")

    with zipfile.ZipFile(template_path, 'r') as z:
        z.extractall(unpacked_dir)

    # Substituir textos no slide
    slide_path = os.path.join(unpacked_dir, "ppt", "slides", "slide1.xml")
    with open(slide_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    for antigo, novo in substituicoes.items():
        xml_content = xml_content.replace(antigo, novo)

    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    # Gerar QR Code PIX e substituir imagem
    try:
        from app.core.pix import gerar_qrcode_pix_bytes
        from PIL import Image

        qr_bytes = gerar_qrcode_pix_bytes("65999211041", "LAC Solar Ltda", "Cuiaba", valor_pago)
        png_img = Image.open(io.BytesIO(qr_bytes))
        rgb_img = png_img.convert("RGB")
        jpg_buffer = io.BytesIO()
        rgb_img.save(jpg_buffer, format="JPEG", quality=95)
        jpg_bytes = jpg_buffer.getvalue()

        media_path = os.path.join(unpacked_dir, "ppt", "media", "image2.jpg")

        # Adicionar relationship pro QR Code
        rels_path = os.path.join(unpacked_dir, "ppt", "slides", "_rels", "slide1.xml.rels")
        with open(rels_path, "r", encoding="utf-8") as rf:
            rels_content = rf.read()
        if "image2.jpg" not in rels_content:
            rels_content = rels_content.replace("</Relationships>", '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image2.jpg"/></Relationships>')
            with open(rels_path, "w", encoding="utf-8") as rf:
                rf.write(rels_content)

        # Adicionar pic element pro QR Code no slide
        slide_path_qr = os.path.join(unpacked_dir, "ppt", "slides", "slide1.xml")
        with open(slide_path_qr, "r", encoding="utf-8") as sf:
            slide_content = sf.read()
        if "rId4" not in slide_content:
            qr_pic = '<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:nvPicPr><p:cNvPr id="9998" name="QR PIX"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId4"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="7600000" y="7900000"/><a:ext cx="1300000" cy="1300000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
            slide_content = slide_content.replace("</p:spTree>", qr_pic + "</p:spTree>")
            with open(slide_path_qr, "w", encoding="utf-8") as sf:
                sf.write(slide_content)
        with open(media_path, "wb") as f:
            f.write(jpg_bytes)
    except Exception as e:
        print("Erro ao gerar QR Code: " + str(e))

    # Reempacotar PPTX
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root_dir, dirs, files in os.walk(unpacked_dir):
            for file in files:
                file_path = os.path.join(root_dir, file)
                arcname = os.path.relpath(file_path, unpacked_dir)
                zout.write(file_path, arcname)

    shutil.rmtree(unpacked_dir, ignore_errors=True)

    # Tentar converter pra PDF
    pdf_path = output_path.replace(".pptx", ".pdf")
    try:
        import subprocess
        soffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        subprocess.run(
            [soffice_path, "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(output_path), output_path],
            capture_output=True, timeout=30,
        )
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            os.remove(output_path)
            os.remove(pdf_path)
            nome_arquivo = "recibo_" + c.get("nome", "cliente").replace(" ", "_") + "_" + MESES_CURTO[mes] + "_" + str(ano) + ".pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=" + nome_arquivo},
            )
    except Exception:
        pass

    # Sem LibreOffice: retorna PPTX
    with open(output_path, "rb") as f:
        pptx_bytes = f.read()
    os.remove(output_path)

    nome_arquivo = "recibo_" + c.get("nome", "cliente").replace(" ", "_") + "_" + MESES_CURTO[mes] + "_" + str(ano) + ".pptx"
    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": "attachment; filename=" + nome_arquivo},
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
