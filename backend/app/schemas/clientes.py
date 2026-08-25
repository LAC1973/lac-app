from pydantic import BaseModel
from typing import Optional
from datetime import date


class ClienteCreate(BaseModel):
    usina_id: Optional[int] = None
    item: Optional[int] = None
    nome: str
    nome_uc: Optional[str] = None
    numero_uc: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    identidade: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    dia_vencimento: int = 5
    valor_kwh: float = 0.75
    data_contratacao: Optional[date] = None
    poste: Optional[str] = None
    dia_leitura: Optional[int] = None
    activo: bool = True
    eh_agregado: bool = False
    dados_pagamento: Optional[str] = None
    pix: Optional[str] = None


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    nome_uc: Optional[str] = None
    numero_uc: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    identidade: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    dia_vencimento: Optional[int] = None
    valor_kwh: Optional[float] = None
    data_contratacao: Optional[date] = None
    poste: Optional[str] = None
    dia_leitura: Optional[int] = None
    activo: Optional[bool] = None
    eh_agregado: Optional[bool] = None
    dados_pagamento: Optional[str] = None
    pix: Optional[str] = None


class PercentualCreate(BaseModel):
    cliente_uc_id: Optional[int] = None
    cliente_id: Optional[int] = None
    usina_id: int
    percentual: float
    data_vigencia: date

class ClienteUCCreate(BaseModel):
    cliente_id: int
    usina_id: int
    nome_uc: Optional[str] = None
    numero_uc: Optional[str] = None
    numero_uc_novo: Optional[str] = None
    poste: Optional[str] = None
    item: Optional[int] = None
    dia_leitura: Optional[int] = None


class ClienteUCUpdate(BaseModel):
    nome_uc: Optional[str] = None
    numero_uc: Optional[str] = None
    numero_uc_novo: Optional[str] = None
    poste: Optional[str] = None
    item: Optional[int] = None
    dia_leitura: Optional[int] = None