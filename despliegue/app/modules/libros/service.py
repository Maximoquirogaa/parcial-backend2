from typing import Optional, Sequence
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutorEnLibroRead,
    LibroCreate,
    LibroDetailRead,
    LibroListRead,
    LibroUpdate,
)


def _build_libro_detail_read(libro: Libro) -> LibroDetailRead:
    """Helper para transformar el modelo con relaciones precargadas al DTO LibroDetailRead."""
    autores_dto = []
    # Ordenar las autorías por el campo orden especificado en la relación
    autorias_ordenadas = sorted(libro.autorias, key=lambda a: a.orden)
    for autoria in autorias_ordenadas:
        if autoria.autor is not None:
            autores_dto.append(
                AutorEnLibroRead(
                    id=autoria.autor.id,
                    nombre=autoria.autor.nombre,
                    nacionalidad=autoria.autor.nacionalidad,
                    rol=autoria.rol,
                    orden=autoria.orden,
                )
            )

    return LibroDetailRead(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialRead.model_validate(libro.editorial) if libro.editorial else None,
        genero=GeneroRead.model_validate(libro.genero) if libro.genero else None,
        autores=autores_dto,
    )


async def get_libro_detail_by_id(session: AsyncSession, libro_id: int) -> LibroDetailRead:
    """
    Obtiene el detalle completo de un libro mediante carga anticipada:
    joinedload para relaciones a 1 (editorial, género)
    selectinload para la colección (autorías -> autor)
    Garantiza número constante de consultas (sin problema N+1, Ejercicio 6).
    """
    stmt = (
        select(Libro)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
        .where(Libro.id == libro_id)
    )
    result = await session.execute(stmt)
    libro = result.scalar_one_or_none()

    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Libro con ID {libro_id} no encontrado."
        )

    return _build_libro_detail_read(libro)


async def create_libro(session: AsyncSession, data: LibroCreate) -> LibroDetailRead:
    """
    Crea un libro y sus autorías asociadas.
    Cumple Ejercicio 5: NINGÚN if consulta antes si un id existe (editorial, género, autores).
    Se escribe directamente y si la base rechaza una clave foránea o unicidad, se responde 409.
    """
    libro = Libro(
        isbn=data.isbn,
        titulo=data.titulo,
        precio=data.precio,
        stock=data.stock,
        editorial_id=data.editorial_id,
        genero_id=data.genero_id,
    )

    # Asociar autores en la tabla intermedia de asociación
    for autor_data in data.autores:
        relacion = LibroAutor(
            libro=libro,
            autor_id=autor_data.autor_id,
            rol=autor_data.rol,
            orden=autor_data.orden,
        )
        libro.autorias.append(relacion)

    session.add(libro)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error de integridad: verifique que el ISBN no esté repetido y que la editorial, género y autores existan."
        )

    # Retornar el detalle con carga anticipada
    return await get_libro_detail_by_id(session, libro.id)


async def get_libros_list(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: Optional[str] = None,
    genero_id: Optional[int] = None,
) -> Sequence[Libro]:
    """
    Listado con paginación (RN-10) y filtros con parámetros ligados (RN-11).
    Carga anticipada con joinedload para editorial y género (sin N+1).
    """
    stmt = (
        select(Libro)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
        )
    )

    if titulo:
        # Parámetro ligado seguro mediante ilike, sin concatenación de SQL
        stmt = stmt.where(Libro.titulo.ilike(f"%{titulo}%"))

    if genero_id is not None:
        stmt = stmt.where(Libro.genero_id == genero_id)

    stmt = stmt.order_by(Libro.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_libro(
    session: AsyncSession,
    libro_id: int,
    data: LibroUpdate,
) -> LibroDetailRead:
    libro = await session.get(Libro, libro_id)
    if not libro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Libro con ID {libro_id} no encontrado."
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(libro, field, val)

    session.add(libro)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error al actualizar libro: clave foránea o unicidad inválida."
        )

    return await get_libro_detail_by_id(session, libro.id)

