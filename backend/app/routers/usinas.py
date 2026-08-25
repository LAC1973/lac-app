from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.usinas import UsinaCreate, UsinaUpdate

router = APIRouter()


@router.get("/")
async def list_usinas(user: dict = Depends(require_permission("usinas", "visualizar"))):
    """Lista todas as usinas com seus inversores."""
    sb = get_supabase_admin()
    result = sb.table("usinas").select("*, inversores(*, placas(*))").order("id").execute()
    return result.data or []


@router.get("/{usina_id}")
async def get_usina(usina_id: int, user: dict = Depends(require_permission("usinas", "visualizar"))):
    """Detalhes de uma usina específica."""
    sb = get_supabase_admin()
    result = sb.table("usinas").select("*, inversores(*, placas(*))").eq("id", usina_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Usina não encontrada")
    return result.data


@router.post("/")
async def create_usina(req: UsinaCreate, user: dict = Depends(require_permission("usinas", "criar"))):
    """Cria uma nova usina."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    if "inicio_operacao" in data:
        data["inicio_operacao"] = str(data["inicio_operacao"])
    result = sb.table("usinas").insert(data).execute()
    return result.data[0]


@router.put("/{usina_id}")
async def update_usina(usina_id: int, req: UsinaUpdate, user: dict = Depends(require_permission("usinas", "editar"))):
    """Edita uma usina existente."""
    sb = get_supabase_admin()
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    if "inicio_operacao" in data:
        data["inicio_operacao"] = str(data["inicio_operacao"])
    result = sb.table("usinas").update(data).eq("id", usina_id).execute()
    return result.data[0] if result.data else {"message": "Atualizado"}

@router.put("/{usina_id}/toggle-active")
async def toggle_active_usina(usina_id: int, user: dict = Depends(require_permission("usinas", "editar"))):
    """Ativa/desativa uma usina."""
    sb = get_supabase_admin()
    usina = sb.table("usinas").select("activo").eq("id", usina_id).single().execute()
    if not usina.data:
        raise HTTPException(status_code=404, detail="Usina nao encontrada")
    new_status = not usina.data.get("activo", True)
    sb.table("usinas").update({"activo": new_status}).eq("id", usina_id).execute()
    return {"message": "Usina " + ("ativada" if new_status else "desativada"), "activo": new_status}

@router.delete("/{usina_id}")
async def delete_usina(usina_id: int, user: dict = Depends(require_permission("usinas", "excluir"))):
    """Exclui uma usina e todos os dados vinculados (CASCADE)."""
    sb = get_supabase_admin()
    sb.table("usinas").delete().eq("id", usina_id).execute()
    return {"message": "Usina excluída"}