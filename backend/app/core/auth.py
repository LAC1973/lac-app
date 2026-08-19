from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import get_supabase_admin

security = HTTPBearer()

MODULOS = [
    "usinas", "clientes", "percentuais", "producao",
    "faturas", "recibos", "rgd", "saldo_acm",
    "dre", "despesas", "dashboard",
]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verifica o token pelo Supabase e retorna o profile do usuário."""
    sb = get_supabase_admin()
    token = credentials.credentials

    try:
        auth_response = sb.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    if not auth_response or not auth_response.user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    user_id = str(auth_response.user.id)

    result = sb.table("profiles").select("*").eq("id", user_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    if not result.data.get("activo", True):
        raise HTTPException(status_code=403, detail="Usuário desativado")

    return result.data


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Exige que o usuário seja admin."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")
    return user


def require_permission(modulo: str, accao: str):
    """
    Factory que checa permissão granular.
    Uso: Depends(require_permission("faturas", "editar"))
    """
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("is_admin"):
            return user

        sb = get_supabase_admin()
        result = (
            sb.table("permissoes")
            .select("*")
            .eq("profile_id", user["id"])
            .eq("modulo", modulo)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para o módulo '{modulo}'",
            )

        campo = f"pode_{accao}"
        if not result.data.get(campo, False):
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para '{accao}' em '{modulo}'",
            )

        return user

    return checker