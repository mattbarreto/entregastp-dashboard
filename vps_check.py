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

    print("=== ESTUDIANTES DATA CHECK ===")
    cursor.execute("PRAGMA table_info(nc_oniw___Estudiantes)")
    cols = [r['name'] for r in cursor.fetchall()]
    
    fk_col = next((c for c in cols if 'Cohortes_id' in c), None)
    if fk_col:
        print(f"Found FK Col: {fk_col}")
        cursor.execute(f"SELECT COUNT(*) as count, {fk_col} FROM nc_oniw___Estudiantes GROUP BY {fk_col}")
        print(f"Stats by Cohort ID: {cursor.fetchall()}")
    else:
        print("FK Col NOT FOUND in Estudiantes. Cols: ", cols)

    print("\n=== ENTREGAS DATA CHECK ===")
    cursor.execute("PRAGMA table_info(nc_oniw___Entregas)")
    ent_cols = [r['name'] for r in cursor.fetchall()]
    print(f"Cols in Entregas: {ent_cols}")

    conn.close()

if __name__ == "__main__":
    main()
