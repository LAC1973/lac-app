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

    resultado = []
    soma = 0

    for cliente in clientes.data or []:
        perm = (
            sb.table("percentuais")
            .select("*")
            .eq("cliente_id", cliente["id"])
            .eq("usina_id", usina_id)
            .order("data_vigencia", desc=True)
            .limit(1)
            .execute()
        )
        percentual_vigente = perm.data[0] if perm.data else None
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

    soma = 0
    for cliente in clientes.data or []:
        if cliente["id"] == req.cliente_id:
            continue
        perm = (
            sb.table("percentuais")
            .select("percentual")
            .eq("cliente_id", cliente["id"])
            .eq("usina_id", req.usina_id)
            .order("data_vigencia", desc=True)
            .limit(1)
            .execute()
        )
        if perm.data:
            soma += perm.data[0]["percentual"]

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