from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_admin
from app.core.supabase import get_supabase_admin
from app.schemas.configuracoes import ConfiguracaoUpdate

router = APIRouter()


@router.get("/")
async def list_configuracoes(admin: dict = Depends(require_admin)):
    """Lista as configuracoes do sistema (admin apenas)."""
    sb = get_supabase_admin()
    result = sb.table("configuracoes").select("*").order("chave").execute()
    return result.data or []


@router.put("/{chave}")
async def update_configuracao(
    chave: str,
    req: ConfiguracaoUpdate,
    admin: dict = Depends(require_admin),
):
    """Atualiza o valor de uma configuracao existente (admin apenas)."""
    sb = get_supabase_admin()
    result = (
        sb.table("configuracoes")
        .update({"valor": req.valor})
        .eq("chave", chave)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Configuracao nao encontrada")
    return result.data[0]
