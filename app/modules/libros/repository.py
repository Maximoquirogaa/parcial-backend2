from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock


class LibroRepository(SoftDeleteRepository[Libro]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Libro)

    async def get_by_isbn(self, isbn: str) -> Optional[Libro]:
        stmt = (
            select(Libro)
            .where(Libro.isbn == isbn, Libro.borrado_en.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_detail_by_id(self, libro_id: int) -> Optional[Libro]:
        stmt = (
            select(Libro)
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor),
            )
            .where(Libro.id == libro_id, Libro.borrado_en.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_detail_including_deleted(self, libro_id: int) -> Optional[Libro]:
        stmt = (
            select(Libro)
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor),
            )
            .where(Libro.id == libro_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar_con_filtros(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
        titulo: Optional[str] = None,
        genero_id: Optional[int] = None,
    ) -> Sequence[Libro]:
        stmt = (
            select(Libro)
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
            )
            .where(Libro.borrado_en.is_(None))
        )

        if titulo:
            stmt = stmt.where(Libro.titulo.ilike(f"%{titulo}%"))

        if genero_id is not None:
            stmt = stmt.where(Libro.genero_id == genero_id)

        stmt = stmt.order_by(Libro.id).offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_con_filtros(
        self,
        titulo: Optional[str] = None,
        genero_id: Optional[int] = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Libro)
            .where(Libro.borrado_en.is_(None))
        )

        if titulo:
            stmt = stmt.where(Libro.titulo.ilike(f"%{titulo}%"))

        if genero_id is not None:
            stmt = stmt.where(Libro.genero_id == genero_id)

        result = await self.session.execute(stmt)
        return result.scalar_one()


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MovimientoStock)

    async def listar_por_libro(
        self,
        libro_id: int,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> Sequence[MovimientoStock]:
        stmt = (
            select(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
            .order_by(MovimientoStock.cuando.desc())
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_por_libro(self, libro_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
