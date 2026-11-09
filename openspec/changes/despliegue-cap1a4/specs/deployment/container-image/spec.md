# Spec Delta

## Purpose

Define cómo se empaqueta el TP de los capítulos 1 a 4 en una imagen Docker reproducible, segura y auto-verificable, ejecutable con `docker run` contra una base PostgreSQL externa al contenedor.

## ADDED Requirements

### Requirement: Imagen base y tamaño

La imagen SHALL construirse a partir de `python:3.12-alpine`, cuya imagen base ocupa menos de 100 MB en disco. No se usa `python:3.12-slim` ni ninguna base que supere ese límite.

#### Scenario: Verificación de la imagen base

- **WHEN** se ejecuta `docker images` en la máquina que construyó la imagen
- **THEN** `python:3.12-alpine` figura por debajo de los 100 MB y el `Dockerfile` declara `FROM python:3.12-alpine`

#### Scenario: Dependencias instalables en Alpine

- **WHEN** se construye la imagen desde cero
- **THEN** las dependencias de `requirements.txt` (`asyncpg`, `pydantic-core` y el resto) se instalan sin compilar nada y no hace falta agregar un compilador

### Requirement: Orden de capas y caché

El `Dockerfile` SHALL copiar e instalar `requirements.txt` antes de copiar el código, con `pip install --no-cache-dir`. Un cambio en el código no MUST reinstalar las dependencias.

#### Scenario: Cambio de código sin reinstalar dependencias

- **WHEN** se modifica un archivo de la aplicación y se vuelve a construir la imagen
- **THEN** la capa de instalación de dependencias sale de la caché y sólo se reconstruyen las capas del código

### Requirement: Ejecución sin privilegios

La imagen SHALL crear un usuario sin privilegios y activarlo con `USER` antes de arrancar la aplicación. El proceso principal MUST NOT ejecutarse como root.

#### Scenario: Usuario del proceso en ejecución

- **WHEN** el contenedor está corriendo y se ejecuta `docker exec libreria id`
- **THEN** el usuario informado no es `root` (uid distinto de 0)

### Requirement: Ausencia de secretos en la imagen

La imagen MUST NOT contener `.env`, entornos virtuales, `.git`, `__pycache__`, contraseñas ni la dirección de la base. El `.dockerignore` SHALL excluir esos archivos y la configuración SHALL entrar sólo como variables de entorno al ejecutar el contenedor.

#### Scenario: Inspección del contenido de la imagen

- **WHEN** se ejecuta `docker run --rm --entrypoint ls <imagen> /app` y `docker run --rm --entrypoint env <imagen>`
- **THEN** no aparece el archivo `.env` y no figuran `DATABASE_URL` ni ninguna contraseña en el entorno horneado

### Requirement: Arranque con migraciones y servidor accesible

Al arrancar, el contenedor SHALL ejecutar `alembic upgrade head` y luego levantar uvicorn con `app.main:app` escuchando en `0.0.0.0:8000`. Si la base no responde, MUST terminar con error en lugar de quedar atendiendo.

#### Scenario: Arranque normal

- **WHEN** se inicia el contenedor con una `DATABASE_URL` válida
- **THEN** `docker logs` muestra las migraciones del TP aplicadas y el servidor escuchando, y el contenedor queda en estado `healthy`

#### Scenario: Base inalcanzable

- **WHEN** se inicia el contenedor sin una base accesible
- **THEN** `alembic upgrade head` falla y el contenedor termina con código de error distinto de cero

#### Scenario: Publicación del puerto

- **WHEN** el contenedor se ejecuta con `-p <puerto>:8000`
- **THEN** la aplicación responde desde fuera del contenedor en el puerto publicado

### Requirement: Healthcheck interno

La imagen SHALL declarar un `HEALTHCHECK` que consulte `GET /health/ready` en `http://127.0.0.1:8000`. MUST NOT usar `localhost`, porque en Alpine resuelve primero a IPv6 y uvicorn escucha en IPv4.

#### Scenario: Contenedor sano

- **WHEN** el contenedor terminó de arrancar y la base responde
- **THEN** `docker ps` muestra el estado `healthy`

#### Scenario: Verificación manual del healthcheck

- **WHEN** se ejecuta `docker exec libreria wget -qO- http://127.0.0.1:8000/health/live`
- **THEN** responde 200 sin error de conexión

### Requirement: Ejecución con docker run y variables externas

La imagen SHALL ejecutarse con `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria`. La configuración y los secretos MUST provenir del archivo de variables, que vive en el servidor y fuera del repositorio.

#### Scenario: Reinicio automático

- **WHEN** el proceso o el servidor se reinicia y el contenedor no fue detenido explícitamente
- **THEN** Docker vuelve a levantar el contenedor por `--restart unless-stopped`

#### Scenario: Ejecución sin variables

- **WHEN** se corre la imagen sin `DATABASE_URL`
- **THEN** el contenedor no queda sirviendo: termina con error porque no alcanza ninguna base

### Requirement: Conectividad con la base externa

La documentación SHALL advertir que `localhost` dentro del contenedor es el propio contenedor. Si PostgreSQL corre en el servidor, la conexión SHALL usar `host.docker.internal`, habilitado en Linux con `--add-host host.docker.internal:host-gateway`.

#### Scenario: Base en el mismo servidor

- **WHEN** la base corre directamente en el VPS y se usa `host.docker.internal` en `DATABASE_URL`
- **THEN** el contenedor alcanza PostgreSQL y `/health/ready` responde 200

#### Scenario: Dirección provista por la cátedra

- **WHEN** la cátedra entrega otra dirección de base
- **THEN** esa dirección se usa en el archivo de variables y queda documentada en `DEPLOY.md`
