from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteDetailRead,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    VentaResumenRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.clientes.service import (
    create_cliente,
    create_perfil_cliente,
    get_cliente_by_id,
    get_clientes,
    get_ventas_de_cliente,
    update_cliente,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def get_uow(session: AsyncSession = Depends(get_session)) -> ClientesUnitOfWork:
    return ClientesUnitOfWork(session)


@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def post_cliente(
    payload: ClienteCreate,
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await create_cliente(uow, payload)


@router.get("/", response_model=Pagina[ClienteDetailRead], status_code=status.HTTP_200_OK)
async def list_clientes(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await get_clientes(uow, params)


@router.get("/{id}", response_model=ClienteDetailRead, status_code=status.HTTP_200_OK)
async def get_cliente(
    id: int,
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await get_cliente_by_id(uow, id)


@router.patch("/{id}", response_model=ClienteDetailRead, status_code=status.HTTP_200_OK)
async def patch_cliente(
    id: int,
    payload: ClienteUpdate,
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await update_cliente(uow, id, payload)


@router.post("/{id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED)
async def post_cliente_perfil(
    id: int,
    payload: PerfilCreate,
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await create_perfil_cliente(uow, id, payload)


@router.get("/{id}/ventas", response_model=Pagina[VentaResumenRead], status_code=status.HTTP_200_OK)
async def get_cliente_ventas(
    id: int,
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: ClientesUnitOfWork = Depends(get_uow)
):
    return await get_ventas_de_cliente(uow, id, params)
