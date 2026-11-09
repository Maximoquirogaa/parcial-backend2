from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository


class LibrosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)

    async def registrar_movimiento_stock(
        self,
        libro: Libro,
        cantidad: int,
        motivo: str,
        venta_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
    ) -> MovimientoStock:
        from app.modules.libros.service import registrar_movimiento_stock
        return await registrar_movimiento_stock(
            session_o_uow=self,
            libro=libro,
            cantidad=cantidad,
            motivo=motivo,
            venta_id=venta_id,
            usuario_id=usuario_id,
        )
