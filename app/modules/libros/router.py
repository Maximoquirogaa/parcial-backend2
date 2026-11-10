from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.dependencies import requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetailRead,
    LibroListRead,
    LibroUpdate,
    MovimientoStockRead,
    ReponerStockRequest,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.libros.service import (
    create_libro,
    delete_libro,
    get_libro_detail_by_id,
    get_libros_list,
    get_movimientos_libro,
    reponer_stock,
    update_libro,
)

# Catálogo público (sin sesión) y mutaciones protegidas (ADMIN).
router_publico = APIRouter(prefix="/libros", tags=["Libros"])
router = APIRouter(
    prefix="/libros",
    tags=["Libros"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


def get_uow(session: AsyncSession = Depends(get_session)) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


@router.post("/", response_model=LibroDetailRead, status_code=status.HTTP_201_CREATED)
async def post_libro(
    payload: LibroCreate,
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await create_libro(uow, payload)


@router_publico.get("/", response_model=Pagina[LibroListRead], status_code=status.HTTP_200_OK)
async def list_libros(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    titulo: Optional[str] = Query(None, description="Filtro insensible a mayúsculas por parte del título"),
    genero_id: Optional[int] = Query(None, description="Filtro por ID de género"),
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await get_libros_list(
        uow,
        params=params,
        titulo=titulo,
        genero_id=genero_id
    )


@router_publico.get("/{id}", response_model=LibroDetailRead, status_code=status.HTTP_200_OK)
async def get_libro(
    id: int,
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await get_libro_detail_by_id(uow, id)


@router.patch("/{id}", response_model=LibroDetailRead, status_code=status.HTTP_200_OK)
async def patch_libro(
    id: int,
    payload: LibroUpdate,
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await update_libro(uow, id, payload)


@router.post("/{id}/reponer", response_model=MovimientoStockRead, status_code=status.HTTP_200_OK)
async def post_reponer_stock(
    id: int,
    payload: ReponerStockRequest,
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await reponer_stock(uow, id, payload)


@router.get("/{id}/movimientos", response_model=Pagina[MovimientoStockRead], status_code=status.HTTP_200_OK)
async def get_libro_movimientos(
    id: int,
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    return await get_movimientos_libro(uow, id, params)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_libro_endpoint(
    id: int,
    uow: LibrosUnitOfWork = Depends(get_uow)
):
    await delete_libro(uow, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
