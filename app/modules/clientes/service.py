from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Pagina, ParametrosPagina, paginar
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteDetailRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    VentaResumenRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork


async def create_cliente(uow: ClientesUnitOfWork, data: ClienteCreate) -> Cliente:
    async with uow:
        cliente = Cliente(nombre=data.nombre, email=str(data.email))
        try:
            await uow.clientes.add(cliente)
            return cliente
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un cliente registrado con ese correo electrónico."
            )


async def get_cliente_by_id(uow: ClientesUnitOfWork, cliente_id: int) -> Cliente:
    async with uow:
        cliente = await uow.clientes.get_by_id_with_perfil(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con ID {cliente_id} no encontrado."
            )
        return cliente


async def get_clientes(uow: ClientesUnitOfWork, params: ParametrosPagina) -> Pagina[ClienteDetailRead]:
    async with uow:
        total = await uow.clientes.count()
        skip = (params.page - 1) * params.size
        clientes = await uow.clientes.listar_con_perfil(skip=skip, limit=params.size)
        items_read = [ClienteDetailRead.model_validate(c) for c in clientes]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)


async def update_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    data: ClienteUpdate
) -> Cliente:
    async with uow:
        cliente = await uow.clientes.get_by_id_with_perfil(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con ID {cliente_id} no encontrado."
            )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "email" and value is not None:
                setattr(cliente, key, str(value))
            else:
                setattr(cliente, key, value)

        try:
            await uow.clientes.update(cliente)
            return cliente
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error al actualizar cliente: el correo electrónico ya está en uso."
            )


async def create_perfil_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    data: PerfilCreate
) -> PerfilCliente:
    async with uow:
        # Verificar existencia del cliente
        cliente = await uow.clientes.get_by_id(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con ID {cliente_id} no encontrado."
            )

        perfil = PerfilCliente(
            cliente_id=cliente_id,
            telefono=data.telefono,
            direccion=data.direccion
        )
        try:
            await uow.perfiles.add(perfil)
            return perfil
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente ya cuenta con un perfil registrado (un cliente solo puede tener un perfil)."
            )


async def get_ventas_de_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    params: ParametrosPagina
) -> Pagina[VentaResumenRead]:
    async with uow:
        cliente = await uow.clientes.get_by_id(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con ID {cliente_id} no encontrado."
            )

        total = await uow.clientes.count_ventas_de_cliente(cliente_id)
        skip = (params.page - 1) * params.size
        ventas = await uow.clientes.get_ventas_de_cliente(cliente_id, skip=skip, limit=params.size)
        items_read = [VentaResumenRead.model_validate(v) for v in ventas]
        return paginar(items=items_read, total=total, page=params.page, size=params.size)
