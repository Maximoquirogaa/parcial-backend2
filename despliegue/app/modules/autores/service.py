from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate, LibroDeAutorRead
from app.modules.libros.models import LibroAutor


async def create_autor(session: AsyncSession, data: AutorCreate) -> Autor:
    autor = Autor(**data.model_dump())
    session.add(autor)
    await session.commit()
    await session.refresh(autor)
    return autor


async def get_autor_by_id(session: AsyncSession, autor_id: int) -> Autor:
    autor = await session.get(Autor, autor_id)
    if not autor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Autor con ID {autor_id} no encontrado."
        )
    return autor


async def update_autor(session: AsyncSession, autor_id: int, data: AutorUpdate) -> Autor:
    autor = await get_autor_by_id(session, autor_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(autor, key, value)

    session.add(autor)
    await session.commit()
    await session.refresh(autor)
    return autor


async def get_libros_de_autor(session: AsyncSession, autor_id: int) -> list[LibroDeAutorRead]:
    await get_autor_by_id(session, autor_id)
    # Carga anticipada de la relación a uno con joinedload para evitar N+1
    query = (
        select(LibroAutor)
        .options(joinedload(LibroAutor.libro))
        .where(LibroAutor.autor_id == autor_id)
        .order_by(LibroAutor.orden)
    )
    result = await session.execute(query)
    autorias = result.scalars().all()

    return [
        LibroDeAutorRead(
            id=autoria.libro.id,
            isbn=autoria.libro.isbn,
            titulo=autoria.libro.titulo,
            rol=autoria.rol,
            orden=autoria.orden
        )
        for autoria in autorias
        if autoria.libro is not None
    ]

