"""
Tests TDD — Bloque 5 (5.2): hash ficticio del login (C-04).

El lifespan debe calcular el hash ficticio una vez y guardarlo en
`app.state.hash_ficticio`; el login debe usarlo cuando el correo no existe,
de modo que la respuesta y el tiempo sean comparables a los de una contraseña
incorrecta.
"""
import time

import pytest
from fastapi import FastAPI

from app.core.security import hash_password
from tests.conftest import crear_usuario_bd, email_tdd


@pytest.fixture
def app_auth():
    from app.modules.auth.router import router

    app = FastAPI()
    app.include_router(router)
    return app


def _entorno_rapido(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_1234567890123456")
    monkeypatch.setenv("BCRYPT_COST", "4")  # barato para el test


# ============================================================================
# 5.2: El lifespan calcula y guarda hash_ficticio
# ============================================================================

@pytest.mark.asyncio
async def test_lifespan_guarda_hash_ficticio_en_app_state(monkeypatch):
    from app.main import lifespan

    _entorno_rapido(monkeypatch)

    app = FastAPI(lifespan=lifespan)
    assert not hasattr(app.state, "hash_ficticio")

    async with lifespan(app):
        assert hasattr(app.state, "hash_ficticio")
        hash_ = app.state.hash_ficticio
        assert isinstance(hash_, str) and hash_.startswith("$2")
        # El costo del hash ficticio es el de la configuración
        assert int(hash_.split("$")[2]) == 4


@pytest.mark.asyncio
async def test_lifespan_calcula_hash_ficticio_una_sola_vez(monkeypatch):
    """El lifespan pide el hash ficticio exactamente una vez, con bcrypt de config."""
    import app.main as main

    _entorno_rapido(monkeypatch)

    llamadas = []
    hash_original = hash_password

    async def hash_espion(password: str) -> str:
        llamadas.append(password)
        return await hash_original(password)

    monkeypatch.setattr(main, "hash_password", hash_espion)

    app = FastAPI(lifespan=main.lifespan)
    async with main.lifespan(app):
        assert len(llamadas) == 1, "el lifespan debe calcular el hash ficticio una sola vez"
        assert app.state.hash_ficticio.startswith("$2")


# ============================================================================
# 5.2: El login usa el hash ficticio cuando el correo no existe
# ============================================================================

@pytest.mark.asyncio
async def test_login_correo_inexistente_usa_hash_ficticio(app_auth, api):
    """Con `hash_ficticio` en el estado y sin el viejo `dummy_hash`: responde 401."""
    client = await api(app_auth)
    assert hasattr(app_auth.state, "hash_ficticio")
    assert not hasattr(app_auth.state, "dummy_hash")

    respuesta = await client.post(
        "/auth/login",
        json={"email": email_tdd("inexistente"), "password": "cualquier_clave"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Credenciales inválidas."}


@pytest.mark.asyncio
async def test_login_sin_hash_ficticio_en_estado_no_da_500(app_auth, api):
    """Si el estado no trajera el hash ficticio, el login sigue respondiendo 401."""
    client = await api(app_auth)
    del app_auth.state.hash_ficticio

    respuesta = await client.post(
        "/auth/login",
        json={"email": email_tdd("sin_ficticio"), "password": "cualquier_clave"},
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_c04_cuerpo_y_tiempo_comparables(app_auth, api):
    """C-04: correo existente con contraseña mala vs. correo inexistente."""
    client = await api(app_auth)
    fabrica = app_auth.state.fabrica_sesiones

    email_existente = email_tdd("c04_existente")
    hash_real = await hash_password("clave_correcta_tdd")
    await crear_usuario_bd(fabrica, email_existente, password_hash=hash_real)

    # Contraseña incorrecta con correo existente
    inicio_1 = time.perf_counter()
    respuesta_1 = await client.post(
        "/auth/login", json={"email": email_existente, "password": "clave_mala_tdd"}
    )
    tiempo_1 = time.perf_counter() - inicio_1

    # Correo inexistente
    inicio_2 = time.perf_counter()
    respuesta_2 = await client.post(
        "/auth/login",
        json={"email": email_tdd("c04_inexistente"), "password": "clave_mala_tdd"},
    )
    tiempo_2 = time.perf_counter() - inicio_2

    assert respuesta_1.status_code == 401
    assert respuesta_2.status_code == 401
    # Mismo cuerpo exacto
    assert respuesta_1.json() == respuesta_2.json()
    # Ambos pasan por un bcrypt real (costo 12 ≈ cientos de ms): tiempos comparables
    assert tiempo_1 >= 0.05, f"demasiado rápido para verificar bcrypt: {tiempo_1:.3f}s"
    assert tiempo_2 >= 0.05, f"demasiado rápido para verificar bcrypt: {tiempo_2:.3f}s"
    razon = max(tiempo_1, tiempo_2) / min(tiempo_1, tiempo_2)
    assert razon <= 5, f"tiempos no comparables: {tiempo_1:.3f}s vs {tiempo_2:.3f}s"
