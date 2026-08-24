from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.faturas import FaturaCreate, FaturaUpdate, GerarFaturasMes
from datetime import date

router = APIRouter()


@router.get("/")
async def list_faturas(
    mes_referencia: str = Query(None, description="Filtrar por mês (YYYY-MM-DD)"),
    usina_id: int = Query(None),
    cliente_id: int = Query(None),
    status: str = Query(None),
    user: dict = Depends(require_permission("faturas", "visualizar")),
):
    """Lista faturas com filtros opcionais."""
    sb = get_supabase_admin()
    # !inner necessario pra poder filtrar pela coluna usina_id da tabela embutida
    query = sb.table("faturas").select("*, clientes!inner(nome, celular, usina_id, valor_kwh, numero_uc, usinas(nome))")

    if mes_referencia:
        query = query.eq("mes_referencia", mes_referencia)
    if cliente_id:
        query = query.eq("cliente_id", cliente_id)
    if status:
        query = query.eq("status", status)
    if usina_id:
        query = query.eq("clientes.usina_id", usina_id)

    result = query.order("created_at", desc=True).limit(2000).execute()

    return result.data or []


@router.post("/gerar")
async def gerar_faturas_mes(
    req: GerarFaturasMes,
    user: dict = Depends(require_permission("faturas", "criar")),
):
    """Gera faturas para todos os clientes ativos no mês."""
    sb = get_supabase_admin()
    mes = str(req.mes_referencia)

    # Verificar se já existem faturas nesse mês
    existentes = sb.table("faturas").select("cliente_id").eq("mes_referencia", mes).execute()
    clientes_com_fatura = {f["cliente_id"] for f in existentes.data or []}

    # Buscar clientes ativos (excluindo agregados)
    clientes = (
        sb.table("clientes")
        .select("*, usinas(id, nome)")
        .eq("activo", True)
        .eq("eh_agregado", False)
        .execute()
    )

    if not clientes.data:
        raise HTTPException(status_code=400, detail="Nenhum cliente ativo encontrado")

    ano = req.mes_referencia.year
    mes_num = req.mes_referencia.month
    faturas_geradas = []

    # Calcular primeiro/último dia do mês (igual para todos os clientes)
    primeiro_dia = f"{ano}-{mes_num:02d}-01"
    if mes_num == 12:
        ultimo_dia = f"{ano + 1}-01-01"
    else:
        ultimo_dia = f"{ano}-{mes_num + 1:02d}-01"

    # Produção total do mês, por usina (uma única passada, não por cliente)
    usina_ids = list({c["usina_id"] for c in clientes.data})
    inversores = (
        sb.table("inversores").select("id, usina_id").in_("usina_id", usina_ids).execute()
        if usina_ids else None
    )
    usina_para_inversores = {}
    for inv in (inversores.data if inversores else []) or []:
        usina_para_inversores.setdefault(inv["usina_id"], []).append(inv["id"])

    todos_inversor_ids = [i for ids in usina_para_inversores.values() for i in ids]
    producao_por_inversor = {}
    if todos_inversor_ids:
        producao = (
            sb.table("producao_diaria")
            .select("inversor_id, producao_kwh")
            .in_("inversor_id", todos_inversor_ids)
            .gte("data", primeiro_dia)
            .lt("data", ultimo_dia)
            .execute()
        )
        for r in producao.data or []:
            producao_por_inversor[r["inversor_id"]] = (
                producao_por_inversor.get(r["inversor_id"], 0) + r["producao_kwh"]
            )

    producao_por_usina = {
        usina_id: sum(producao_por_inversor.get(i, 0) for i in inv_ids)
        for usina_id, inv_ids in usina_para_inversores.items()
    }

    # Percentual vigente de cada cliente (uma única passada, não por cliente)
    cliente_usina_map = {c["id"]: c["usina_id"] for c in clientes.data}
    percs = (
        sb.table("percentuais")
        .select("cliente_id, usina_id, percentual")
        .in_("cliente_id", list(cliente_usina_map.keys()))
        .order("data_vigencia", desc=True)
        .execute()
    )
    percentual_map = {}
    for p in percs.data or []:
        cid = p["cliente_id"]
        if cid in percentual_map:
            continue
        if p["usina_id"] != cliente_usina_map.get(cid):
            continue
        percentual_map[cid] = p["percentual"]

    for cliente in clientes.data:
        if cliente["id"] in clientes_com_fatura:
            continue

        usina_id = cliente["usina_id"]
        producao_total = producao_por_usina.get(usina_id, 0)
        percentual = percentual_map.get(cliente["id"], 0)

        # Calcular valores
        kwh_injetado = producao_total * (percentual / 100)
        valor_kwh = cliente["valor_kwh"] or 0.75
        valor_total = kwh_injetado * valor_kwh
        valor_final = valor_total

        # Data de vencimento
        dia_venc = cliente.get("dia_vencimento", 5)
        try:
            data_vencimento = date(ano, mes_num, dia_venc)
        except ValueError:
            data_vencimento = date(ano, mes_num, 28)

        fatura_data = {
            "cliente_id": cliente["id"],
            "mes_referencia": mes,
            "kwh_injetado": round(kwh_injetado, 2),
            "valor_kwh_aplicado": valor_kwh,
            "valor_total": round(valor_total, 2),
            "desconto_sazonal": 0,
            "valor_final": round(valor_final, 2),
            "data_vencimento": str(data_vencimento),
            "status": "pendente",
        }

        result = sb.table("faturas").insert(fatura_data).execute()
        faturas_geradas.append(result.data[0] if result.data else fatura_data)

    return {
        "message": f"{len(faturas_geradas)} fatura(s) gerada(s) para {mes}",
        "faturas": faturas_geradas,
        "ignoradas": len(clientes_com_fatura),
    }


