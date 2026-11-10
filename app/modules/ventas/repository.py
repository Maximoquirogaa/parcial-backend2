from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Venta)

    async def get_detail_by_id(self, venta_id: int) -> Optional[Venta]:
        stmt = (
            select(Venta)
            .options(
                selectinload(Venta.cliente),
                selectinload(Venta.renglones).selectinload(RenglonVenta.libro),
            )
            .where(Venta.id == venta_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar(
        self,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[Venta]:
        stmt = select(Venta).order_by(Venta.id).offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def listar_por_usuario(
        self,
        usuario_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Sequence[Venta]:
        stmt = (
            select(Venta)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .where(Cliente.usuario_id == usuario_id)
            .order_by(Venta.id)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_por_usuario(self, usuario_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Venta)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .where(Cliente.usuario_id == usuario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
