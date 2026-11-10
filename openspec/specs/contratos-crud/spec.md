# contratos-crud Specification

## Purpose
Define los contratos de entrada y salida de la API, la semántica de códigos de estado, las reglas del PATCH parcial y el formato uniforme de los listados paginados.

## Requirements

### Requirement: Contratos separados y estrictos
Los contratos de entrada SHALL ser independientes de los modelos de tabla y MUST rechazar los campos que no declaran. Ninguna respuesta SHALL incluir `password_hash`.

#### Scenario: Campo no declarado
- **WHEN** se envía un cuerpo con un campo que el contrato de entrada no declara, por ejemplo `rol` en el registro de un usuario
- **THEN** la respuesta es 422 y no se ejecuta la escritura

#### Scenario: Intento de editar stock por PATCH
- **WHEN** se envía un PATCH de libro con el campo `stock`
- **THEN** la respuesta es 422 y el stock no cambia

#### Scenario: Respuesta de usuario
- **WHEN** se consulta un usuario o el resultado de un registro
- **THEN** la respuesta no contiene `password_hash` en ninguna forma

### Requirement: PATCH aplica sólo los campos enviados
Los PATCH SHALL actualizar únicamente los campos presentes en el cuerpo y SHALL dejar intactos los ausentes.

#### Scenario: PATCH de un solo campo
- **WHEN** se envía un PATCH con únicamente el título de un libro
- **THEN** sólo cambia el título y los demás campos conservan su valor

#### Scenario: PATCH con campo vacío
- **WHEN** se envía un PATCH con un campo declarado pero sin valor válido
- **THEN** la respuesta es 422 y no se modifica el registro

### Requirement: Códigos de estado consistentes
La API SHALL responder 201 al crear, 204 al dar de baja un libro sin cuerpo, 404 cuando el recurso de la ruta no existe, 409 cuando la operación choca con datos guardados y 422 cuando el cuerpo o los parámetros no cumplen el contrato.

#### Scenario: Alta exitosa
- **WHEN** se crea un recurso con un cuerpo válido
- **THEN** la respuesta es 201 con el recurso creado

#### Scenario: Baja de libro
- **WHEN** se da de baja un libro existente
- **THEN** la respuesta es 204 sin cuerpo

#### Scenario: Recurso inexistente
- **WHEN** se pide por identificador un recurso que no existe
- **THEN** la respuesta es 404 con mensaje propio

#### Scenario: Choque de unicidad
- **WHEN** se intenta crear un recurso que viola una unicidad de la base
- **THEN** la respuesta es 409 con un mensaje propio, sin texto interno de la base

#### Scenario: Identificador de ruta no entero
- **WHEN** se envía un identificador de ruta que no es un entero, con sesión iniciada
- **THEN** la respuesta es 422 sin ejecutar el handler

### Requirement: Envoltorio de paginación
Todos los listados SHALL devolver `{items, total, page, size, pages}`. `page` empieza en 1, `size` va de 1 a 100 con 20 por defecto, `pages` se calcula desde `total` y `total` cuenta con los mismos filtros que la página. Con cero resultados SHALL haber una página vacía. Pedir una página posterior a la última o un `size` fuera de rango SHALL ser 422.

#### Scenario: Página dentro del rango
- **WHEN** se pide `GET /libros?size=2` con cinco libros
- **THEN** la respuesta trae dos ítems, `total` 5, `page` 1, `size` 2 y `pages` 3

#### Scenario: Página fuera de rango
- **WHEN** se pide una página mayor que la última disponible
- **THEN** la respuesta es 422

#### Scenario: Tamaño fuera de rango
- **WHEN** se pide `size=500`
- **THEN** la respuesta es 422

#### Scenario: Sin resultados
- **WHEN** un filtro no encuentra coincidencias
- **THEN** la respuesta trae `items` vacío, `total` 0, `page` 1 y `pages` 1

#### Scenario: Total con filtro
- **WHEN** se lista con `titulo=ficc&size=1`
- **THEN** `total` y `pages` reflejan sólo los libros que coinciden con el filtro

### Requirement: Búsqueda por título segura
La búsqueda de libros por título SHALL usar parámetros ligados, sin distinguir mayúsculas y sin concatenar datos del usuario en el SQL.

#### Scenario: Intento de inyección
- **WHEN** se busca con el título `' OR '1'='1'`
- **THEN** la respuesta trae una lista vacía con total 0 y no se ejecuta SQL arbitrario

#### Scenario: Coincidencia parcial sin distinguir mayúsculas
- **WHEN** se busca por un fragmento del título en minúsculas
- **THEN** se devuelven los libros cuyo título contiene ese fragmento sin importar mayúsculas

### Requirement: Errores sin información interna
Ningún error SHALL devolver texto interno de la base ni una traza, y ninguna entrada inválida SHALL terminar en 500.

#### Scenario: Violación de integridad en alta
- **WHEN** una escritura viola una restricción de la base
- **THEN** la respuesta es un error del dominio con mensaje propio y sin nombre de tabla, columna ni consulta

#### Scenario: Entrada inválida
- **WHEN** se envía un cuerpo con tipos o valores inválidos
- **THEN** la respuesta es 422, nunca 500
