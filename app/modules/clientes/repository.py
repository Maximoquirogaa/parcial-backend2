from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.ventas.models import Venta


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Cliente)

    async def get_by_id_with_perfil(self, cliente_id: int) -> Optional[Cliente]:
        stmt = (
            select(Cliente)
            .options(
                joinedload(Cliente.perfil),
                joinedload(Cliente.usuario),
            )
            .where(Cliente.id == cliente_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar_con_perfil(
        self,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[Cliente]:
        stmt = (
            select(Cliente)
            .options(joinedload(Cliente.perfil))
            .order_by(Cliente.id)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, email: str) -> Optional[Cliente]:
        stmt = select(Cliente).where(Cliente.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_usuario_id(self, usuario_id: int) -> Optional[Cliente]:
        stmt = (
            select(Cliente)
            .options(joinedload(Cliente.perfil))
            .where(Cliente.usuario_id == usuario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_ventas_de_cliente(
        self,
        cliente_id: int,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[Venta]:
        stmt = (
            select(Venta)
            .where(Venta.cliente_id == cliente_id)
            .order_by(Venta.id)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_ventas_de_cliente(self, cliente_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Venta)
            .where(Venta.cliente_id == cliente_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, PerfilCliente)

    async def get_by_cliente_id(self, cliente_id: int) -> Optional[PerfilCliente]:
        stmt = select(PerfilCliente).where(PerfilCliente.cliente_id == cliente_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
