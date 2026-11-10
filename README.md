# Parcial: La Librería con Acceso, Transacciones y Despliegue en el VPS

Trabajo Práctico Integrador — Capítulos 1 a 6: Del objeto a la transacción.  
**Materia:** Programación III  
**Carrera:** Tecnicatura Universitaria en Programación a Distancia — Universidad Tecnológica Nacional (UTN)

## Integrantes del Grupo
* **Máximo Juan Cruz Quiroga**
* **Fabrizio Simón**

---

## 1. Descripción del Proyecto

API asincrónica construida con **FastAPI**, **SQLModel**, **SQLAlchemy 2.0 (asincrónico)**, **asyncpg**, **PostgreSQL** y versionada con **Alembic**.

El sistema modela una librería completa que administra su catálogo, ventas, control de inventario y seguridad con autenticación y autorización basada en roles (RBAC):
* **Arquitectura en capas desacopladas:** Router → Service → Unit of Work → Repository → Model.
* **Autenticación segura:** Contraseñas hasheadas con `bcrypt` ejecutado fuera del bucle de eventos (`asyncio.to_thread`) bajo un semáforo de concurrencia. Tokens JWT firmados que viajan exclusivamente en una cookie `access_token` con atributos `HttpOnly`, `SameSite=Lax` y `Max-Age`.
* **Protección contra ataques de fuerza bruta:** Límite de 5 intentos fallidos en 60 segundos por IP/email antes de verificar contraseñas, respondiendo con HTTP `429 Too Many Requests` y cabecera `Retry-After: 60`.
* **Autorización en base de datos:** Consulta de roles vigentes (`ADMIN`, `VENDEDOR`, `CLIENTE`) directamente en `asignacion_rol` en cada petición protegida. Permite revocar roles inmediatamente sin esperar expiración del JWT.
* **Transacciones atómicas (Unit of Work):** Garantiza atomicidad en operaciones compuestas:
  - Auto-registro de clientes: crea `usuario`, rol `CLIENTE` y `cliente` en una sola transacción.
  - Registro de ventas: descuenta stock, crea `venta`, inserta `renglon_venta` y registra un `movimiento_stock` por renglón en una sola transacción.
  - Auditoría de seguridad: registra en `evento_seguridad` cada alta de personal, cambio de rol y cambio de contraseña en la misma transacción.
* **Tabla de sólo agregado (Append-Only):** La tabla `movimiento_stock` está protegida por un disparador PL/pgSQL que rechaza `UPDATE` y `DELETE`. El stock de un libro sólo cambia a través de movimientos.
* **Borrado lógico y reuso de identificadores:** `Libro` implementa borrado lógico (`borrado_en`). El `isbn` posee un índice único parcial `WHERE borrado_en IS NULL`, permitiendo reutilizar el ISBN de libros descatalogados manteniendo la integridad histórica de ventas.
* **Lecturas optimizadas sin N+1:** Consultas con relaciones precargadas (`selectinload`), manteniendo un número constante de consultas fijas independiente del número de renglones.

---

## 2. Estructura del Proyecto

Organización modular funcional y por capas:

```text
parcial/
├── app/
│   ├── core/
│   │   ├── config.py           # Settings con pydantic-settings (sin secretos por defecto)
│   │   ├── database.py         # Motor asincrónico, sesión en lifespan y get_session
│   │   ├── dependencies.py     # get_usuario_actual, roles vigentes, requiere_rol
│   │   ├── paginacion.py       # Envoltorio {items, total, page, size, pages}
│   │   ├── repository.py       # BaseRepository[T] y SoftDeleteRepository[T]
│   │   ├── security.py         # bcrypt (con semáforo y to_thread) y JWT
│   │   └── unit_of_work.py     # UnitOfWork base con confirmación / reversión automática
│   ├── modules/
│   │   ├── autores/            # Autores
│   │   ├── clientes/           # Clientes y PerfilCliente
│   │   ├── editoriales/        # Editoriales
│   │   ├── generos/            # Géneros literarios
│   │   ├── health/             # GET /health/live y GET /health/ready
│   │   ├── libros/             # Libros, MovimientoStock, LibroAutor
│   │   ├── usuarios/           # Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
│   │   └── ventas/             # Ventas, RenglonVenta y BackgroundTasks
│   └── main.py                 # Ciclo de vida (lifespan), rutas abiertas y protegidas
├── migrations/                 # Alembic asincrónico
│   ├── versions/               # Migraciones 1 a 4 (incluyendo disparador PL/pgSQL)
│   └── env.py
├── test/
│   ├── libreria.http           # Casos de prueba C-01 a C-16 en formato REST Client
│   └── solo_agregado.sql       # Consultas SQL para validar el caso C-14
├── evidencia/
│   ├── C-14_psql_solo_agregado.txt      # Captura de sesión psql demostrando el trigger solo-agregado
│   └── C-15_consultas_sin_n_mas_1.txt   # Consultas SQL demostrando ausencia de N+1
├── tests/                      # Suite de pruebas automatizadas TDD (pytest - 90 tests)
├── alembic.ini                 # Configuración de migraciones
├── env.example                 # Plantilla de variables de entorno sin credenciales reales
├── requirements.txt            # Dependencias del proyecto
├── seed.py                     # Carga de datos semilla iniciales
└── README.md                   # Esta documentación
```

---

## 3. Guía de Puesta en Marcha Desde Cero

