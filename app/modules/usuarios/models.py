from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, DateTime, CheckConstraint, Index, text
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock


class RolEnum(str, Enum):
    ADMIN = "ADMIN"
    VENDEDOR = "VENDEDOR"
    CLIENTE = "CLIENTE"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password_hash: str = Field(nullable=False)
    nombre: str = Field(nullable=False)
    activo: bool = Field(default=True, nullable=False)
    debe_cambiar_password: bool = Field(default=False, nullable=False)
    creado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # Relaciones
    roles: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"uselist": False}
    )
    movimientos_stock: list["MovimientoStock"] = Relationship(back_populates="usuario")


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')",
            name="check_asignacion_rol_permitido"
        ),
        Index(
            "uq_usuario_rol_vigente",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL")
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, nullable=False)
    rol: str = Field(nullable=False)
    asignada_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    vence_en: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    revocada_en: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    usuario: Optional[Usuario] = Relationship(back_populates="roles")


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False)
    ip: str = Field(nullable=False)
    exitoso: bool = Field(nullable=False)
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"

    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str = Field(index=True, nullable=False)
    usuario_afectado_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        nullable=True
    )
    actor_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        nullable=True
    )
    actor_tipo: str = Field(nullable=False)  # "USUARIO" o "SISTEMA"
    detalle: Optional[str] = Field(default=None, nullable=True)
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
