from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from pydantic.functional_validators import AfterValidator

from app.core.security import validar_72_bytes

# Tipo reutilizable para contraseñas con límite de 72 bytes
Password72 = Annotated[str, AfterValidator(validar_72_bytes)]


class RegistroRequest(BaseModel):
    """Schema de entrada para auto-registro de cliente."""
    email: EmailStr
    password: Password72
    nombre: str

    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    """Schema de entrada para login."""
    email: EmailStr
    password: Password72

    model_config = ConfigDict(extra="forbid")


class LoginResponse(BaseModel):
    """Schema de respuesta del login — SIN token (va en cookie HttpOnly)."""
    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int

    model_config = ConfigDict(extra="forbid")


class CambiarPasswordRequest(BaseModel):
    """Schema de entrada para cambio de contraseña."""
    password_actual: Password72
    password_nueva: Password72

    model_config = ConfigDict(extra="forbid")


class RolVigenteRead(BaseModel):
    """Un rol vigente del usuario."""
    id: int
    rol: str

    model_config = ConfigDict(from_attributes=True)


class UsuarioActualRead(BaseModel):
    """Respuesta de GET /auth/yo"""
    id: int
    email: str
    nombre: str
    debe_cambiar_password: bool
    roles_vigentes: list[str]   # roles actuales en DB
    roles_token: list[str]      # roles que declara el token

    model_config = ConfigDict(from_attributes=True)


class MensajeResponse(BaseModel):
    """Respuesta genérica de mensaje."""
    mensaje: str

    model_config = ConfigDict(from_attributes=True)
