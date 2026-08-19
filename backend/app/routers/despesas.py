from fastapi import APIRouter, Depends, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin

router = APIRouter()


@router.get("/")
async def list_despesas(
    mes_referencia: str = Query(None),
    user: dict = Depends(require_permission("despesas", "visualizar")),
):
    sb = get_supabase_admin()
    query = sb.table("despesas").select("*")
    if mes_referencia:
        query = query.eq("mes_referencia", mes_referencia)
    result = query.order("categoria").execute()
    return result.data or []


@router.post("/")
async def create_despesa(
    data: dict,
    user: dict = Depends(require_permission("despesas", "criar")),
):
    sb = get_supabase_admin()
    result = sb.table("despesas").insert(data).execute()
    return result.data[0]


@router.delete("/{despesa_id}")
async def delete_despesa(
    despesa_id: int,
    user: dict = Depends(require_permission("despesas", "excluir")),
):
    sb = get_supabase_admin()
    sb.table("despesas").delete().eq("id", despesa_id).execute()
    return {"message": "Despesa excluida"}