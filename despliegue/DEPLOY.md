# DEPLOY — Librería API (TP capítulos 1 a 4)

> **Estado: borrador.** Este documento se completará con los datos reales cuando
> haya acceso al VPS. Todo lo marcado `(TBD — pendiente de acceso al VPS)` se
> rellena entonces; nada de lo que sigue contiene secretos.

## 1. Datos del despliegue

| Dato | Valor |
| --- | --- |
| URL pública | `(TBD — pendiente de acceso al VPS)` |
| Fecha y hora del despliegue | `(TBD — pendiente de acceso al VPS)` |
| Puerto asignado por la cátedra | `(TBD — pendiente de acceso al VPS)` |
| Host/base provistos por la cátedra | `(TBD — pendiente de acceso al VPS)` |
| Credenciales de la base | Sólo en `~/libreria.env` en el VPS (permisos `600`). Nunca se escriben en este archivo. |

## 2. Requisitos

- Docker 20.10 o superior en el VPS (y en la máquina del grupo para la
  verificación local previa, ya ejecutada y registrada en `evidencia/`).
- Base PostgreSQL provista por la cátedra, accesible desde el VPS.
- Un puerto TCP expuesto por la cátedra para el contenedor.
- `despliegue/` copiado al VPS (ver §3).

## 3. Archivo de variables (fuera del repositorio)

Se crea en el VPS, en el directorio personal, con permisos `600` y **sin** entrar
en el repositorio ni en la imagen (`.dockerignore` excluye `.env`):

```sh
umask 077
cat > ~/libreria.env <<'EOF'
DATABASE_URL=postgresql+asyncpg://<usuario>:<contrasena>@<host>:5432/<base>
SQL_ECHO=false
EOF
chmod 600 ~/libreria.env
```

Los valores reales los provee la cátedra: `(TBD — pendiente de acceso al VPS)`.

Notas:

- El TP de los capítulos 1 a 4 **no lee** `SQL_ECHO`: `app/core/database.py`
  tiene `echo=True` fijo. La variable se mantiene por paridad con la consigna y
  con el archivo que se usará más adelante; no altera el comportamiento.
- `DATABASE_URL` jamás debe apuntar a `localhost` dentro del contenedor: si
  PostgreSQL corre en el host del VPS, usar `host.docker.internal` (ver §5).

## 4. Copia al VPS

```sh
scp -r despliegue/ <usuario>@<vps>:~/despliegue
# o bien:
rsync -av --exclude '.env' --exclude '__pycache__' --exclude 'venv/' despliegue/ <usuario>@<vps>:~/despliegue
```

## 5. Construcción y arranque

```sh
# En el VPS, desde el directorio que contiene despliegue/
docker build -t libreria:cap1a4 despliegue

docker run -d \
  --name libreria \
  -p <PUERTO>:8000 \
  --restart unless-stopped \
  --env-file ~/libreria.env \
  libreria:cap1a4
```

- `<PUERTO>`: `(TBD — pendiente de acceso al VPS)`.
- Si PostgreSQL corre en el host del VPS, agregar a la línea de `docker run`:

  ```sh
  --add-host host.docker.internal:host-gateway
  ```

  y usar `host.docker.internal` en `DATABASE_URL`. Si la cátedra entrega otra
  dirección, se usa esa.

El `CMD` del `Dockerfile` ejecuta `alembic upgrade head && uvicorn app.main:app
--host 0.0.0.0 --port 8000`: si la migración falla, el contenedor termina con
código distinto de cero en lugar de quedar "vivo pero roto".

## 6. Carga de datos iniciales

```sh
docker exec libreria python seed.py
```

## 7. Verificación

```sh
docker ps                                   # STATE = healthy
docker exec libreria wget -qO- http://127.0.0.1:8000/health/ready   # 200
# Desde fuera del VPS:
#   GET  /health/ready  -> 200
#   GET  /libros/       -> 200 con los libros del TP
#   POST /ventas/       -> 201 con precios copiados y total calculado
```

## 8. Cambios aplicados al TP

Verificado con `git diff --no-index` contra una extracción limpia del commit
congelado `f934174` (comando: `git diff --no-index --stat <extracción> despliegue`).
Salida real (`git diff --no-index --name-status`, ejecutado el 2026-11-08):

```
A	despliegue/.dockerignore
A	despliegue/DEPLOY.md
A	despliegue/Dockerfile
M	<f934174_extract>/env.example
A	despliegue/evidencia/D-01_imagen_base.txt
A	despliegue/evidencia/D-05_sin_database_url.txt
A	despliegue/evidencia/D-06_contenido_imagen.txt
A	despliegue/evidencia/D-07_usuario.txt
M	<f934174_extract>/requirements.txt
```

