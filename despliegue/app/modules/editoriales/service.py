from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.libros.models import Libro


async def create_editorial(session: AsyncSession, data: EditorialCreate) -> Editorial:
    editorial = Editorial(**data.model_dump())
    session.add(editorial)
    try:
        await session.commit()
        await session.refresh(editorial)
        return editorial
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una editorial con ese nombre."
        )


async def get_editoriales(session: AsyncSession, limit: int, offset: int) -> Sequence[Editorial]:
    query = select(Editorial).order_by(Editorial.id).limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def get_editorial_by_id(session: AsyncSession, editorial_id: int) -> Editorial:
    editorial = await session.get(Editorial, editorial_id)
    if not editorial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Editorial con ID {editorial_id} no encontrada."
        )
    return editorial


async def update_editorial(
    session: AsyncSession,
    editorial_id: int,
    data: EditorialUpdate
) -> Editorial:
    editorial = await get_editorial_by_id(session, editorial_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(editorial, key, value)

    session.add(editorial)
    try:
        await session.commit()
        await session.refresh(editorial)
        return editorial
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo actualizar la editorial. Verifique que el nombre no esté duplicado."
        )


async def get_libros_de_editorial(session: AsyncSession, editorial_id: int) -> Sequence[Libro]:
    await get_editorial_by_id(session, editorial_id)
    query = select(Libro).where(Libro.editorial_id == editorial_id).order_by(Libro.id)
    result = await session.execute(query)
    return result.scalars().all()

