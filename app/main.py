import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import init_engine_and_sessionmaker
from app.core.security import hash_password
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("libreria.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Inicialización de motor asincrónico y fábrica de sesiones en app.state
    engine, session_maker = init_engine_and_sessionmaker(
        database_url=settings.database_url,
        pool_size=settings.POOL_SIZE,
        echo=settings.SQL_ECHO
    )
    app.state.engine = engine
    app.state.fabrica_sesiones = session_maker

    # 2. Pre-cálculo del hash ficticio del login (bcrypt fuera del bucle, en to_thread)
    app.state.hash_ficticio = await hash_password("clave_ficticia_para_login")

    logger.info("Recursos de base de datos y hash ficticio inicializados en app.state.")

    yield

    # Liberación ordenada de conexiones al apagar
    logger.info("Cerrando conexiones del motor de base de datos...")
    await engine.dispose()
    logger.info("Motor de base de datos cerrado correctamente.")


app = FastAPI(
    title="Librería API",
    description="API asincrónica con FastAPI, SQLModel y PostgreSQL - Programación III UTN",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Conflicto de integridad de datos detectado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Operación rechazada: conflicto de integridad de datos o registro duplicado."}
    )


# Inclusión de routers
app.include_router(health_router)
app.include_router(editoriales_router)
app.include_router(generos_router)
app.include_router(autores_router)
app.include_router(libros_router)
app.include_router(clientes_router)
app.include_router(ventas_router)
