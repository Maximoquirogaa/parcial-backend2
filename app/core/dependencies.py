"""
Dependencias de autenticación y autorización de FastAPI.

Reglas críticas (spec autorizacion):
- token SOLO de cookie 'access_token' — NUNCA de Authorization: Bearer
- roles vigentes verificados en la DB en cada petición (no confiar solo en el token)
- requiere_cambio_resuelto: 403 si debe_cambiar_password is True
"""
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decodificar_token
from app.modules.usuarios.models import AsignacionRol, Usuario


async def get_usuario_actual(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> Usuario:
    """
    Dependencia que extrae y verifica el usuario de la cookie 'access_token'.
    - 401 si no hay cookie
    - 401 si el token es inválido o venció
    - 401 si el usuario no existe o está inactivo
    """
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Se requiere cookie de sesión.",
        )

    try:
        payload = decodificar_token(access_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ha expirado. Inicie sesión nuevamente.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesión inválido.",
        )

    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesión malformado.",
        )

    stmt = select(Usuario).where(Usuario.email == email)
    result = await session.execute(stmt)
    usuario: Optional[Usuario] = result.scalar_one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo.",
        )

    return usuario


def requiere_rol(*roles: str):
    """
    Fábrica de dependencias que verifica roles vigentes en la DB.
    Los roles del token NO conceden permisos por sí solos.
    """
    async def _verificar_rol(
        usuario: Usuario = Depends(get_usuario_actual),
        session: AsyncSession = Depends(get_session),
    ) -> Usuario:
        ahora = datetime.now(timezone.utc)
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario.id,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
            AsignacionRol.rol.in_(list(roles)),
        )
        result = await session.execute(stmt)
        asignacion = result.scalar_one_or_none()

        if asignacion is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(roles)}.",
            )
        return usuario

    return _verificar_rol


async def requiere_cambio_resuelto(
    usuario: Usuario = Depends(get_usuario_actual),
) -> Usuario:
    """
    Dependencia de grupo: bloquea con 403 si el usuario tiene
    'debe_cambiar_password' en True.
    """
    if usuario.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña antes de continuar.",
        )
    return usuario


def get_roles_del_token(
    access_token: Optional[str] = Cookie(default=None),
) -> list[str]:
    """Extrae roles del token sin validar contra DB (solo para /auth/yo)."""
    if not access_token:
        return []
    try:
        payload = decodificar_token(access_token)
        return payload.get("roles", [])
    except jwt.InvalidTokenError:
        return []
