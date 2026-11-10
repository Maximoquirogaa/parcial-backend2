"""
Tests TDD — Bloque 8: Ventas atómicas, stock y movimientos (8.1, 8.2, 8.3, 8.4) y Casos C-10, C-11, C-12, C-13.
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.ventas.models import Venta
from tests.conftest import (
    cookie_de,
    crear_cliente_bd,
    crear_editorial_bd,
    crear_libro_bd,
    crear_usuario_bd,
    email_tdd,
    isbn_tdd,
)


# ============================================================================
# 8.1 & 8.4: POST /ventas atómica con comprobante en background (C-10)
# ============================================================================

@pytest.mark.asyncio
async def test_venta_valida_descuenta_stock_y_registra_movimiento(cliente_principal: AsyncClient):
    """
    C-10: Venta válida (201) descuenta stock mediante registrar_movimiento_stock,
    calcula el total en el servidor y crea MovimientoStock por renglón.
    """
    fabrica = app.state.fabrica_sesiones
    email_vendedor = email_tdd("vendedor_b8")
    await crear_usuario_bd(fabrica, email_vendedor, roles=("VENDEDOR",))

    cli_id = await crear_cliente_bd(fabrica, email_tdd("cli_b8"))
    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Venta")
    isbn1 = isbn_tdd("v1")
    isbn2 = isbn_tdd("v2")

    l1_id = await crear_libro_bd(fabrica, isbn1, stock=10, editorial_id=ed_id)
    l2_id = await crear_libro_bd(fabrica, isbn2, stock=5, editorial_id=ed_id)

    payload = {
        "cliente_id": cli_id,
        "renglones": [
            {"libro_id": l1_id, "cantidad": 2},
            {"libro_id": l2_id, "cantidad": 1},
        ],
    }

    res = await cliente_principal.post(
        "/ventas/",
        headers=cookie_de(email_vendedor, roles=["VENDEDOR"]),
        json=payload,
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert len(data["renglones"]) == 2
    # Precio unitario 1500.00 * 2 + 1500.00 * 1 = 4500.00
    assert Decimal(data["total"]) == Decimal("4500.00")

    # Verificar stock en DB y movimientos
    async with fabrica() as session:
        l1 = await session.get(Libro, l1_id)
        l2 = await session.get(Libro, l2_id)
        assert l1.stock == 8
        assert l2.stock == 4

        stmt_m = select(MovimientoStock).where(MovimientoStock.venta_id == data["id"])
        movs = (await session.execute(stmt_m)).scalars().all()
        assert len(movs) == 2
        cantidades = sorted([m.cantidad for m in movs])
        assert cantidades == [-2, -1]
        assert all(m.motivo == "Venta" for m in movs)


# ============================================================================
# 8.2: Atomicidad de ventas (C-11, C-12)
# ============================================================================

@pytest.mark.asyncio
async def test_venta_stock_insuficiente_revierte_y_da_409(cliente_principal: AsyncClient):
    """
    C-11: Venta con stock insuficiente da 409 y NO modifica stock ni crea venta.
    """
    fabrica = app.state.fabrica_sesiones
    email_vendedor = email_tdd("vendedor_b8_insuf")
    await crear_usuario_bd(fabrica, email_vendedor, roles=("VENDEDOR",))

    cli_id = await crear_cliente_bd(fabrica, email_tdd("cli_b8_insuf"))
    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Venta Insuf")
    isbn = isbn_tdd("v_insuf")
    l_id = await crear_libro_bd(fabrica, isbn, stock=2, editorial_id=ed_id)

    payload = {
        "cliente_id": cli_id,
        "renglones": [{"libro_id": l_id, "cantidad": 5}],
    }

    res = await cliente_principal.post(
        "/ventas/",
        headers=cookie_de(email_vendedor, roles=["VENDEDOR"]),
        json=payload,
    )
    assert res.status_code == 409, res.text
    assert "Stock insuficiente" in res.json()["detail"]

    # Verificar que el stock sigue intacto en 2
    async with fabrica() as session:
        libro = await session.get(Libro, l_id)
        assert libro.stock == 2


@pytest.mark.asyncio
async def test_venta_libro_dado_de_baja_da_409(cliente_principal: AsyncClient):
    """
    C-12: Venta de un libro con borrado_en no nulo da 409.
    """
    from datetime import datetime, timezone

    fabrica = app.state.fabrica_sesiones
    email_vendedor = email_tdd("vendedor_b8_baja")
    await crear_usuario_bd(fabrica, email_vendedor, roles=("VENDEDOR",))

    cli_id = await crear_cliente_bd(fabrica, email_tdd("cli_b8_baja"))
    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Venta Baja")
    isbn = isbn_tdd("v_baja")
    l_id = await crear_libro_bd(fabrica, isbn, stock=10, editorial_id=ed_id)

    # Darlo de baja lógica
    async with fabrica() as session:
        l = await session.get(Libro, l_id)
        l.borrado_en = datetime.now(timezone.utc)
        await session.commit()

    payload = {
        "cliente_id": cli_id,
        "renglones": [{"libro_id": l_id, "cantidad": 1}],
    }

    res = await cliente_principal.post(
        "/ventas/",
        headers=cookie_de(email_vendedor, roles=["VENDEDOR"]),
        json=payload,
    )
    assert res.status_code == 409, res.text
    assert "dado de baja" in res.json()["detail"].lower() or "no existe" in res.json()["detail"].lower()


# ============================================================================
# 8.3: Reposición, movimientos y borrado lógico de libros (C-13)
# ============================================================================

@pytest.mark.asyncio
async def test_reponer_stock_crea_movimiento_y_actualiza_stock(cliente_principal: AsyncClient):
    """
    C-13: POST /libros/{id}/reponer suma stock y crea MovimientoStock con motivo "Reposición".
    """
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_b8_reponer")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))

    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Reponer")
    isbn = isbn_tdd("reponer")
    l_id = await crear_libro_bd(fabrica, isbn, stock=5, editorial_id=ed_id)

    res = await cliente_principal.post(
        f"/libros/{l_id}/reponer",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
        json={"cantidad": 15, "motivo": "Reposición de prueba"},
    )
    assert res.status_code == 200, res.text
    mov_data = res.json()
    assert mov_data["cantidad"] == 15
    assert mov_data["motivo"] == "Reposición de prueba"

    # Verificar stock en DB
    async with fabrica() as session:
        libro = await session.get(Libro, l_id)
        assert libro.stock == 20


@pytest.mark.asyncio
async def test_listar_movimientos_de_libro(cliente_principal: AsyncClient):
    """
    GET /libros/{id}/movimientos devuelve los movimientos paginados.
    """
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_b8_movs")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))

    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Movs")
    isbn = isbn_tdd("movs")
    l_id = await crear_libro_bd(fabrica, isbn, stock=0, editorial_id=ed_id)

    # Hacer una reposición
    await cliente_principal.post(
        f"/libros/{l_id}/reponer",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
        json={"cantidad": 10},
    )

    res = await cliente_principal.get(
        f"/libros/{l_id}/movimientos",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 1
    assert any(m["cantidad"] == 10 for m in data["items"])


@pytest.mark.asyncio
async def test_delete_libro_borrado_logico_y_reutilizacion_isbn(cliente_principal: AsyncClient):
    """
    C-13: DELETE /libros/{id} (204) realiza borrado lógico: no aparece en listado,
    pero el mismo ISBN se puede volver a dar de alta gracias al índice único parcial.
    """
    fabrica = app.state.fabrica_sesiones
    email_admin = email_tdd("admin_b8_delete")
    await crear_usuario_bd(fabrica, email_admin, roles=("ADMIN",))

    ed_id = await crear_editorial_bd(fabrica, "tdd Ed Delete")
    isbn = isbn_tdd("soft_del")
    l_id = await crear_libro_bd(fabrica, isbn, stock=3, editorial_id=ed_id)

    # 1. Borrar libro (204)
    res_del = await cliente_principal.delete(
        f"/libros/{l_id}",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
    )
    assert res_del.status_code == 204

    # 2. Libro no aparece en GET público /libros/
    res_list = await cliente_principal.get(f"/libros/?titulo={isbn}")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 0

    # 3. GET /libros/{id} da 404
    res_det = await cliente_principal.get(f"/libros/{l_id}")
    assert res_det.status_code == 404

    # 4. Volver a dar de alta un libro con el MISMO ISBN debe permitirse (índice parcial)
    res_recrear = await cliente_principal.post(
        "/libros/",
        headers=cookie_de(email_admin, roles=["ADMIN"]),
        json={
            "isbn": isbn,
            "titulo": "Libro Recreado",
            "precio": "2000.00",
            "stock_inicial": 5,
            "editorial_id": ed_id,
            "autores": [],
        },
    )
    assert res_recrear.status_code == 201, res_recrear.text
    assert res_recrear.json()["isbn"] == isbn


# ============================================================================
# 8.6: Verificación de handlers async def
# ============================================================================

def test_todos_los_handlers_son_async_def():
    """
    8.6: Ningún handler de endpoint debe ser sincrónico (def común);
    todos deben ser corrutinas (async def) para no bloquear el bucle de eventos.
    """
    import inspect
    from app.main import app

    non_async = []
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint and not inspect.iscoroutinefunction(endpoint):
            non_async.append(f"{route.path} -> {endpoint.__name__}")
    assert len(non_async) == 0, f"Handlers sincrónicos encontrados: {non_async}"
