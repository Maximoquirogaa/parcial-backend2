# modelo-migraciones Specification

## Purpose
Define el modelo de dominio ampliado del parcial —usuarios, roles, intentos de acceso, eventos de seguridad, movimientos de stock y los cambios en clientes y libros— junto con sus restricciones y la forma en que el esquema evoluciona mediante migraciones versionadas.

## Requirements

### Requirement: Tablas de acceso y auditoría
El esquema SHALL incluir las tablas `usuario`, `asignacion_rol`, `intento_acceso` y `evento_seguridad` con las columnas indicadas por la consigna, `usuario.email` único y un CHECK que limita `asignacion_rol.rol` a ADMIN, VENDEDOR o CLIENTE.

#### Scenario: Rol inválido en la base
- **WHEN** se intenta guardar una asignación con un rol fuera de los tres permitidos
- **THEN** la base rechaza la escritura por el CHECK

#### Scenario: Email de usuario repetido
- **WHEN** se intenta guardar un segundo usuario con el mismo email
- **THEN** la base rechaza la escritura por el UNIQUE

#### Scenario: Consulta de intentos por correo, IP y fecha
- **WHEN** se filtra `intento_acceso` por email, IP y rango de fechas
- **THEN** existe un índice compuesto que sostiene la consulta

### Requirement: Una sola asignación abierta por usuario y rol
`asignacion_rol` SHALL tener un índice único parcial sobre (`usuario_id`, `rol`) limitado a las filas con `revocada_en` nula. Revocar SHALL escribir la fecha de revocación sin borrar la fila.

#### Scenario: Asignación duplicada vigente
- **WHEN** existe una asignación vigente y se intenta crear otra igual
- **THEN** la base rechaza la segunda escritura

#### Scenario: Reasignación tras revocar
- **WHEN** se revoca una asignación y se crea otra del mismo rol
- **THEN** la nueva fila se guarda y la anterior conserva su historial

### Requirement: Cliente vinculado opcionalmente a un usuario
La tabla `cliente` SHALL incorporar `usuario_id` nulo permitido y único, además de mantener `email` único. La relación SHALL navegar hacia un único usuario.

#### Scenario: Cliente sin acceso web
- **WHEN** se crea un cliente sin usuario asociado
- **THEN** la fila se guarda con `usuario_id` nulo

#### Scenario: Dos clientes con el mismo usuario
- **WHEN** se intenta vincular el mismo usuario a un segundo cliente
- **THEN** la base rechaza la escritura por el UNIQUE

### Requirement: Libro con borrado lógico e ISBN único entre vigentes
La tabla `libro` SHALL incorporar `borrado_en` con zona horaria y nulo permitido. La unicidad del ISBN SHALL garantizarse con un índice único parcial limitado a las filas con `borrado_en` nula, en lugar del UNIQUE común. Los CHECK de precio positivo y stock no negativo SHALL mantenerse.

#### Scenario: Dos libros vigentes con el mismo ISBN
- **WHEN** se intenta cargar un ISBN ya usado por un libro vigente
- **THEN** la base rechaza la escritura

#### Scenario: Reutilizar el ISBN de un libro dado de baja
- **WHEN** se carga un libro con el ISBN de uno dado de baja
- **THEN** la escritura se acepta

#### Scenario: Libro dado de baja conserva sus ventas
- **WHEN** un libro con ventas asociadas se da de baja
- **THEN** la fila permanece y las ventas anteriores siguen pudiendo referenciarlo

### Requirement: Movimiento de stock
El esquema SHALL incluir `movimiento_stock` con `libro_id`, `venta_id` nulo, `usuario_id`, `cantidad`, `motivo` y `cuando`, con CHECK de cantidad distinta de cero. Para cada libro, el stock SHALL ser igual a la suma de las cantidades de sus movimientos.

#### Scenario: Movimiento con cantidad cero
- **WHEN** se intenta registrar un movimiento con cantidad cero
- **THEN** la base rechaza la escritura por el CHECK

#### Scenario: Consistencia de stock
- **WHEN** se consultan stock y movimientos de un libro después de una venta
- **THEN** el stock coincide con la suma de las cantidades de sus movimientos

### Requirement: Tipos y claves foráneas del modelo ampliado
Todas las fechas nuevas SHALL ser `timestamptz`. El dinero SHALL permanecer como `NUMERIC` y `Decimal` en Python. Cada clave foránea nueva SHALL tener su propio índice y la navegación SHALL declararse en ambos extremos.

#### Scenario: Fecha con zona horaria
- **WHEN** se inspecciona una columna de fecha nueva
- **THEN** su tipo incluye zona horaria

#### Scenario: Consulta por clave foránea
- **WHEN** se filtra una tabla nueva por su clave foránea
- **THEN** existe un índice que la sostiene

### Requirement: Esquema evolucionado sólo con migraciones
El esquema SHALL crearse exclusivamente con Alembic; la aplicación MUST NOT usar `create_all`. Sobre las migraciones existentes SHALL agregarse dos nuevas: una autogenerada con las tablas y cambios de columnas, y otra escrita a mano con el disparador de sólo agregado.

#### Scenario: Base vacía
- **WHEN** se ejecuta `alembic upgrade head` sobre una base vacía
- **THEN** el esquema queda completo, incluidos índices y disparador

#### Scenario: Reversión completa
- **WHEN** se ejecuta `alembic downgrade base` y luego otra vez `alembic upgrade head`
- **THEN** ambas operaciones terminan sin error y el esquema queda equivalente

#### Scenario: Migración autogenerada revisada
- **WHEN** se lee la migración autogenerada
- **THEN** contiene un comentario que indica que fue revisada y, si hubo correcciones manuales, las explica

#### Scenario: Disparador escrito a mano
- **WHEN** se lee la cuarta migración
- **THEN** contiene el disparador de sólo agregado y su downgrade lo elimina
