from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PermissaoModulo(BaseModel):
    modulo: str
    pode_visualizar: bool = False
    pode_criar: bool = False
    pode_editar: bool = False
    pode_excluir: bool = False


class CreateFuncionarioRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    permissoes: list[PermissaoModulo] = []


class UpdateFuncionarioRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    activo: Optional[bool] = None


class UpdatePermissoesRequest(BaseModel):
    permissoes: list[PermissaoModulo]


class ResetPasswordRequest(BaseModel):
    new_password: str