import asyncio
from decimal import Decimal
import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro
from app.modules.libros.service import registrar_movimiento_stock
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    ClienteEnVentaRead,
    RenglonRead,
    VentaCreate,
    VentaDetailRead,
    VentaListRead,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork

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


async def get_venta_detail_by_id(uow: VentasUnitOfWork, venta_id: int) -> VentaDetailRead:
    """
    Detalle de venta con cliente, renglones y libros resueltos con selectinload
    (número fijo de consultas, sin N+1, incluso con libros dados de baja).
    """
    async with uow:
        venta = await uow.ventas.get_detail_by_id(venta_id)
        if not venta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venta con ID {venta_id} no encontrada."
            )
        return _build_venta_detail_read(venta)


async def create_venta(uow: VentasUnitOfWork, data: VentaCreate) -> VentaDetailRead:
    """
    Crea una venta con sus renglones dentro de una transacción atómica del UoW:
    - Valida cliente y libros (409 si no existen o están dados de baja).
    - Valida cantidades y stock suficiente (409 si insuficiente).
    - Copia precio unitario y calcula total.
    - Descuenta stock mediante el punto único `registrar_movimiento_stock`.
    """
    async with uow:
        # Verificar cliente
        cliente = await uow.session.get(Cliente, data.cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error de integridad: el cliente indicado no existe o los datos son inválidos."
            )

        # Consultar los libros indicados
        libro_ids = [r.libro_id for r in data.renglones]
        stmt_libros = select(Libro).where(Libro.id.in_(libro_ids))
        result_libros = await uow.session.execute(stmt_libros)
        libros_dict = {libro.id: libro for libro in result_libros.scalars().all()}

        # Validar existencia y vigencia de libros
        for lid in libro_ids:
            if lid not in libros_dict or libros_dict[lid].borrado_en is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El libro con ID {lid} no existe en el catálogo o fue dado de baja."
                )

        # Validar stock suficiente
        for item in data.renglones:
            libro = libros_dict[item.libro_id]
            if libro.stock < item.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Stock insuficiente para el libro '{libro.titulo}'. Stock disponible: {libro.stock}, solicitado: {item.cantidad}."
                )

        # Calcular total y armar venta con renglones
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
        try:
            await uow.ventas.add(venta)

            # Descontar stock usando el punto único de mutación por cada renglón
            for item in data.renglones:
                libro = libros_dict[item.libro_id]
                await registrar_movimiento_stock(
                    uow,
                    libro=libro,
                    cantidad=-item.cantidad,
                    motivo="Venta",
                    venta_id=venta.id,
                )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error de integridad: el cliente indicado no existe o los datos son inválidos."
            )

        detailed = await uow.ventas.get_detail_by_id(venta.id)
        return _build_venta_detail_read(detailed)


async def get_ventas_list(
    uow: VentasUnitOfWork,
    params: ParametrosPagina,
) -> Pagina[VentaListRead]:
    async with uow:
        total = await uow.ventas.count()
        skip = (params.page - 1) * params.size
        ventas = await uow.ventas.listar(skip=skip, limit=params.size)
        items_read = [VentaListRead.model_validate(v) for v in ventas]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
