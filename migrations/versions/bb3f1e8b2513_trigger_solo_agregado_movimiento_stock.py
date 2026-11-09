"""trigger_solo_agregado_movimiento_stock

Revision ID: bb3f1e8b2513
Revises: 755b04050a0b
Create Date: 2026-11-08 22:49:59.000000

Implementación manual del disparador de solo-agregado:
- Función PL/pgSQL que rechaza UPDATE y DELETE sobre movimiento_stock con código/mensaje descriptivo.
- Disparador BEFORE UPDATE OR DELETE sobre movimiento_stock.
- Downgrade limpio que elimina disparador y función.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb3f1e8b2513'
down_revision: Union[str, Sequence[str], None] = '755b04050a0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear función que rechaza modificaciones y borrados en movimiento_stock
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION rechazar_modificacion_movimiento_stock()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla movimiento_stock es de solo agregado: no se permiten operaciones de UPDATE ni DELETE.'
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
    """))

    # 2. Crear disparador BEFORE UPDATE OR DELETE
    op.execute(sa.text("""
        CREATE TRIGGER trg_movimiento_stock_solo_agregado
        BEFORE UPDATE OR DELETE ON movimiento_stock
        FOR EACH ROW
        EXECUTE FUNCTION rechazar_modificacion_movimiento_stock();
    """))


def downgrade() -> None:
    # Eliminar disparador y función en orden
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_movimiento_stock_solo_agregado ON movimiento_stock;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS rechazar_modificacion_movimiento_stock();"))
