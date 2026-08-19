from pydantic import BaseModel
from typing import Optional
from datetime import date


class ReciboCreate(BaseModel):
    cliente_id: int
    mes_referencia: date
    data_pagamento: date
    valor_pago: float
    forma_pagamento: str = "PIX"
    observacoes: Optional[str] = None


class ReciboUpdate(BaseModel):
    data_pagamento: Optional[date] = None
    valor_pago: Optional[float] = None
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None