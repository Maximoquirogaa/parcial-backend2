# Proposal

## Why

El TP de la librería de los capítulos 1 a 4 ya funciona en la máquina del grupo, pero todavía no puede usarlo nadie más: no está empaquetado ni publicado. El parcial exige entregar ese mismo TP —sin los cambios de acceso, roles ni Unit of Work— dentro de una imagen Docker reproducible y dejarlo en línea en el VPS con una configuración que no filtre secretos, con evidencia verificable de cada paso.

## What Changes

- Se agrega una carpeta `despliegue/` con el snapshot congelado del TP de los capítulos 1 a 4 (commit `f934174`), tomado antes de cualquier refactor del change `parcial-cap1a6`. La lógica del TP no se modifica.
- Se agrega un `Dockerfile` basado en `python:3.12-alpine` que instala dependencias antes del código, corre con usuario no-root, aplica `alembic upgrade head` y levanta uvicorn en `0.0.0.0:8000`, con `HEALTHCHECK` sobre `/health/ready` usando `127.0.0.1`.
- Se agrega un `.dockerignore` que excluye `.env`, entornos virtuales, `.git`, `__pycache__` y artefactos locales, de modo que ningún secreto quede horneado en la imagen.
- Se agrega un `env.example` con la forma de `DATABASE_URL` (driver `postgresql+asyncpg`), `SQL_ECHO=false` y ningún valor real.
- Se publica la imagen en el VPS con `docker run --restart unless-stopped --env-file`, documentando los datos de acceso provistos por la cátedra y el aviso de `host.docker.internal`/`--add-host`.
- Se agrega `DEPLOY.md` con URL pública, fecha y hora del despliegue, comandos `docker build`/`docker run` completos, cambios hechos al TP y procedimiento de actualización.
- Se agrega `evidencia/D-01` a `D-08` con los comandos y las salidas de cada caso de despliegue.
- **No** se toca el código del TP, no se agregan capas, autenticación, roles, modelos ni migraciones nuevas, y no se modifica el change `parcial-cap1a6`.

## Capabilities

### New Capabilities

- `deployment/container-image`: empaquetado del TP de los capítulos 1 a 4 como imagen Docker segura, reproducible y auto-verificable.
- `deployment/vps-release`: publicación de esa imagen en el VPS, operación con variables externas y documentación y evidencia de la entrega.

### Modified Capabilities

<!-- Ninguna: el cambio no modifica requisitos de capacidades existentes. La carpeta openspec/specs está vacía. -->

## Impact

- **Archivos nuevos**: `despliegue/` (snapshot del TP), `despliegue/Dockerfile`, `despliegue/.dockerignore`, `despliegue/env.example`, `despliegue/DEPLOY.md`, `despliegue/evidencia/D-01…D-08`.
- **Código de la aplicación**: sin cambios. El snapshot se toma de `f934174` antes del refactor planificado en `parcial-cap1a6`.
- **Infraestructura**: Docker 20.10+ en la máquina del grupo y en el VPS; PostgreSQL 16 provisto por el servidor.
- **Datos y secretos**: la base vive en el VPS, fuera del contenedor; las credenciales viajan sólo por `--env-file` y nunca se versionan.
- **Entregable**: el `.zip` del parcial incluye `despliegue/` como segundo proyecto independiente de `parcial/`.