Resumen del mismo diff con `--stat`: `9 files changed, 306 insertions(+),
3 deletions(-)`.

(`A` = agregado respecto de `f934174`, `M` = modificado. No hay ninguna
diferencia en `app/`, `migrations/`, `test/`, `seed.py`, `alembic.ini`,
`README.md` ni `docs/`.)

Qué significa cada diferencia:

- **Agregados (empaquetado / documentación / evidencia):** `Dockerfile`,
  `.dockerignore`, `DEPLOY.md` y `evidencia/`. Ninguno toca la lógica.
- **`env.example` (modificado):** ya existía en `f934174` con
  `DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost:5432/libreria_db`;
  se reemplazó por la forma genérica
  `postgresql+asyncpg://usuario:contraseña@host:5432/base` más `SQL_ECHO=false`,
  sin valores reales. Es documentación de configuración, no lógica.
- **`requirements.txt` (modificado):** `sqlalchemy>=2.0` → `sqlalchemy[asyncio]>=2.0`.
  Sólo cambia la declaración de dependencias: el extra `asyncio` declara
  `greenlet>=1`, que SQLAlchemy usa en modo asincrónico. No se modifica ningún
  archivo de código. Queda registrado acá porque el delta no forma parte de la
  lista `Dockerfile` / `.dockerignore` / `env.example` / `DEPLOY.md` / `evidencia/`
  prevista para el snapshot.
- **No hizo falta ninguna corrección de arranque:**
  - La ruta de salud **ya existía** en `f934174`: `app/modules/health/router.py`
    define `GET /health/live` y `GET /health/ready` y `app/main.py` ya incluye ese
    router. No se agregó ni modificó ninguna ruta.
  - `SQL_ECHO` / `echo=True` **no se tocó**: `app/core/database.py` del TP deja
    `echo=True` fijo; la consigna prohíbe modificar la lógica, así que el
    comportamiento se conserva tal cual está.
- **Sin cambios en lógica:** el diff no muestra ninguna diferencia en `app/`,
  `migrations/`, `test/`, `seed.py`, `alembic.ini`, `README.md` ni `docs/`.

## 9. Procedimiento de actualización

1. Conservar la imagen actual como respaldo antes de reconstruir:

   ```sh
   docker tag libreria:cap1a4 libreria:cap1a4-prev
   ```

2. Copiar los archivos actualizados al VPS (§4).
3. Reconstruir:

   ```sh
   docker build -t libreria:cap1a4 despliegue
   ```

4. Reemplazar el contenedor con el mismo comando de §5:

   ```sh
   docker rm -f libreria
   docker run -d --name libreria -p <PUERTO>:8000 --restart unless-stopped \
     --env-file ~/libreria.env libreria:cap1a4
   ```

5. Verificar `healthy` con `docker ps` y `GET /health/ready` → 200.
   Los datos **no** se pierden: viven en la base del servidor, no en el
   contenedor. `alembic upgrade head` es idempotente, así que las migraciones no
   se repiten.

**Rollback:** ante un problema, `docker rm -f libreria` y volver a correr el
mismo `docker run` apuntando a `libreria:cap1a4-prev`. La base no se toca.

> Pendiente: este procedimiento aún **no** se ejecutó de punta a punta en el VPS
> (tarea 6.3 del change `despliegue-cap1a4`); se ajustará este archivo si algún
> comando no coincide con lo probado allí.

## 10. Evidencia

La carpeta `evidencia/` guarda el comando y la salida literal de cada caso:

| Caso | Archivo | Estado |
| --- | --- | --- |
| D-01 imagen base | `evidencia/D-01_imagen_base.txt` | presente |
| D-02 build y run en servidor limpio | `evidencia/D-02_build_run.txt` | `(TBD — pendiente de acceso al VPS)` |
| D-03 URL pública | `evidencia/D-03_url_publica.txt` | `(TBD — pendiente de acceso al VPS)` |
| D-04 reinicio | `evidencia/D-04_reinicio.txt` | `(TBD — pendiente de acceso al VPS)` |
| D-05 sin `DATABASE_URL` | `evidencia/D-05_sin_database_url.txt` | presente |
| D-06 contenido de la imagen | `evidencia/D-06_contenido_imagen.txt` | presente |
| D-07 usuario del proceso | `evidencia/D-07_usuario.txt` | presente |
| D-08 aviso del comprobante | `evidencia/D-08_aviso_comprobante.txt` | `(TBD — pendiente de acceso al VPS)` |
