from pydantic import BaseModel
from datetime import date


class FinanciamentoCreate(BaseModel):
    nome: str
    valor_mensal: float
    mes_referencia: date
