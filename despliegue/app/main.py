import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import DATABASE_URL
from app.core.database import init_engine_and_sessionmaker
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("libreria.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización del motor asincrónico y fábrica de sesiones (Ejercicio 1)
    engine, session_maker = init_engine_and_sessionmaker(DATABASE_URL)
    app.state.engine = engine
    app.state.fabrica_sesiones = session_maker
    logger.info("Motor asincrónico y fábrica de sesiones inicializados en app.state.")

    yield

    # Cierre ordenado y sin fugas de conexiones al apagar la aplicación
    logger.info("Cerrando motor de base de datos...")
    await engine.dispose()
    logger.info("Motor de base de datos cerrado correctamente.")


app = FastAPI(
    title="Librería API",
    description="API asincrónica con FastAPI, SQLModel y PostgreSQL - Programación III UTN",
    version="1.0.0",
    lifespan=lifespan,
)


# RN-12: Traducción global de IntegrityError a mensaje propio sin exponer trazas internas ni nombres de tablas
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(f"IntegrityError capturado en ruta {request.url.path}: {exc.orig}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Error de integridad: violación de restricción en la base de datos (unicidad o clave foránea)."}
    )


# Registro de todos los routers por módulo funcional (Consigna pág. 5 y 6)
app.include_router(health_router)
app.include_router(editoriales_router)
app.include_router(generos_router)
app.include_router(autores_router)
app.include_router(libros_router)
app.include_router(clientes_router)
app.include_router(ventas_router)