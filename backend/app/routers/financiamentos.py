from fastapi import APIRouter, Depends, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin

router = APIRouter()


@router.get("/")
async def list_financiamentos(
    mes_referencia: str = Query(None),
    user: dict = Depends(require_permission("despesas", "visualizar")),
):
    sb = get_supabase_admin()
    query = sb.table("financiamentos").select("*")
    if mes_referencia:
        query = query.eq("mes_referencia", mes_referencia)
    result = query.order("nome").execute()
    return result.data or []


@router.post("/")
async def create_financiamento(
    data: dict,
    user: dict = Depends(require_permission("despesas", "criar")),
):
    sb = get_supabase_admin()
    result = sb.table("financiamentos").insert(data).execute()
    return result.data[0]


@router.delete("/{financiamento_id}")
async def delete_financiamento(
    financiamento_id: int,
    user: dict = Depends(require_permission("despesas", "excluir")),
):
    sb = get_supabase_admin()
    sb.table("financiamentos").delete().eq("id", financiamento_id).execute()
    return {"message": "Financiamento excluido"}