@router.post("/")
async def create_fatura(
    req: FaturaCreate,
    user: dict = Depends(require_permission("faturas", "criar")),
):
    """Cria uma fatura individual manualmente."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    for campo in ["mes_referencia", "data_vencimento"]:
        if campo in data:
            data[campo] = str(data[campo])
    result = sb.table("faturas").insert(data).execute()
    return result.data[0]


@router.put("/{fatura_id}")
async def update_fatura(
    fatura_id: int,
    req: FaturaUpdate,
    user: dict = Depends(require_permission("faturas", "editar")),
):
    """Edita uma fatura existente."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    if "data_vencimento" in data:
        data["data_vencimento"] = str(data["data_vencimento"])

    # Recalcular valor_final se mudou valor_total ou desconto
    if "valor_total" in data or "desconto_sazonal" in data:
        fatura_atual = sb.table("faturas").select("*").eq("id", fatura_id).single().execute()
        if fatura_atual.data:
            vt = data.get("valor_total", fatura_atual.data["valor_total"]) or 0
            ds = data.get("desconto_sazonal", fatura_atual.data["desconto_sazonal"]) or 0
            data["valor_final"] = round(vt - ds, 2)

    result = sb.table("faturas").update(data).eq("id", fatura_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}


@router.put("/{fatura_id}/status")
async def update_status(
    fatura_id: int,
    status: str = Query(..., description="pendente, enviada, paga, atrasada"),
    user: dict = Depends(require_permission("faturas", "editar")),
):
    """Atualiza o status de uma fatura."""
    sb = get_supabase_admin()

    if status not in ["pendente", "enviada", "paga", "atrasada"]:
        raise HTTPException(status_code=400, detail="Status inválido")

    sb.table("faturas").update({"status": status}).eq("id", fatura_id).execute()
    return {"message": f"Status atualizado para '{status}'"}


@router.delete("/{fatura_id}")
async def delete_fatura(
    fatura_id: int,
    user: dict = Depends(require_permission("faturas", "excluir")),
):
    """Exclui uma fatura."""
    sb = get_supabase_admin()
    sb.table("faturas").delete().eq("id", fatura_id).execute()
    return {"message": "Fatura excluída"}