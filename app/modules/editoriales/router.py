from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.dependencies import requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
    LibroDeEditorialRead,
)
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.editoriales.service import (
    create_editorial,
    get_editorial_by_id,
    get_editoriales,
    get_libros_de_editorial,
    update_editorial,
)

router_publico = APIRouter(prefix="/editoriales", tags=["Editoriales"])
router = APIRouter(
    prefix="/editoriales",
    tags=["Editoriales"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


def get_uow(session: AsyncSession = Depends(get_session)) -> EditorialesUnitOfWork:
    return EditorialesUnitOfWork(session)


@router.post("/", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def post_editorial(
    payload: EditorialCreate,
    uow: EditorialesUnitOfWork = Depends(get_uow)
):
    return await create_editorial(uow, payload)


@router_publico.get("/", response_model=Pagina[EditorialRead], status_code=status.HTTP_200_OK)
async def list_editoriales(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: EditorialesUnitOfWork = Depends(get_uow)
):
    return await get_editoriales(uow, params)


@router_publico.get("/{id}", response_model=EditorialRead, status_code=status.HTTP_200_OK)
async def get_editorial(
    id: int,
    uow: EditorialesUnitOfWork = Depends(get_uow)
):
    return await get_editorial_by_id(uow, id)


@router.patch("/{id}", response_model=EditorialRead, status_code=status.HTTP_200_OK)
async def patch_editorial(
    id: int,
    payload: EditorialUpdate,
    uow: EditorialesUnitOfWork = Depends(get_uow)
):
    return await update_editorial(uow, id, payload)


@router_publico.get("/{id}/libros", response_model=Pagina[LibroDeEditorialRead], status_code=status.HTTP_200_OK)
async def get_editorial_libros(
    id: int,
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: EditorialesUnitOfWork = Depends(get_uow)
):
    return await get_libros_de_editorial(uow, id, params)
