from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.editoriales.models import Editorial
    from app.modules.autores.models import Autor
    from app.modules.ventas.models import RenglonVenta
    from app.modules.generos.models import Genero


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="check_libro_precio_positivo"),
        CheckConstraint("stock >= 0", name="check_libro_stock_no_negativo"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    isbn: str = Field(nullable=False, unique=True, index=True)
    titulo: str = Field(nullable=False)
    precio: Decimal = Field(
        sa_column=Column(Numeric(10, 2), nullable=False)
    )
    stock: int = Field(default=0, nullable=False)
    editorial_id: int = Field(foreign_key="editorial.id", index=True, nullable=False)
    genero_id: Optional[int] = Field(default=None, foreign_key="genero.id", index=True, nullable=True)

    # Relaciones
    editorial: Optional["Editorial"] = Relationship(back_populates="libros")
    genero: Optional["Genero"] = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(
        back_populates="libro",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    renglones: list["RenglonVenta"] = Relationship(back_populates="libro")


class LibroAutor(SQLModel, table=True):
    """
    Entidad de asociación para la relación Muchos a Muchos entre Libro y Autor.
    Guarda datos propios de la autoría: rol y orden en la portada.
    """
    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint("orden >= 1", name="check_libro_autor_orden_minimo"),
        CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')",
            name="check_libro_autor_rol_valido"
        ),
    )

    libro_id: int = Field(
        primary_key=True,
        foreign_key="libro.id",
        index=True,
        nullable=False
    )
    autor_id: int = Field(
        primary_key=True,
        foreign_key="autor.id",
        index=True,
        nullable=False
    )
    rol: str = Field(nullable=False)
    orden: int = Field(nullable=False)

    # Relaciones
    libro: Optional[Libro] = Relationship(back_populates="autorias")
    autor: Optional["Autor"] = Relationship(back_populates="libro_autores")

