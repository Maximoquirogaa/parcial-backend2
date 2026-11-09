from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteDetailRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.ventas.models import Venta


async def create_cliente(session: AsyncSession, data: ClienteCreate) -> Cliente:
    cliente = Cliente(nombre=data.nombre, email=str(data.email))
    session.add(cliente)
    try:
        await session.commit()
        await session.refresh(cliente)
        return cliente
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente registrado con ese correo electrónico."
        )


async def get_cliente_by_id(session: AsyncSession, cliente_id: int) -> Cliente:
    """
    Obtiene el cliente con su perfil mediante joinedload (relación 1 a 0..1, sin N+1).
    """
    stmt = (
        select(Cliente)
        .options(joinedload(Cliente.perfil))
        .where(Cliente.id == cliente_id)
    )
    result = await session.execute(stmt)
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {cliente_id} no encontrado."
        )
    return cliente


async def update_cliente(
    session: AsyncSession,
    cliente_id: int,
    data: ClienteUpdate
) -> Cliente:
    cliente = await get_cliente_by_id(session, cliente_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "email" and value is not None:
            setattr(cliente, key, str(value))
        else:
            setattr(cliente, key, value)

    session.add(cliente)
    try:
        await session.commit()
        await session.refresh(cliente)
        return cliente
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error al actualizar cliente: el correo electrónico ya está en uso."
        )


async def create_perfil_cliente(
    session: AsyncSession,
    cliente_id: int,
    data: PerfilCreate
) -> PerfilCliente:
    """
    Crea el perfil para un cliente.
    Si el cliente no existe responde 404.
    Si el cliente ya tiene un perfil, la base rechaza por UNIQUE en cliente_id y se responde 409 (RN-09).
    """
    # Verificar existencia del cliente
    await get_cliente_by_id(session, cliente_id)

    perfil = PerfilCliente(
        cliente_id=cliente_id,
        telefono=data.telefono,
        direccion=data.direccion
    )
    session.add(perfil)
    try:
        await session.commit()
        await session.refresh(perfil)
        return perfil
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya cuenta con un perfil registrado (un cliente solo puede tener un perfil)."
        )


async def get_ventas_de_cliente(session: AsyncSession, cliente_id: int) -> Sequence[Venta]:
    await get_cliente_by_id(session, cliente_id)
    query = select(Venta).where(Venta.cliente_id == cliente_id).order_by(Venta.id)
    result = await session.execute(query)
    return result.scalars().all()

