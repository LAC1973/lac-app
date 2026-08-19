from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import require_permission, get_current_user
from app.core.supabase import get_supabase_admin
from app.schemas.producao import ProducaoBulk
from datetime import date, datetime

router = APIRouter()


@router.post("/")
async def registrar_producao(
    req: ProducaoBulk,
    user: dict = Depends(require_permission("producao", "criar")),
):
    """Registra produção diária em lote (vários inversores de uma vez)."""
    sb = get_supabase_admin()

    hoje = date.today()
    resultados = []

    for reg in req.registros:
        if reg.data > hoje:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível registrar produção para data futura ({reg.data})",
            )

        data = {
            "inversor_id": reg.inversor_id,
            "data": str(reg.data),
            "producao_kwh": reg.producao_kwh,
            "registrado_por": user["id"],
        }

        # Upsert: se já existe registro pra esse inversor+data, atualiza
        result = sb.table("producao_diaria").upsert(
            data, on_conflict="inversor_id,data"
        ).execute()

        resultados.append(result.data[0] if result.data else data)

    return {"message": f"{len(resultados)} registro(s) salvos", "registros": resultados}


@router.get("/dia")
async def get_producao_dia(
    data: date = Query(..., description="Data no formato YYYY-MM-DD"),
    user: dict = Depends(require_permission("producao", "visualizar")),
):
    """Retorna a produção de todos os inversores em um dia específico."""
    sb = get_supabase_admin()

    # Buscar todas as usinas com inversores
    usinas = sb.table("usinas").select("*, inversores(*)").order("id").execute()

    resultado = []
    for usina in usinas.data or []:
        inversores_producao = []
        total_usina = 0

        for inv in usina.get("inversores", []):
            prod = (
                sb.table("producao_diaria")
                .select("*")
                .eq("inversor_id", inv["id"])
                .eq("data", str(data))
                .execute()
            )
            kwh = prod.data[0]["producao_kwh"] if prod.data else None
            if kwh:
                total_usina += kwh

            inversores_producao.append({
                "inversor_id": inv["id"],
                "marca": inv["marca"],
                "potencia_kwp": inv["potencia_kwp"],
                "producao_kwh": kwh,
            })

        resultado.append({
            "usina_id": usina["id"],
            "usina_nome": usina["nome"],
            "inversores": inversores_producao,
            "total_usina": total_usina,
        })

    return resultado


@router.get("/mensal")
async def get_producao_mensal(
    ano: int = Query(...),
    mes: int = Query(...),
    user: dict = Depends(require_permission("producao", "visualizar")),
):
    """Retorna a produção diária de todo o mês, agrupada por usina."""
    sb = get_supabase_admin()

    # Calcular primeiro e último dia do mês
    primeiro_dia = f"{ano}-{mes:02d}-01"
    if mes == 12:
        ultimo_dia = f"{ano + 1}-01-01"
    else:
        ultimo_dia = f"{ano}-{mes + 1:02d}-01"

    usinas = sb.table("usinas").select("*, inversores(*)").order("id").execute()

    resultado = []
    for usina in usinas.data or []:
        inversor_ids = [inv["id"] for inv in usina.get("inversores", [])]
        if not inversor_ids:
            continue

        producao = (
            sb.table("producao_diaria")
            .select("*")
            .in_("inversor_id", inversor_ids)
            .gte("data", primeiro_dia)
            .lt("data", ultimo_dia)
            .order("data")
            .execute()
        )

        # Agrupar por dia
        dias = {}
        for reg in producao.data or []:
            dia = reg["data"]
            if dia not in dias:
                dias[dia] = {"data": dia, "total": 0, "inversores": {}}
            dias[dia]["inversores"][reg["inversor_id"]] = reg["producao_kwh"]
            dias[dia]["total"] += reg["producao_kwh"]

        total_mes = sum(d["total"] for d in dias.values())

        resultado.append({
            "usina_id": usina["id"],
            "usina_nome": usina["nome"],
            "inversores": usina.get("inversores", []),
            "dias": list(dias.values()),
            "total_mes": total_mes,
        })

    return resultado


@router.get("/total-usina")
async def get_total_usina_mes(
    usina_id: int = Query(...),
    ano: int = Query(...),
    mes: int = Query(...),
    user: dict = Depends(require_permission("producao", "visualizar")),
):
    """Retorna o total de produção de uma usina em um mês (usado nas faturas)."""
    sb = get_supabase_admin()

    primeiro_dia = f"{ano}-{mes:02d}-01"
    if mes == 12:
        ultimo_dia = f"{ano + 1}-01-01"
    else:
        ultimo_dia = f"{ano}-{mes + 1:02d}-01"

    inversores = (
        sb.table("inversores")
        .select("id")
        .eq("usina_id", usina_id)
        .execute()
    )

    inversor_ids = [inv["id"] for inv in inversores.data or []]
    if not inversor_ids:
        return {"usina_id": usina_id, "total_kwh": 0}

    producao = (
        sb.table("producao_diaria")
        .select("producao_kwh")
        .in_("inversor_id", inversor_ids)
        .gte("data", primeiro_dia)
        .lt("data", ultimo_dia)
        .execute()
    )

    total = sum(reg["producao_kwh"] for reg in producao.data or [])

    return {"usina_id": usina_id, "total_kwh": total}