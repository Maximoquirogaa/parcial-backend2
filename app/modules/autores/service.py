from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate, LibroDeAutorRead
from app.modules.autores.unit_of_work import AutoresUnitOfWork


async def create_autor(uow: AutoresUnitOfWork, data: AutorCreate) -> Autor:
    async with uow:
        autor = Autor(**data.model_dump())
        await uow.autores.add(autor)
        return autor


async def get_autores(uow: AutoresUnitOfWork, params: ParametrosPagina) -> Pagina[AutorRead]:
    async with uow:
        total = await uow.autores.count()
        skip = (params.page - 1) * params.size
        items = await uow.autores.get_all(skip=skip, limit=params.size, order_by=Autor.id)
        items_read = [AutorRead.model_validate(item) for item in items]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def get_autor_by_id(uow: AutoresUnitOfWork, autor_id: int) -> Autor:
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if not autor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Autor con ID {autor_id} no encontrado."
            )
        return autor


async def update_autor(
    uow: AutoresUnitOfWork,
    autor_id: int,
    data: AutorUpdate
) -> Autor:
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if not autor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Autor con ID {autor_id} no encontrado."
            )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(autor, key, value)

        await uow.autores.update(autor)
        return autor


async def get_libros_de_autor(
    uow: AutoresUnitOfWork,
    autor_id: int,
    params: ParametrosPagina
) -> Pagina[LibroDeAutorRead]:
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if not autor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Autor con ID {autor_id} no encontrado."
            )

        total = await uow.autores.count_libros_de_autor(autor_id)
        skip = (params.page - 1) * params.size
        autorias = await uow.autores.get_libros_de_autor(autor_id, skip=skip, limit=params.size)

        items_read = [
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
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
