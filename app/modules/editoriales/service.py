from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate, LibroDeEditorialRead
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork


async def create_editorial(uow: EditorialesUnitOfWork, data: EditorialCreate) -> Editorial:
    async with uow:
        editorial = Editorial(**data.model_dump())
        try:
            await uow.editoriales.add(editorial)
            return editorial
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una editorial con ese nombre."
            )


async def get_editoriales(uow: EditorialesUnitOfWork, params: ParametrosPagina) -> Pagina[EditorialRead]:
    async with uow:
        total = await uow.editoriales.count()
        skip = (params.page - 1) * params.size
        # Validar si page supera el rango antes o dejar que paginar lo haga
        items = await uow.editoriales.get_all(skip=skip, limit=params.size, order_by=Editorial.id)
        items_read = [EditorialRead.model_validate(item) for item in items]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def get_editorial_by_id(uow: EditorialesUnitOfWork, editorial_id: int) -> Editorial:
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if not editorial:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Editorial con ID {editorial_id} no encontrada."
            )
        return editorial


async def update_editorial(
    uow: EditorialesUnitOfWork,
    editorial_id: int,
    data: EditorialUpdate
) -> Editorial:
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if not editorial:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Editorial con ID {editorial_id} no encontrada."
            )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(editorial, key, value)

        try:
            await uow.editoriales.update(editorial)
            return editorial
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se pudo actualizar la editorial. Verifique que el nombre no esté duplicado."
            )


async def get_libros_de_editorial(
    uow: EditorialesUnitOfWork,
    editorial_id: int,
    params: ParametrosPagina
) -> Pagina[LibroDeEditorialRead]:
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if not editorial:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Editorial con ID {editorial_id} no encontrada."
            )

        total = await uow.editoriales.count_libros(editorial_id)
        skip = (params.page - 1) * params.size
        libros = await uow.editoriales.get_libros(editorial_id, skip=skip, limit=params.size)
        items_read = [LibroDeEditorialRead.model_validate(libro) for libro in libros]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
