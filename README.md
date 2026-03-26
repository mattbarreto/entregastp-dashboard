# Sistema de Seguimiento de Entregas - IFTS

<div align="center">

![Versión](https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/python-3.11-blue.svg?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)
![NocoDB](https://img.shields.io/badge/nocodb-v0.250+-orange.svg?style=for-the-badge)

</div>

Sistema *self-hosted* integral para el seguimiento y gestión de entregas de estudiantes en cursos de tecnicatura superior. Combina la potencia No-Code de NocoDB para la carga de datos con un Dashboard en Flask a medida para la visualización y análisis de progreso.

**Desarrollado por:** Matías Barreto  
**Web:** [www.matiasbarreto.com](https://www.matiasbarreto.com)

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características Principales](#-características-principales)
- [Arquitectura](#-arquitectura)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Despliegue](#-instalación-y-despliegue)
- [Configuración de NocoDB (Importante)](#%EF%B8%8F-configuración-de-nocodb-importante)
  - [1. Creación de Tablas](#1-creación-de-tablas)
  - [2. Configuración de Columnas y Relaciones](#2-configuración-de-columnas-y-relaciones)
  - [3. Formulario Público para Estudiantes](#3-formulario-público-para-estudiantes)
- [Guía Rápida de Uso](#-guía-rápida-de-uso)
- [Desarrollo Local](#-desarrollo-local)
- [Solución de Problemas (Troubleshooting)](#-solución-de-problemas-troubleshooting)
- [Licencia](#-licencia)

---

## 📝 Descripción

Este sistema permite a docentes y ayudantes de tecnicaturas superiores llevar un control riguroso, centralizado y visual del progreso de sus alumnos. 

A través de **NocoDB**, se generan formularios públicos para que los estudiantes suban sus trabajos sin necesidad de login. Por otro lado, el **Dashboard Flask** consume esta base de datos en tiempo real (modo solo lectura) para renderizar una matriz semafórica e indicadores de rendimiento, facilitando la detección temprana de alumnos en riesgo.

## ✨ Características Principales

- 📊 **Matriz Semafórica Visual:** Estado de entregas codificado por colores: Verde (a tiempo/corregido), Amarillo (tarde/rehacer), Rojo (vencido/no entregado), Gris (pendiente).
- 🎯 **Métricas Inteligentes:** Cálculo de índices de cumplimiento ponderando automáticamente trabajos semanales vs. TPs integradores.
- 👥 **Soporte Multi-Cohorte:** Gestiona múltiples comisiones o cursos simultáneamente, filtrando en vivo.
- 📤 **Exportación a Excel:** Descarga de reportes detallados con dos hojas (Resumen de Calificaciones y Detalle de Entregas) mediante `openpyxl`.
- 🔗 **Integración Directa:** Panel lateral interactivo con accesos directos al email y perfil de GitHub del estudiante seleccionado.

---

## 🏗 Arquitectura

La solución se divide en tres componentes dockerizados:

1.  **NocoDB:** Actúa como *Backend-as-a-Service* (BaaS) y CMS para el docente. Se conecta a una base de datos SQLite.
2.  **Dashboard Flask:** Aplicación web (Python/Gunicorn) que lee la base de datos SQLite generada por NocoDB para construir la interfaz y los reportes. Utiliza Tailwind CSS mediante CDN para el frontend.
3.  **Traefik (Opcional pero recomendado):** En entornos de producción, se sugiere el uso de un proxy inverso como Traefik para gestionar certificados SSL y enrutamiento (ej. `seguimientotps.tudominio.com` y `nocodb.tudominio.com`).

---

## ⚙️ Requisitos Previos

Para desplegar este proyecto en tu servidor (VPS) o entorno local, necesitas:

- [Docker Engine](https://docs.docker.com/engine/install/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- Git

---

## 🚀 Instalación y Despliegue

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/mattbarreto/entregastp-dashboard.git
cd entregastp-dashboard
```

### Paso 2: Variables de entorno

Copia el archivo de ejemplo para establecer las variables de entorno.

```bash
cp .env.example .env
```

Edita el archivo `.env` según tus necesidades (por defecto, la configuración funciona *out-of-the-box* para Docker).

### Paso 3: Levantar los servicios

Inicia la infraestructura utilizando Docker Compose:

```bash
docker compose up -d
```

Los servicios estarán disponibles en:
- **NocoDB (Administración):** `http://localhost:8080` (Crea tu cuenta admin en el primer inicio).
- **Dashboard Flask:** `http://localhost:5000` (Estará vacío hasta configurar NocoDB).

---

## 🛠️ Configuración de NocoDB (Importante)

Para que el Dashboard de Flask funcione correctamente, NocoDB debe tener un esquema de tablas específico. **No automatices este paso por API**, créalas manualmente desde la interfaz visual de NocoDB (`http://localhost:8080`) para asegurar la correcta generación de metadatos internos.

### 1. Creación de Tablas
Crea un "Nuevo Proyecto" y añade **4 tablas vacías** con los siguientes nombres exactos:
1. `Cohortes`
2. `Actividades`
3. `Estudiantes`
4. `Entregas`

### 2. Configuración de Columnas y Relaciones

Configura cada tabla con las columnas detalladas a continuación. **Nota:** Al crear relaciones (`LinkToAnotherRecord`), selecciona siempre el tipo **"Tiene muchos" (Has Many)** cuando apuntes desde una tabla hija a una tabla padre (ej. de Estudiantes a Cohortes).

#### Tabla: `Cohortes`
| Nombre de Columna | Tipo de NocoDB | Descripción |
| :--- | :--- | :--- |
| **Nombre** | `SingleLineText` | (Display Value) Ej: "pln-1c-2026" |
| **Activa** | `Checkbox` | Marcar si la cohorte está en curso |

#### Tabla: `Actividades`
| Nombre de Columna | Tipo de NocoDB | Descripción |
| :--- | :--- | :--- |
| **Nombre** | `SingleLineText` | (Display Value) Ej: "Semana 1", "TP1" |
| **Orden** | `Number` | Orden cronológico (1, 2, 3...) |
| **Fecha Límite** | `Date` o `DateTime` | Deadline de la entrega |
| **Tipo** | `SingleSelect` | Opciones: `Semanal`, `Integrador` |
| **Peso** | `Number` | Multiplicador (Ej: `1` semanal, `2` integrador) |
| **URL Guía** | `URL` | Enlace a consigna o material |
| **Cohorte** | `LinkToAnotherRecord` | Elige **"Tiene muchos"** apuntando a `Cohortes` |

#### Tabla: `Estudiantes`
| Nombre de Columna | Tipo de NocoDB | Descripción |
| :--- | :--- | :--- |
| **Apellido** | `SingleLineText` | (Display Value) Apellido principal |
| **Nombre** | `SingleLineText` | Nombre de pila |
| **Email** | `Email` | Correo de contacto |
| **GitHub** | `URL` o `SingleLineText` | URL del perfil |
| **Cohorte** | `LinkToAnotherRecord` | Elige **"Tiene muchos"** apuntando a `Cohortes` |

#### Tabla: `Entregas`
⚠️ *Importante: En NocoDB, el "Display Value" (1ra columna) no puede ser un SingleSelect.*
| Nombre de Columna | Tipo de NocoDB | Descripción |
| :--- | :--- | :--- |
| **ID Entrega** | `SingleLineText` | (Display Value) Déjalo vacío, solo cumple el requisito técnico |
| **Estado** | `SingleSelect` | Opciones: `Entregado`, `Entregado tarde`, `Corregido`, `Rehacer` |
| **URL Entrega** | `URL` | Link al Repositorio/Documento del alumno |
| **Estudiante** | `LinkToAnotherRecord` | Elige **"Tiene muchos"** apuntando a `Estudiantes` |
| **Actividad** | `LinkToAnotherRecord` | Elige **"Tiene muchos"** apuntando a `Actividades` |

### 3. Formulario Público para Estudiantes

Para que los estudiantes puedan entregar sus trabajos, debes crear una vista de tipo Formulario en NocoDB:

1.  Ve a la tabla **`Entregas`**.
2.  Haz clic en el botón **`+`** al lado de las vistas (donde dice "Grid View").
3.  Selecciona **`Form`** y ponle un nombre (ej. "Entrega de TPs").
4.  Configura el formulario:
    *   **Oculta** el campo `ID Entrega` (clic en el ojo).
    *   Deja visibles `Estudiante`, `Actividad` y `URL Entrega`.
    *   Puedes ocultar `Estado` y ponerle un valor predeterminado de "Entregado".
5.  Haz clic en **`Share`** (arriba a la derecha) y activa **`Shared View`**.
6.  Copia la URL generada. **Este es el enlace que debes enviar a tus estudiantes.**

---

## 📚 Guía Rápida de Uso

1. **Alta de Cursada:** Comienza creando una `Cohorte` y márcala como "Activa".
2. **Carga de Alumnos:** Importa tu lista de alumnos a la tabla `Estudiantes` (Puedes usar la función "Importar CSV" de NocoDB). Asígnales la cohorte correspondiente.
3. **Planificación:** Carga las tareas en la tabla `Actividades`, asignándoles su fecha límite y cohorte.
4. **Recepción:** Crea una "Form View" (Paso 3 arriba) y comparte esa URL pública con tus alumnos.
5. **Corrección y Seguimiento:** Revisa los envíos desde NocoDB cambiando su `Estado`. Abre el **Dashboard Flask** para tener una visión panóptica del grupo y acceder a las métricas de rendimiento.

---

## 💻 Desarrollo Local

Para modificar el Dashboard Flask sin usar Docker:

1. Asegúrate de tener Python 3.11+ instalado.
2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   pip install -r dashboard/requirements.txt
   ```
3. Genera una base de datos de prueba con datos simulados (Opcional):
   ```bash
   python seed_db.py
   ```
4. Ejecuta el servidor Flask de desarrollo:
   ```bash
   flask --app dashboard.app run --debug
   ```

---

## 🔧 Solución de Problemas (Troubleshooting)

### Error 500 al acceder al Dashboard (SQLite OperationalError)
- **Causa:** El Dashboard no encuentra las tablas en la base de datos `noco.db`.
- **Solución:** Asegúrate de haber completado la [Configuración de NocoDB](#%EF%B8%8F-configuración-de-nocodb-importante). El dashboard no se romperá si las tablas no existen (mostrará vacío), pero fallará si el esquema o los nombres difieren de los esperados.

### NocoDB bloquea la base de datos ("database is locked")
- **Causa:** Concurrencia de escritura de SQLite.
- **Solución:** Reinicia ambos contenedores:
  ```bash
  docker compose restart
  ```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

<div align="center">
  <sub>Desarrollado con ❤️ para la educación</sub>
</div>
