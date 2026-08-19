from pydantic import BaseModel
from datetime import date


class ProducaoRegistro(BaseModel):
    inversor_id: int
    data: date
    producao_kwh: float


class ProducaoBulk(BaseModel):
    registros: list[ProducaoRegistro]