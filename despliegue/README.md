# Librería API: Catálogo, Clientes y Ventas con FastAPI y PostgreSQL

Trabajo Práctico Integrador — Unidades 1 a 4: Del objeto a la persistencia.  
**Materia:** Programación III  
**Carrera:** Tecnicatura Universitaria en Programación a Distancia — Universidad Tecnológica Nacional (UTN)

---

## 1. Descripción del Proyecto

API asincrónica desarrollada con **FastAPI**, **SQLModel**, **SQLAlchemy 2.0 (asincrónico)**, **asyncpg**, **PostgreSQL** y versionada con **Alembic**.

El dominio modela el catálogo y las operaciones de venta de una librería de barrio, abarcando todas las relaciones relacionales fundamentales:
* **Agregación:** `Libro` y `Editorial` (clave foránea con índice).
* **Agregación opcional:** `Libro` y `Genero` (clave foránea nullable con índice).
* **Muchos a muchos con datos:** `Libro` y `Autor` modelado a través de la entidad de asociación `LibroAutor` con atributos propios (`rol` y `orden`).
* **Uno a uno:** `Cliente` y `PerfilCliente` (`cliente_id` UNIQUE e índice, retornando un único objeto con `uselist=False`).
* **Asociación:** `Venta` y `Cliente`.
* **Composición:** `Venta` y `RenglonVenta` (se crean juntos en una misma transacción, precio unitario copiado y total calculado en servidor).
* **Asociación:** `RenglonVenta` y `Libro`.

---

## 2. Estructura del Proyecto

Organización por módulos funcionales según la directiva de la cátedra:

```text
Parcial_Backend/
├── app/
│   ├── core/
│   │   ├── config.py           # Lectura de DATABASE_URL desde .env con python-dotenv
│   │   └── database.py         # Motor asincrónico, fábrica de sesiones y dependencia get_session
│   ├── modules/
│   │   ├── autores/            # Modelos, schemas, servicio y router de autores
│   │   ├── clientes/           # Clientes y PerfilCliente (1 a 0..1)
│   │   ├── editoriales/        # Catálogo de editoriales
│   │   ├── generos/            # Géneros literarios
│   │   ├── health/             # Endpoints /health/live y /health/ready
│   │   ├── libros/             # Libros y LibroAutor (entidad intermedia con rol y orden)
│   │   └── ventas/             # Ventas y RenglonVenta (cálculo en backend y BackgroundTasks)
│   └── main.py                 # Ciclo de vida (lifespan), registro de routers y manejo de errores
├── migrations/                 # Configuración de Alembic y versiones autogeneradas
│   ├── versions/
│   │   ├── f929122fc980_crear_tablas_iniciales_sin_genero.py
│   │   └── 7e0413ea1de1_agregar_tabla_genero_y_columna_libro_.py
│   └── env.py                  # Configuración asincrónica de migraciones
├── test/
│   ├── libreria.http           # Casos de prueba HTTP listos para ejecutar (C-01 a C-08)
│   └── test_runner.py          # Ejecutor automatizado en Python para verificar la suite completa
├── .env                        # Variables de entorno locales (no se versiona en Git)
├── env.example                 # Plantilla de variables de entorno sin credenciales reales
├── requirements.txt            # Dependencias del proyecto
├── seed.py                     # Script para cargar datos semilla conocidos
└── README.md                   # Documentación técnica y pasos de instalación
```

---

## 3. Guía de Puesta en Marcha Desde Cero

### Paso 1: Clonar el repositorio y crear el entorno virtual

```bash
cd Parcial_Backend
python -m venv venv

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# En Linux/macOS:
source venv/bin/activate
```

### Paso 2: Instalar las dependencias

```bash
pip install -r requirements.txt
```

### Paso 3: Configurar las variables de entorno

Copiar el archivo de plantilla `env.example` para generar tu archivo `.env`:

```bash
cp env.example .env
```

Editar `.env` indicando la cadena de conexión de tu base de datos PostgreSQL local:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/libreria_db
```

*(Asegurarse de que la base de datos `libreria_db` exista en PostgreSQL).*

### Paso 4: Ejecutar las migraciones con Alembic

El esquema se crea exclusivamente a través de migraciones evolutivas versionadas:

```bash
python -m alembic upgrade head
```

*(Si se desea validar la capacidad de rollback requerida por el Ejercicio 3:)*
```bash
python -m alembic downgrade -1
python -m alembic upgrade head
```

### Paso 5: Poblar los datos iniciales conocidos

Ejecutar el script seeder que deja la base de datos en un estado predecible y reproducible para los tests:

```bash
python seed.py
```

### Paso 6: Iniciar el servidor de desarrollo

```bash
uvicorn app.main:app --reload
```
O con el CLI estándar de FastAPI:
```bash
fastapi dev app/main.py
```

El servidor estará accesible en `http://127.0.0.1:8000` y la documentación interactiva OpenAPI/Swagger en `http://127.0.0.1:8000/docs`.

---

## 4. Casos de Prueba (C-01 a C-08)

