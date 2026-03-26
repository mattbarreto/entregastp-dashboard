"""
Dashboard Flask para seguimiento de entregas de estudiantes.
Lee datos de SQLite de NocoDB en modo read-only.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from flask import Flask, render_template, request

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        # Intentar conexión normal si URI falla
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn


def discover_schema(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """
    Descubre el schema real de NocoDB leyendo las tablas de metadatos.
    """
    schema = {}
    cursor = conn.cursor()

    try:
        # Verificar tablas de metadatos
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nc_models_v2'")
        has_models = cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nc_columns_v2'")
        has_columns = cursor.fetchone() is not None

        if has_models and has_columns:
            # Leer modelos (tablas)
            cursor.execute("SELECT id, table_name, title FROM nc_models_v2")
            models_data = cursor.fetchall()
            models = {row['title']: row['table_name'] for row in models_data}
            title_to_id = {row['title']: row['id'] for row in models_data}

            # Leer todas las columnas
            cursor.execute("SELECT fk_model_id, column_name, title, uidt FROM nc_columns_v2")
            columns_data = cursor.fetchall()
            
            columns_by_model = {}
            for row in columns_data:
                mid = row['fk_model_id']
                if mid not in columns_by_model:
                    columns_by_model[mid] = {}
                columns_by_model[mid][row['title']] = row['column_name']

            # Mapear a estructura esperada
            for title in ['Cohortes', 'Actividades', 'Estudiantes', 'Entregas']:
                if title in models:
                    mid = title_to_id[title]
                    schema[title] = {
                        'table_name': models[title],
                        'columns': columns_by_model.get(mid, {})
                    }

            if schema:
                logger.info(f"Schema descubierto: {list(schema.keys())}")
                return schema

    except Exception as e:
        logger.warning(f"Error en discover_schema (metadatos): {e}")

    # FALLBACK: Estructura básica si falla la detección
    for title, default_table in TABLE_TITLES.items():
        schema[title] = {'table_name': default_table, 'columns': {}}
    return schema


def get_column_name(schema: Dict, table_title: str, column_title: str) -> Optional[str]:
    """Obtiene el nombre físico de una columna con soporte para alias comunes."""
    if table_title not in schema:
        return None
    
    cols = schema[table_title]['columns']
    
    # Intento 1: Nombre exacto
    if column_title in cols:
        return cols[column_title]
    
    # Intento 2: Alias comunes
    aliases = {
        'Fecha Límite': ['Fecha', 'Deadline', 'Fecha_Limite'],
        'URL Guía': ['URL_Guia', 'URL_Gu_a', 'Guia', 'Link'],
        'Activa': ['Activo', 'Status'],
        'Nombre': ['Title', 'Name'],
        'Apellido': ['Lastname', 'Surname'],
        'URL Entrega': ['URL', 'Link', 'Entrega'],
        'Estudiante': ['Estudiante_id', 'nc_fk_estudiante_id'],
        'Actividad': ['Actividad_id', 'nc_fk_actividad_id'],
        'Cohorte': ['Cohorte_id', 'nc_fk_cohorte_id']
    }
    
    if column_title in aliases:
        for alias in aliases[column_title]:
            if alias in cols:
                return cols[alias]
                
    return None


def get_table_name(schema: Dict, table_title: str) -> Optional[str]:
    """Obtiene el nombre físico de una tabla."""
    if table_title not in schema:
        return None
    return schema[table_title]['table_name']


# === CAPA DATOS ===

def get_cohortes(conn: sqlite3.Connection, schema: Dict) -> List[Dict]:
    """Lista todas las cohortes activas."""
    table = get_table_name(schema, 'Cohortes')
    if not table:
        return []

    col_id = 'id'
    col_nombre = get_column_name(schema, 'Cohortes', 'Nombre') or 'Nombre'
    col_activa = get_column_name(schema, 'Cohortes', 'Activa') or 'Activa'

    cursor = conn.cursor()
    
    try:
        if FILTRAR_ACTIVAS:
            query = f"SELECT {col_id} as id, {col_nombre} as nombre FROM {table} WHERE {col_activa} = 1 ORDER BY {col_nombre}"
        else:
            query = f"SELECT {col_id} as id, {col_nombre} as nombre FROM {table} ORDER BY {col_nombre}"
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        logger.error(f"Error consultando cohortes: {e}")
        return []


def get_matrix_data(conn: sqlite3.Connection, schema: Dict, cohorte_id: int) -> Tuple[List, List, Dict]:
    """Obtiene datos para la matriz estudiante x actividad."""
    table_est = get_table_name(schema, 'Estudiantes')
    table_act = get_table_name(schema, 'Actividades')
    table_ent = get_table_name(schema, 'Entregas')

    if not all([table_est, table_act, table_ent]):
        return [], [], {}

    cursor = conn.cursor()

    # Resolver nombres de columnas
    col_est_id = 'id'
    col_est_nombre = get_column_name(schema, 'Estudiantes', 'Nombre') or 'Nombre'
    col_est_apellido = get_column_name(schema, 'Estudiantes', 'Apellido') or 'Apellido'
    col_est_email = get_column_name(schema, 'Estudiantes', 'Email') or 'Email'
    col_est_github = get_column_name(schema, 'Estudiantes', 'GitHub') or 'GitHub'
    col_est_cohorte = get_column_name(schema, 'Estudiantes', 'Cohorte') or 'nc_fk_cohorte_id'

    col_act_id = 'id'
    col_act_nombre = get_column_name(schema, 'Actividades', 'Nombre') or 'Nombre'
    col_act_orden = get_column_name(schema, 'Actividades', 'Orden') or 'Orden'
    col_act_fecha_limite = get_column_name(schema, 'Actividades', 'Fecha Límite') or 'Fecha'
    col_act_cohorte = get_column_name(schema, 'Actividades', 'Cohorte') or 'nc_fk_cohorte_id'

    col_ent_estado = get_column_name(schema, 'Entregas', 'Estado') or 'Estado'
    col_ent_url = get_column_name(schema, 'Entregas', 'URL Entrega') or 'URL_Entrega'
    col_ent_estudiante = get_column_name(schema, 'Entregas', 'Estudiante') or 'nc_fk_estudiante_id'
    col_ent_actividad = get_column_name(schema, 'Entregas', 'Actividad') or 'nc_fk_actividad_id'

    try:
        # 1. Estudiantes
        cursor.execute(f"SELECT {col_est_id} as id, {col_est_nombre} as nombre, {col_est_apellido} as apellido, {col_est_email} as email, {col_est_github} as github FROM {table_est} WHERE {col_est_cohorte} = ? ORDER BY {col_est_apellido}", (cohorte_id,))
        students = [dict(row) for row in cursor.fetchall()]

        # 2. Actividades
        cursor.execute(f"SELECT {col_act_id} as id, {col_act_nombre} as nombre, {col_act_fecha_limite} as fecha_limite FROM {table_act} WHERE {col_act_cohorte} = ? ORDER BY {col_act_orden}", (cohorte_id,))
        activities = [dict(row) for row in cursor.fetchall()]

        # 3. Entregas
        student_ids = [s['id'] for s in students]
        activity_ids = [a['id'] for a in activities]
        cells = {}

        if student_ids and activity_ids:
            placeholders_s = ','.join('?' * len(student_ids))
            placeholders_a = ','.join('?' * len(activity_ids))
            query_ent = f"SELECT {col_ent_estudiante} as estudiante_id, {col_ent_actividad} as actividad_id, {col_ent_estado} as estado, {col_ent_url} as url, created_at as fecha_entrega FROM {table_ent} WHERE {col_ent_estudiante} IN ({placeholders_s}) AND {col_ent_actividad} IN ({placeholders_a})"
            cursor.execute(query_ent, student_ids + activity_ids)
            for row in cursor.fetchall():
                cells[(row['estudiante_id'], row['actividad_id'])] = dict(row)

        return students, activities, cells
    except Exception as e:
        logger.error(f"Error en get_matrix_data: {e}")
        return [], [], {}


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str: return None
    formats = ['%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']
    for fmt in formats:
        try: return datetime.strptime(date_str, fmt)
        except: continue
    return None


def compute_cell(entrega: Optional[Dict], fecha_limite_str: Optional[str], now: datetime) -> Dict:
    fecha_limite = parse_date(fecha_limite_str)
    COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS = '#22c55e', '#eab308', '#ef4444', '#d1d5db'
    
    if not entrega:
        if fecha_limite and fecha_limite < now:
            return {'color': COLOR_ROJO, 'status': 'No entregado', 'label': '✗'}
        return {'color': COLOR_GRIS, 'status': 'Pendiente', 'label': '−'}

    estado = entrega.get('estado', 'Entregado')
    fecha_entrega = parse_date(entrega.get('fecha_entrega'))
    esta_tarde = (fecha_entrega > fecha_limite) if (fecha_entrega and fecha_limite) else False

    if estado == 'Corregido': return {'color': COLOR_VERDE, 'status': 'Corregido', 'label': '✓'}
    if estado == 'Rehacer': return {'color': COLOR_AMARILLO, 'status': 'Rehacer', 'label': '↻'}
    if esta_tarde: return {'color': COLOR_AMARILLO, 'status': 'Tarde', 'label': '⚠'}
    return {'color': COLOR_VERDE, 'status': 'Entregado', 'label': '✓'}


@app.route('/')
def index():
    conn = get_db()
    try:
        schema = discover_schema(conn)
        cohortes = get_cohortes(conn, schema)
        
        cohorte_id = request.args.get('cohorte', type=int)
        if not cohorte_id and cohortes: cohorte_id = cohortes[0]['id']
        
        selected_cohorte = next((c for c in cohortes if c['id'] == cohorte_id), None)
        students, activities, cells = ([], [], {})
        processed_cells = {}

        if cohorte_id:
            students, activities, cells = get_matrix_data(conn, schema, cohorte_id)
            now = datetime.now()
            for s in students:
                for a in activities:
                    key = (s['id'], a['id'])
                    processed_cells[key] = compute_cell(cells.get(key), a.get('fecha_limite'), now)

        return render_template('index.html', cohortes=cohortes, selected_cohorte=selected_cohorte, 
                               students=students, activities=activities, cells=processed_cells)
    finally:
        conn.close()

@app.route('/faq')
def faq(): return render_template('faq.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
