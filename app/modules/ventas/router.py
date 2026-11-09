from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.paginacion import Pagina, ParametrosPagina, get_parametros_pagina
from app.modules.ventas.schemas import (
    VentaCreate,
    VentaDetailRead,
    VentaListRead,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork
from app.modules.ventas.service import (
    create_venta,
    enviar_comprobante_background,
    get_venta_detail_by_id,
    get_ventas_list,
)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def get_uow(session: AsyncSession = Depends(get_session)) -> VentasUnitOfWork:
    return VentasUnitOfWork(session)


@router.post("/", response_model=VentaDetailRead, status_code=status.HTTP_201_CREATED)
async def post_venta(
    payload: VentaCreate,
    background_tasks: BackgroundTasks,
    uow: VentasUnitOfWork = Depends(get_uow)
):
    """
    Registra una nueva venta con sus renglones calculados en servidor (RN-04 a RN-07).
    Encola la simulación del envío de comprobante en BackgroundTasks (Ejercicio 7).
    """
    venta_detalle = await create_venta(uow, payload)

    # Agendar aviso asincrónico simulado en segundo plano
    background_tasks.add_task(
        enviar_comprobante_background,
        cliente_email=venta_detalle.cliente.email,
        venta_id=venta_detalle.id,
        total=venta_detalle.total,
    )

    return venta_detalle


@router.get("/", response_model=Pagina[VentaListRead], status_code=status.HTTP_200_OK)
async def list_ventas(
    params: ParametrosPagina = Depends(get_parametros_pagina),
    uow: VentasUnitOfWork = Depends(get_uow)
):
    return await get_ventas_list(uow, params=params)


@router.get("/{id}", response_model=VentaDetailRead, status_code=status.HTTP_200_OK)
async def get_venta(
    id: int,
    uow: VentasUnitOfWork = Depends(get_uow)
):
    return await get_venta_detail_by_id(uow, id)
