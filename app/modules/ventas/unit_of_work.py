from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.ventas.repository import VentaRepository


class VentasUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ventas = VentaRepository(session)
