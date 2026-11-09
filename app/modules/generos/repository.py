from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro


class GeneroRepository(BaseRepository[Genero]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Genero)

    async def get_by_nombre(self, nombre: str) -> Optional[Genero]:
        stmt = select(Genero).where(Genero.nombre == nombre)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_libros(
        self,
        genero_id: int,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[Libro]:
        stmt = (
            select(Libro)
            .where(Libro.genero_id == genero_id, Libro.borrado_en.is_(None))
            .order_by(Libro.id)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_libros(self, genero_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Libro)
            .where(Libro.genero_id == genero_id, Libro.borrado_en.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
