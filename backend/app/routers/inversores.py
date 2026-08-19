from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.usinas import InversorBase

router = APIRouter()


@router.post("/{usina_id}")
async def create_inversor(
    usina_id: int,
    req: InversorBase,
    user: dict = Depends(require_permission("usinas", "editar")),
):
    """Adiciona um inversor a uma usina."""
    sb = get_supabase_admin()
    data = req.model_dump()
    data["usina_id"] = usina_id
    result = sb.table("inversores").insert(data).execute()
    return result.data[0]


@router.put("/{inversor_id}")
async def update_inversor(
    inversor_id: int,
    req: InversorBase,
    user: dict = Depends(require_permission("usinas", "editar")),
):
    """Edita um inversor existente."""
    sb = get_supabase_admin()
    result = sb.table("inversores").update(req.model_dump()).eq("id", inversor_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}


@router.delete("/{inversor_id}")
async def delete_inversor(
    inversor_id: int,
    user: dict = Depends(require_permission("usinas", "excluir")),
):
    """Remove um inversor."""
    sb = get_supabase_admin()
    sb.table("inversores").delete().eq("id", inversor_id).execute()
    return {"message": "Inversor excluído"}