from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Optional[Usuario]:
        from sqlalchemy import select
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AsignacionRol)

    async def get_vigentes_por_usuario(self, usuario_id: int) -> Sequence[AsignacionRol]:
        ahora = datetime.now(timezone.utc)
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_vigente_por_rol(self, usuario_id: int, rol: str) -> Optional[AsignacionRol]:
        ahora = datetime.now(timezone.utc)
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
            (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_admins_vigentes(self) -> int:
        ahora = datetime.now(timezone.utc)
        stmt = (
            select(func.count())
            .select_from(AsignacionRol)
            .where(
                AsignacionRol.rol == "ADMIN",
                AsignacionRol.revocada_en.is_(None),
                (AsignacionRol.vence_en.is_(None)) | (AsignacionRol.vence_en > ahora),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EventoSeguridad)

    async def listar_por_usuario(
        self, usuario_id: int, skip: int = 0, limit: Optional[int] = None
    ) -> Sequence[EventoSeguridad]:
        stmt = (
            select(EventoSeguridad)
            .where(EventoSeguridad.usuario_afectado_id == usuario_id)
            .order_by(EventoSeguridad.cuando.desc())
            .offset(skip)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_por_usuario(self, usuario_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(EventoSeguridad)
            .where(EventoSeguridad.usuario_afectado_id == usuario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
