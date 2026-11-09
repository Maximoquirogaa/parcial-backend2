from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import CheckConstraint, Column, DateTime, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import Libro


class Venta(SQLModel, table=True):
    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint("total >= 0", name="check_venta_total_no_negativo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True, nullable=False)
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    total: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False)
    )

    # Relaciones
    cliente: Optional["Cliente"] = Relationship(back_populates="ventas")
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="venta",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class RenglonVenta(SQLModel, table=True):
    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="check_renglon_cantidad_positiva"),
        CheckConstraint("precio_unitario > 0", name="check_renglon_precio_unitario_positivo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="venta.id", index=True, nullable=False)
    libro_id: int = Field(foreign_key="libro.id", index=True, nullable=False)
    cantidad: int = Field(nullable=False)
    precio_unitario: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False)
    )

    # Relaciones
    venta: Optional[Venta] = Relationship(back_populates="renglones")
    libro: Optional["Libro"] = Relationship(back_populates="renglones")

