# Design

## Context

El repositorio contiene el TP de la librería de los capítulos 1 a 4 (commit `f934174`) sobre el stack FastAPI + SQLModel + SQLAlchemy async + asyncpg + Alembic + PostgreSQL. El entrypoint real es `app.main:app`; `main.py` vive en `app/`, no en la raíz. `requirements.txt` ya trae `fastapi[standard]` (incluye uvicorn), `sqlmodel`, `sqlalchemy`, `asyncpg`, `alembic` y `python-dotenv`.

El TP tiene dos particularidades que condicionan el empaquetado:

- `app/core/config.py` define un `DATABASE_URL` por defecto apuntando a `localhost` y carga `.env` desde la raíz del proyecto.
- `init_engine_and_sessionmaker` usa `echo=True` fijo; el TP no lee `SQL_ECHO`.

El change `parcial-cap1a6` va a refactorizar capas, autenticación y modelos sobre el código actual. Este change debe congelar el TP anterior en `despliegue/` antes de ese refactor y no compartir archivos con él. Ver `proposal.md` para la motivación.

## Goals / Non-Goals

**Goals:**

- Producir un snapshot determinista y aislado del TP 1 a 4 en `despliegue/`.
- Construir una imagen Alpine por debajo del límite de la base, sin secretos y sin root.
- Arrancar migraciones y servidor en un solo comando, con salud verificable desde Docker.
- Publicar el contenedor en el VPS y dejar evidencia reproducible de D-01 a D-08.

**Non-Goals:**

- No se agrega Compose, proxy inverso ni TLS: la cátedra asigna el puerto y la URL.
- No se contenedoriza PostgreSQL ni se migran datos: la base vive en el servidor.
- No se toca la lógica del TP, ni se corrigen los defectos de los capítulos 1 a 4 salvo que impidan arrancar.
- No se incluye el despliegue dentro de `parcial/`: son dos proyectos separados en el `.zip`.

## Decisions

### 1. Snapshot con `git archive` del commit `f934174`

Se genera `despliegue/` con `git archive f934174` en lugar de copiar el árbol de trabajo. Así el snapshot es reproducible, no arrastra el `.env` local, `__pycache__`, `venv` ni los cambios posteriores (README y evidencia del caso C-07), y queda garantizado que no incluye nada del refactor de `parcial-cap1a6`.

- **Alternativa descartada**: copiar la carpeta actual con el explorador de archivos. No es determinista y puede filtrar `.env` o `__pycache__`.

### 2. Dockerfile de una sola etapa, con capas ordenadas

Una sola etapa alcanza porque no hay compilación nativa: `asyncpg`, `pydantic-core` y el resto tienen wheels para musllinux. Se ordena `COPY requirements.txt` → `pip install --no-cache-dir` → `COPY . .` para que la capa de dependencias se reutilice.

- **Alternativa descartada**: multi-stage con imagen builder. Agrega tamaño y complejidad sin beneficio, porque no se compila nada. El requisito de "multi-capa" se refiere a las capas del Dockerfile, no a multi-stage.

Boceto:

```dockerfile
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

RUN addgroup -S app && adduser -S app -G app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### 3. Usuario no-root creado antes del `COPY` con `--chown`

Se crea `app` como grupo y usuario de sistema y se copia el código con `--chown=app:app`. El proceso corre sin privilegios y no necesita escribir en `/app` (bytecode desactivado). No se usa `USER nobody` porque no garantiza un grupo consistente ni permite ajustar permisos.

### 4. Migraciones y servidor en el mismo `CMD`

`sh -c "alembic upgrade head && uvicorn ..."` hace que un fallo de migración corte el arranque con código distinto de cero y que Docker no deje el contenedor "vivo pero roto". Un entrypoint separado sería más limpio pero agrega un archivo y no aporta al alcance.

### 5. HEALTHCHECK con `127.0.0.1` y `wget`

Alpine no trae `curl`; busybox `wget` sí. Se usa `127.0.0.1` explícito porque `localhost` resuelve primero a `::1` y uvicorn con `--host 0.0.0.0` escucha sólo IPv4. Se apunta a `/health/ready` (no `/health/live`) para que el estado refleje también la base.

### 6. `env.example` con variables del contenedor

`despliegue/env.example` documenta `DATABASE_URL=postgresql+asyncpg://usuario:contraseña@host:5432/base` y `SQL_ECHO=false`, sin valores reales. `SQL_ECHO` se incluye por paridad con la consigna y con el archivo que se usará en el servidor, aunque el TP 1 a 4 no lo lea: no cambia el comportamiento y evita divergencias al migrar al parcial. No se agrega soporte en el código porque la lógica del TP no se toca.

