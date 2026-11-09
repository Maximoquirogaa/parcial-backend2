"""
Tests TDD — Bloque 5: Seguridad (security.py), validación de contraseñas y JWT.
"""
import asyncio

import pytest
from pydantic import BaseModel, ValidationError
from typing import Annotated
from pydantic.functional_validators import AfterValidator

from app.core.security import (
    hash_password,
    verify_password,
    crear_token,
    decodificar_token,
    validar_72_bytes,
)
import jwt


# ============================================================================
# 5.1: Hash/Verificación bcrypt
# ============================================================================

@pytest.mark.asyncio
async def test_hash_password_changes_each_call():
    """El hash es distinto en cada llamada (salt aleatorio)."""
    h1 = await hash_password("misma_clave_secreta")
    h2 = await hash_password("misma_clave_secreta")
    assert h1 != h2


@pytest.mark.asyncio
async def test_verify_password_correct():
    """verify_password con la misma contraseña devuelve True."""
    h = await hash_password("clave_correcta")
    assert await verify_password("clave_correcta", h) is True


@pytest.mark.asyncio
async def test_verify_password_wrong():
    """verify_password con contraseña distinta devuelve False."""
    h = await hash_password("clave_correcta")
    assert await verify_password("clave_incorrecta", h) is False


# ============================================================================
# 5.1: JWT — crear y decodificar token
# ============================================================================

def test_token_creation_and_decode():
    """Crear un token y decodificarlo devuelve sub y roles correctos."""
    token = crear_token(sub="usuario@test.com", roles=["ADMIN", "VENDEDOR"])
    payload = decodificar_token(token)
    assert payload["sub"] == "usuario@test.com"
    assert "ADMIN" in payload["roles"]
    assert "VENDEDOR" in payload["roles"]


def test_token_expired():
    """Un token con exp en el pasado falla al decodificar."""
    from datetime import datetime, timezone
    from app.core.config import get_settings
    import jwt as pyjwt

    settings = get_settings()
    past = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())
    payload = {"sub": "test@test.com", "roles": [], "iat": past, "exp": past + 60}
    token = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    with pytest.raises(pyjwt.ExpiredSignatureError):
        decodificar_token(token)


def test_token_invalid_signature():
    """Un token con firma inválida lanza error."""
    # Creamos un token con un secret distinto
    payload = {"sub": "test@test.com", "roles": [], "exp": 9999999999}
    bad_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(bad_token)


# ============================================================================
# 5.3: Validador de 72 bytes
# ============================================================================

# ============================================================================
# 5.1: Costo configurable tomado de la configuración
# ============================================================================

@pytest.mark.asyncio
async def test_hash_password_usa_el_costo_de_la_configuracion():
    """El hash nuevo lleva el costo declarado en BCRYPT_COST, no uno fijo."""
    from app.core.config import get_settings

    hash_ = await hash_password("clave_para_costo")
    # Formato bcrypt: $2b$<costo>$<salt><hash>
    costo_en_hash = int(hash_.split("$")[2])
    assert costo_en_hash == get_settings().BCRYPT_COST


def test_crear_token_respeta_la_duracion_configurada():
    """El campo exp del token es ahora + TOKEN_EXPIRE_MINUTES."""
    import time

    from app.core.config import get_settings

    settings = get_settings()
    token = crear_token(sub="duracion@test.com", roles=[])
    payload = decodificar_token(token)
    esperado = time.time() + settings.TOKEN_EXPIRE_MINUTES * 60
    assert abs(payload["exp"] - esperado) <= 10


# ============================================================================
# 5.1: bcrypt fuera del bucle de eventos y bajo semáforo
# ============================================================================

