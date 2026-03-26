#!/usr/bin/env python3
"""
Genera una base de datos SQLite de prueba que imita la estructura interna de NocoDB.
Usada para desarrollo local del dashboard sin necesidad de tener NocoDB corriendo.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

TEST_DATA_DIR = "test_data"
DB_PATH = os.path.join(TEST_DATA_DIR, "noco.db")

# Nombres de estudiantes ficticios argentinos
NOMBRES = ["María", "Juan", "Lucía", "Martín", "Sofía", "Diego", "Valentina", "Lucas", "Emma", "Mateo"]
APELLIDOS = ["García", "Rodríguez", "González", "Fernández", "López", "Martínez", "Pérez", "Álvarez", "Romero", "Torres"]

def create_directories():
    """Crea directorio test_data si no existe."""
    os.makedirs(TEST_DATA_DIR, exist_ok=True)

def create_mock_tables(conn):
    """Crea tablas de metadatos de NocoDB y tablas físicas de datos."""
    cursor = conn.cursor()

    # Tablas de metadatos de NocoDB (nc_models_v2, nc_columns_v2)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_models_v2 (
            id TEXT PRIMARY KEY,
            table_name TEXT UNIQUE,
            title TEXT,
            type TEXT,
            meta TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_columns_v2 (
            id TEXT PRIMARY KEY,
            fk_model_id TEXT,
            column_name TEXT,
            title TEXT,
            uidt TEXT,
            dt TEXT,
            pk INTEGER DEFAULT 0,
            rq INTEGER DEFAULT 0,
            cdf TEXT,
            un INTEGER DEFAULT 0,
            ao TEXT,
            at TEXT,
            cc TEXT,
            csn TEXT,
            dtx TEXT,
            np TEXT,
            ns TEXT,
            clen TEXT,
            cop TEXT,
            pknn INTEGER DEFAULT 0,
            altered INTEGER DEFAULT 0,
            fk_model_id_backup TEXT,
            UNIQUE(fk_model_id, column_name)
        )
    ''')

    # Tablas físicas con nombres estilo NocoDB
    # Cohortes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_abcd_Cohortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_c1_Nombre TEXT,
            nc_c2_Curso TEXT,
            nc_c3_Cuatrimestre TEXT,
            nc_c4_Ano INTEGER,
            nc_c5_Fecha_Inicio TEXT,
            nc_c6_Fecha_Fin TEXT,
            nc_c7_Activa INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Actividades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_abcd_Actividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_c1_Nombre TEXT,
            nc_c2_Orden INTEGER,
            nc_c3_Tipo_Entrega TEXT DEFAULT 'GitHub',
            nc_c4_Fecha_Limite TEXT,
            nc_c5_Descripcion TEXT,
            nc_c6_Obligatoria INTEGER DEFAULT 1,
            nc_c7_Tipo TEXT DEFAULT 'Semanal',
            nc_c8_Peso INTEGER DEFAULT 1,
            nc_c9_URL_Guia TEXT,
            nc_fk_cohorte_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Estudiantes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_abcd_Estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_c1_Nombre TEXT,
            nc_c2_Apellido TEXT,
            nc_c3_Email TEXT,
            nc_c4_GitHub TEXT,
            nc_c5_Entregas TEXT,
            nc_fk_cohorte_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Entregas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_abcd_Entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_c1_URL_Entrega TEXT,
            nc_c2_Archivo TEXT,
            nc_c3_Estado TEXT DEFAULT 'Entregado',
            nc_c5_Observaciones TEXT,
            nc_fk_estudiante_id INTEGER,
            nc_fk_actividad_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    conn.commit()

def populate_metadata(conn):
    """Puebla las tablas de metadatos de NocoDB."""
    cursor = conn.cursor()

    # Insertar modelos (tablas)
    models = [
        ("md_cohortes", "nc_abcd_Cohortes", "Cohortes", "table"),
        ("md_actividades", "nc_abcd_Actividades", "Actividades", "table"),
        ("md_estudiantes", "nc_abcd_Estudiantes", "Estudiantes", "table"),
        ("md_entregas", "nc_abcd_Entregas", "Entregas", "table"),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO nc_models_v2 (id, table_name, title, type) VALUES (?, ?, ?, ?)",
        models
    )

    # Insertar columnas para cada modelo
    columns = [
        # Cohortes
        ("col_c_1", "md_cohortes", "nc_c1_Nombre", "Nombre", "SingleLineText"),
        ("col_c_2", "md_cohortes", "nc_c2_Curso", "Curso", "SingleSelect"),
        ("col_c_3", "md_cohortes", "nc_c3_Cuatrimestre", "Cuatrimestre", "SingleSelect"),
        ("col_c_4", "md_cohortes", "nc_c4_Ano", "Año", "Number"),
        ("col_c_5", "md_cohortes", "nc_c5_Fecha_Inicio", "Fecha Inicio", "Date"),
        ("col_c_6", "md_cohortes", "nc_c6_Fecha_Fin", "Fecha Fin", "Date"),
        ("col_c_7", "md_cohortes", "nc_c7_Activa", "Activa", "Checkbox"),
        # Actividades
        ("col_a_1", "md_actividades", "nc_c1_Nombre", "Nombre", "SingleLineText"),
        ("col_a_2", "md_actividades", "nc_c2_Orden", "Orden", "Number"),
        ("col_a_3", "md_actividades", "nc_c3_Tipo_Entrega", "Tipo Entrega", "SingleSelect"),
        ("col_a_4", "md_actividades", "nc_c4_Fecha_Limite", "Fecha Límite", "DateTime"),
        ("col_a_5", "md_actividades", "nc_c5_Descripcion", "Descripción", "LongText"),
        ("col_a_6", "md_actividades", "nc_c6_Obligatoria", "Obligatoria", "Checkbox"),
        ("col_a_7", "md_actividades", "nc_c7_Tipo", "Tipo", "SingleSelect"),
        ("col_a_8", "md_actividades", "nc_c8_Peso", "Peso", "Number"),
        ("col_a_9", "md_actividades", "nc_c9_URL_Guia", "URL Guía", "URL"),
        ("col_a_10", "md_actividades", "nc_fk_cohorte_id", "Cohorte", "LinkToAnotherRecord"),
        # Estudiantes
        ("col_e_1", "md_estudiantes", "nc_c1_Nombre", "Nombre", "SingleLineText"),
        ("col_e_2", "md_estudiantes", "nc_c2_Apellido", "Apellido", "SingleLineText"),
        ("col_e_3", "md_estudiantes", "nc_c3_Email", "Email", "Email"),
        ("col_e_4", "md_estudiantes", "nc_c4_GitHub", "GitHub", "URL"),
        ("col_e_5", "md_estudiantes", "nc_c5_Entregas", "Entregas", "LinkToAnotherRecord"),
        ("col_e_6", "md_estudiantes", "nc_fk_cohorte_id", "Cohorte", "LinkToAnotherRecord"),
        # Entregas
        ("col_en_1", "md_entregas", "nc_c1_URL_Entrega", "URL Entrega", "URL"),
        ("col_en_2", "md_entregas", "nc_c2_Archivo", "Archivo", "Attachment"),
        ("col_en_3", "md_entregas", "nc_c3_Estado", "Estado", "SingleSelect"),
        ("col_en_4", "md_entregas", "nc_c5_Observaciones", "Observaciones", "LongText"),
        ("col_en_5", "md_entregas", "nc_fk_estudiante_id", "Estudiante", "LinkToAnotherRecord"),
        ("col_en_6", "md_entregas", "nc_fk_actividad_id", "Actividad", "LinkToAnotherRecord"),
    ]

    cursor.executemany(
        """INSERT OR REPLACE INTO nc_columns_v2
           (id, fk_model_id, column_name, title, uidt) VALUES (?, ?, ?, ?, ?)""",
        columns
    )

    conn.commit()

def populate_data(conn):
    """Puebla las tablas de datos con información de prueba."""
    cursor = conn.cursor()
    now = datetime.now()

    # Crear cohorte activa
    cohorte_id = 1
    cursor.execute('''
        INSERT INTO nc_abcd_Cohortes (id, nc_c1_Nombre, nc_c2_Curso, nc_c3_Cuatrimestre,
                                      nc_c4_Ano, nc_c5_Fecha_Inicio, nc_c6_Fecha_Fin,
                                      nc_c7_Activa, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (cohorte_id, "2026-Q1-Redes", "Tecnicatura Redes", "Q1", 2026,
          "2026-03-01", "2026-07-15", 1, now.isoformat()))

    # Crear 7 actividades: 5 semanales + 2 TPs integradores
    actividades = [
        # Semanales (peso 1)
        (1, "Semana 1", 1, "GitHub", (now - timedelta(days=14)).isoformat(), "Introducción", 1, "Semanal", 1, "https://colab.research.google.com/guia-semana1", cohorte_id),
        (2, "Semana 2", 2, "GitHub", (now - timedelta(days=7)).isoformat(), "Variables", 1, "Semanal", 1, "https://colab.research.google.com/guia-semana2", cohorte_id),
        (3, "Semana 3", 3, "GitHub", (now - timedelta(days=2)).isoformat(), "Funciones", 1, "Semanal", 1, "https://colab.research.google.com/guia-semana3", cohorte_id),
        (4, "Semana 4", 4, "GitHub", now.isoformat(), "Condicionales", 1, "Semanal", 1, "https://colab.research.google.com/guia-semana4", cohorte_id),
        (5, "Semana 5", 5, "GitHub", (now + timedelta(days=7)).isoformat(), "Bucles", 1, "Semanal", 1, "https://colab.research.google.com/guia-semana5", cohorte_id),
        # TPs Integradores (peso 10)
        (6, "TP Integrador 1", 6, "GitHub", (now + timedelta(days=21)).isoformat(), "Proyecto integrador primera parte", 1, "Integrador", 10, "https://docs.google.com/tp-integrador1", cohorte_id),
        (7, "TP Integrador 2", 7, "GitHub", (now + timedelta(days=45)).isoformat(), "Proyecto final", 1, "Integrador", 10, "https://docs.google.com/tp-integrador2", cohorte_id),
    ]

    cursor.executemany('''
        INSERT INTO nc_abcd_Actividades (id, nc_c1_Nombre, nc_c2_Orden, nc_c3_Tipo_Entrega,
                                          nc_c4_Fecha_Limite, nc_c5_Descripcion,
                                          nc_c6_Obligatoria, nc_c7_Tipo, nc_c8_Peso, nc_c9_URL_Guia,
                                          nc_fk_cohorte_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], now.isoformat()) for a in actividades])

    # Crear 8 estudiantes
    estudiantes = []
    for i in range(8):
        nombre = random.choice(NOMBRES)
        apellido = random.choice(APELLIDOS)
        email = f"{nombre.lower()}.{apellido.lower()}@universidad.edu.ar"
        github = f"https://github.com/{nombre.lower()}{apellido.lower()}{random.randint(10,99)}"
        estudiantes.append((i + 1, nombre, apellido, email, github, cohorte_id))

    cursor.executemany('''
        INSERT INTO nc_abcd_Estudiantes (id, nc_c1_Nombre, nc_c2_Apellido, nc_c3_Email,
                                          nc_c4_GitHub, nc_fk_cohorte_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(e[0], e[1], e[2], e[3], e[4], e[5], now.isoformat()) for e in estudiantes])

    # Crear entregas con distribución de estados
    entregas = []
    entrega_id = 1

    for estudiante in estudiantes:
        estudiante_id = estudiante[0]
        for actividad in actividades:
            actividad_id = actividad[0]
            fecha_limite = datetime.fromisoformat(actividad[4])

            # Determinar si entrega y en qué estado (distribución aleatoria)
            rand = random.random()

            if actividad_id <= 2:  # Semana 1 y 2 (vencidas) - mayoría entregó
                if rand < 0.7:  # 70% entregó
                    # Mix de a tiempo y tarde
                    estado = "Corregido" if random.random() < 0.5 else "Entregado"
                    fecha_entrega = fecha_limite - timedelta(hours=random.randint(1, 48)) if random.random() < 0.6 else fecha_limite + timedelta(hours=random.randint(1, 24))
                    url = f"https://github.com/entrega{estudiante_id}/{actividad[1].replace(' ', '').lower()}"
                    entregas.append((entrega_id, url, None, estado, estudiante_id, actividad_id, fecha_entrega.isoformat()))
                    entrega_id += 1
                # 30% no entregó (rojo)

            elif actividad_id == 3:  # Semana 3 (vence hoy)
                if rand < 0.5:  # 50% entregó
                    estado = "Entregado"
                    fecha_entrega = now - timedelta(hours=random.randint(1, 12))
                    url = f"https://github.com/entrega{estudiante_id}/{actividad[1].replace(' ', '').lower()}"
                    entregas.append((entrega_id, url, None, estado, estudiante_id, actividad_id, fecha_entrega.isoformat()))
                    entrega_id += 1
                # 50% no entregó aún (gris - pendiente)

            elif actividad_id == 4:  # Semana 4 (vence ahora)
                if rand < 0.3:  # 30% entregó
                    estado = "Entregado"
                    fecha_entrega = now - timedelta(hours=random.randint(1, 6))
                    url = f"https://github.com/entrega{estudiante_id}/{actividad[1].replace(' ', '').lower()}"
                    entregas.append((entrega_id, url, None, estado, estudiante_id, actividad_id, fecha_entrega.isoformat()))
                    entrega_id += 1
                # 70% no entregó aún (gris)

            # Semana 5 (futura) - nadie entregó (gris)

    cursor.executemany('''
        INSERT INTO nc_abcd_Entregas (id, nc_c1_URL_Entrega, nc_c2_Archivo, nc_c3_Estado,
                                       nc_fk_estudiante_id, nc_fk_actividad_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', entregas)

    conn.commit()

def main():
    """Función principal."""
    print("Generando base de datos de prueba...")

    create_directories()

    # Eliminar DB existente si existe
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"   Eliminada base anterior: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        create_mock_tables(conn)
        print("   [OK] Tablas creadas")

        populate_metadata(conn)
        print("   [OK] Metadatos de NocoDB insertados")

        populate_data(conn)
        print("   [OK] Datos de prueba insertados")

        print(f"\nBase de datos lista en: {DB_PATH}")
        print("\nResumen:")
        print("  - 1 cohorte activa (2026-Q1-Redes)")
        print("  - 5 actividades (Semana 1-5)")
        print("  - 8 estudiantes")
        print("  - Mix de entregas: verdes, amarillas, rojas y grises")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
