from pydantic import BaseModel


class ConfiguracaoUpdate(BaseModel):
    valor: str