### Paso 1: Crear y activar el entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# En Linux / macOS:
source venv/bin/activate
```

### Paso 2: Instalar las dependencias

```bash
pip install -r requirements.txt
```

### Paso 3: Configurar las variables de entorno

Copiar el archivo de plantilla `env.example` para generar el `.env` local:

```bash
# En Windows (PowerShell):
Copy-Item env.example .env

# En Linux / macOS:
cp env.example .env
```

Generar una clave de firma criptográfica secreta y segura de 256 bits (32 bytes en hexadecimal):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Editar el archivo `.env` resultante configurando las credenciales de PostgreSQL y la `SECRET_KEY` generada:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_contraseña_aqui
POSTGRES_DB=libreria_db
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
SECRET_KEY=pegar_aqui_la_clave_hexadecimal_generada
BCRYPT_COST=12
BCRYPT_MAX_CONCURRENT=4
POOL_SIZE=5
SQL_ECHO=false
```

*(Asegurarse de que la base de datos `libreria_db` exista en PostgreSQL).*

### Paso 4: Ejecutar las migraciones con Alembic

El esquema se crea exclusivamente a través de las migraciones versionadas:

```bash
alembic upgrade head
```

Esto ejecuta en orden:
1. Migración inicial de tablas base.
2. Agregado de tabla género y columna de libro.
3. Tablas de acceso (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`), `movimiento_stock` y borrado lógico en `libro`.
4. Migración manual con función y disparador PL/pgSQL `rechazar_modificacion_movimiento_stock`.

### Paso 5: Poblar los datos iniciales (Seed)

Ejecutar el script semilla para inicializar la base de datos con los datos requeridos por la consigna:

```bash
python seed.py
```

Datos precargados:
* **Usuarios:**
  - `admin@example.com` (Rol: ADMIN)
  - `admin2@example.com` (Rol: ADMIN)
  - `vendedor@example.com` (Rol: VENDEDOR)
  - `ana@example.com` (Rol: CLIENTE, vinculada al cliente Ana Paz)
  - `nuevo@example.com` (Rol: VENDEDOR, con `debe_cambiar_password=True`)
* **Contraseñas iniciales (entorno desarrollo/pruebas):**
  - Todas las cuentas tienen como contraseña inicial: `admin123` (salvo `nuevo@example.com` que utiliza `claveProvisoria1`).
* **Catálogo inicial:** 3 editoriales, 3 géneros, 6 autores y 5 libros con su stock inicial cargado mediante movimientos de stock.
* **Clientes:** Lucía Fernández (con perfil), Tomás Ríos (sin usuario) y Ana Paz (con usuario).
* **Ventas:** Venta inicial 1 de Lucía Fernández con 2 renglones y sus movimientos de salida correspondientes.
* **Auditoría:** Registro inicial en `evento_seguridad` con actor `SISTEMA`.

### Paso 6: Iniciar el servidor de desarrollo

```bash
uvicorn app.main:app --reload
```

El servidor quedará disponible en: `http://127.0.0.1:8000`.

* Documentación Swagger interactiva: `http://127.0.0.1:8000/docs`
* Endpoint de verificación de salud en vivo: `http://127.0.0.1:8000/health/live`
* Endpoint de verificación de base de datos lista: `http://127.0.0.1:8000/health/ready`

---

## 4. Casos de Prueba y Verificación

### Pruebas HTTP (C-01 a C-16)
El archivo `test/libreria.http` contiene todos los casos de prueba de referencia listos para ser ejecutados con la extensión **REST Client** de VS Code / Cursor:
* **C-01:** Parámetro de ruta inválido con sesión (422 sin ejecutar handler).
* **C-02:** Auto-registro con transacción única y control de unicidad de email (201 / 409).
* **C-03:** Cookie de sesión HttpOnly sin token en cuerpo ni aceptación de Bearer en cabecera (Set-Cookie / 401).
* **C-04:** Login con credenciales inválidas y usuario inexistente (mismo mensaje 401 y tiempo equivalente contra hash ficticio).
* **C-05:** Límite de 5 intentos fallidos y bloqueo temporal al 6to (429 con `Retry-After: 60`).
* **C-06:** Distinción entre 401 y 403, y control de acceso propio (`/mis-ventas` vs `/ventas/{id}`).
* **C-07:** Revocación inmediata de rol con sesión abierta y rechazo de vencimientos pasados o sin zona horaria (422 / 403).
* **C-08:** Autoprotección del administrador (no puede revocarse a sí mismo el rol ADMIN - 409).
* **C-09:** Control de cambio obligatorio de contraseña (bloqueo 403 salvo `/auth`).
* **C-10:** Registro de venta válida con cálculo en backend, descuento atómico de stock y BackgroundTask.
* **C-11:** Rechazo atómico de venta por stock insuficiente sin escrituras residuales (409).
* **C-12:** Rechazo de venta con cliente o libro inexistente/dado de baja (409).
* **C-13:** Reposición de stock, borrado lógico de libro (204) y reuso de ISBN descatalogado.
* **C-14:** Verificación del disparador de solo-agregado sobre `movimiento_stock` (ver `test/solo_agregado.sql` y `evidencia/C-14_psql_solo_agregado.txt`).
* **C-15:** Verificación empírica de lecturas sin N+1 en `GET /ventas/{id}` (ver `evidencia/C-15_consultas_sin_n_mas_1.txt`).
* **C-16:** Búsqueda con parámetros ligados contra SQL Injection, paginación estricta y rechazo de modificación de stock por PATCH.

### Suite Automatizada de Pruebas (Pytest - TDD)
Para ejecutar la suite completa de 90 tests automatizados:

```bash
pytest tests/ -v
```
