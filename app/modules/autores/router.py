from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.autores.schemas import (
    AutorCreate,
    AutorRead,
    AutorUpdate,
    LibroDeAutorRead,
)
from app.modules.autores.unit_of_work import AutoresUnitOfWork
from app.modules.autores.service import (
    create_autor,
    get_autor_by_id,
    get_autores,
    get_libros_de_autor,
    update_autor,
)

router = APIRouter(prefix="/autores", tags=["Autores"])


def get_uow(session: AsyncSession = Depends(get_session)) -> AutoresUnitOfWork:
    return AutoresUnitOfWork(session)


@router.post("/", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def post_autor(
    payload: AutorCreate,
    uow: AutoresUnitOfWork = Depends(get_uow)
):
    return await create_autor(uow, payload)


@router.get("/", response_model=Pagina[AutorRead], status_code=status.HTTP_200_OK)
async def list_autores(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: AutoresUnitOfWork = Depends(get_uow)
):
    return await get_autores(uow, params)


@router.get("/{id}", response_model=AutorRead, status_code=status.HTTP_200_OK)
async def get_autor(
    id: int,
    uow: AutoresUnitOfWork = Depends(get_uow)
):
    return await get_autor_by_id(uow, id)


@router.patch("/{id}", response_model=AutorRead, status_code=status.HTTP_200_OK)
async def patch_autor(
    id: int,
    payload: AutorUpdate,
    uow: AutoresUnitOfWork = Depends(get_uow)
):
    return await update_autor(uow, id, payload)


@router.get("/{id}/libros", response_model=Pagina[LibroDeAutorRead], status_code=status.HTTP_200_OK)
async def get_autor_libros(
    id: int,
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: AutoresUnitOfWork = Depends(get_uow)
):
    return await get_libros_de_autor(uow, id, params)
