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

    print("=== ACTIVIDADES COLS ===")
    cursor.execute("PRAGMA table_info(nc_oniw___Actividades)")
    print(cursor.fetchall())
    
    print("\n=== COLUMNS METADATA ===")
    cursor.execute("SELECT m.title as table_title, c.title as col_title, c.column_name FROM nc_columns_v2 c JOIN nc_models_v2 m ON m.id = c.fk_model_id WHERE m.title = 'Actividades'")
    print(cursor.fetchall())

    conn.close()

if __name__ == "__main__":
    main()
