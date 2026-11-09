from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict
from typing import Annotated
from pydantic.functional_validators import AfterValidator
from app.core.security import validar_72_bytes

Password72 = Annotated[str, AfterValidator(validar_72_bytes)]


class UsuarioPersonalCreate(BaseModel):
    """Alta de personal con contraseña provisoria."""
    email: str
    nombre: str
    password: Password72

    model_config = ConfigDict(extra="forbid")


class AsignacionRolCreate(BaseModel):
    """Asignación de rol con vencimiento opcional."""
    rol: str
    vence_en: Optional[datetime] = None

    model_config = ConfigDict(extra="forbid")


class AsignacionRolRead(BaseModel):
    """Lectura de una asignación de rol."""
    id: int
    rol: str
    asignada_en: datetime
    vence_en: Optional[datetime] = None
    revocada_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventoSeguridadRead(BaseModel):
    """Lectura de un evento de seguridad."""
    id: int
    tipo: str
    actor_tipo: str
    actor_id: Optional[int] = None
    usuario_afectado_id: Optional[int] = None
    detalle: Optional[str] = None
    cuando: datetime

    model_config = ConfigDict(from_attributes=True)


class UsuarioRead(BaseModel):
    """Lectura básica de usuario."""
    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool

    model_config = ConfigDict(from_attributes=True)
