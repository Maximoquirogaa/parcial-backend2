from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.repository import EditorialRepository


class EditorialesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.editoriales = EditorialRepository(session)
