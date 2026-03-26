# Sistema de Seguimiento de Entregas - IFTS

![Versión](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

Sistema self-hosted para seguimiento de entregas de estudiantes en cursos de tecnicatura superior.

**Desarrollado por:** Matías Barreto  
**Web:** [www.matiasbarreto.com](https://www.matiasbarreto.com)  
**Versión:** v1.0.0

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Tecnologías](#-tecnologías)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Guía para Ayudantes](#-guía-para-ayudantes)
- [FAQ](#-faq)
- [Troubleshooting](#-troubleshooting)
- [Desarrollo](#-desarrollo)
- [Licencia](#-licencia)

---

## 📝 Descripción

Este sistema permite a docentes y ayudantes de tecnicaturas superiores:

- 📊 **Visualizar** el estado de entregas de todos los estudiantes en una matriz intuitiva
- 🎯 **Calcular** índices de cumplimiento ponderados (semanales vs. integradores)
- 📈 **Identificar** estudiantes en riesgo de forma temprana
- 📤 **Exportar** reportes completos a Excel
- 🔗 **Centralizar** enlaces a guías y recursos por actividad

### Características principales

| Característica | Descripción |
|----------------|-------------|
| **Multi-cohorte** | Soporta múltiples cursos y cuatrimestres simultáneos |
| **Visualización por colores** | Verde (a tiempo), Amarillo (tarde), Rojo (no entregó), Gris (pendiente) |
| **Panel lateral** | Ver detalle completo de cada estudiante con un clic |
| **Cálculo inteligente** | TPs integradores pesan más que entregas semanales |
| **Exportación Excel** | Reportes con dos hojas: resumen y detalle |
| **Formularios públicos** | Estudiantes entregan sin necesidad de login |

---

## 🛠 Tecnologías

- **NocoDB** (v0.250+) - Base de datos y formularios
- **Flask** (v3.0.0) - Backend del dashboard
- **SQLite** - Almacenamiento de datos
- **Tailwind CSS** - Estilos del frontend
- **Docker** & Docker Compose - Deployment
- **OpenPyXL** - Exportación a Excel

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  NocoDB (http://localhost:8080)                              │
│  ├── Formulario público para entregas (estudiantes)         │
│  └── Panel de administración (docentes/ayudantes)           │
│       ├── Tabla Cohortes                                    │
│       ├── Tabla Estudiantes                                 │
│       ├── Tabla Actividades                                 │
│       └── Tabla Entregas                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │   SQLite    │
              │   noco.db   │
              └──────┬──────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Dashboard Flask (http://localhost:5000)                     │
│  ├── /            - Dashboard principal (matriz)            │
│  ├── /resumen     - Vista de métricas (solo docentes)       │
│  ├── /faq         - Preguntas frecuentes                    │
│  └── /api/exportar-excel - Descarga de reportes             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Instalación

### Requisitos previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (opcional, para clonar)

### Paso 1: Clonar o descargar

```bash
git clone https://github.com/tu-usuario/entregas-dashboard.git
cd entregas-dashboard
```

O descarga el ZIP y descomprime.

### Paso 2: Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```bash
# Opcional: filtrar solo cohortes activas
COHORTE_FILTRAR_ACTIVAS=true

# Modo Flask (production para deployment)
FLASK_ENV=production
```

### Paso 3: Levantar servicios

```bash
docker-compose up -d
```

Espera 30 segundos a que NocoDB inicialice.

### Paso 4: Configurar NocoDB

1. Accede a `http://localhost:8080`
2. Crea tu cuenta de administrador
3. Crea un proyecto llamado "Seguimiento Entregas"
4. Crea las tablas según el [schema de base de datos](#schema-de-base-de-datos)

### Paso 5: Verificar

- Dashboard: `http://localhost:5000`
- NocoDB Admin: `http://localhost:8080`

---

## ⚙️ Configuración

### Schema de Base de Datos

#### Tabla: Cohortes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Nombre | Single Line Text | Ej: "2026-Q1-Redes" |
| Curso | Single Select | "Tecnicatura Redes", "Tecnicatura Desarrollo" |
| Cuatrimestre | Single Select | "Q1", "Q2" |
| Año | Number | Año de la cohorte |
| Fecha Inicio | Date | Inicio de clases |
| Fecha Fin | Date | Fin de clases |
| Activa | Checkbox | Visible en dashboard |

#### Tabla: Actividades

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Nombre | Single Line Text | "Semana 1", "TP Integrador 1" |
| Orden | Number | Orden de aparición (1, 2, 3...) |
| Tipo | Single Select | "Semanal" o "Integrador" |
| Peso | Number | 1 para semanales, 10 para integradores |
| Fecha Límite | DateTime | Deadline de entrega |
| URL Guía | URL | Link al Colab/documento |
| Cohorte | Link | Relación con tabla Cohortes |

#### Tabla: Estudiantes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Nombre | Single Line Text | Nombre del estudiante |
| Apellido | Single Line Text | Apellido del estudiante |
| Email | Email | Correo institucional |
| GitHub | URL | Peril de GitHub |
| Cohorte | Link | Relación con tabla Cohortes |

#### Tabla: Entregas

| Campo | Tipo | Descripción |
|-------|------|-------------|
| Estudiante | Link | Relación con tabla Estudiantes |
| Actividad | Link | Relación con tabla Actividades |
| URL Entrega | URL | Link a la entrega (GitHub, etc.) |
| Archivo | Attachment | Archivo adjunto (opcional) |
| Estado | Single Select | "Entregado", "Corregido", "Rehacer", "No entregado" |
| Observaciones | Long Text | Feedback del docente |

---

## 📚 Guía para Ayudantes

### Crear una cohorte

1. En NocoDB, ve a **Tabla Cohortes**
2. Haz clic en **+ Nuevo**
3. Completa los campos:
   - **Nombre:** Usa formato "AÑO-Cuatrimestre-Curso" (ej: "2026-Q1-Redes")
   - **Curso:** Selecciona de la lista
   - **Cuatrimestre:** Q1 o Q2
   - **Año:** 2026, 2027, etc.
   - **Fechas:** Inicio y fin del período
   - **Activa:** Marca esta casilla

### Cargar estudiantes desde CSV

1. Prepara un archivo CSV con este formato:
   ```csv
   Nombre,Apellido,Email,GitHub
   Juan,Pérez,juan.perez@universidad.edu.ar,https://github.com/juanperez
   María,García,maria.garcia@universidad.edu.ar,https://github.com/mariagarcia
   ```

2. En NocoDB, tabla **Estudiantes**:
   - Haz clic en los tres puntos (⋯) arriba a la derecha
   - Selecciona **Importar CSV**
   - Selecciona tu archivo
   - Mapea las columnas correspondientes
   - **Importante:** Asigna la cohorte a todos los estudiantes importados

### Crear actividades/semanas

1. En NocoDB, ve a **Tabla Actividades**
2. Haz clic en **+ Nuevo**
3. Completa:
   - **Nombre:** "Semana 1", "Semana 2", "TP Integrador 1", etc.
   - **Orden:** Número secuencial (1, 2, 3, 4...)
   - **Tipo:**
     - "Semanal" para prácticas semanales
     - "Integrador" para TPs evaluativos
   - **Peso:**
     - 1 para semanales
     - 10 para integradores
   - **Fecha Límite:** Fecha y hora límite de entrega
   - **URL Guía:** Link al notebook de Colab o documento

### Usar el formulario de entregas

1. En NocoDB, tabla **Entregas**
2. Crea una **Form View** (vista de formulario)
3. Configura campos visibles:
   - Estudiante (dropdown)
   - Actividad (dropdown)
   - URL Entrega
   - Archivo (opcional)
4. Guarda y copia la URL pública
5. Comparte la URL con los estudiantes

### Corregir entregas en NocoDB

1. Ve a la tabla **Entregas**
2. Busca la entrega por:
   - Filtro por estudiante, o
   - Filtro por actividad
3. Cambia el campo **Estado**:
   - **Entregado** → Recibido, pendiente de corrección
   - **Corregido** → Revisado y aprobado ✅
   - **Rehacer** → Debe corregir y reenviar ⚠️
   - **No entregado** → No se recibió ❌
4. Agrega **Observaciones** con el feedback

### Usar el dashboard de seguimiento

1. Accede a `http://localhost:5000`
2. Selecciona la cohorte desde el dropdown
3. Visualiza:
   - **Filas:** Estudiantes (ordenados alfabéticamente)
   - **Columnas:** Actividades (en orden cronológico)
   - **Colores:** Estado de cada entrega
4. **Haz clic en un estudiante** para ver detalle:
   - Email y GitHub
   - Listado de todas sus entregas
   - Estado de cada una

### Usar la vista de resumen (solo docentes)

1. Accede a `http://localhost:5000/resumen`
2. Visualiza métricas por estudiante:
   - % Entregas semanales
   - % Entregas integradores
   - Índice de participación
   - Índice final ponderado
   - Clasificación (Excelente/Bueno/Regular/Deficiente)
3. Identifica rápidamente estudiantes en riesgo

### Exportar a Excel

1. En la vista **Resumen**, haz clic en **📊 Exportar Excel**
2. Se descargará un archivo con dos hojas:
   - **Resumen:** Una fila por estudiante con todas las métricas
   - **Detalle:** Todas las entregas con su estado

---

## ❓ FAQ

**¿Dónde encuentro más información?**

Visita la página de FAQ integrada: `http://localhost:5000/faq`

**¿Cómo calcula el sistema el índice final?**

```
Índice Final = (TP Integrador 1 × 40%) + (TP Integrador 2 × 40%) + (Participación × 20%)

Participación = (Entregas a tiempo × 1.0 + Entregas tarde × 0.5) / Total semanales × 100
```

**¿Puedo usar el sistema sin Docker?**

Sí, pero requiere instalar NocoDB y Python manualmente. Ver sección [Desarrollo](#-desarrollo).

**¿Cuántos estudiantes soporta?**

Probado hasta 200 estudiantes por cohorte. Para más, considera migrar a PostgreSQL.

---

## 🔧 Troubleshooting

### Error: "database is locked"

**Causa:** SQLite no permite escritura simultánea.  
**Solución:**
```bash
docker restart nocodb
docker restart entregas-dashboard
```

### El dashboard muestra "No hay datos"

**Verifica:**
1. Existe una cohorte con "Activa" marcado
2. La cohorte tiene estudiantes
3. La cohorte tiene actividades

### Las columnas no se ven correctamente

**Solución:** Reinicia el dashboard para releer el schema:
```bash
docker restart entregas-dashboard
```

### NocoDB no inicia

**Verifica puertos:**
```bash
docker logs nocodb
```
Asegúrate de que el puerto 8080 no esté ocupado.

---

## 💻 Desarrollo

### Requisitos

- Python 3.11+
- pip
- virtualenv (opcional)

### Setup local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r dashboard/requirements.txt

# Generar base de prueba
python seed_db.py

# Ejecutar dashboard
export NOCODB_DB_PATH=test_data/noco.db  # Linux/Mac
set NOCODB_DB_PATH=test_data/noco.db     # Windows
flask --app dashboard.app run --debug
```

### Estructura del proyecto

```
entregas-tracker/
├── docker-compose.yml          # Orquestación de servicios
├── README.md                   # Este archivo
├── LICENSE                     # Licencia MIT
├── .env.example                # Variables de entorno ejemplo
├── .gitignore                  # Exclusiones de git
├── backup.sh                   # Script de backup
├── seed_db.py                  # Datos de prueba
└── dashboard/
    ├── Dockerfile              # Build del dashboard
    ├── requirements.txt        # Dependencias Python
    ├── app.py                  # Backend Flask
    └── templates/
        ├── index.html          # Dashboard principal
        ├── resumen.html        # Vista de métricas
        └── faq.html            # Preguntas frecuentes
```

---

## 📄 Licencia

MIT License - ver archivo [LICENSE](LICENSE) para detalles.

---

## 👤 Autor

**Matías Barreto**
- Web: [www.matiasbarreto.com](https://www.matiasbarreto.com)
- Versión: v1.0.0

---

<div align="center">
  <sub>Desarrollado con ❤️ para la educación pública</sub>
</div>