### 7. Construcción en el VPS y sin registro

Se elige construir la imagen en el VPS a partir de `despliegue/` copiado por `scp`/`rsync` y ejecutar `docker build` allí. Evita publicar en un registry y mantiene la imagen cerca de donde corre.

- **Alternativa descartada**: construir localmente y transferir con `docker save`/`docker load`. Válida, pero el archivo pesa más que el contexto y complica la actualización. Si el VPS no tuviera recursos para construir, se documentaría como cambio de estrategia en `DEPLOY.md`.

### 8. `--env-file` en el servidor, fuera del repositorio

El archivo de variables se crea en el VPS (por ejemplo `~/libreria.env`, permisos `600`) y se referencia con `--env-file`. No se versiona, no se copia a la imagen y no se muestra su contenido en `DEPLOY.md`; sólo su nombre.

### 9. Base externa: `host.docker.internal` con `--add-host`

Si PostgreSQL corre en el host, `DATABASE_URL` usa `host.docker.internal` y el `docker run` agrega `--add-host host.docker.internal:host-gateway` en Linux. Si la cátedra entrega otra dirección, se usa esa y se documenta. Nunca se usa `localhost` dentro del contenedor.

### 10. Evidencia en archivos de texto numerados

Cada caso D se guarda como `despliegue/evidencia/D-0N_<slug>.txt` con el comando ejecutado y su salida literal. Para D-01 se incluye `docker images` con la base y la imagen del proyecto; para D-03/D-04, las respuestas HTTP; para D-08, el fragmento de `docker logs`.

### 11. D-05 y el `DATABASE_URL` por defecto del TP

El TP define un valor por defecto `...@localhost:5432/libreria_db`. Al correr sin `DATABASE_URL`, el contenedor intenta conectarse a `localhost` (él mismo) y `alembic upgrade head` falla, por lo que el contenedor termina con error: el resultado observable de D-05 se cumple. No se modifica `config.py` para quitar el default porque la consigna prohíbe tocar la lógica; `DEPLOY.md` y la evidencia explican que el fallo proviene de la conexión y no de una validación explícita.

## Risks / Trade-offs

- **`localhost` en `DATABASE_URL`** → Mitigación: documentar `host.docker.internal` y `--add-host`; verificar `/health/ready` antes de dar por cerrado el despliegue.
- **Healthcheck falsamente unhealthy por IPv6** → Mitigación: `127.0.0.1` fijo y prueba manual con `docker exec ... wget`.
- **Secreto horneado por copiar `.env`** → Mitigación: `.dockerignore` con `.env`, `venv`, `.git`, `__pycache__`; verificación D-06 con `env` y `ls`.
- **Alpine sin wheels para alguna dependencia** → Mitigación: construir antes de viajar al VPS; si fallara, documentar el paquete de build necesario (no se espera con el stack actual).
- **Puerto ocupado o firewall del VPS** → Mitigación: verificar `docker ps` y probar la URL pública desde fuera antes de generar D-03.
- **Pérdida de datos al recrear el contenedor** → Mitigación: la base es externa; D-04 confirma que los datos sobreviven al `docker rm -f`.
- **Deriva entre el snapshot y el repo** → Mitigación: snapshot por commit y revisión de `git diff --no-index` contra `f934174`; sólo se aceptan los archivos de empaquetado y documentación.
- **D-05 depende de un default del TP** → Mitigación: registrar la salida real y explicarla en `DEPLOY.md`; no se altera el código para forzar el comportamiento.

## Migration Plan

1. Generar `despliegue/` desde `f934174`.
2. Agregar `Dockerfile`, `.dockerignore`, `env.example` y verificar la imagen en local (build, run contra una base accesible, healthcheck, usuario, ausencia de secretos).
3. Copiar `despliegue/` al VPS, crear el archivo de variables y construir la imagen allí.
4. Detener y eliminar cualquier contenedor previo con el mismo nombre; ejecutar `docker run` con `--restart unless-stopped` y `--add-host` si corresponde.
5. Cargar datos iniciales con `docker exec`.
6. Ejecutar y capturar D-01 a D-08.
7. Escribir `DEPLOY.md` con URL, fecha/hora, comandos y procedimiento de actualización.
8. Rollback: conservar la imagen anterior etiquetada; ante una falla, `docker rm -f libreria` y correr la etiqueta previa. La base no se toca.

## Open Questions

- Puerto público, URL, credenciales del VPS y datos de la base: los provee la cátedra al grupo. Se completan en `DEPLOY.md` y en el archivo de variables del servidor; no cambian el diseño.
- Si el VPS no permite construir imágenes, se evaluará `docker save`/`load`; se documentará la estrategia elegida en `DEPLOY.md`.
