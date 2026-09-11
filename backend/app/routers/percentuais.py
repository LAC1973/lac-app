from PIL import ImageFile
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from app.schemas.clientes import PercentualCreate

router = APIRouter()


@router.get("/usina/{usina_id}")
async def list_percentuais_usina(
    usina_id: int,
    user: dict = Depends(require_permission("percentuais", "visualizar")),
):
    """Lista os percentuais vigentes de todas as UCs de uma usina."""
    sb = get_supabase_admin()

    # Parte dos percentuais da usina, não das UCs dela: uma UC pode ser
    # compensada por uma usina diferente da que está no seu cadastro.
    percs = (
        sb.table("percentuais")
        .select("*, clientes_ucs(*, clientes(nome, cpf_cnpj))")
        .eq("usina_id", usina_id)
        .order("data_vigencia", desc=True)
        .execute()
    )

    vigentes = {}
    for p in percs.data or []:
        uc = p.get("clientes_ucs")
        if not uc or not uc.get("activo"):
            continue
        # veio ordenado por data desc, então o primeiro de cada UC é o vigente
        vigentes.setdefault(p["cliente_uc_id"], p)

    resultado = []
    soma = 0

    for percentual_vigente in sorted(
        vigentes.values(), key=lambda p: p["clientes_ucs"].get("item") or 0
    ):
        uc = percentual_vigente["clientes_ucs"]
        valor = percentual_vigente["percentual"]
        soma += valor

        resultado.append({
            "uc_id": uc["id"],
            "cliente_id": uc["cliente_id"],
            "nome_cliente": uc.get("clientes", {}).get("nome", ""),
            "nome_uc": uc.get("nome_uc", ""),
            "numero_uc": uc.get("numero_uc", ""),
            "item": uc.get("item"),
            "percentual_vigente": percentual_vigente,
        })

    return {
        "clientes": resultado,
        "soma_percentuais": soma,
        "completo": abs(soma - 100) < 0.01,
    }

@router.get("/cliente/{cliente_id}")
async def list_percentuais_cliente(
    cliente_id: int,
    user: dict = Depends(require_permission("percentuais", "visualizar")),
):
    """Histórico de percentuais de um cliente."""
    sb = get_supabase_admin()
    result = (
        sb.table("percentuais")
        .select("*")
        .eq("cliente_id", cliente_id)
        .order("data_vigencia", desc=True)
        .execute()
    )
    return result.data or []


@router.post("/")
async def create_percentual(
    req: PercentualCreate,
    user: dict = Depends(require_permission("percentuais", "criar")),
):
    """Define um novo percentual para uma UC. Nao exclui os antigos (historico)."""
    sb = get_supabase_admin()

    # Verificar se a soma vai ultrapassar 100%.
    # Soma os percentuais VIGENTES da usina, um por UC, exceto o da UC que está
    # sendo definida agora. Parte dos percentuais da usina (não das UCs
    # cadastradas nela), porque uma UC pode ser compensada por outra usina.
    uc_atual = req.cliente_uc_id or req.cliente_id

    percs = (
        sb.table("percentuais")
        .select("cliente_uc_id, percentual, data_vigencia")
        .eq("usina_id", req.usina_id)
        .order("data_vigencia", desc=True)
        .execute()
    )

    vigente_por_uc = {}
    for p in percs.data or []:
        vigente_por_uc.setdefault(p["cliente_uc_id"], p["percentual"])

    soma = sum(v for uc_id, v in vigente_por_uc.items() if uc_id != uc_atual)

    if soma + req.percentual > 100.01:
        raise HTTPException(
            status_code=400,
            detail="A soma dos percentuais ficaria em {:.2f}%, ultrapassando 100%".format(soma + req.percentual),
        )

    data = req.model_dump()
    data["data_vigencia"] = str(data["data_vigencia"])
    # Suporta tanto cliente_uc_id quanto cliente_id
    if not data.get("cliente_uc_id"):
        data["cliente_uc_id"] = data.get("cliente_id")
    # cliente_id e obrigatorio na tabela: resolve pelo titular da UC
    if not data.get("cliente_id"):
        uc = (
            sb.table("clientes_ucs")
            .select("cliente_id")
            .eq("id", data["cliente_uc_id"])
            .single()
            .execute()
        )
        if not uc.data:
            raise HTTPException(status_code=404, detail="UC nao encontrada")
        data["cliente_id"] = uc.data["cliente_id"]
    result = sb.table("percentuais").insert(data).execute()
    return result.data[0]


@router.delete("/{percentual_id}")
async def delete_percentual(
    percentual_id: int,
    user: dict = Depends(require_permission("percentuais", "excluir")),
):
    """Exclui um registro de percentual."""
    sb = get_supabase_admin()
    sb.table("percentuais").delete().eq("id", percentual_id).execute()
    return {"message": "Percentual excluído"}

@router.post("/{percentual_id}/documento")
async def upload_documento_percentual(
    percentual_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(require_permission("percentuais", "criar")),
):  
    """Upload de protocolo/aceite da Energisa para alteracao de percentual."""
    from app.core.supabase import get_supabase_admin
    import uuid

    sb = get_supabase_admin()
    content = await file.read()
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    path = f"percentuais/{percentual_id}/{uuid.uuid4()}.{ext}"

    sb.storage.from_("documentos").upload(path, content, {"content-type": file.content_type})
    url = sb.storage.from_("documentos").get_public_url(path)

    sb.table("percentuais").update({"documento_url": url, "documento_nome": file.filename}).eq("id", percentual_id).execute()

    return {"url": url, "nome": file.filename}