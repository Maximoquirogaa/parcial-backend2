"""Pruebas de acceso a lo propio: /mis-ventas y detalle de venta (tarea 6.7)."""
import pytest

from app.main import app
from tests.conftest import (
    cookie_de,
    crear_cliente_bd,
    crear_editorial_bd,
    crear_libro_bd,
    crear_usuario_bd,
    crear_venta_bd,
    email_tdd,
    isbn_tdd,
)


async def _escenario(cliente_principal):
    """Crea dos clientes con usuario y una venta para cada uno."""
    fabrica = app.state.fabrica_sesiones
    email_dueno = email_tdd("dueno")
    email_otro = email_tdd("otro")
    email_vendedor = email_tdd("vendedor")

    id_dueno = await crear_usuario_bd(fabrica, email_dueno)
    id_otro = await crear_usuario_bd(fabrica, email_otro)
    await crear_usuario_bd(fabrica, email_vendedor, roles=("VENDEDOR",))

    cliente_dueno = await crear_cliente_bd(fabrica, email_tdd("cliente_dueno"), usuario_id=id_dueno)
    cliente_otro = await crear_cliente_bd(fabrica, email_tdd("cliente_otro"), usuario_id=id_otro)

    editorial = await crear_editorial_bd(fabrica, "tdd Editorial Ventas")
    libro = await crear_libro_bd(fabrica, isbn_tdd("venta"), editorial_id=editorial)

    venta_dueno = await crear_venta_bd(fabrica, cliente_dueno, libro)
    venta_otro = await crear_venta_bd(fabrica, cliente_otro, libro)

    return {
        "email_dueno": email_dueno,
        "email_otro": email_otro,
        "email_vendedor": email_vendedor,
        "venta_dueno": venta_dueno,
        "venta_otro": venta_otro,
    }


@pytest.mark.asyncio
async def test_cliente_ve_su_venta_y_no_la_ajena(cliente_principal):
    datos = await _escenario(cliente_principal)

    propia = await cliente_principal.get(
        f"/ventas/{datos['venta_dueno']}",
        headers=cookie_de(datos["email_dueno"]),
    )
    assert propia.status_code == 200, propia.text

    ajena = await cliente_principal.get(
        f"/ventas/{datos['venta_otro']}",
        headers=cookie_de(datos["email_dueno"]),
    )
    assert ajena.status_code == 403, ajena.text


@pytest.mark.asyncio
async def test_personal_ve_cualquier_venta(cliente_principal):
    datos = await _escenario(cliente_principal)

    respuesta = await cliente_principal.get(
        f"/ventas/{datos['venta_otro']}",
        headers=cookie_de(datos["email_vendedor"], roles=["VENDEDOR"]),
    )
    assert respuesta.status_code == 200, respuesta.text


@pytest.mark.asyncio
async def test_detalle_inexistente_da_404(cliente_principal):
    datos = await _escenario(cliente_principal)

    respuesta = await cliente_principal.get(
        "/ventas/999999",
        headers=cookie_de(datos["email_dueno"]),
    )
    assert respuesta.status_code == 404, respuesta.text


@pytest.mark.asyncio
async def test_mis_ventas_solo_devuelve_las_propias(cliente_principal):
    datos = await _escenario(cliente_principal)

    respuesta = await cliente_principal.get(
        "/mis-ventas",
        headers=cookie_de(datos["email_dueno"]),
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    ids = [item["id"] for item in cuerpo["items"]]
    assert ids == [datos["venta_dueno"]]
    assert datos["venta_otro"] not in ids
    assert cuerpo["total"] == 1


@pytest.mark.asyncio
async def test_mis_ventas_sin_sesion_da_401(cliente_principal):
    respuesta = await cliente_principal.get("/mis-ventas")
    assert respuesta.status_code == 401, respuesta.text
