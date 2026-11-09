from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True, index=True)

    # Relación 1 a 0..1 con PerfilCliente: uselist=False garantiza que devuelva un objeto y no una lista
    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )

    # Relación 1 a N con Venta
    ventas: list["Venta"] = Relationship(back_populates="cliente")


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        foreign_key="cliente.id",
        unique=True,
        index=True,
        nullable=False
    )
    telefono: str = Field(nullable=False)
    direccion: str = Field(nullable=False)

    # Relación inversa hacia Cliente
    cliente: Optional[Cliente] = Relationship(back_populates="perfil")

