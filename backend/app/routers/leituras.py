from fastapi import APIRouter, Depends, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.leituras import LeiturasBulk

router = APIRouter()


@router.get("/")
async def get_leituras_mes(
    usina_id: int = Query(...),
    mes_referencia: str = Query(...),
    user: dict = Depends(require_permission("faturas", "editar")),
):
    """Retorna faturas da usina com leitura anterior pra auto-preenchimento."""
    sb = get_supabase_admin()

    # Buscar clientes da usina
    clientes = (
        sb.table("clientes")
        .select("id, item, nome, nome_uc, numero_uc, activo")
        .eq("usina_id", usina_id)
        .eq("activo", True)
        .order("item")
        .execute()
    )
    cliente_ids = [c["id"] for c in clientes.data or []]
    if not cliente_ids:
        return []

    # Faturas do mês atual
    faturas = (
        sb.table("faturas")
        .select("*")
        .in_("cliente_id", cliente_ids)
        .eq("mes_referencia", mes_referencia)
        .execute()
    )
    fatura_map = {f["cliente_id"]: f for f in faturas.data or []}

    # Calcular mês anterior pra buscar leitura_final anterior
    ano = int(mes_referencia.split("-")[0])
    mes = int(mes_referencia.split("-")[1])
    if mes == 1:
        mes_ant = f"{ano - 1}-12-01"
    else:
        mes_ant = f"{ano}-{mes - 1:02d}-01"

    faturas_ant = (
        sb.table("faturas")
        .select("cliente_id, leitura_final")
        .in_("cliente_id", cliente_ids)
        .eq("mes_referencia", mes_ant)
        .execute()
    )
    leitura_ant_map = {f["cliente_id"]: f["leitura_final"] for f in faturas_ant.data or []}

    resultado = []
    for cliente in clientes.data or []:
        fatura = fatura_map.get(cliente["id"])
        leitura_ant = leitura_ant_map.get(cliente["id"])

        resultado.append({
            "cliente_id": cliente["id"],
            "item": cliente.get("item"),
            "nome": cliente.get("nome"),
            "nome_uc": cliente.get("nome_uc"),
            "numero_uc": cliente.get("numero_uc"),
            "fatura_id": fatura["id"] if fatura else None,
            "leitura_inicial": fatura.get("leitura_inicial") if fatura else None,
            "leitura_final": fatura.get("leitura_final") if fatura else None,
            "consumo_kwh": fatura.get("consumo_kwh") if fatura else None,
            "kwh_injetado": fatura.get("kwh_injetado") if fatura else None,
            "saldo_kwh": fatura.get("saldo_kwh") if fatura else None,
            "leitura_anterior": leitura_ant,
        })

    return resultado


@router.post("/")
async def salvar_leituras(
    req: LeiturasBulk,
    user: dict = Depends(require_permission("faturas", "editar")),
):
    """Salva leituras em lote e recalcula consumo automaticamente."""
    sb = get_supabase_admin()

    # Buscar de uma vez as faturas que precisam de leitura existente pra calcular consumo
    faltando_ids = [
        reg.fatura_id
        for reg in req.registros
        if reg.fatura_id and (reg.leitura_inicial is None or reg.leitura_final is None)
    ]
    existentes_map = {}
    if faltando_ids:
        existentes = (
            sb.table("faturas")
            .select("id, leitura_inicial, leitura_final")
            .in_("id", faltando_ids)
            .execute()
        )
        existentes_map = {f["id"]: f for f in existentes.data or []}

    payloads = []
    for reg in req.registros:
        if not reg.fatura_id:
            continue

        update = {"id": reg.fatura_id}
        if reg.leitura_inicial is not None:
            update["leitura_inicial"] = reg.leitura_inicial
        if reg.leitura_final is not None:
            update["leitura_final"] = reg.leitura_final

        # Calcular consumo se tem ambas leituras
        ini = reg.leitura_inicial
        fin = reg.leitura_final

        if ini is None or fin is None:
            existente = existentes_map.get(reg.fatura_id)
            if existente:
                if ini is None:
                    ini = existente.get("leitura_inicial")
                if fin is None:
                    fin = existente.get("leitura_final")

        if ini is not None and fin is not None:
            update["consumo_kwh"] = round(fin - ini, 2)

        if len(update) > 1:
            payloads.append(update)

    if payloads:
        sb.table("faturas").upsert(payloads, on_conflict="id").execute()

    return {"message": f"{len(payloads)} leitura(s) atualizada(s)"}