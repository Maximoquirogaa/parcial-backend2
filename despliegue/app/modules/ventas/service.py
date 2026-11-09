import asyncio
from decimal import Decimal
import logging
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    ClienteEnVentaRead,
    RenglonRead,
    VentaCreate,
    VentaDetailRead,
)

logger = logging.getLogger("libreria.ventas")


async def enviar_comprobante_background(cliente_email: str, venta_id: int, total: Decimal) -> None:
    """
    Tarea en segundo plano simulada con asyncio.sleep(0.5) y log (Ejercicio 7).
    Corre después de enviar la respuesta sin bloquear el servidor.
    """
    await asyncio.sleep(0.5)
    logger.info(
        f"[Segundo Plano] Comprobante de venta #{venta_id} por ${total:.2f} enviado al cliente: {cliente_email}"
    )


def _build_venta_detail_read(venta: Venta) -> VentaDetailRead:
    renglones_dto = [
        RenglonRead(
            libro_id=r.libro_id,
            titulo=r.libro.titulo if r.libro else "Desconocido",
            cantidad=r.cantidad,
            precio_unitario=r.precio_unitario,
            subtotal=r.precio_unitario * r.cantidad,
        )
        for r in venta.renglones
    ]

    return VentaDetailRead(
        id=venta.id,
        fecha=venta.fecha,
        total=venta.total,
        cliente=ClienteEnVentaRead(
            id=venta.cliente.id,
            nombre=venta.cliente.nombre,
            email=venta.cliente.email,
        ),
        renglones=renglones_dto,
    )


async def get_venta_detail_by_id(session: AsyncSession, venta_id: int) -> VentaDetailRead:
    """
    Detalle de venta con cliente y renglones resueltos con número fijo de consultas
    (joinedload para cliente y libro, selectinload para renglones). Sin N+1 (Ejercicio 6).
    """
    stmt = (
        select(Venta)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
        .where(Venta.id == venta_id)
    )
    result = await session.execute(stmt)
    venta = result.scalar_one_or_none()

    if not venta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Venta con ID {venta_id} no encontrada."
        )

    return _build_venta_detail_read(venta)


async def create_venta(session: AsyncSession, data: VentaCreate) -> VentaDetailRead:
    """
    Crea una venta con sus renglones (RN-04):
    - Copia el precio del libro al registrar la venta (RN-06).
    - Calcula el total como suma de cantidad * precio_unitario (RN-07).
    - Si el cliente o algún libro no existen responde 409 (Caso C-05).
    """
    # Consultar los libros indicados para copiar sus precios unitarios actuales
    libro_ids = [r.libro_id for r in data.renglones]
    stmt_libros = select(Libro).where(Libro.id.in_(libro_ids))
    result_libros = await session.execute(stmt_libros)
    libros_dict = {libro.id: libro for libro in result_libros.scalars().all()}

    # Si algún libro solicitado no existe en la base, responder 409 (C-05)
    for lid in libro_ids:
        if lid not in libros_dict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El libro con ID {lid} no existe en el catálogo."
            )

    # Calcular total y armar renglones de composición
    total_acumulado = Decimal("0.00")
    venta = Venta(cliente_id=data.cliente_id, total=Decimal("0.00"))

    for item in data.renglones:
        libro = libros_dict[item.libro_id]
        precio_unitario = libro.precio
        subtotal = precio_unitario * item.cantidad
        total_acumulado += subtotal

        renglon = RenglonVenta(
            venta=venta,
            libro_id=item.libro_id,
            cantidad=item.cantidad,
            precio_unitario=precio_unitario,
        )
        venta.renglones.append(renglon)

    venta.total = total_acumulado
    session.add(venta)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error de integridad: el cliente indicado no existe o los datos son inválidos."
        )

    return await get_venta_detail_by_id(session, venta.id)


async def get_ventas_list(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> Sequence[Venta]:
    """Listado paginado de ventas (RN-10)."""
    stmt = select(Venta).order_by(Venta.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()

