from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.libros.schemas import (
    AutorEnLibroRead,
    LibroCreate,
    LibroDetailRead,
    LibroListRead,
    LibroUpdate,
    MovimientoStockRead,
    ReponerStockRequest,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork


async def registrar_movimiento_stock(
    session_o_uow,
    libro: Libro,
    cantidad: int,
    motivo: str,
    venta_id: Optional[int] = None,
    usuario_id: Optional[int] = None,
) -> MovimientoStock:
    """
    PUNTO ÚNICO de mutación de stock en todo el sistema.
    Actualiza libro.stock y crea el registro inmutable en movimiento_stock.
    """
    if cantidad == 0:
        raise ValueError("La cantidad del movimiento no puede ser cero.")

    from app.core.unit_of_work import UnitOfWork
    if isinstance(session_o_uow, UnitOfWork):
        session = session_o_uow.session
    else:
        session = session_o_uow

    libro.stock += cantidad
    movimiento = MovimientoStock(
        libro_id=libro.id,
        cantidad=cantidad,
        motivo=motivo,
        venta_id=venta_id,
        usuario_id=usuario_id,
    )
    session.add(movimiento)
    session.add(libro)
    await session.flush()
    return movimiento


def _build_libro_detail_read(libro: Libro) -> LibroDetailRead:
    """Helper para transformar el modelo con relaciones precargadas al DTO LibroDetailRead."""
    autores_dto = []
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


async def get_libro_detail_by_id(uow: LibrosUnitOfWork, libro_id: int) -> LibroDetailRead:
    async with uow:
        libro = await uow.libros.get_detail_by_id(libro_id)
        if not libro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Libro con ID {libro_id} no encontrado."
            )
        return _build_libro_detail_read(libro)


async def create_libro(uow: LibrosUnitOfWork, data: LibroCreate) -> LibroDetailRead:
    async with uow:
        # Se crea con stock 0 y luego se usa el punto único de stock si stock inicial > 0
        stock_a_asignar = data.stock
        libro = Libro(
            isbn=data.isbn,
            titulo=data.titulo,
            precio=data.precio,
            stock=0,
            editorial_id=data.editorial_id,
            genero_id=data.genero_id,
        )

        for autor_data in data.autores:
            relacion = LibroAutor(
                libro=libro,
                autor_id=autor_data.autor_id,
                rol=autor_data.rol,
                orden=autor_data.orden,
            )
            libro.autorias.append(relacion)

        try:
            await uow.libros.add(libro)
            if stock_a_asignar > 0:
                await registrar_movimiento_stock(
                    uow,
                    libro=libro,
                    cantidad=stock_a_asignar,
                    motivo="Stock inicial",
                )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error de integridad: verifique que el ISBN no esté repetido y que la editorial, género y autores existan."
            )

        detailed = await uow.libros.get_detail_by_id(libro.id)
        return _build_libro_detail_read(detailed)


async def get_libros_list(
    uow: LibrosUnitOfWork,
    params: ParametrosPagina,
    titulo: Optional[str] = None,
    genero_id: Optional[int] = None,
) -> Pagina[LibroListRead]:
    async with uow:
        total = await uow.libros.count_con_filtros(titulo=titulo, genero_id=genero_id)
        skip = (params.page - 1) * params.size
        libros = await uow.libros.listar_con_filtros(
            skip=skip,
            limit=params.size,
            titulo=titulo,
            genero_id=genero_id,
        )
        items_read = [LibroListRead.model_validate(libro) for libro in libros]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def update_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
    data: LibroUpdate,
) -> LibroDetailRead:
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if not libro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Libro con ID {libro_id} no encontrado."
            )

        update_dict = data.model_dump(exclude_unset=True)
        for field, val in update_dict.items():
            setattr(libro, field, val)

        try:
            await uow.libros.update(libro)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error al actualizar libro: clave foránea o unicidad inválida."
            )

        detailed = await uow.libros.get_detail_by_id(libro.id)
        return _build_libro_detail_read(detailed)


async def reponer_stock(
    uow: LibrosUnitOfWork,
    libro_id: int,
    data: ReponerStockRequest,
    usuario_id: Optional[int] = None,
) -> MovimientoStockRead:
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if not libro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Libro con ID {libro_id} no encontrado."
            )

        movimiento = await registrar_movimiento_stock(
            uow,
            libro=libro,
            cantidad=data.cantidad,
            motivo=data.motivo,
            usuario_id=usuario_id,
        )
        return MovimientoStockRead.model_validate(movimiento)


async def get_movimientos_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
    params: ParametrosPagina,
) -> Pagina[MovimientoStockRead]:
    async with uow:
        libro = await uow.libros.get_by_id_including_deleted(libro_id)
        if not libro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Libro con ID {libro_id} no encontrado."
            )

        total = await uow.movimientos.count_por_libro(libro_id)
        skip = (params.page - 1) * params.size
        movs = await uow.movimientos.listar_por_libro(libro_id, skip=skip, limit=params.size)
        items_read = [MovimientoStockRead.model_validate(m) for m in movs]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def delete_libro(uow: LibrosUnitOfWork, libro_id: int) -> None:
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if not libro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Libro con ID {libro_id} no encontrado."
            )
        await uow.libros.soft_delete(libro)
