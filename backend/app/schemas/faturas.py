from pydantic import BaseModel
from typing import Optional
from datetime import date


class FaturaCreate(BaseModel):
    cliente_id: int
    cliente_uc_id: Optional[int] = None
    mes_referencia: date
    leitura_inicial: Optional[float] = None
    leitura_final: Optional[float] = None
    consumo_kwh: Optional[float] = None
    kwh_injetado: Optional[float] = None
    saldo_kwh: Optional[float] = None
    valor_kwh_aplicado: Optional[float] = None
    valor_total: Optional[float] = None
    desconto_sazonal: float = 0
    valor_final: Optional[float] = None
    data_vencimento: Optional[date] = None


class FaturaUpdate(BaseModel):
    leitura_inicial: Optional[float] = None
    leitura_final: Optional[float] = None
    consumo_kwh: Optional[float] = None
    kwh_injetado: Optional[float] = None
    saldo_kwh: Optional[float] = None
    valor_kwh_aplicado: Optional[float] = None
    valor_total: Optional[float] = None
    desconto_sazonal: Optional[float] = None
    valor_final: Optional[float] = None
    data_vencimento: Optional[date] = None
    status: Optional[str] = None


class GerarFaturasMes(BaseModel):
    mes_referencia: date