from pydantic import BaseModel
from typing import Optional
from datetime import date


class DespesaCreate(BaseModel):
    categoria: str
    subcategoria: Optional[str] = None
    valor_mensal: float
    mes_referencia: date
