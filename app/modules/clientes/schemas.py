from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteBase(BaseModel):
    nombre: str
    email: EmailStr

    model_config = ConfigDict(extra="forbid")


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None

    model_config = ConfigDict(extra="forbid")


class PerfilBase(BaseModel):
    telefono: str
    direccion: str

    model_config = ConfigDict(extra="forbid")


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
    usuario_id: Optional[int] = None
    perfil: Optional[PerfilRead] = None

    model_config = ConfigDict(from_attributes=True)


class VentaResumenRead(BaseModel):
    id: int
    fecha: datetime
    total: Decimal

    model_config = ConfigDict(from_attributes=True)
