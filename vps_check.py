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

    print("=== NocoDB Final Verification ===")
    
    # Tables
    cursor.execute("SELECT id, title, table_name FROM nc_models_v2")
    models = cursor.fetchall()
    model_titles = {m['id']: m['title'] for m in models}
    
    for m in models:
        print(f"\n[TABLE] {m['title']} ({m['table_name']})")
        # Columns
        cursor.execute("SELECT title, column_name, uidt FROM nc_columns_v2 WHERE fk_model_id = ?", (m['id'],))
        cols = cursor.fetchall()
        for c in cols:
            if c['uidt'] == 'LinkToAnotherRecord' or c['column_name']:
                print(f"  - {c['title']} | Phys: {c['column_name']} | Type: {c['uidt']}")

    conn.close()

if __name__ == "__main__":
    main()
