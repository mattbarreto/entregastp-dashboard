import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def main():
    conn = sqlite3.connect('/data/noco.db')
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    print("=== COHORTES ===")
    cursor.execute("SELECT id, Nombre FROM nc_oniw___Cohortes")
    for c in cursor.fetchall():
        print(f"ID: {c['id']} | Name: {c['Nombre']}")

    print("\n=== ACTIVIDADES STATS ===")
    cursor.execute("PRAGMA table_info(nc_oniw___Actividades)")
    cols = [r['name'] for r in cursor.fetchall()]
    fk_col = next((c for c in cols if 'Cohortes_id' in c), None)
    
    if fk_col:
        cursor.execute(f"SELECT COUNT(*) as count, {fk_col} as coh_id FROM nc_oniw___Actividades GROUP BY {fk_col}")
        print(f"Activities by Cohort ID: {cursor.fetchall()}")
    else:
        print(f"NO FK found in Actividades. Cols: {cols}")

    print("\n=== ESTUDIANTES STATS ===")
    cursor.execute("PRAGMA table_info(nc_oniw___Estudiantes)")
    st_cols = [r['name'] for r in cursor.fetchall()]
    st_fk_col = next((c for c in st_cols if 'Cohortes_id' in c), None)
    if st_fk_col:
        cursor.execute(f"SELECT COUNT(*) as count, {st_fk_col} as coh_id FROM nc_oniw___Estudiantes GROUP BY {st_fk_col}")
        print(f"Students by Cohort ID: {cursor.fetchall()}")

    conn.close()

if __name__ == "__main__":
    main()
