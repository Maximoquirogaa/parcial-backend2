from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.modules.ventas.schemas import (
    VentaCreate,
    VentaDetailRead,
    VentaListRead,
)
from app.modules.ventas.service import (
    create_venta,
    enviar_comprobante_background,
    get_venta_detail_by_id,
    get_ventas_list,
)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


@router.post("/", response_model=VentaDetailRead, status_code=status.HTTP_201_CREATED)
async def post_venta(
    payload: VentaCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Registra una nueva venta con sus renglones calculados en servidor (RN-04 a RN-07).
    Encola la simulación del envío de comprobante en BackgroundTasks (Ejercicio 7).
    """
    venta_detalle = await create_venta(session, payload)

    # Agendar aviso asincrónico simulado en segundo plano
    background_tasks.add_task(
        enviar_comprobante_background,
        cliente_email=venta_detalle.cliente.email,
        venta_id=venta_detalle.id,
        total=venta_detalle.total,
    )

    return venta_detalle


@router.get("/", response_model=list[VentaListRead], status_code=status.HTTP_200_OK)
async def list_ventas(
    limit: int = Query(20, ge=1, le=100, description="Paginación: cantidad máxima (1-100)"),
    offset: int = Query(0, ge=0, description="Paginación: desplazamiento desde 0"),
    session: AsyncSession = Depends(get_session)
):
    return await get_ventas_list(session, limit=limit, offset=offset)


@router.get("/{id}", response_model=VentaDetailRead, status_code=status.HTTP_200_OK)
async def get_venta(
    id: int,
    session: AsyncSession = Depends(get_session)
):
    return await get_venta_detail_by_id(session, id)

