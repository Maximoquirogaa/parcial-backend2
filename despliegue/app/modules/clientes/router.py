from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteDetailRead,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    VentaResumenRead,
)
from app.modules.clientes.service import (
    create_cliente,
    create_perfil_cliente,
    get_cliente_by_id,
    get_ventas_de_cliente,
    update_cliente,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def post_cliente(
    payload: ClienteCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_cliente(session, payload)


@router.get("/{id}", response_model=ClienteDetailRead, status_code=status.HTTP_200_OK)
async def get_cliente(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_cliente_by_id(session, id)


@router.patch("/{id}", response_model=ClienteDetailRead, status_code=status.HTTP_200_OK)
async def patch_cliente(
    id: int,
    payload: ClienteUpdate,
    session: AsyncSession = Depends(get_session)
):
    return await update_cliente(session, id, payload)


@router.post("/{id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED)
async def post_cliente_perfil(
    id: int,
    payload: PerfilCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_perfil_cliente(session, id, payload)


@router.get("/{id}/ventas", response_model=list[VentaResumenRead], status_code=status.HTTP_200_OK)
async def get_cliente_ventas(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_ventas_de_cliente(session, id)

