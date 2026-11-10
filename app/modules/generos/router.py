from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.dependencies import requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.generos.schemas import GeneroCreate, GeneroRead, LibroDeGeneroRead
from app.modules.generos.unit_of_work import GenerosUnitOfWork
from app.modules.generos.service import (
    create_genero,
    get_generos,
    get_libros_de_genero,
)

router_publico = APIRouter(prefix="/generos", tags=["Géneros"])
router = APIRouter(
    prefix="/generos",
    tags=["Géneros"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


def get_uow(session: AsyncSession = Depends(get_session)) -> GenerosUnitOfWork:
    return GenerosUnitOfWork(session)


@router.post("/", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def post_genero(
    payload: GeneroCreate,
    uow: GenerosUnitOfWork = Depends(get_uow)
):
    return await create_genero(uow, payload)


@router_publico.get("/", response_model=Pagina[GeneroRead], status_code=status.HTTP_200_OK)
async def list_generos(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: GenerosUnitOfWork = Depends(get_uow)
):
    return await get_generos(uow, params)


@router_publico.get("/{id}/libros", response_model=Pagina[LibroDeGeneroRead], status_code=status.HTTP_200_OK)
async def get_genero_libros(
    id: int,
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: GenerosUnitOfWork = Depends(get_uow)
):
    return await get_libros_de_genero(uow, id, params)
