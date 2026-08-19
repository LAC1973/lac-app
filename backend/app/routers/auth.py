from fastapi import APIRouter, HTTPException, Depends
from app.schemas.users import LoginRequest
from app.core.supabase import get_supabase, get_supabase_admin
from app.core.auth import get_current_user

router = APIRouter()


@router.post("/login")
async def login(req: LoginRequest):
    sb = get_supabase()
    try:
        result = sb.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    if not result.session:
        raise HTTPException(status_code=401, detail="Falha na autenticação")

    return {
        "access_token": result.session.access_token,
        "user": {
            "id": result.user.id,
            "email": result.user.email,
        },
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retorna o perfil do usuário logado com suas permissões."""
    sb = get_supabase_admin()

    permissoes = []
    if not user.get("is_admin"):
        result = (
            sb.table("permissoes")
            .select("*")
            .eq("profile_id", user["id"])
            .execute()
        )
        permissoes = result.data or []

    return {
        **user,
        "permissoes": permissoes,
    }