@pytest.mark.asyncio
async def test_bcrypt_corre_fuera_del_bucle_de_eventos(monkeypatch):
    """Mientras se calcula un hash, el bucle sigue atendiendo otras tareas."""
    import time as tiempo

    import app.core.security as seguridad

    def hash_lento(password: str, cost: int) -> str:
        tiempo.sleep(0.2)  # trabajo bloqueante simulado de bcrypt
        return "$2b$12$hashlento"

    monkeypatch.setattr(seguridad, "_hash_sync", hash_lento)

    ticks = 0
    tarea_hash = asyncio.create_task(hash_password("clave_lenta"))

    async def observador():
        nonlocal ticks
        while not tarea_hash.done():
            ticks += 1
            await asyncio.sleep(0.01)

    await observador()
    await tarea_hash

    # Si bcrypt corriera dentro del bucle, el observador no podría avanzar
    # mientras dura el hash (0.2 s = ~20 iteraciones de 10 ms).
    assert ticks >= 5, f"el bucle quedó bloqueado durante el hash (ticks={ticks})"


@pytest.mark.asyncio
async def test_concurrencia_de_bcrypt_limitada_por_semaforo(monkeypatch):
    """Nunca hay más llamadas simultáneas a bcrypt de las que permite la config."""
    import time as tiempo

    import app.core.config as config
    import app.core.security as seguridad

    activos = 0
    maximo_visto = 0

    def hash_lento(password: str, cost: int) -> str:
        nonlocal activos, maximo_visto
        activos += 1
        maximo_visto = max(maximo_visto, activos)
        tiempo.sleep(0.03)
        activos -= 1
        return "$2b$12$concurrencia"

    monkeypatch.setattr(seguridad, "_hash_sync", hash_lento)

    # El semáforo de módulo puede ya existir de pruebas anteriores; lo reseteamos
    # para que respete el valor actual de la configuración.
    settings = config.get_settings()
    seguridad._semaforo = asyncio.Semaphore(settings.BCRYPT_MAX_CONCURRENT)

    await asyncio.gather(*[hash_password(f"clave{i}") for i in range(8)])

    assert maximo_visto <= settings.BCRYPT_MAX_CONCURRENT, (
        f"se vieron {maximo_visto} hashes simultáneos "
        f"(límite {settings.BCRYPT_MAX_CONCURRENT})"
    )
    assert maximo_visto >= 2, "el semáforo no permitió ninguna concurrencia"


def test_72_byte_validator_accepts_exactly_72():
    """Exactamente 72 bytes ASCII — aceptado."""
    pwd = "a" * 72  # 72 bytes ASCII
    assert validar_72_bytes(pwd) == pwd


def test_72_byte_validator_rejects_73_bytes():
    """73 bytes ASCII — rechazado con ValueError."""
    pwd = "a" * 73
    with pytest.raises(ValueError, match="72 bytes"):
        validar_72_bytes(pwd)


def test_72_byte_validator_multibyte():
    """Emoji de 4 bytes: 19 emojis = 76 bytes > 72 → rechazado."""
    pwd = "🔑" * 19  # 19 × 4 bytes = 76 bytes
    with pytest.raises(ValueError, match="72 bytes"):
        validar_72_bytes(pwd)


def test_72_byte_validator_multibyte_accepts_18():
    """18 emojis de 4 bytes = 72 bytes exactos → aceptado."""
    pwd = "🔑" * 18  # 18 × 4 bytes = 72 bytes
    assert validar_72_bytes(pwd) == pwd


# ============================================================================
# 5.3: Schema con validador de 72 bytes
# ============================================================================

class _SchemaConPassword(BaseModel):
    email: str
    password: Annotated[str, AfterValidator(validar_72_bytes)]


def test_registro_schema_forbids_73_byte_password():
    """Un schema que usa validar_72_bytes rechaza una contraseña de 73 bytes."""
    with pytest.raises(ValidationError):
        _SchemaConPassword(email="test@test.com", password="a" * 73)


def test_registro_schema_accepts_72_byte_password():
    """Un schema que usa validar_72_bytes acepta una contraseña de 72 bytes."""
    obj = _SchemaConPassword(email="test@test.com", password="a" * 72)
    assert obj.password == "a" * 72
