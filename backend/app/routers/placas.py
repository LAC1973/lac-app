from fastapi import APIRouter, Depends
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.usinas import PlacaBase

router = APIRouter()


@router.post("/{usina_id}")
async def create_placa(
    usina_id: int,
    req: PlacaBase,
    user: dict = Depends(require_permission("usinas", "editar")),
):
    sb = get_supabase_admin()
    data = req.model_dump()
    data["usina_id"] = usina_id
    result = sb.table("placas").insert(data).execute()
    return result.data[0]


@router.put("/{placa_id}")
async def update_placa(
    placa_id: int,
    req: PlacaBase,
    user: dict = Depends(require_permission("usinas", "editar")),
):
    sb = get_supabase_admin()
    result = sb.table("placas").update(req.model_dump()).eq("id", placa_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}


@router.delete("/{placa_id}")
async def delete_placa(
    placa_id: int,
    user: dict = Depends(require_permission("usinas", "excluir")),
):
    sb = get_supabase_admin()
    sb.table("placas").delete().eq("id", placa_id).execute()
    return {"message": "Placa excluida"}