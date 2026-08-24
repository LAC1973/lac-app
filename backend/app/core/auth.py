import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import get_supabase_admin

security = HTTPBearer()

MODULOS = [
    "usinas", "clientes", "percentuais", "producao",
    "faturas", "recibos", "rgd", "saldo_acm",
    "dre", "despesas", "dashboard",
]

# Cache em memória (por processo) do profile/permissoes resolvidos por token,
# pra evitar reverificar o mesmo token no Supabase em rajadas de requisições
# (ex: uma pagina que dispara 3 GETs juntos no mount).
_CACHE_TTL_SECONDS = 30
_user_cache: dict[str, dict] = {}


def _get_cached(token: str) -> dict | None:
    entry = _user_cache.get(token)
    if entry and entry["expires_at"] > time.time():
        return entry
    return None


def _put_cache(token: str, profile: dict) -> dict:
    now = time.time()
    # limpa entradas expiradas pra nao crescer sem limite ao longo dos dias
    for t in [t for t, e in _user_cache.items() if e["expires_at"] <= now]:
        del _user_cache[t]

    entry = {"profile": profile, "permissoes": None, "expires_at": now + _CACHE_TTL_SECONDS}
    _user_cache[token] = entry
    return entry


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verifica o token pelo Supabase e retorna o profile do usuário."""
    token = credentials.credentials

    cached = _get_cached(token)
    if cached:
        return cached["profile"]

    sb = get_supabase_admin()

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

    _put_cache(token, result.data)
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
    async def checker(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict:
        user = await get_current_user(credentials)
        if user.get("is_admin"):
            return user

        token = credentials.credentials
        cached = _get_cached(token)
        permissoes = cached["permissoes"] if cached else None

        if permissoes is None:
            sb = get_supabase_admin()
            result = (
                sb.table("permissoes")
                .select("*")
                .eq("profile_id", user["id"])
                .execute()
            )
            permissoes = {p["modulo"]: p for p in (result.data or [])}
            if cached:
                cached["permissoes"] = permissoes

        perm = permissoes.get(modulo)
        if not perm:
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para o módulo '{modulo}'",
            )

        campo = f"pode_{accao}"
        if not perm.get(campo, False):
            raise HTTPException(
                status_code=403,
                detail=f"Sem permissão para '{accao}' em '{modulo}'",
            )

        return user

    return checker