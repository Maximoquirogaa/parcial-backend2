from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Editorial(SQLModel, table=True):
    __tablename__ = "editorial"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False, unique=True, index=True)
    pais: str = Field(nullable=False)

    # Relación 1 a N con Libro
    libros: list["Libro"] = Relationship(back_populates="editorial")

