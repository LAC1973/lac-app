from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
import uuid

router = APIRouter()


@router.post("/upload")
async def upload_documento(
    file: UploadFile = File(...),
    tipo: str = Form(...),
    usina_id: int = Form(None),
    cliente_id: int = Form(None),
    user: dict = Depends(require_permission("usinas", "editar")),
):
    """Upload de documento para Supabase Storage."""
    sb = get_supabase_admin()

    if not usina_id and not cliente_id:
        raise HTTPException(status_code=400, detail="Informe usina_id ou cliente_id")

    # Gerar nome unico
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    nome_unico = f"{uuid.uuid4().hex}.{ext}"

    if usina_id:
        path = f"usinas/{usina_id}/{tipo}/{nome_unico}"
    else:
        path = f"clientes/{cliente_id}/{tipo}/{nome_unico}"

    # Upload pro Supabase Storage
    content = await file.read()
    try:
        sb.storage.from_("documentos").upload(path, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")

    # Gerar URL publica
    url = sb.storage.from_("documentos").get_public_url(path)

    # Salvar registro no banco
    data = {
        "tipo": tipo,
        "nome_arquivo": file.filename,
        "url": url,
        "usina_id": usina_id,
        "cliente_id": cliente_id,
    }
    result = sb.table("documentos").insert(data).execute()

    return result.data[0]


@router.get("/")
async def list_documentos(
    usina_id: int = Query(None),
    cliente_id: int = Query(None),
    user: dict = Depends(require_permission("usinas", "visualizar")),
):
    """Lista documentos de uma usina ou cliente."""
    sb = get_supabase_admin()
    query = sb.table("documentos").select("*")

    if usina_id:
        query = query.eq("usina_id", usina_id)
    elif cliente_id:
        query = query.eq("cliente_id", cliente_id)

    result = query.order("created_at", desc=True).limit(2000).execute()
    return result.data or []


@router.delete("/{documento_id}")
async def delete_documento(
    documento_id: int,
    user: dict = Depends(require_permission("usinas", "excluir")),
):
    """Exclui documento do banco e do storage."""
    sb = get_supabase_admin()

    doc = sb.table("documentos").select("url").eq("id", documento_id).single().execute()
    if doc.data:
        # Extrair path da URL pra deletar do storage
        url = doc.data["url"]
        try:
            path = url.split("/documentos/")[1] if "/documentos/" in url else None
            if path:
                sb.storage.from_("documentos").remove([path])
        except Exception:
            pass

    sb.table("documentos").delete().eq("id", documento_id).execute()
    return {"message": "Documento excluido"}