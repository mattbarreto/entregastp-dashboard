"""
Dashboard Flask para seguimiento de entregas de estudiantes.
Lee datos de SQLite de NocoDB en modo read-only.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from flask import Flask, render_template, request

app = Flask(__name__)

# === CONFIGURACIÓN ===
DB_PATH = os.environ.get('NOCODB_DB_PATH', '/data/noco.db')
FILTRAR_ACTIVAS = os.environ.get('COHORTE_FILTRAR_ACTIVAS', 'true').lower() == 'true'

# Nombres visibles de tablas que esperamos encontrar
TABLE_TITLES = {
    'Cohortes': 'nc_abcd_Cohortes',
    'Actividades': 'nc_abcd_Actividades',
    'Estudiantes': 'nc_abcd_Estudiantes',
    'Entregas': 'nc_abcd_Entregas'
}


# === CAPA DB ===

def get_db():
    """
    Conexión SQLite read-only con timeout.
    Cierra la conexión en finally de la ruta.
    """
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def discover_schema(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """
    Descubre el schema real de NocoDB leyendo las tablas de metadatos.
    Retorna: {
        'Cohortes': {
            'table_name': 'nc_abcd_Cohortes',
            'columns': {'Nombre': 'nc_c1_Nombre', 'Activa': 'nc_c7_Activa', ...}
        },
        ...
    }
    """
    schema = {}
    cursor = conn.cursor()

    # Primero intentar leer metadatos de NocoDB
    try:
        # Verificar si existen tablas de metadatos
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nc_models_v2'")
        has_models = cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nc_columns_v2'")
        has_columns = cursor.fetchone() is not None

        if has_models and has_columns:
            # Leer modelos (tablas)
            cursor.execute("SELECT id, table_name, title FROM nc_models_v2 WHERE type='table'")
            models = {row['title']: row['table_name'] for row in cursor.fetchall()}

            # Leer columnas de cada modelo
            cursor.execute("""
                SELECT fk_model_id, column_name, title, uidt
                FROM nc_columns_v2
                WHERE fk_model_id IN (SELECT id FROM nc_models_v2 WHERE type='table')
            """)
            columns_by_model = {}
            for row in cursor.fetchall():
                model_id = row['fk_model_id']
                if model_id not in columns_by_model:
                    columns_by_model[model_id] = {}
                columns_by_model[model_id][row['title']] = {
                    'column_name': row['column_name'],
                    'uidt': row['uidt']
                }

            # Mapear a estructura esperada
            cursor.execute("SELECT id, title FROM nc_models_v2 WHERE type='table'")
            for row in cursor.fetchall():
                title = row['title']
                table_name = row['id']  # usamos id como key para buscar columnas
                if title in ['Cohortes', 'Actividades', 'Estudiantes', 'Entregas']:
                    schema[title] = {
                        'table_name': models.get(title, f'nc_abcd_{title}'),
                        'columns': {}
                    }
                    if table_name in columns_by_model:
                        for col_title, col_info in columns_by_model[table_name].items():
                            schema[title]['columns'][col_title] = col_info['column_name']

            if schema:
                return schema

    except Exception as e:
        # Fallback a PRAGMA si falla metadatos
        pass

    # FALLBACK: Usar PRAGMA table_info con heurística
    for title, default_table in TABLE_TITLES.items():
        schema[title] = {'table_name': default_table, 'columns': {}}

        try:
            cursor.execute(f"PRAGMA table_info({default_table})")
            pragma_cols = cursor.fetchall()

            for col in pragma_cols:
                col_name = col['name']
                # Heurística: nc_cN_Title -> mapear a Title
                if col_name.startswith('nc_c') and '_' in col_name[4:]:
                    parts = col_name.split('_', 3)
                    if len(parts) >= 3:
                        visible_name = parts[2].replace('_', ' ')
                        schema[title]['columns'][visible_name] = col_name
                elif col_name.startswith('nc_fk_'):
                    # Foreign keys: nc_fk_tablename_id -> Tablename
                    fk_parts = col_name[6:].rsplit('_', 1)
                    if len(fk_parts) == 2:
                        fk_title = fk_parts[0].replace('_', ' ').title()
                        schema[title]['columns'][fk_title] = col_name
                else:
                    schema[title]['columns'][col_name] = col_name

        except Exception as e:
            # Si la tabla no existe, mantener schema vacío para esa tabla
            pass

    return schema


def get_column_name(schema: Dict, table_title: str, column_title: str) -> Optional[str]:
    """Obtiene el nombre físico de una columna dado su título visible."""
    if table_title not in schema:
        return None
    return schema[table_title]['columns'].get(column_title)


def get_table_name(schema: Dict, table_title: str) -> Optional[str]:
    """Obtiene el nombre físico de una tabla."""
    if table_title not in schema:
        return None
    return schema[table_title]['table_name']


# === CAPA DATOS ===

def get_cohortes(conn: sqlite3.Connection, schema: Dict) -> List[Dict]:
    """
    Lista todas las cohortes. Si FILTRAR_ACTIVAS=True, solo las activas.
    """
    table = get_table_name(schema, 'Cohortes')
    if not table:
        return []

    col_id = 'id'
    col_nombre = get_column_name(schema, 'Cohortes', 'Nombre') or 'nc_c1_Nombre'
    col_activa = get_column_name(schema, 'Cohortes', 'Activa') or 'nc_c7_Activa'

    cursor = conn.cursor()

    if FILTRAR_ACTIVAS and col_activa:
        query = f"""
            SELECT {col_id} as id, {col_nombre} as nombre
            FROM {table}
            WHERE {col_activa} = 1
            ORDER BY {col_nombre}
        """
    else:
        query = f"""
            SELECT {col_id} as id, {col_nombre} as nombre
            FROM {table}
            ORDER BY {col_nombre}
        """

    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def get_matrix_data(conn: sqlite3.Connection, schema: Dict, cohorte_id: int) -> Tuple[List, List, Dict]:
    """
    Obtiene datos para la matriz estudiante × actividad.

    Retorna:
    - students: lista de estudiantes ordenados por apellido
    - activities: lista de actividades ordenadas por Orden
    - cells: dict {(student_id, activity_id): cell_info}
    """
    table_est = get_table_name(schema, 'Estudiantes')
    table_act = get_table_name(schema, 'Actividades')
    table_ent = get_table_name(schema, 'Entregas')

    if not all([table_est, table_act, table_ent]):
        return [], [], {}

    cursor = conn.cursor()

    # Columnas de Estudiantes
    col_est_id = 'id'
    col_est_nombre = get_column_name(schema, 'Estudiantes', 'Nombre') or 'nc_c1_Nombre'
    col_est_apellido = get_column_name(schema, 'Estudiantes', 'Apellido') or 'nc_c2_Apellido'
    col_est_email = get_column_name(schema, 'Estudiantes', 'Email') or 'nc_c3_Email'
    col_est_github = get_column_name(schema, 'Estudiantes', 'GitHub') or 'nc_c4_GitHub'
    col_est_cohorte = get_column_name(schema, 'Estudiantes', 'Cohorte') or 'nc_fk_cohorte_id'

    # Columnas de Actividades
    col_act_id = 'id'
    col_act_nombre = get_column_name(schema, 'Actividades', 'Nombre') or 'nc_c1_Nombre'
    col_act_orden = get_column_name(schema, 'Actividades', 'Orden') or 'nc_c2_Orden'
    col_act_fecha_limite = get_column_name(schema, 'Actividades', 'Fecha Límite') or 'nc_c4_Fecha_Limite'
    col_act_tipo = get_column_name(schema, 'Actividades', 'Tipo') or 'nc_c7_Tipo'
    col_act_peso = get_column_name(schema, 'Actividades', 'Peso') or 'nc_c8_Peso'
    col_act_url_guia = get_column_name(schema, 'Actividades', 'URL Guía') or 'nc_c9_URL_Guia'
    col_act_cohorte = get_column_name(schema, 'Actividades', 'Cohorte') or 'nc_fk_cohorte_id'

    # Columnas de Entregas
    col_ent_id = 'id'
    col_ent_estado = get_column_name(schema, 'Entregas', 'Estado') or 'nc_c3_Estado'
    col_ent_url = get_column_name(schema, 'Entregas', 'URL Entrega') or 'nc_c1_URL_Entrega'
    col_ent_fecha = 'created_at'
    col_ent_estudiante = get_column_name(schema, 'Entregas', 'Estudiante') or 'nc_fk_estudiante_id'
    col_ent_actividad = get_column_name(schema, 'Entregas', 'Actividad') or 'nc_fk_actividad_id'

    # 1. Obtener estudiantes de la cohorte
    query_est = f"""
        SELECT {col_est_id} as id,
               {col_est_nombre} as nombre,
               {col_est_apellido} as apellido,
               {col_est_email} as email,
               {col_est_github} as github
        FROM {table_est}
        WHERE {col_est_cohorte} = ?
        ORDER BY {col_est_apellido}, {col_est_nombre}
    """
    cursor.execute(query_est, (cohorte_id,))
    students = [dict(row) for row in cursor.fetchall()]

    # 2. Obtener actividades de la cohorte
    query_act = f"""
        SELECT {col_act_id} as id,
               {col_act_nombre} as nombre,
               {col_act_fecha_limite} as fecha_limite
        FROM {table_act}
        WHERE {col_act_cohorte} = ?
        ORDER BY {col_act_orden}
    """
    cursor.execute(query_act, (cohorte_id,))
    activities = [dict(row) for row in cursor.fetchall()]

    # 3. Obtener entregas
    student_ids = [s['id'] for s in students]
    activity_ids = [a['id'] for a in activities]

    if student_ids and activity_ids:
        placeholders_students = ','.join('?' * len(student_ids))
        placeholders_activities = ','.join('?' * len(activity_ids))

        query_ent = f"""
            SELECT {col_ent_estudiante} as estudiante_id,
                   {col_ent_actividad} as actividad_id,
                   {col_ent_estado} as estado,
                   {col_ent_url} as url,
                   {col_ent_fecha} as fecha_entrega
            FROM {table_ent}
            WHERE {col_ent_estudiante} IN ({placeholders_students})
              AND {col_ent_actividad} IN ({placeholders_activities})
        """
        cursor.execute(query_ent, student_ids + activity_ids)
        entregas_raw = cursor.fetchall()
    else:
        entregas_raw = []

    # 4. Construir diccionario de celdas
    cells = {}
    for row in entregas_raw:
        key = (row['estudiante_id'], row['actividad_id'])
        cells[key] = dict(row)

    return students, activities, cells


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parsea fechas en varios formatos:
    - ISO 8601 con timezone: 2026-03-26T10:30:00+00:00
    - ISO 8601 sin timezone: 2026-03-26T10:30:00
    - Fecha simple: 2026-03-26
    - None o string vacío -> None
    """
    if not date_str:
        return None

    formats = [
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d'
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def compute_cell(entrega: Optional[Dict], fecha_limite_str: Optional[str], now: datetime) -> Dict:
    """
    Calcula el estado visual de una celda basado en:
    - Si hay entrega o no
    - Estado de la entrega
    - Comparación de fechas

    Retorna dict con:
    - color: código hex del color de fondo
    - text_color: código hex del color de texto
    - status: descripción del estado
    - label: texto a mostrar (opcional)
    - url: link a la entrega (si existe)
    """
    fecha_limite = parse_date(fecha_limite_str)

    # Colores del SPEC
    COLOR_VERDE = '#22c55e'
    COLOR_AMARILLO = '#eab308'
    COLOR_ROJO = '#ef4444'
    COLOR_GRIS = '#d1d5db'

    TEXT_DARK = '#1f2937'
    TEXT_LIGHT = '#ffffff'

    # Sin entrega
    if not entrega:
        if fecha_limite and fecha_limite < now:
            # No entregó y pasó la fecha límite
            return {
                'color': COLOR_ROJO,
                'text_color': TEXT_LIGHT,
                'status': 'No entregado',
                'label': '✗',
                'url': None,
                'tooltip': 'No entregado (fecha límite vencida)'
            }
        else:
            # No entregó aún pero hay tiempo
            return {
                'color': COLOR_GRIS,
                'text_color': TEXT_DARK,
                'status': 'Pendiente',
                'label': '−',
                'url': None,
                'tooltip': 'Pendiente' + (f' (límite: {fecha_limite.strftime("%d/%m")})' if fecha_limite else '')
            }

    # Con entrega - analizar estado y fecha
    estado = entrega.get('estado', 'Entregado')
    fecha_entrega = parse_date(entrega.get('fecha_entrega'))
    url = entrega.get('url')

    # Verificar si está tarde
    esta_tarde = False
    if fecha_entrega and fecha_limite:
        esta_tarde = fecha_entrega > fecha_limite

    if estado in ['Corregido']:
        # Corregido siempre verde (ya fue revisado)
        return {
            'color': COLOR_VERDE,
            'text_color': TEXT_LIGHT,
            'status': 'Corregido',
            'label': '✓',
            'url': url,
            'tooltip': f'Corregido' + (f' ({fecha_entrega.strftime("%d/%m %H:%M")})' if fecha_entrega else '')
        }
    elif estado == 'Entregado':
        if esta_tarde:
            return {
                'color': COLOR_AMARILLO,
                'text_color': TEXT_DARK,
                'status': 'Entregado tarde',
                'label': '⚠',
                'url': url,
                'tooltip': f'Entregado tarde ({fecha_entrega.strftime("%d/%m %H:%M")})'
            }
        else:
            return {
                'color': COLOR_VERDE,
                'text_color': TEXT_LIGHT,
                'status': 'Entregado',
                'label': '✓',
                'url': url,
                'tooltip': f'Entregado ({fecha_entrega.strftime("%d/%m %H:%M")})'
            }
    elif estado == 'Rehacer':
        return {
            'color': COLOR_AMARILLO,
            'text_color': TEXT_DARK,
            'status': 'Rehacer',
            'label': '↻',
            'url': url,
            'tooltip': 'Debe rehacer la entrega'
        }
    else:
        # Estado desconocido, mostrar como entregado
        return {
            'color': COLOR_VERDE,
            'text_color': TEXT_LIGHT,
            'status': estado,
            'label': '?',
            'url': url,
            'tooltip': estado
        }


def calcular_metricas_estudiante(entregas_estudiante: List[Dict], actividades: List[Dict]) -> Dict:
    """
    Calcula métricas de cumplimiento para un estudiante.

    Retorna dict con:
    - porcentaje_semanales: % de entregas semanales a tiempo
    - porcentaje_integradores: % de entregas integradores a tiempo
    - indice_participacion: índice ponderado de participación
    - indice_final: índice final ponderado (40% TP1 + 40% TP2 + 20% participación)
    - clasificacion: Excelente/Bueno/Regular/Deficiente
    """
    if not entregas_estudiante or not actividades:
        return {
            'porcentaje_semanales': 0,
            'porcentaje_integradores': 0,
            'indice_participacion': 0,
            'indice_final': 0,
            'clasificacion': 'Sin datos'
        }

    # Mapear actividades por ID para acceder a tipo y peso
    actividades_dict = {a['id']: a for a in actividades}

    # Separar semanales e integradores
    semanales = []
    integradores = []

    for entrega in entregas_estudiante:
        act_id = entrega.get('actividad_id')
        if act_id not in actividades_dict:
            continue

        act = actividades_dict[act_id]
        es_integrador = act.get('tipo') == 'Integrador'

        # Determinar estado
        estado = entrega.get('estado', 'No entregado')
        es_a_tiempo = estado in ['Entregado', 'Corregido']
        es_tarde = estado in ['Entregado tarde', 'Rehacer']

        item = {
            'actividad': act,
            'estado': estado,
            'es_a_tiempo': es_a_tiempo,
            'es_tarde': es_tarde,
            'peso': act.get('peso', 1)
        }

        if es_integrador:
            integradores.append(item)
        else:
            semanales.append(item)

    # Calcular porcentaje de semanales
    if semanales:
        semanales_a_tiempo = sum(1 for s in semanales if s['es_a_tiempo'])
        semanales_tarde = sum(1 for s in semanales if s['es_tarde'])
        porcentaje_semanales = (semanales_a_tiempo / len(semanales)) * 100
        indice_participacion = ((semanales_a_tiempo * 1.0) + (semanales_tarde * 0.5)) / len(semanales) * 100
    else:
        porcentaje_semanales = 0
        indice_participacion = 0

    # Calcular porcentaje de integradores
    if integradores:
        integradores_a_tiempo = sum(1 for i in integradores if i['es_a_tiempo'])
        integradores_tarde = sum(1 for i in integradores if i['es_tarde'])
        total_integradores = len(integradores)
        porcentaje_integradores = (integradores_a_tiempo / total_integradores) * 100

        # Índice ponderado de integradores (pesan más)
        peso_total_integradores = sum(i['peso'] for i in integradores)
        peso_a_tiempo = sum(i['peso'] for i in integradores if i['es_a_tiempo'])
        peso_tarde = sum(i['peso'] * 0.5 for i in integradores if i['es_tarde'])

        if peso_total_integradores > 0:
            indice_integradores = ((peso_a_tiempo + peso_tarde) / peso_total_integradores) * 100
        else:
            indice_integradores = 0
    else:
        porcentaje_integradores = 0
        indice_integradores = 0

    # Índice final ponderado (40% TP1 + 40% TP2 + 20% participación)
    # Si hay integradores, usamos el índice de integradores, sino solo participación
    if integradores:
        # Asumimos 2 integradores de igual peso si no hay específico
        if len(integradores) >= 2:
            tp1_score = 100 if integradores[0]['es_a_tiempo'] else (50 if integradores[0]['es_tarde'] else 0)
            tp2_score = 100 if integradores[1]['es_a_tiempo'] else (50 if integradores[1]['es_tarde'] else 0)
        else:
            tp1_score = indice_integradores
            tp2_score = indice_integradores

        indice_final = (tp1_score * 0.4) + (tp2_score * 0.4) + (indice_participacion * 0.2)
    else:
        indice_final = indice_participacion

    # Clasificación
    if indice_final >= 90:
        clasificacion = 'Excelente'
    elif indice_final >= 70:
        clasificacion = 'Bueno'
    elif indice_final >= 50:
        clasificacion = 'Regular'
    else:
        clasificacion = 'Deficiente'

    return {
        'porcentaje_semanales': round(porcentaje_semanales, 1),
        'porcentaje_integradores': round(porcentaje_integradores, 1),
        'indice_participacion': round(indice_participacion, 1),
        'indice_final': round(indice_final, 1),
        'clasificacion': clasificacion,
        'total_semanales': len(semanales),
        'semanales_a_tiempo': sum(1 for s in semanales if s['es_a_tiempo']),
        'total_integradores': len(integradores),
        'integradores_a_tiempo': sum(1 for i in integradores if i['es_a_tiempo'])
    }


# === RUTAS ===

@app.route('/')
def index():
    """
    Dashboard principal.
    Query param opcional: ?cohorte=ID
    """
    conn = get_db()
    try:
        # Descubrir schema dinámicamente
        schema = discover_schema(conn)

        # Obtener cohortes
        cohortes = get_cohortes(conn, schema)

        # Determinar cohorte seleccionada
        cohorte_id = request.args.get('cohorte', type=int)
        if not cohorte_id and cohortes:
            cohorte_id = cohortes[0]['id']

        selected_cohorte = None
        for c in cohortes:
            if c['id'] == cohorte_id:
                selected_cohorte = c
                break

        # Obtener datos de la matriz
        students = []
        activities = []
        cells = {}
        processed_cells = {}

        if cohorte_id:
            students, activities, cells = get_matrix_data(conn, schema, cohorte_id)

            # Procesar celdas para calcular colores
            now = datetime.now()
            for (sid, aid), entrega in cells.items():
                # Encontrar fecha límite de la actividad
                fecha_limite = None
                for act in activities:
                    if act['id'] == aid:
                        fecha_limite = act.get('fecha_limite')
                        break

                processed_cells[(sid, aid)] = compute_cell(entrega, fecha_limite, now)

            # También procesar celdas vacías (sin entrega)
            for student in students:
                for activity in activities:
                    key = (student['id'], activity['id'])
                    if key not in processed_cells:
                        processed_cells[key] = compute_cell(None, activity.get('fecha_limite'), now)

        # Preparar datos de estudiantes para el panel lateral (email, github)
        students_data = {}
        for s in students:
            students_data[s['id']] = {
                'nombre': s['nombre'],
                'apellido': s['apellido'],
                'email': s.get('email', ''),
                'github': s.get('github', '')
            }

        # Preparar datos de entregas por estudiante para el panel
        entregas_por_estudiante = {}
        for (sid, aid), cell in processed_cells.items():
            if sid not in entregas_por_estudiante:
                entregas_por_estudiante[sid] = []
            # Encontrar nombre de actividad
            act_nombre = ''
            for act in activities:
                if act['id'] == aid:
                    act_nombre = act['nombre']
                    break
            entregas_por_estudiante[sid].append({
                'actividad_id': aid,
                'actividad': act_nombre,
                'estado': cell['status'],
                'color': cell['color'],
                'fecha': cell.get('tooltip', '').split('(')[1].replace(')', '') if '(' in cell.get('tooltip', '') else ''
            })

        return render_template(
            'index.html',
            cohortes=cohortes,
            selected_cohorte=selected_cohorte,
            students=students,
            activities=activities,
            cells=processed_cells,
            students_data=students_data,
            entregas_por_estudiante=entregas_por_estudiante
        )

    finally:
        conn.close()


@app.route('/faq')
def faq():
    """Página de preguntas frecuentes."""
    return render_template('faq.html')


@app.route('/api/estudiante/<int:estudiante_id>')
def get_estudiante_api(estudiante_id):
    """API endpoint para obtener datos de un estudiante."""
    conn = get_db()
    try:
        schema = discover_schema(conn)

        table_est = get_table_name(schema, 'Estudiantes')
        col_est_id = 'id'
        col_est_nombre = get_column_name(schema, 'Estudiantes', 'Nombre') or 'nc_c1_Nombre'
        col_est_apellido = get_column_name(schema, 'Estudiantes', 'Apellido') or 'nc_c2_Apellido'
        col_est_email = get_column_name(schema, 'Estudiantes', 'Email') or 'nc_c3_Email'
        col_est_github = get_column_name(schema, 'Estudiantes', 'GitHub') or 'nc_c4_GitHub'

        cursor = conn.cursor()
        query = f"""
            SELECT {col_est_id} as id,
                   {col_est_nombre} as nombre,
                   {col_est_apellido} as apellido,
                   {col_est_email} as email,
                   {col_est_github} as github
            FROM {table_est}
            WHERE {col_est_id} = ?
        """
        cursor.execute(query, (estudiante_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        else:
            return {'error': 'Estudiante no encontrado'}, 404

    finally:
        conn.close()


@app.route('/resumen')
def resumen():
    """
    Vista de resumen para docentes con métricas de cumplimiento.
    Query param opcional: ?cohorte=ID
    """
    conn = get_db()
    try:
        schema = discover_schema(conn)
        cohortes = get_cohortes(conn, schema)

        cohorte_id = request.args.get('cohorte', type=int)
        if not cohorte_id and cohortes:
            cohorte_id = cohortes[0]['id']

        selected_cohorte = None
        for c in cohortes:
            if c['id'] == cohorte_id:
                selected_cohorte = c
                break

        resumen_data = []

        if cohorte_id:
            students, activities, cells = get_matrix_data(conn, schema, cohorte_id)

            # Procesar celdas
            now = datetime.now()
            processed_cells = {}
            for (sid, aid), entrega in cells.items():
                fecha_limite = None
                for act in activities:
                    if act['id'] == aid:
                        fecha_limite = act.get('fecha_limite')
                        break
                processed_cells[(sid, aid)] = compute_cell(entrega, fecha_limite, now)

            for student in students:
                # Recolectar entregas del estudiante
                entregas_est = []
                for activity in activities:
                    key = (student['id'], activity['id'])
                    if key in processed_cells:
                        cell = processed_cells[key]
                        entregas_est.append({
                            'actividad_id': activity['id'],
                            'estado': cell['status'],
                            'tipo': activity.get('tipo', 'Semanal'),
                            'peso': activity.get('peso', 1)
                        })

                metricas = calcular_metricas_estudiante(entregas_est, activities)

                resumen_data.append({
                    'id': student['id'],
                    'apellido': student['apellido'],
                    'nombre': student['nombre'],
                    'email': student.get('email', ''),
                    'github': student.get('github', ''),
                    **metricas
                })

        # Ordenar por índice final (descendente)
        resumen_data.sort(key=lambda x: x['indice_final'], reverse=True)

        return render_template(
            'resumen.html',
            cohortes=cohortes,
            selected_cohorte=selected_cohorte,
            resumen=resumen_data
        )

    finally:
        conn.close()


@app.route('/api/exportar-excel')
def exportar_excel():
    """
    Exporta el resumen a Excel.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO

    conn = get_db()
    try:
        schema = discover_schema(conn)
        cohortes = get_cohortes(conn, schema)

        cohorte_id = request.args.get('cohorte', type=int)
        if not cohorte_id and cohortes:
            cohorte_id = cohortes[0]['id']

        cohorte_nombre = 'Todas'
        for c in cohortes:
            if c['id'] == cohorte_id:
                cohorte_nombre = c['nombre']
                break

        wb = Workbook()

        # Hoja 1: Resumen por estudiante
        ws1 = wb.active
        ws1.title = "Resumen"

        headers = ['Apellido', 'Nombre', 'Email', 'GitHub', '% Semanales', '% Integradores',
                   'Índice Participación', 'Índice Final', 'Clasificación']

        for col, header in enumerate(headers, 1):
            cell = ws1.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")

        resumen_data = []
        if cohorte_id:
            students, activities, cells = get_matrix_data(conn, schema, cohorte_id)
            now = datetime.now()
            processed_cells = {}
            for (sid, aid), entrega in cells.items():
                fecha_limite = None
                for act in activities:
                    if act['id'] == aid:
                        fecha_limite = act.get('fecha_limite')
                        break
                processed_cells[(sid, aid)] = compute_cell(entrega, fecha_limite, now)

            for student in students:
                entregas_est = []
                for activity in activities:
                    key = (student['id'], activity['id'])
                    if key in processed_cells:
                        cell = processed_cells[key]
                        entregas_est.append({
                            'actividad_id': activity['id'],
                            'estado': cell['status'],
                            'tipo': activity.get('tipo', 'Semanal'),
                            'peso': activity.get('peso', 1)
                        })

                metricas = calcular_metricas_estudiante(entregas_est, activities)
                resumen_data.append({
                    'apellido': student['apellido'],
                    'nombre': student['nombre'],
                    'email': student.get('email', ''),
                    'github': student.get('github', ''),
                    **metricas
                })

            resumen_data.sort(key=lambda x: x['indice_final'], reverse=True)

        # Llenar datos
        for row_idx, data in enumerate(resumen_data, 2):
            ws1.cell(row=row_idx, column=1, value=data['apellido'])
            ws1.cell(row=row_idx, column=2, value=data['nombre'])
            ws1.cell(row=row_idx, column=3, value=data['email'])
            ws1.cell(row=row_idx, column=4, value=data['github'])
            ws1.cell(row=row_idx, column=5, value=data['porcentaje_semanales'])
            ws1.cell(row=row_idx, column=6, value=data['porcentaje_integradores'])
            ws1.cell(row=row_idx, column=7, value=data['indice_participacion'])
            ws1.cell(row=row_idx, column=8, value=data['indice_final'])
            ws1.cell(row=row_idx, column=9, value=data['clasificacion'])

            # Colorear clasificación
            clasificacion_cell = ws1.cell(row=row_idx, column=9)
            if data['clasificacion'] == 'Excelente':
                clasificacion_cell.fill = PatternFill(start_color="22c55e", end_color="22c55e", fill_type="solid")
            elif data['clasificacion'] == 'Bueno':
                clasificacion_cell.fill = PatternFill(start_color="3b82f6", end_color="3b82f6", fill_type="solid")
            elif data['clasificacion'] == 'Regular':
                clasificacion_cell.fill = PatternFill(start_color="eab308", end_color="eab308", fill_type="solid")
            else:
                clasificacion_cell.fill = PatternFill(start_color="ef4444", end_color="ef4444", fill_type="solid")

        # Ajustar anchos
        for col in range(1, 10):
            ws1.column_dimensions[chr(64 + col)].width = 18

        # Hoja 2: Detalle completo
        ws2 = wb.create_sheet("Detalle")

        detail_headers = ['Estudiante', 'Actividad', 'Tipo', 'Estado', 'Peso']
        for col, header in enumerate(detail_headers, 1):
            cell = ws2.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")

        # Llenar detalle
        row_idx = 2
        for student in students:
            for activity in activities:
                key = (student['id'], activity['id'])
                cell = processed_cells.get(key)
                if cell:
                    ws2.cell(row=row_idx, column=1, value=f"{student['apellido']}, {student['nombre']}")
                    ws2.cell(row=row_idx, column=2, value=activity['nombre'])
                    ws2.cell(row=row_idx, column=3, value=activity.get('tipo', 'Semanal'))
                    ws2.cell(row=row_idx, column=4, value=cell['status'])
                    ws2.cell(row=row_idx, column=5, value=activity.get('peso', 1))
                    row_idx += 1

        # Guardar en memoria
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'resumen_{cohorte_nombre}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )

    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
