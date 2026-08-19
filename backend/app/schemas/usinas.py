from pydantic import BaseModel
from typing import Optional
from datetime import date


class InversorBase(BaseModel):
    marca: str
    modelo: Optional[str] = None
    potencia_kwp: float
    tipo: str = "principal"
    ordem: int = 1


class InversorResponse(InversorBase):
    id: int
    usina_id: int


class PlacaBase(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    potencia_wp: float
    quantidade: int = 1


class PlacaResponse(PlacaBase):
    id: int
    usina_id: int


class UsinaCreate(BaseModel):
    nome: str
    proprietario_nome: Optional[str] = None
    proprietario_cpf: Optional[str] = None
    proprietario_identidade: Optional[str] = None
    proprietario_celular: Optional[str] = None
    proprietario_endereco: Optional[str] = None
    uc_poste: Optional[str] = None
    potencia_kwp: Optional[float] = None
    data_leitura: Optional[int] = None
    inicio_operacao: Optional[date] = None
    observacoes: Optional[str] = None
    engenheiro_nome: Optional[str] = None
    engenheiro_crea: Optional[str] = None


class UsinaUpdate(UsinaCreate):
    nome: Optional[str] = None