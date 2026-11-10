"""Router del módulo `usuarios` y del historial de eventos de seguridad.

Todo el grupo exige rol ADMIN; la sesión y el cambio obligatorio de
contraseña los controla el grupo protegido montado en `main.py`.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_usuario_actual, requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    AsignacionRolCreate,
    AsignacionRolRead,
    EventoSeguridadRead,
    UsuarioPersonalCreate,
    UsuarioRead,
)
from app.modules.usuarios.service import (
    asignar_rol,
    crear_personal,
    listar_eventos,
    obtener_roles_usuario,
    revocar_rol,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)

eventos_router = APIRouter(
    prefix="/eventos",
    tags=["Eventos de seguridad"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


def get_uow(session: AsyncSession = Depends(get_session)) -> UsuariosUnitOfWork:
    return UsuariosUnitOfWork(session)


@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def post_usuario(
    payload: UsuarioPersonalCreate,
    actor: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_uow),
):
    """Alta de personal con contraseña provisoria y cambio obligatorio."""
    return await crear_personal(uow, payload, actor_id=actor.id)


@router.get(
    "/{id}/roles",
    response_model=list[AsignacionRolRead],
    status_code=status.HTTP_200_OK,
)
async def get_roles(
    id: int,
    uow: UsuariosUnitOfWork = Depends(get_uow),
):
    """Roles vigentes del usuario (404 si el usuario no existe)."""
    return await obtener_roles_usuario(uow, id)


@router.post(
    "/{id}/roles",
    response_model=AsignacionRolRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_rol(
    id: int,
    payload: AsignacionRolCreate,
    actor: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_uow),
):
    """Asigna un rol con vencimiento opcional."""
    return await asignar_rol(uow, id, payload, actor_id=actor.id)


@router.delete("/{id}/roles/{rol}", status_code=status.HTTP_200_OK)
async def delete_rol(
    id: int,
    rol: str,
    actor: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_uow),
):
    """Revoca un rol sin borrar la fila (marca `revocada_en`)."""
    return await revocar_rol(uow, id, rol, actor_id=actor.id)


@eventos_router.get("", response_model=Pagina[EventoSeguridadRead], status_code=status.HTTP_200_OK)
async def get_eventos(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: UsuariosUnitOfWork = Depends(get_uow),
):
    """Historial paginado de eventos de seguridad."""
    return await listar_eventos(uow, params)
