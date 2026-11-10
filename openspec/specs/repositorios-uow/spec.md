# repositorios-uow Specification

## Purpose
Define la capa de acceso a datos: repositorios genéricos por entidad, Unit of Work por módulo que delimita las transacciones y la asignación de responsabilidades entre router, servicio, UoW y repositorio.

## Requirements

### Requirement: Repositorio base genérico
El repositorio base SHALL recibir en su constructor la sesión y la clase del modelo, y SHALL ofrecer al menos consulta por identificador, listado, conteo, alta, actualización y baja.

#### Scenario: Consulta por identificador
- **WHEN** se pide una entidad por su identificador
- **THEN** el repositorio devuelve la fila correspondiente o nada si no existe

#### Scenario: Conteo con filtros
- **WHEN** se solicita el total de una consulta con filtros
- **THEN** el valor coincide con los registros que cumplen los mismos filtros que el listado

#### Scenario: Clase del modelo requerida
- **WHEN** se construye un repositorio sin la clase del modelo
- **THEN** la operación falla de forma explícita, porque el genérico no se conserva en tiempo de ejecución

### Requirement: Repositorio de borrado lógico
El repositorio de libros SHALL extender el base, excluir por defecto las filas dadas de baja y agregar la consulta por identificador incluyendo dados de baja y la baja lógica. Esos dos métodos MUST NOT existir en el repositorio base.

#### Scenario: Listado excluye dados de baja
- **WHEN** se lista el catálogo y hay libros dados de baja
- **THEN** esos libros no aparecen

#### Scenario: Detalle incluyendo dados de baja
- **WHEN** se consulta por identificador con la variante que incluye dados de baja
- **THEN** se devuelve la fila aunque esté dada de baja

#### Scenario: Baja lógica
- **WHEN** se da de baja un libro
- **THEN** se escribe la fecha de borrado y la fila permanece

#### Scenario: Base sin métodos de borrado lógico
- **WHEN** se inspecciona el repositorio base
- **THEN** no expone la consulta con dados de baja ni la baja lógica

### Requirement: Los repositorios no confirman
Las operaciones de alta y actualización SHALL hacer `flush()` y MUST NOT hacer `commit()`. Ningún repositorio SHALL cerrar la sesión.

#### Scenario: Alta dentro de una transacción
- **WHEN** un repositorio agrega una entidad
- **THEN** los cambios quedan pendientes en la sesión y no se confirman solos

#### Scenario: Reversión posterior
- **WHEN** una operación falla después de una escritura del repositorio
- **THEN** la transacción se revierte y no queda la escritura parcial

### Requirement: Unit of Work base
El Unit of Work base SHALL ser un gestor de contexto asincrónico que confirma al salir sin excepción, revierte al salir con excepción y no cierra la sesión que no creó.

#### Scenario: Salida exitosa
- **WHEN** el bloque del Unit of Work termina sin excepción
- **THEN** la transacción se confirma

#### Scenario: Salida con excepción
- **WHEN** el bloque del Unit of Work termina con excepción
- **THEN** la transacción se revierte y la excepción se propaga

#### Scenario: Sesión ajena
- **WHEN** el Unit of Work termina
- **THEN** no cierra la sesión, porque la sesión la administra la dependencia de la petición

### Requirement: Unit of Work por módulo
Cada módulo SHALL tener su Unit of Work que compone sus repositorios sobre la misma sesión. El router SHALL construir el Unit of Work y pasarlo sin abrirlo; el servicio SHALL abrirlo con `async with` y MUST NOT construirlo. Las dependencias de identidad y rol SHALL usar la misma sesión.

#### Scenario: Construcción en el router
- **WHEN** llega una petición a un módulo
- **THEN** el router construye el Unit of Work y lo entrega al servicio

#### Scenario: Apertura en el servicio
- **WHEN** el servicio ejecuta una operación de negocio
- **THEN** abre el Unit of Work y lo usa como límite transaccional

#### Scenario: Una sola conexión autenticada
- **WHEN** una petición autenticada verifica identidad y rol y luego usa el Unit of Work
- **THEN** todas las operaciones comparten la misma sesión y no se toma una segunda conexión del pool

### Requirement: Operaciones de negocio atómicas
Las operaciones que escriben varias filas —registro de cliente, registro de venta y registro de eventos— SHALL ejecutarse en un único bloque del Unit of Work, de modo que o se guardan todas las escrituras o ninguna.

#### Scenario: Venta con varias escrituras
- **WHEN** se registra una venta con sus renglones, descuentos de stock y movimientos
- **THEN** todas las escrituras se confirman juntas o se revierten juntas

#### Scenario: Falla en la última escritura
- **WHEN** una escritura posterior falla dentro de la operación
- **THEN** no queda ninguna de las escrituras anteriores

### Requirement: Punto único de escritura de stock
El stock SHALL modificarse sólo a través de un único punto que registra el movimiento correspondiente. El alta con stock inicial, la reposición y la venta SHALL usarlo y MUST NOT escribir el stock por otra vía.

#### Scenario: Alta con stock inicial
- **WHEN** se crea un libro con stock inicial distinto de cero
- **THEN** se registra un movimiento de entrada por ese stock

#### Scenario: Reposición
- **WHEN** el administrador repone stock
- **THEN** el stock aumenta y se registra un movimiento con el motivo de reposición

#### Scenario: Venta
- **WHEN** se registra una venta
- **THEN** cada renglón descuenta stock y deja un movimiento de salida

#### Scenario: Escritura alternativa
- **WHEN** se busca en el código una escritura de stock fuera del punto único
- **THEN** no existe ninguna
