"""ampliar_modelo_usuarios_stock_borrado_logico

Revision ID: 755b04050a0b
Revises: 7e0413ea1de1
Create Date: 2026-11-08 22:49:16.334309

Nota de revisión manual:
- Se revisaron los nombres y el orden de creación de tablas foráneas para evitar referencias circulares.
- Se nombró explícitamente la clave foránea 'fk_cliente_usuario_id' para posibilitar downgrade limpio.
- Se verificaron los tipos timestamptz en todas las columnas de fecha.
- Se incorporaron los índices únicos parciales 'uq_usuario_rol_vigente' y 'uq_libro_isbn_vigente'.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '755b04050a0b'
down_revision: Union[str, Sequence[str], None] = '7e0413ea1de1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla intento_acceso
    op.create_table(
        'intento_acceso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('ip', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('exitoso', sa.Boolean(), nullable=False),
        sa.Column('cuando', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_intento_acceso_email'), 'intento_acceso', ['email'], unique=False)
    op.create_index('ix_intento_acceso_email_ip_cuando', 'intento_acceso', ['email', 'ip', 'cuando'], unique=False)

    # 2. Tabla usuario
    op.create_table(
        'usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('debe_cambiar_password', sa.Boolean(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuario_email'), 'usuario', ['email'], unique=True)

    # 3. Tabla asignacion_rol
    op.create_table(
        'asignacion_rol',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('rol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('asignada_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('vence_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocada_en', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')", name='check_asignacion_rol_permitido'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name='fk_asignacion_rol_usuario_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asignacion_rol_usuario_id'), 'asignacion_rol', ['usuario_id'], unique=False)
    op.create_index('uq_usuario_rol_vigente', 'asignacion_rol', ['usuario_id', 'rol'], unique=True, postgresql_where=sa.text('revocada_en IS NULL'))

    # 4. Tabla evento_seguridad
    op.create_table(
        'evento_seguridad',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tipo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('usuario_afectado_id', sa.Integer(), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_tipo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('detalle', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('cuando', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['usuario.id'], name='fk_evento_seguridad_actor_id'),
        sa.ForeignKeyConstraint(['usuario_afectado_id'], ['usuario.id'], name='fk_evento_seguridad_usuario_afectado_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evento_seguridad_actor_id'), 'evento_seguridad', ['actor_id'], unique=False)
    op.create_index(op.f('ix_evento_seguridad_tipo'), 'evento_seguridad', ['tipo'], unique=False)
    op.create_index(op.f('ix_evento_seguridad_usuario_afectado_id'), 'evento_seguridad', ['usuario_afectado_id'], unique=False)

    # 5. Tabla movimiento_stock
    op.create_table(
        'movimiento_stock',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('libro_id', sa.Integer(), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('motivo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('cuando', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('cantidad != 0', name='check_movimiento_cantidad_no_cero'),
        sa.ForeignKeyConstraint(['libro_id'], ['libro.id'], name='fk_movimiento_stock_libro_id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name='fk_movimiento_stock_usuario_id'),
        sa.ForeignKeyConstraint(['venta_id'], ['venta.id'], name='fk_movimiento_stock_venta_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_movimiento_stock_libro_id'), 'movimiento_stock', ['libro_id'], unique=False)
    op.create_index(op.f('ix_movimiento_stock_usuario_id'), 'movimiento_stock', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_movimiento_stock_venta_id'), 'movimiento_stock', ['venta_id'], unique=False)

    # 6. Modificaciones sobre cliente
    op.add_column('cliente', sa.Column('usuario_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_cliente_usuario_id'), 'cliente', ['usuario_id'], unique=True)
    op.create_foreign_key('fk_cliente_usuario_id', 'cliente', 'usuario', ['usuario_id'], ['id'])

    # 7. Modificaciones sobre libro
    op.add_column('libro', sa.Column('borrado_en', sa.DateTime(timezone=True), nullable=True))
    op.drop_index(op.f('ix_libro_isbn'), table_name='libro')
    op.create_index(op.f('ix_libro_isbn'), 'libro', ['isbn'], unique=False)
    op.create_index('uq_libro_isbn_vigente', 'libro', ['isbn'], unique=True, postgresql_where=sa.text('borrado_en IS NULL'))


def downgrade() -> None:
    op.drop_index('uq_libro_isbn_vigente', table_name='libro', postgresql_where=sa.text('borrado_en IS NULL'))
    op.drop_index(op.f('ix_libro_isbn'), table_name='libro')
    op.create_index(op.f('ix_libro_isbn'), 'libro', ['isbn'], unique=True)
    op.drop_column('libro', 'borrado_en')

    op.drop_constraint('fk_cliente_usuario_id', 'cliente', type_='foreignkey')
    op.drop_index(op.f('ix_cliente_usuario_id'), table_name='cliente')
    op.drop_column('cliente', 'usuario_id')

    op.drop_index(op.f('ix_movimiento_stock_venta_id'), table_name='movimiento_stock')
    op.drop_index(op.f('ix_movimiento_stock_usuario_id'), table_name='movimiento_stock')
    op.drop_index(op.f('ix_movimiento_stock_libro_id'), table_name='movimiento_stock')
    op.drop_table('movimiento_stock')

    op.drop_index(op.f('ix_evento_seguridad_usuario_afectado_id'), table_name='evento_seguridad')
    op.drop_index(op.f('ix_evento_seguridad_tipo'), table_name='evento_seguridad')
    op.drop_index(op.f('ix_evento_seguridad_actor_id'), table_name='evento_seguridad')
    op.drop_table('evento_seguridad')

    op.drop_index('uq_usuario_rol_vigente', table_name='asignacion_rol', postgresql_where=sa.text('revocada_en IS NULL'))
    op.drop_index(op.f('ix_asignacion_rol_usuario_id'), table_name='asignacion_rol')
    op.drop_table('asignacion_rol')

    op.drop_index(op.f('ix_usuario_email'), table_name='usuario')
    op.drop_table('usuario')

    op.drop_index('ix_intento_acceso_email_ip_cuando', table_name='intento_acceso')
    op.drop_index(op.f('ix_intento_acceso_email'), table_name='intento_acceso')
    op.drop_table('intento_acceso')
