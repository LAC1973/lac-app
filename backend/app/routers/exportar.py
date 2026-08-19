from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from fpdf import FPDF
import io

router = APIRouter()

MESES_FULL = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
              'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


@router.get("/fatura-usina")
async def exportar_fatura_usina(
    usina_id: int = Query(...),
    ano: int = Query(...),
    user: dict = Depends(require_permission("faturas", "visualizar")),
):
    sb = get_supabase_admin()

    usina = sb.table("usinas").select("*").eq("id", usina_id).single().execute()
    if not usina.data:
        return {"detail": "Usina nao encontrada"}

    clientes = (
        sb.table("clientes")
        .select("id, item, nome, nome_uc, cpf_cnpj, numero_uc, dia_vencimento, activo")
        .eq("usina_id", usina_id)
        .order("item")
        .execute()
    )

    cliente_ids = [c["id"] for c in clientes.data or []]
    if not cliente_ids:
        return {"detail": "Nenhum cliente encontrado"}

    faturas = (
        sb.table("faturas")
        .select("*")
        .in_("cliente_id", cliente_ids)
        .gte("mes_referencia", f"{ano}-01-01")
        .lte("mes_referencia", f"{ano}-12-01")
        .execute()
    )

    fatura_map = {}
    for f in faturas.data or []:
        mes = int(f["mes_referencia"].split("-")[1])
        fatura_map[(f["cliente_id"], mes)] = f

    # Larguras
    w_item = 6
    w_nome = 34
    w_dia = 6
    w_cpf = 20
    w_uc = 18
    w_fixas = w_item + w_nome + w_dia + w_cpf + w_uc  # 84

    w_col = 9  # cada sub-coluna do mes
    w_mes = w_col * 5  # 45 por mes
    w_total = w_fixas + (w_mes * 12)  # 84 + 540 = 624

    page_w = w_total + 16  # margens
    page_h = 297  # altura A4

    pdf = FPDF(orientation="L", unit="mm", format=(page_h, page_w))
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_margins(8, 8, 8)
    pdf.add_page()

    # Cabecalho
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"{usina.data['nome']}  -  {ano}", ln=True)
    pdf.ln(2)

    # Linha 1: Nomes dos meses
    pdf.set_font("Helvetica", "B", 5)
    pdf.cell(w_fixas, 4, "")
    for m in range(12):
        pdf.cell(w_mes, 4, MESES_FULL[m], border=1, align="C")
    pdf.ln()

    # Linha 2: Sub-cabecalhos
    pdf.set_font("Helvetica", "B", 4)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(w_fixas, 4, "", border=0)
    for m in range(12):
        pdf.cell(w_col * 2, 4, "Dados Leitura", border=1, align="C", fill=True)
        pdf.cell(w_col * 3, 4, "Consumo Kwh/mes", border=1, align="C", fill=True)
    pdf.ln()

    # Linha 3: Cabecalhos colunas
    pdf.set_font("Helvetica", "B", 4)
    pdf.cell(w_item, 4, "Item", border=1, align="C", fill=True)
    pdf.cell(w_nome, 4, "Nome da UC", border=1, align="C", fill=True)
    pdf.cell(w_dia, 4, "DIA", border=1, align="C", fill=True)
    pdf.cell(w_cpf, 4, "CPF", border=1, align="C", fill=True)
    pdf.cell(w_uc, 4, "num. UC", border=1, align="C", fill=True)
    for m in range(12):
        pdf.cell(w_col, 4, "Ini", border=1, align="C", fill=True)
        pdf.cell(w_col, 4, "Fin", border=1, align="C", fill=True)
        pdf.cell(w_col, 4, "Cons", border=1, align="C", fill=True)
        pdf.cell(w_col, 4, "Injet", border=1, align="C", fill=True)
        pdf.cell(w_col, 4, "Saldo", border=1, align="C", fill=True)
    pdf.ln()

    # Dados
    pdf.set_font("Helvetica", "", 4)
    totais = {m: {"consumo": 0, "injetado": 0} for m in range(12)}

    for cliente in clientes.data or []:
        pdf.cell(w_item, 3.8, str(cliente.get("item") or ""), border=1, align="C")
        nome_uc = (cliente.get("nome_uc") or cliente.get("nome") or "")[:22]
        pdf.cell(w_nome, 3.8, nome_uc, border=1)
        pdf.cell(w_dia, 3.8, str(cliente.get("dia_vencimento") or ""), border=1, align="C")
        cpf = (cliente.get("cpf_cnpj") or "")[:16]
        pdf.cell(w_cpf, 3.8, cpf, border=1, align="C")
        uc = (cliente.get("numero_uc") or "")[:12]
        pdf.cell(w_uc, 3.8, uc, border=1, align="C")

        for m in range(12):
            f = fatura_map.get((cliente["id"], m + 1))
            if f:
                lei_ini = f"{f['leitura_inicial']:.0f}" if f.get("leitura_inicial") else ""
                lei_fin = f"{f['leitura_final']:.0f}" if f.get("leitura_final") else ""
                consumo = f"{f['consumo_kwh']:.0f}" if f.get("consumo_kwh") else ""
                injetado = f"{f['kwh_injetado']:.0f}" if f.get("kwh_injetado") else ""
                saldo = f"{f['saldo_kwh']:.0f}" if f.get("saldo_kwh") else ""

                if f.get("consumo_kwh"):
                    totais[m]["consumo"] += f["consumo_kwh"]
                if f.get("kwh_injetado"):
                    totais[m]["injetado"] += f["kwh_injetado"]
            else:
                lei_ini = lei_fin = consumo = injetado = saldo = ""

            pdf.cell(w_col, 3.8, lei_ini, border=1, align="R")
            pdf.cell(w_col, 3.8, lei_fin, border=1, align="R")
            pdf.cell(w_col, 3.8, consumo, border=1, align="R")
            pdf.cell(w_col, 3.8, injetado, border=1, align="R")
            pdf.cell(w_col, 3.8, saldo, border=1, align="R")

        pdf.ln()

    # Totais
    pdf.set_font("Helvetica", "B", 4)
    pdf.set_fill_color(255, 248, 225)
    pdf.cell(w_item + w_nome + w_dia + w_cpf, 4, "", border=1, fill=True)
    pdf.cell(w_uc, 4, "Total", border=1, align="R", fill=True)
    for m in range(12):
        pdf.cell(w_col, 4, "", border=1, fill=True)
        pdf.cell(w_col, 4, "", border=1, fill=True)
        cons = f"{totais[m]['consumo']:.0f}" if totais[m]['consumo'] else ""
        inj = f"{totais[m]['injetado']:.0f}" if totais[m]['injetado'] else ""
        pdf.cell(w_col, 4, cons, border=1, align="R", fill=True)
        pdf.cell(w_col, 4, inj, border=1, align="R", fill=True)
        pdf.cell(w_col, 4, "", border=1, fill=True)
    pdf.ln()

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    nome_arquivo = f"faturas_{usina.data['nome'].replace(' ', '_')}_{ano}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )