from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository


class AutoresUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.autores = AutorRepository(session)
