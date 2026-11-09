import pytest
from datetime import datetime, timezone
from sqlmodel import SQLModel
from sqlalchemy import Index, CheckConstraint
from app.modules.usuarios.models import (
    Usuario,
    AsignacionRol,
    IntentoAcceso,
    EventoSeguridad,
    RolEnum,
)
from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro, MovimientoStock


def test_models_exist_and_have_required_tables():
    assert Usuario.__tablename__ == "usuario"
    assert AsignacionRol.__tablename__ == "asignacion_rol"
    assert IntentoAcceso.__tablename__ == "intento_acceso"
    assert EventoSeguridad.__tablename__ == "evento_seguridad"
    assert MovimientoStock.__tablename__ == "movimiento_stock"


def test_asignacion_rol_check_constraint_and_partial_unique_index():
    table = AsignacionRol.__table__
    idx_names = [idx.name for idx in table.indexes]
    partial_idx = next((idx for idx in table.indexes if "uq_usuario_rol_vigente" in idx.name), None)
    assert partial_idx is not None, f"Expected uq_usuario_rol_vigente in {idx_names}"
    assert partial_idx.unique is True
    assert "revocada_en IS NULL" in str(partial_idx.dialect_options.get("postgresql", {}).get("where", ""))

    check_constraints = [c.name for c in table.constraints if isinstance(c, CheckConstraint)]
    assert "check_asignacion_rol_permitido" in check_constraints


def test_intento_acceso_indexes():
    table = IntentoAcceso.__table__
    idx_names = [idx.name for idx in table.indexes]
    composite_idx = next((idx for idx in table.indexes if "ix_intento_acceso_email_ip_cuando" in idx.name), None)
    assert composite_idx is not None, f"Expected composite index in {idx_names}"
    col_names = [c.name for c in composite_idx.columns]
    assert col_names == ["email", "ip", "cuando"]


def test_libro_soft_delete_and_partial_isbn_index():
    table = Libro.__table__
    assert "borrado_en" in table.c
    isbn_col = table.c.isbn
    assert not isbn_col.unique
    partial_isbn_idx = next((idx for idx in table.indexes if "uq_libro_isbn_vigente" in idx.name), None)
    assert partial_isbn_idx is not None
    assert partial_isbn_idx.unique is True
    assert "borrado_en IS NULL" in str(partial_isbn_idx.dialect_options.get("postgresql", {}).get("where", ""))


def test_cliente_usuario_id_field_and_unique():
    table = Cliente.__table__
    assert "usuario_id" in table.c
    col = table.c.usuario_id
    assert col.nullable is True
    assert col.unique is True


def test_movimiento_stock_check_cantidad_distinta_cero():
    table = MovimientoStock.__table__
    check_constraints = [c.name for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("check_movimiento_cantidad_no_cero" in (c or "") for c in check_constraints)
    assert "libro_id" in table.c
    assert "venta_id" in table.c
    assert "usuario_id" in table.c
    assert "cantidad" in table.c
    assert "motivo" in table.c
    assert "cuando" in table.c
