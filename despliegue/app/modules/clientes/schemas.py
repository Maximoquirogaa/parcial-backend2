from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteBase(BaseModel):
    nombre: str
    email: EmailStr


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None


class PerfilBase(BaseModel):
    telefono: str
    direccion: str


class PerfilCreate(PerfilBase):
    pass


class PerfilRead(PerfilBase):
    id: int
    cliente_id: int

    model_config = ConfigDict(from_attributes=True)


class ClienteRead(ClienteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ClienteDetailRead(ClienteBase):
    id: int
    perfil: Optional[PerfilRead] = None

    model_config = ConfigDict(from_attributes=True)


class VentaResumenRead(BaseModel):
    id: int
    fecha: datetime
    total: Decimal

    model_config = ConfigDict(from_attributes=True)

