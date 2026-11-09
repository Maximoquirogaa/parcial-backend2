"""
Módulo de seguridad: hashing bcrypt no bloqueante bajo semáforo y manejo de JWT.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

# Semáforo lazy-initialized para limitar concurrencia de bcrypt
_semaforo: asyncio.Semaphore | None = None


def get_semaforo() -> asyncio.Semaphore:
    """Retorna (y crea si es necesario) el semáforo global de bcrypt."""
    global _semaforo
    if _semaforo is None:
        settings = get_settings()
        _semaforo = asyncio.Semaphore(settings.BCRYPT_MAX_CONCURRENT)
    return _semaforo


def _hash_sync(password: str, cost: int) -> str:
    """Función síncrona que ejecuta bcrypt — para correr en hilo."""
    salt = bcrypt.gensalt(rounds=cost)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_sync(plain: str, hashed: str) -> bool:
    """Función síncrona de verificación bcrypt — para correr en hilo."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


async def hash_password(password: str) -> str:
    """
    Calcula el hash bcrypt de la contraseña fuera del event loop, bajo semáforo.
    MUST llamarse ANTES de abrir cualquier transacción de base de datos.
    """
    settings = get_settings()
    sem = get_semaforo()
    async with sem:
        return await asyncio.to_thread(_hash_sync, password, settings.BCRYPT_COST)


async def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica una contraseña contra su hash bcrypt fuera del event loop, bajo semáforo.
    """
    sem = get_semaforo()
    async with sem:
        return await asyncio.to_thread(_verify_sync, plain, hashed)


def crear_token(sub: str, roles: list[str]) -> str:
    """
    Emite un JWT con `sub`, `exp`, `roles` e `iat`.
    `sub` debe ser el email del usuario.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": sub,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decodificar_token(token: str) -> dict[str, Any]:
    """
    Decodifica y verifica un JWT. Lanza jwt.ExpiredSignatureError o
    jwt.InvalidTokenError ante tokens inválidos o vencidos.
    """
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def validar_72_bytes(v: str) -> str:
    """
    Validador Pydantic para contraseñas: rechaza más de 72 bytes UTF-8.
    bcrypt trunca en silencio los bytes 73+; este validador lo hace explícito.
    """
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes en UTF-8.")
    return v


# Hash ficticio precalculado como respaldo (mismo costo que la configuración),
# para que el login nunca falle si el lifespan no dejó el suyo en app.state.
_hash_ficticio_respaldo: dict[str, str] = {}


async def obtener_hash_ficticio(state) -> str:
    """
    Hash contra el que se verifica cuando el correo del login no existe.
    Toma el que calculó el lifespan en `state.hash_ficticio`; si no estuviera
    disponible, calcula (una sola vez) un respaldo con el mismo costo.
    El costo es siempre el de la configuración, nunca uno fijo en el código.
    """
    disponible = getattr(state, "hash_ficticio", None)
    if disponible:
        return disponible
    if "valor" not in _hash_ficticio_respaldo:
        _hash_ficticio_respaldo["valor"] = await hash_password("clave_ficticia_de_timing")
    return _hash_ficticio_respaldo["valor"]
