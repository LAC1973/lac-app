from pydantic import BaseModel
from typing import Optional


class LeituraRegistro(BaseModel):
    fatura_id: int
    leitura_inicial: Optional[float] = None
    leitura_final: Optional[float] = None


class LeiturasBulk(BaseModel):
    registros: list[LeituraRegistro]