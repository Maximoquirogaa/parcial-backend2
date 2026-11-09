from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = AsignacionRolRepository(session)
        self.eventos = EventoSeguridadRepository(session)
