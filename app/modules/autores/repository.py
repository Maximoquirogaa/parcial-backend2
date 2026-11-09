from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.autores.models import Autor
from app.modules.libros.models import Libro, LibroAutor


class AutorRepository(BaseRepository[Autor]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Autor)

    async def get_libros_de_autor(
        self,
        autor_id: int,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[LibroAutor]:
        stmt = (
            select(LibroAutor)
            .join(Libro, LibroAutor.libro_id == Libro.id)
            .options(joinedload(LibroAutor.libro))
            .where(LibroAutor.autor_id == autor_id, Libro.borrado_en.is_(None))
            .order_by(LibroAutor.orden)
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_libros_de_autor(self, autor_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(LibroAutor)
            .join(Libro, LibroAutor.libro_id == Libro.id)
            .where(LibroAutor.autor_id == autor_id, Libro.borrado_en.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
