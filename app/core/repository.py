from datetime import datetime, timezone
from typing import Any, Generic, Optional, Sequence, Type, TypeVar
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Repositorio base genérico.
    Recibe la sesión y la clase del modelo explícita (para introspección en tiempo de ejecución).
    Sus métodos de persistencia hacen flush() y NUNCA commit() ni close().
    """

    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        if model_cls is None:
            raise ValueError("Se requiere model_cls para inicializar el repositorio.")
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, id_: Any) -> Optional[T]:
        return await self.session.get(self.model_cls, id_)

    async def get_all(
        self,
        *whereclause,
        skip: int = 0,
        limit: Optional[int] = None,
        order_by: Optional[Any] = None
    ) -> Sequence[T]:
        stmt = select(self.model_cls)
        if whereclause:
            stmt = stmt.where(*whereclause)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, *whereclause) -> int:
        stmt = select(func.count()).select_from(self.model_cls)
        if whereclause:
            stmt = stmt.where(*whereclause)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T) -> T:
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class SoftDeleteRepository(BaseRepository[T]):
    """
    Repositorio para entidades con borrado lógico (columna borrado_en).
    Filtra automáticamente por borrado_en IS NULL en sus operaciones por defecto
    y ofrece métodos explícitos para incluir bajas o dar de baja lógica.
    """

    async def get_by_id(self, id_: Any) -> Optional[T]:
        entity = await self.session.get(self.model_cls, id_)
        if entity is not None and getattr(entity, "borrado_en", None) is not None:
            return None
        return entity

    async def get_by_id_including_deleted(self, id_: Any) -> Optional[T]:
        return await self.session.get(self.model_cls, id_)

    async def get_all(
        self,
        *whereclause,
        skip: int = 0,
        limit: Optional[int] = None,
        order_by: Optional[Any] = None
    ) -> Sequence[T]:
        filtros = [self.model_cls.borrado_en.is_(None)]
        if whereclause:
            filtros.extend(whereclause)
        return await super().get_all(*filtros, skip=skip, limit=limit, order_by=order_by)

    async def count(self, *whereclause) -> int:
        filtros = [self.model_cls.borrado_en.is_(None)]
        if whereclause:
            filtros.extend(whereclause)
        return await super().count(*filtros)

    async def soft_delete(self, entity: T) -> None:
        setattr(entity, "borrado_en", datetime.now(timezone.utc))
        await self.update(entity)
