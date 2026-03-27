import urllib.request
import urllib.error
import json
import getpass
import os

print("=== Autenticación NocoDB (Bearer Auth) ===")
# Leer URL desde .env si existe, sino pedirla
URL = None
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('NOCODB_URL='):
                URL = line.strip().split('=', 1)[1].strip('"\'')
                break

if not URL:
    URL = input("Ingresa la URL pública de tu NocoDB (ej: https://nocodb.midominio.com): ").strip()
else:
    print(f"Detectada URL desde .env: {URL}")

email = input("Email de admin NocoDB: ")
password = getpass.getpass("Contraseña NocoDB: ")

# 1. Login para obtener el JWT Token Temporal
try:
    login_req = urllib.request.Request(
        f"{URL}/api/v1/auth/user/signin", 
        data=json.dumps({"email": email, "password": password}).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    login_res = json.loads(urllib.request.urlopen(login_req).read())
    token = login_res.get('token')
    print("¡Login exitoso! Token Bearer obtenido.")
except urllib.error.HTTPError as e:
    print(f"Error de Login (HTTP {e.code}): {e.read().decode('utf-8')}")
    exit(1)

# Configuramos el header con el Bearer token (xc-auth)
HEADERS = {'xc-auth': token, 'Content-Type': 'application/json'}

def post(path, data):
    req = urllib.request.Request(f"{URL}{path}", data=json.dumps(data).encode('utf-8'), headers=HEADERS)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} en {path}: {e.read().decode('utf-8')}")
        return None

def get(path):
    req = urllib.request.Request(f"{URL}{path}", headers=HEADERS)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} en {path}: {e.read().decode('utf-8')}")
        return None

# 2. Obtener IDs y Crear Tablas
print("\n>> Obteniendo Workspace...")
ws_res = get("/api/v3/meta/workspaces")
ws_id = ws_res['list'][0]['id']

print(">> Obteniendo Base...")
base_res = get(f"/api/v3/meta/workspaces/{ws_id}/bases")
if base_res and 'list' in base_res and len(base_res['list']) > 0:
    base_id = base_res['list'][0]['id']
else:
    print("Creando nueva base entregastp...")
    base_id = post(f"/api/v3/meta/workspaces/{ws_id}/bases", {"title": "entregastp"}).get('id')

# 3. Esquema Exacto del README (Renombrar campos primarios)
renames = {
    "Cohortes": "Nombre",
    "Actividades": "Nombre",
    "Estudiantes": "Apellido",
    "Entregas": "ID Entrega"
}

schemas = {
    "Cohortes": [
        {"title": "Activa", "type": "Checkbox"}
    ],
    "Actividades": [
        {"title": "Orden", "type": "Number"},
        {"title": "Fecha Límite", "type": "Date"},
        {"title": "Tipo", "type": "SingleSelect", "options": "Semanal,Integrador"},
        {"title": "Peso", "type": "Number"},
        {"title": "URL Guía", "type": "URL"}
    ],
    "Estudiantes": [
        {"title": "Nombre", "type": "SingleLineText"},
        {"title": "Email", "type": "Email"},
        {"title": "GitHub", "type": "URL"}
    ],
    "Entregas": [
        {"title": "Estado", "type": "SingleSelect", "options": "Entregado,Entregado tarde,Corregido,Rehacer"},
        {"title": "URL Entrega", "type": "URL"}
    ]
}

print(f"\nBase localizada (ID: {base_id}). Obteniendo tablas actuales...")
tables_res = get(f"/api/v3/meta/bases/{base_id}/tables")
table_map = {}
if tables_res and 'list' in tables_res:
    for t in tables_res['list']:
        table_map[t['title']] = t['id']

# Eliminar tabla Features si existe
if "Features" in table_map:
    print(">> Eliminando tabla default 'Features'...")
    req = urllib.request.Request(f"{URL}/api/v3/meta/bases/{base_id}/tables/{table_map['Features']}", headers=HEADERS, method='DELETE')
    urllib.request.urlopen(req)

for table_name in schemas.keys():
    if table_name not in table_map:
        print(f"La tabla {table_name} no existía, creando...")
        res = post(f"/api/v3/meta/bases/{base_id}/tables", {"title": table_name})
        if res:
            table_map[table_name] = res.get('id')
            print(f"  [OK] Tabla '{table_name}' creada.")

    t_id = table_map.get(table_name)
    if not t_id: continue

    # Renombrar campo primario (Id o Title -> Nombre/Apellido)
    fields_res = get(f"/api/v3/meta/bases/{base_id}/tables/{t_id}")
    if fields_res and 'fields' in fields_res:
        title_field = next((f for f in fields_res['fields'] if f['title'] == 'Title'), None)
        if title_field:
            new_name = renames[table_name]
            print(f"   -> Renombrando campo principal 'Title' a '{new_name}'...")
            req = urllib.request.Request(f"{URL}/api/v3/meta/bases/{base_id}/fields/{title_field['id']}", data=json.dumps({"title": new_name}).encode('utf-8'), headers=HEADERS, method='PATCH')
            urllib.request.urlopen(req)

    print(f">> Creando columnas para {table_name}...")
    for field in schemas[table_name]:
        print(f"   -> Agregando columna '{field['title']}'...")
        f_res = post(f"/api/v3/meta/bases/{base_id}/tables/{t_id}/fields", field)

print("\n>> Creando Relaciones (Foreign Keys)...")
relations = [
    {"table": "Actividades", "title": "Link a Cohortes", "target": "Cohortes"},
    {"table": "Estudiantes", "title": "Link a Cohortes", "target": "Cohortes"},
    {"table": "Entregas", "title": "Link a Estudiantes", "target": "Estudiantes"},
    {"table": "Entregas", "title": "Link a Actividades", "target": "Actividades"},
]

for rel in relations:
    source_id = table_map.get(rel["table"])
    target_id = table_map.get(rel["target"])
    if source_id and target_id:
        print(f"   -> Enlazando {rel['table']} -> {rel['target']}...")
        payload = {
            "title": rel["title"],
            "type": "LinkToAnotherRecord",
            "fk_related_model_id": target_id,
            "meta": {"type": "bt"} # BelongsTo (desmarcar permitir enlazar a múltiples registros)
        }
        post(f"/api/v3/meta/bases/{base_id}/tables/{source_id}/fields", payload)

print("\n¡Despliegue de estructura de columnas completado!")
print("IMPORTANTE: Las 'Relaciones' ya fueron creadas por la API. Si alguna quedó permitiendo enlazar múltiples registros, configuralo manualmente en la UI.")
