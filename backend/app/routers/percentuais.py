from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.clientes import PercentualCreate

router = APIRouter()


@router.get("/usina/{usina_id}")
async def list_percentuais_usina(
    usina_id: int,
    user: dict = Depends(require_permission("percentuais", "visualizar")),
):
    """Lista os percentuais vigentes de todos os clientes de uma usina."""
    sb = get_supabase_admin()

    clientes = (
        sb.table("clientes")
        .select("id, nome, nome_uc, numero_uc, activo")
        .eq("usina_id", usina_id)
        .eq("activo", True)
        .order("nome")
        .execute()
    )

    cliente_ids = [c["id"] for c in clientes.data or []]

    percentual_map = {}
    if cliente_ids:
        percs = (
            sb.table("percentuais")
            .select("*")
            .in_("cliente_id", cliente_ids)
            .eq("usina_id", usina_id)
            .order("data_vigencia", desc=True)
            .execute()
        )
        for p in percs.data or []:
            # ordenado por data_vigencia desc: o primeiro visto por cliente é o vigente
            percentual_map.setdefault(p["cliente_id"], p)

    resultado = []
    soma = 0

    for cliente in clientes.data or []:
        percentual_vigente = percentual_map.get(cliente["id"])
        valor = percentual_vigente["percentual"] if percentual_vigente else 0
        soma += valor

        resultado.append({
            **cliente,
            "percentual_vigente": percentual_vigente,
        })

    return {
        "clientes": resultado,
        "soma_percentuais": soma,
        "completo": abs(soma - 100) < 0.01,
    }


@router.get("/cliente/{cliente_id}")
async def list_percentuais_cliente(
    cliente_id: int,
    user: dict = Depends(require_permission("percentuais", "visualizar")),
):
    """Histórico de percentuais de um cliente."""
    sb = get_supabase_admin()
    result = (
        sb.table("percentuais")
        .select("*")
        .eq("cliente_id", cliente_id)
        .order("data_vigencia", desc=True)
        .execute()
    )
    return result.data or []


@router.post("/")
async def create_percentual(
    req: PercentualCreate,
    user: dict = Depends(require_permission("percentuais", "criar")),
):
    """Define um novo percentual para um cliente. Não exclui os antigos (histórico)."""
    sb = get_supabase_admin()

    # Verificar se a soma vai ultrapassar 100%
    clientes = (
        sb.table("clientes")
        .select("id")
        .eq("usina_id", req.usina_id)
        .eq("activo", True)
        .execute()
    )

    outros_ids = [c["id"] for c in clientes.data or [] if c["id"] != req.cliente_id]

    soma = 0
    if outros_ids:
        percs = (
            sb.table("percentuais")
            .select("cliente_id, percentual")
            .in_("cliente_id", outros_ids)
            .eq("usina_id", req.usina_id)
            .order("data_vigencia", desc=True)
            .execute()
        )
        vistos = set()
        for p in percs.data or []:
            # ordenado por data_vigencia desc: o primeiro visto por cliente é o vigente
            if p["cliente_id"] in vistos:
                continue
            vistos.add(p["cliente_id"])
            soma += p["percentual"]

    if soma + req.percentual > 100.01:
        raise HTTPException(
            status_code=400,
            detail=f"A soma dos percentuais ficaria em {soma + req.percentual:.2f}%, ultrapassando 100%",
        )

    data = req.model_dump()
    data["data_vigencia"] = str(data["data_vigencia"])
    result = sb.table("percentuais").insert(data).execute()
    return result.data[0]


@router.delete("/{percentual_id}")
async def delete_percentual(
    percentual_id: int,
    user: dict = Depends(require_permission("percentuais", "excluir")),
):
    """Exclui um registro de percentual."""
    sb = get_supabase_admin()
    sb.table("percentuais").delete().eq("id", percentual_id).execute()
    return {"message": "Percentual excluído"}