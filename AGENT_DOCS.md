# Documentación Interna para Agentes y Desarrolladores (AGENT_DOCS)

Este documento contiene la información estructural y arquitectónica central sobre cómo la aplicación Flask (Dashboard) interactúa con la base de datos de NocoDB v2. 

**IMPORTANTE: Este archivo no debe subirse al repositorio público.**

## Arquitectura de Datos: Smart Schema Discovery

El Dashboard implementa un motor de descubrimiento dinámico (`discover_schema`) en `app.py`. Este motor permite que la aplicación Flask sobreviva a las inconsistencias y a la estructura interna críptica de NocoDB v2.

### 1. Nombres Internos de NocoDB
En NocoDB v2, cuando un usuario crea una tabla (ej. `Actividades`), NocoDB no llama a la tabla física de SQLite de esa forma. Le asigna un prefijo (ej. `nc_r9wk___Actividades`) u horrores similares. 
Lo mismo ocurre con las Foreign Keys, que reciben sufijos como `_id` y prefijos como `nc_oniw___`.

### 2. Detección Inteligente 
Debido a estos nombres crípticos, el Dashboard:
1. Lee las tablas estructurales de NocoDB (`nc_models_v2`, `nc_columns_v2`) para mapear "Nombres Visuales" a "Nombres Físicos".
2. Ignora los acentos y las mayúsculas/minúsculas (`get_column_name` usando `unicodedata.normalize`).
3. Soporta alias internos para plurales/singulares.

## Regla de Oro de las Relaciones (Foreign Keys)

Para que el modelo relacional del Dashboard (que espera cruzar `Entregas` con `Estudiantes` y `Actividades`) funcione sin problemas ni bucles de tablas intermedias (Many-to-Many), **todas las relaciones deben crearse desde la tabla padre hacia la hija usando "Tiene muchos" (Has Many)**. 

El código del Dashboard ya está programado para buscar relaciones inversas si fuera necesario, pero este es el método nativo recomendado.

### Guía de Recreación de Relaciones (Paso a Paso)

Si en el futuro hay que recrear el esquema o la base de datos se corrompe, se debe seguir exactamente este orden:

---

**Paso 1: Limpieza (Importante)**
Antes de empezar, borrar todas las columnas que tengan el icono de vinculo en todas las tablas (`Cohortes`, `Actividades`, `Estudiantes`, `Entregas`). Esto resetea las relaciones para que podamos crearlas bien desde cero.

---

**Paso 2: Relación Cohorte a Actividades (1:N)**
1. Ir a la tabla: `Cohortes`.
2. Crear un campo nuevo: `LinkToAnotherRecord`.
3. Nombre del campo: `Actividades`.
4. Tabla destino: `Actividades`.
5. Tipo de relación: `Tiene muchos` (Has Many).
6. Nombre del campo espejo (en Actividades): `Cohorte`.

---

**Paso 3: Relación Cohorte a Estudiantes (1:N)**
1. Ir a la tabla: `Cohortes`.
2. Crear un campo nuevo: `LinkToAnotherRecord`.
3. Nombre del campo: `Estudiantes`.
4. Tabla destino: `Estudiantes`.
5. Tipo de relación: `Tiene muchos` (Has Many).
6. Nombre del campo espejo (en Estudiantes): `Cohorte`.

---

**Paso 4: Relación Estudiantes a Entregas (1:N)**
1. Ir a la tabla: `Estudiantes`.
2. Crear un campo nuevo: `LinkToAnotherRecord`.
3. Nombre del campo: `Entregas`.
4. Tabla destino: `Entregas`.
5. Tipo de relación: `Tiene muchos` (Has Many).
6. Nombre del campo espejo (en Entregas): `Estudiante`.

---

**Paso 5: Relación Actividades a Entregas (1:N)**
1. Ir a la tabla: `Actividades`.
2. Crear un campo nuevo: `LinkToAnotherRecord`.
3. Nombre del campo: `Entregas`.
4. Tabla destino: `Entregas`.
5. Tipo de relación: `Tiene muchos` (Has Many).
6. Nombre del campo espejo (en Entregas): `Actividad`.

### Por qué NocoDB requiere este flujo:
Al elegir "Tiene muchos" (o equivalentemente hacer un Link con Many-to-One desde el lado contrario), se inserta físicamente una columna de `ForeignKey (FK)` en la tabla hija. 
Por ejemplo, la tabla `Entregas` termina teniendo físicamente las columnas `Estudiante_id` y `Actividad_id`. Eso es lo que la macro de Python busca para realizar el `JOIN` dinámico. Si permites múltiples registros en ambos lados, NocoDB silenciosamente creará una tabla intermedia (`_nc_m2m_...`), la cual NO es validada por el Dashboard y romperá la representación de los datos.
