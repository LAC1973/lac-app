from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_admin, MODULOS
from app.core.supabase import get_supabase_admin
from app.schemas.users import (
    CreateFuncionarioRequest,
    UpdateFuncionarioRequest,
    UpdatePermissoesRequest,
    ResetPasswordRequest,
)

router = APIRouter()


@router.get("/")
async def list_users(admin: dict = Depends(require_admin)):
    """Lista todos os funcionários com suas permissões."""
    sb = get_supabase_admin()

    profiles = sb.table("profiles").select("*").order("full_name").execute()

    users_with_perms = []
    for profile in profiles.data or []:
        perms = (
            sb.table("permissoes")
            .select("*")
            .eq("profile_id", profile["id"])
            .execute()
        )
        users_with_perms.append({
            **profile,
            "permissoes": perms.data or [],
        })

    return users_with_perms


@router.post("/")
async def create_funcionario(
    req: CreateFuncionarioRequest,
    admin: dict = Depends(require_admin),
):
    """Admin cria um novo funcionário com email/senha e permissões."""
    sb = get_supabase_admin()

    try:
        auth_result = sb.auth.admin.create_user({
            "email": req.email,
            "password": req.password,
            "email_confirm": True,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao criar usuário: {str(e)}")

    user_id = auth_result.user.id

    sb.table("profiles").insert({
        "id": str(user_id),
        "full_name": req.full_name,
        "email": req.email,
        "phone": req.phone,
        "is_admin": False,
        "activo": True,
        "created_by": admin["id"],
    }).execute()

    for modulo in MODULOS:
        perm = next((p for p in req.permissoes if p.modulo == modulo), None)
        sb.table("permissoes").insert({
            "profile_id": str(user_id),
            "modulo": modulo,
            "pode_visualizar": perm.pode_visualizar if perm else False,
            "pode_criar": perm.pode_criar if perm else False,
            "pode_editar": perm.pode_editar if perm else False,
            "pode_excluir": perm.pode_excluir if perm else False,
        }).execute()

    return {"message": "Funcionário criado com sucesso", "id": str(user_id)}


@router.put("/{user_id}")
async def update_funcionario(
    user_id: str,
    req: UpdateFuncionarioRequest,
    admin: dict = Depends(require_admin),
):
    """Admin edita dados de um funcionário."""
    sb = get_supabase_admin()

    update_data = req.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    sb.table("profiles").update(update_data).eq("id", user_id).execute()

    return {"message": "Funcionário atualizado"}


@router.put("/{user_id}/permissoes")
async def update_permissoes(
    user_id: str,
    req: UpdatePermissoesRequest,
    admin: dict = Depends(require_admin),
):
    """Admin atualiza as permissões de um funcionário."""
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    if profile.data and profile.data.get("is_admin"):
        raise HTTPException(status_code=400, detail="Não é possível alterar permissões do admin")

    for perm in req.permissoes:
        sb.table("permissoes").upsert({
            "profile_id": user_id,
            "modulo": perm.modulo,
            "pode_visualizar": perm.pode_visualizar,
            "pode_criar": perm.pode_criar,
            "pode_editar": perm.pode_editar,
            "pode_excluir": perm.pode_excluir,
        }, on_conflict="profile_id,modulo").execute()

    return {"message": "Permissões atualizadas"}


@router.put("/{user_id}/toggle-active")
async def toggle_active(user_id: str, admin: dict = Depends(require_admin)):
    """Admin ativa/desativa um funcionário."""
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("activo, is_admin").eq("id", user_id).single().execute()

    if not profile.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if profile.data.get("is_admin"):
        raise HTTPException(status_code=400, detail="Não é possível desativar o admin")

    new_status = not profile.data["activo"]
    sb.table("profiles").update({"activo": new_status}).eq("id", user_id).execute()

    return {"message": f"Funcionário {'ativado' if new_status else 'desativado'}", "activo": new_status}


@router.put("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    req: ResetPasswordRequest,
    admin: dict = Depends(require_admin),
):
    """Admin reseta a senha de um funcionário."""
    sb = get_supabase_admin()

    try:
        sb.auth.admin.update_user_by_id(user_id, {"password": req.new_password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao resetar senha: {str(e)}")

    return {"message": "Senha resetada com sucesso"}