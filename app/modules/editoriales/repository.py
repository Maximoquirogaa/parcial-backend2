from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro


class EditorialRepository(BaseRepository[Editorial]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Editorial)

    async def get_by_nombre(self, nombre: str) -> Optional[Editorial]:
        stmt = select(Editorial).where(Editorial.nombre == nombre)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_libros(
        self,
        editorial_id: int,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[Libro]:
        stmt = (
            select(Libro)
            .where(Libro.editorial_id == editorial_id, Libro.borrado_en.is_(None))
            .order_by(Libro.id)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_libros(self, editorial_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Libro)
            .where(Libro.editorial_id == editorial_id, Libro.borrado_en.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