El archivo `test/libreria.http` contiene todos los casos mínimos solicitados en la consigna. Se pueden disparar directamente desde VS Code / PyCharm con el plugin REST Client, o bien ejecutar la suite completa de forma automatizada con:

```bash
python test/test_runner.py
```

### Resumen de casos evaluados:
* **C-01:** Parámetro de ruta no entero (`GET /editoriales/texto`) $\rightarrow$ Responde **422 Unprocessable Entity** sin ejecutar el handler.
* **C-02:** Email o ISBN repetido $\rightarrow$ Responde **409 Conflict** con mensaje propio y sin filtrar trazas de la base (RN-01, RN-02, RN-12).
* **C-03:** Segundo perfil para un mismo cliente $\rightarrow$ Responde **409 Conflict** garantizando la multiplicidad 1 a 0..1 (RN-09).
* **C-04:** Alta de libro con editorial o autor inexistente $\rightarrow$ Responde **409 Conflict** sin consultar previamente con `if` (Ejercicio 5).
* **C-05:** Venta con libro o cliente inexistente $\rightarrow$ Responde **409 Conflict**.
* **C-06:** Venta válida con dos renglones $\rightarrow$ Responde **201 Created**, precios copiados del libro (RN-06), total calculado en servidor (RN-07) y aviso agendado en segundo plano con `BackgroundTasks` (Ejercicio 7).
* **C-07:** Lecturas sin N+1 para libro y venta $\rightarrow$ Resuelve con número constante de consultas (demostrado abajo).
* **C-08:** Búsqueda por título con `' OR '1'='1` $\rightarrow$ Responde **200 OK** con lista vacía `[]`, confirmando el uso de parámetros ligados seguros (RN-11).

---

## 5. Evidencia del Caso C-07 (Lecturas sin N+1)

A continuación se adjunta el fragmento de la consola demostrando que las consultas de detalle ejecutan un **número fijo y constante de sentencias SQL**, independientemente de la cantidad de autores o renglones asociados:

### A) Detalle de Libro (`GET /libros/3`) — Libro con 2 coautores
* **Consulta 1:** Libro + `LEFT JOIN` con `editorial` y `genero` (relaciones a uno resueltas con `joinedload`):
```sql
SELECT libro.id, libro.isbn, libro.titulo, libro.precio, libro.stock, libro.editorial_id, libro.genero_id,
       editorial_1.id AS id_1, editorial_1.nombre, editorial_1.pais,
       genero_1.id AS id_2, genero_1.nombre AS nombre_1 
FROM libro 
LEFT OUTER JOIN editorial AS editorial_1 ON editorial_1.id = libro.editorial_id 
LEFT OUTER JOIN genero AS genero_1 ON genero_1.id = libro.genero_id 
WHERE libro.id = $1::INTEGER;
```
* **Consulta 2:** Colección de autorías con sus autores vinculados (relación a muchos resuelta con `selectinload` y `joinedload`):
```sql
SELECT libro_autor.libro_id AS libro_autor_libro_id, libro_autor.autor_id AS libro_autor_autor_id, 
       libro_autor.rol AS libro_autor_rol, libro_autor.orden AS libro_autor_orden, 
       autor_1.id AS autor_1_id, autor_1.nombre AS autor_1_nombre, autor_1.nacionalidad AS autor_1_nacionalidad 
FROM libro_autor 
LEFT OUTER JOIN autor AS autor_1 ON autor_1.id = libro_autor.autor_id 
WHERE libro_autor.libro_id IN ($1::INTEGER);
```
> **Total:** Exactamente **2 consultas SQL fijas**, sin importar cuántos autores tenga el libro.

---

### B) Detalle de Venta (`GET /ventas/1`) — Venta con 2 renglones
* **Consulta 1:** Venta + `LEFT JOIN` con `cliente` (relación a uno con `joinedload`):
```sql
SELECT venta.id, venta.cliente_id, venta.fecha, venta.total, 
       cliente_1.id AS id_1, cliente_1.nombre, cliente_1.email 
FROM venta 
LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER;
```
* **Consulta 2:** Colección de renglones con sus libros correspondientes (relación a muchos con `selectinload` y `joinedload`):
```sql
SELECT renglon_venta.venta_id AS renglon_venta_venta_id, renglon_venta.id AS renglon_venta_id, 
       renglon_venta.libro_id AS renglon_venta_libro_id, renglon_venta.cantidad AS renglon_venta_cantidad, 
       renglon_venta.precio_unitario AS renglon_venta_precio_unitario, 
       libro_1.id AS libro_1_id, libro_1.isbn AS libro_1_isbn, libro_1.titulo AS libro_1_titulo, 
       libro_1.precio AS libro_1_precio, libro_1.stock AS libro_1_stock, 
       libro_1.editorial_id AS libro_1_editorial_id, libro_1.genero_id AS libro_1_genero_id 
FROM renglon_venta 
LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER);
```
> **Total:** Exactamente **2 consultas SQL fijas**, sin importar cuántos renglones tenga la venta.

