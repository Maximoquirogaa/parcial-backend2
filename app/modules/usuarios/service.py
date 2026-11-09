"""
Servicio de gestión de usuarios y roles (módulo /usuarios).
Solo accesible con rol ADMIN.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.core.security import hash_password
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.schemas import (
    AsignacionRolCreate,
    AsignacionRolRead,
    EventoSeguridadRead,
    UsuarioPersonalCreate,
    UsuarioRead,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork


async def crear_personal(
    uow: UsuariosUnitOfWork,
    data: UsuarioPersonalCreate,
    actor_id: int,
) -> UsuarioRead:
    """Alta de personal con password provisorio y debe_cambiar_password=True."""
    # hash ANTES de la transacción
    password_hash = await hash_password(data.password)

    async with uow:
        try:
            usuario = Usuario(
                email=data.email,
                password_hash=password_hash,
                nombre=data.nombre,
                activo=True,
                debe_cambiar_password=True,
            )
            await uow.usuarios.add(usuario)

            # Evento en MISMO UoW (7.2)
            evento = EventoSeguridad(
                tipo="alta_personal",
                usuario_afectado_id=usuario.id,
                actor_id=actor_id,
                actor_tipo="USUARIO",
                detalle=f"Alta de personal: {usuario.email}",
            )
            await uow.eventos.add(evento)

        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario registrado con ese correo electrónico.",
            )

    return UsuarioRead.model_validate(usuario)


async def obtener_roles_usuario(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
) -> list[AsignacionRolRead]:
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado.",
            )
        roles = await uow.roles.get_vigentes_por_usuario(usuario_id)
        return [AsignacionRolRead.model_validate(r) for r in roles]


async def asignar_rol(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
    data: AsignacionRolCreate,
    actor_id: int,
) -> AsignacionRolRead:
    """Asigna un rol. Si vence_en está en el pasado o sin TZ → 422."""
    if data.vence_en is not None:
        # Validar timezone
        if data.vence_en.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El campo 'vence_en' debe incluir información de zona horaria.",
            )
        # Validar que sea futuro
        if data.vence_en <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El campo 'vence_en' debe ser una fecha futura.",
            )

    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado.",
            )

        # Si hay una asignación vencida, cerrarla
        ahora = datetime.now(timezone.utc)
        stmt_vencida = None
        try:
            from sqlalchemy import select
            from app.modules.usuarios.models import AsignacionRol as AR
            stmt_v = (
                select(AR)
                .where(
                    AR.usuario_id == usuario_id,
                    AR.rol == data.rol,
                    AR.revocada_en.is_(None),
                    AR.vence_en <= ahora,
                )
            )
            result_v = await uow.session.execute(stmt_v)
            asig_vencida = result_v.scalar_one_or_none()
            if asig_vencida:
                asig_vencida.revocada_en = ahora
                await uow.session.flush()
        except Exception:
            pass

        try:
            rol = AsignacionRol(
                usuario_id=usuario_id,
                rol=data.rol,
                vence_en=data.vence_en,
            )
            await uow.roles.add(rol)

            # Evento en MISMO UoW (7.2)
            evento = EventoSeguridad(
                tipo="asignacion_rol",
                usuario_afectado_id=usuario_id,
                actor_id=actor_id,
                actor_tipo="USUARIO",
                detalle=f"Asignación de rol {data.rol} al usuario {usuario.email}.",
            )
            await uow.eventos.add(evento)

        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El usuario ya tiene el rol '{data.rol}' vigente.",
            )

    return AsignacionRolRead.model_validate(rol)


async def revocar_rol(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
    rol: str,
    actor_id: int,
) -> dict:
    """Revoca un rol. No borra la fila — pone revocada_en."""
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado.",
            )

        asignacion = await uow.roles.get_vigente_por_rol(usuario_id, rol)
        if not asignacion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario no tiene el rol '{rol}' vigente.",
            )

        # Autoprotección ADMIN (6.5)
        if rol == "ADMIN":
            if usuario_id == actor_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un administrador no puede revocar su propio rol ADMIN.",
                )
            count = await uow.roles.count_admins_vigentes()
            if count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede revocar el último administrador vigente.",
                )

        asignacion.revocada_en = datetime.now(timezone.utc)
        await uow.session.flush()

        # Evento en MISMO UoW (7.2)
        evento = EventoSeguridad(
            tipo="revocacion_rol",
            usuario_afectado_id=usuario_id,
            actor_id=actor_id,
            actor_tipo="USUARIO",
            detalle=f"Revocación de rol {rol} del usuario {usuario.email}.",
        )
        await uow.eventos.add(evento)

    return {"mensaje": f"Rol '{rol}' revocado correctamente."}


async def listar_eventos_usuario(
    uow: UsuariosUnitOfWork,
    usuario_id: int,
    params: ParametrosPagina,
) -> Pagina[EventoSeguridadRead]:
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado.",
            )
        total = await uow.eventos.count_por_usuario(usuario_id)
        skip = (params.page - 1) * params.size
        eventos = await uow.eventos.listar_por_usuario(usuario_id, skip=skip, limit=params.size)
        items_read = [EventoSeguridadRead.model_validate(e) for e in eventos]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
