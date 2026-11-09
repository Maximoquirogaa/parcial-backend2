from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database_readiness(session: AsyncSession) -> bool:
    """
    Ejecuta 'SELECT 1' de forma asincrónica sobre la base de datos para validar disponibilidad.
    """
    result = await session.execute(text("SELECT 1"))
    return result.scalar() == 1

