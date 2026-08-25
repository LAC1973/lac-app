from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.clientes import ClienteCreate, ClienteUpdate

router = APIRouter()


@router.get("/")
async def list_clientes(
    usina_id: int = Query(None, description="Filtrar por usina"),
    user: dict = Depends(require_permission("clientes", "visualizar")),
):
    """Lista clientes. Pode filtrar por usina."""
    sb = get_supabase_admin()
    query = sb.table("clientes").select("*, usinas(nome), clientes_ucs(*, usinas(nome))")

    if usina_id:
        query = query.eq("usina_id", usina_id)

    result = query.order("nome").execute()
    return result.data or []


@router.get("/{cliente_id}")
async def get_cliente(
    cliente_id: int,
    user: dict = Depends(require_permission("clientes", "visualizar")),
):
    """Detalhes de um cliente com seus percentuais."""
    sb = get_supabase_admin()
    cliente = sb.table("clientes").select("*, usinas(nome), clientes_ucs(*, usinas(nome))").eq("id", cliente_id).single().execute()

    if not cliente.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    percentuais = (
        sb.table("percentuais")
        .select("*")
        .eq("cliente_id", cliente_id)
        .order("data_vigencia", desc=True)
        .execute()
    )

    return {**cliente.data, "percentuais": percentuais.data or []}


@router.post("/")
async def create_cliente(
    req: ClienteCreate,
    user: dict = Depends(require_permission("clientes", "criar")),
):
    """Cria um novo cliente vinculado a uma usina."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    if "data_contratacao" in data:
        data["data_contratacao"] = str(data["data_contratacao"])
    result = sb.table("clientes").insert(data).execute()
    return result.data[0]


@router.put("/{cliente_id}")
async def update_cliente(
    cliente_id: int,
    req: ClienteUpdate,
    user: dict = Depends(require_permission("clientes", "editar")),
):
    """Edita um cliente existente."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    if "data_contratacao" in data:
        data["data_contratacao"] = str(data["data_contratacao"])
    result = sb.table("clientes").update(data).eq("id", cliente_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}

# === CRUD de UCs do cliente ===

@router.get("/{cliente_id}/ucs")
async def list_ucs(
    cliente_id: int,
    user: dict = Depends(require_permission("clientes", "visualizar")),
):
    sb = get_supabase_admin()
    result = (
        sb.table("clientes_ucs")
        .select("*, usinas(nome)")
        .eq("cliente_id", cliente_id)
        .order("item")
        .execute()
    )
    return result.data or []


@router.post("/{cliente_id}/ucs")
async def create_uc(
    cliente_id: int,
    data: dict,
    user: dict = Depends(require_permission("clientes", "criar")),
):
    sb = get_supabase_admin()
    data["cliente_id"] = cliente_id
    result = sb.table("clientes_ucs").insert(data).execute()
    return result.data[0]


@router.put("/ucs/{uc_id}")
async def update_uc(
    uc_id: int,
    data: dict,
    user: dict = Depends(require_permission("clientes", "editar")),
):
    sb = get_supabase_admin()
    result = sb.table("clientes_ucs").update(data).eq("id", uc_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}


@router.delete("/ucs/{uc_id}")
async def delete_uc(
    uc_id: int,
    user: dict = Depends(require_permission("clientes", "excluir")),
):
    sb = get_supabase_admin()
    sb.table("clientes_ucs").delete().eq("id", uc_id).execute()
    return {"message": "UC excluida"}

@router.delete("/{cliente_id}")
async def delete_cliente(
    cliente_id: int,
    user: dict = Depends(require_permission("clientes", "excluir")),
):
    """Exclui um cliente e todos os dados vinculados."""
    sb = get_supabase_admin()
    sb.table("clientes").delete().eq("id", cliente_id).execute()
    return {"message": "Cliente excluído"}