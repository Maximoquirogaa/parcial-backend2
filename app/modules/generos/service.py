from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate, GeneroRead, LibroDeGeneroRead
from app.modules.generos.unit_of_work import GenerosUnitOfWork


async def create_genero(uow: GenerosUnitOfWork, data: GeneroCreate) -> Genero:
    async with uow:
        genero = Genero(nombre=data.nombre)
        try:
            await uow.generos.add(genero)
            return genero
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un género con ese nombre."
            )


async def get_generos(uow: GenerosUnitOfWork, params: ParametrosPagina) -> Pagina[GeneroRead]:
    async with uow:
        total = await uow.generos.count()
        skip = (params.page - 1) * params.size
        items = await uow.generos.get_all(skip=skip, limit=params.size, order_by=Genero.id)
        items_read = [GeneroRead.model_validate(item) for item in items]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def get_genero_by_id(uow: GenerosUnitOfWork, genero_id: int) -> Genero:
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if not genero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Género con ID {genero_id} no encontrado."
            )
        return genero


async def get_libros_de_genero(
    uow: GenerosUnitOfWork,
    genero_id: int,
    params: ParametrosPagina
) -> Pagina[LibroDeGeneroRead]:
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if not genero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Género con ID {genero_id} no encontrado."
            )

        total = await uow.generos.count_libros(genero_id)
        skip = (params.page - 1) * params.size
        libros = await uow.generos.get_libros(genero_id, skip=skip, limit=params.size)
        items_read = [LibroDeGeneroRead.model_validate(libro) for libro in libros]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
