"""
Servicio de autenticación: registro, login, logout, yo, cambiar-password.

Reglas críticas (spec autenticacion):
- hash_password ANTES de abrir cualquier transacción
- token SOLO en cookie HttpOnly 'access_token'
- rate limit: 5 intentos fallidos (email+ip) en 60s → 429
- intento_acceso en sesión/transacción INDEPENDIENTE (ver 7.1)
- hash ficticio para mitigar timing-attack cuando el correo no existe
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import crear_token, hash_password, verify_password
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegistroRequest,
    UsuarioActualRead,
)
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

async def contar_intentos_fallidos_recientes(session: AsyncSession, email: str, ip: str) -> int:
    hace_60s = datetime.now(timezone.utc) - timedelta(seconds=60)
    stmt = (
        select(func.count())
        .select_from(IntentoAcceso)
        .where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exitoso.is_(False),
            IntentoAcceso.cuando >= hace_60s,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Registro de intento de acceso — transacción INDEPENDIENTE
# ---------------------------------------------------------------------------

async def _registrar_intento(session_maker, email: str, ip: str, exitoso: bool) -> None:
    """
    7.1 — QUÉ HACE DISTINTO: usa su propia sesión y hace commit() explícito.
    POR QUÉ NO COMPARTE: si la transacción principal falla (password incorrecta,
    rate limit, etc.) el rollback borraría el registro del intento, perdiendo
    la evidencia necesaria para el rate-limiting y la auditoría.
    COSTO: abre una conexión adicional por petición de login, pero es aceptable
    porque garantiza que el intento queda persistido pase lo que pase.
    """
    async with session_maker() as session:
        intento = IntentoAcceso(email=email, ip=ip, exitoso=exitoso)
        session.add(intento)
        await session.commit()


# ---------------------------------------------------------------------------
# Registro atómico (usuario + rol CLIENTE + cliente)
# ---------------------------------------------------------------------------

async def registrar_usuario(
    request: Request,
    data: RegistroRequest,
) -> dict:
    """
    POST /auth/registro — crea en un único UoW: usuario, asignacion_rol CLIENTE, cliente.
    Hash calculado ANTES de abrir la transacción.
    """
    # hash ANTES de la transacción
    password_hash = await hash_password(data.password)

    session_maker = request.app.state.fabrica_sesiones
    async with session_maker() as session:
        async with session.begin():
            try:
                usuario = Usuario(
                    email=str(data.email),
                    password_hash=password_hash,
                    nombre=data.nombre,
                    activo=True,
                    debe_cambiar_password=False,
                )
                session.add(usuario)
                await session.flush()  # obtener usuario.id

                rol = AsignacionRol(
                    usuario_id=usuario.id,
                    rol="CLIENTE",
                )
                session.add(rol)

                cliente = Cliente(
                    nombre=data.nombre,
                    email=str(data.email),
                    usuario_id=usuario.id,
                )
                session.add(cliente)
                await session.flush()

            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe un usuario o cliente registrado con ese correo electrónico.",
                )

    return {"id": usuario.id, "email": usuario.email, "nombre": usuario.nombre}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
) -> LoginResponse:
    """
    POST /auth/login — orden: rate-limit → verificar → hash ficticio → intento → cookie
    """
    settings = get_settings()
    session_maker = request.app.state.fabrica_sesiones
    client_ip = request.client.host if request.client else "unknown"

    async with session_maker() as session:
        # 1. Rate limiting PRIMERO (antes de cualquier hash)
        fallos = await contar_intentos_fallidos_recientes(session, str(data.email), client_ip)
        if fallos >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Intente nuevamente en 60 segundos.",
                headers={"Retry-After": "60"},
            )

        # 2. Buscar usuario
        stmt = select(Usuario).where(Usuario.email == str(data.email))
        result = await session.execute(stmt)
        usuario: Optional[Usuario] = result.scalar_one_or_none()

    # 3. Verificar contraseña (fuera del with de sesión principal)
    #    Si el usuario no existe, usar el hash ficticio para tiempo constante
    if usuario is None:
        hash_ficticio = await obtener_hash_ficticio(request.app.state)
        await verify_password(data.password, hash_ficticio)  # mitigación de timing
        await _registrar_intento(session_maker, str(data.email), client_ip, exitoso=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")

    es_correcto = await verify_password(data.password, usuario.password_hash)
    await _registrar_intento(session_maker, str(data.email), client_ip, exitoso=es_correcto)

    if not es_correcto:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")

    if not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo.")

    # 4. Obtener roles vigentes para incluir en el token
    async with session_maker() as session:
        ahora = datetime.now(timezone.utc)
        stmt_roles = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario.id,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
        )
        result_roles = await session.execute(stmt_roles)
        roles_vigentes = [r.rol for r in result_roles.scalars().all()]

    # 5. Emitir JWT y setear cookie HttpOnly
    token = crear_token(sub=usuario.email, roles=roles_vigentes)
    max_age = settings.TOKEN_EXPIRE_MINUTES * 60

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        secure=settings.COOKIE_SECURE,
    )

    return LoginResponse(
        mensaje="Login exitoso.",
        debe_cambiar_password=usuario.debe_cambiar_password,
        expira_en_segundos=max_age,
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def logout(response: Response) -> dict:
    """POST /auth/logout — borra la cookie."""
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return {"mensaje": "Sesión cerrada."}


# ---------------------------------------------------------------------------
# Yo (GET /auth/yo)
# ---------------------------------------------------------------------------

async def obtener_yo(request: Request, usuario: Usuario, roles_token: list[str]) -> UsuarioActualRead:
    """GET /auth/yo — devuelve usuario, roles vigentes en DB y roles del token."""
    session_maker = request.app.state.fabrica_sesiones
    ahora = datetime.now(timezone.utc)

    async with session_maker() as session:
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario.id,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
        )
        result = await session.execute(stmt)
        roles_db = [r.rol for r in result.scalars().all()]

    return UsuarioActualRead(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        debe_cambiar_password=usuario.debe_cambiar_password,
        roles_vigentes=roles_db,
        roles_token=roles_token,
    )


# ---------------------------------------------------------------------------
# Cambiar password
# ---------------------------------------------------------------------------

async def cambiar_password(
    request: Request,
    usuario: Usuario,
    password_actual: str,
    password_nueva: str,
) -> dict:
    """POST /auth/cambiar-password — valida actual, hashea nueva, actualiza."""
    es_correcto = await verify_password(password_actual, usuario.password_hash)
    if not es_correcto:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual es incorrecta.",
        )

    # Hash ANTES de la transacción
    nuevo_hash = await hash_password(password_nueva)

    session_maker = request.app.state.fabrica_sesiones
    async with session_maker() as session:
        async with session.begin():
            stmt = select(Usuario).where(Usuario.id == usuario.id)
            result = await session.execute(stmt)
            usuario_db = result.scalar_one()

            usuario_db.password_hash = nuevo_hash
            usuario_db.debe_cambiar_password = False

            # Evento de seguridad en la MISMA transacción (7.2)
            evento = EventoSeguridad(
                tipo="cambio_password",
                usuario_afectado_id=usuario.id,
                actor_id=usuario.id,
                actor_tipo="USUARIO",
                detalle=f"El usuario {usuario.email} cambió su contraseña.",
            )
            session.add(evento)

    return {"mensaje": "Contraseña actualizada correctamente."}
