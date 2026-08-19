from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.core.auth import require_permission
import pdfplumber
import re
import io

router = APIRouter()


@router.post("/extrair")
async def extrair_fatura_energisa(
    file: UploadFile = File(...),
    user: dict = Depends(require_permission("faturas", "criar")),
):
    """Extrai dados da fatura da Energisa (PDF)."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF")

    content = await file.read()
    
    try:
        pdf = pdfplumber.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao ler o PDF")

    texto_completo = ""
    for page in pdf.pages:
        texto_completo += page.extract_text() or ""

    pdf.close()

    resultado = {
        "leitura_atual": None,
        "consumo_kwh": None,
        "energia_injetada": None,
        "saldo_acumulado": None,
        "numero_uc": None,
    }

    # Numero da UC
    uc_match = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', texto_completo)
    if uc_match:
        resultado["numero_uc"] = uc_match.group(1)

    # Leitura Atual - busca na tabela do medidor (segundo numero apos o anterior)
    medidor_match = re.search(r'Ponta\s+(\d[\d.]*)\s+(\d[\d.]*)\s+\d+\s+(\d[\d.]*)', texto_completo)
    if medidor_match:
        resultado["leitura_atual"] = float(medidor_match.group(2).replace('.', ''))
        resultado["consumo_kwh"] = float(medidor_match.group(3).replace('.', ''))

    # Energia Injetada - tenta varias formas de capturar
    # Forma 1: linhas "Energia Atv Injetada" com quantidade KWH
    injetada_matches = re.findall(r'Energia Atv Injetada.*?KWH\s+([\d.,]+)', texto_completo)
    if injetada_matches:
        total_injetada = 0
        for val in injetada_matches:
            num = float(val.replace('.', '').replace(',', '.'))
            total_injetada += num
        resultado["energia_injetada"] = total_injetada

    # Forma 2: se nao achou, tenta pegar da tabela do medidor (mesma linha do consumo)
    if not resultado["energia_injetada"] and resultado["consumo_kwh"]:
        resultado["energia_injetada"] = resultado["consumo_kwh"]

    # Forma 3: busca "Energia INJETADA" no texto
    if not resultado["energia_injetada"]:
        inj2 = re.search(r'Energia\s+INJETADA.*?(\d[\d.,]*)', texto_completo)
        if inj2:
            resultado["energia_injetada"] = float(inj2.group(1).replace('.', '').replace(',', '.'))

    # Saldo Acumulado
    saldo_match = re.search(r'Saldo Acumulado:\s*([\d.]+)', texto_completo)
    if saldo_match:
        resultado["saldo_acumulado"] = float(saldo_match.group(1).replace('.', ''))

    return resultado