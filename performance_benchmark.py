import base64
import cProfile
import pstats
import io
import sqlite3
import csv
import re
import sys
from datetime import datetime
from unittest.mock import patch
from memory_profiler import profile

# Módulos del sistema
from installer import SystemInstaller
from client_app import ClientApp
from system_orchestrator import SystemOrchestrator
from user_manager import Role, UserStatus, UserEncryption, UserManager

# --- CONFIGURACIÓN DEL BENCHMARK ---
BENCHMARK_SECRET_KEY = "SECRET_KEY_123"
ADMIN_EMAIL = "admin_system@empresa.com"
NUM_CLIENTS = 100
REQUESTS_PER_CLIENT = 100
VERBOSE = False               

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CPU_CSV_FILE = f"bm_cpu_{NUM_CLIENTS}_{REQUESTS_PER_CLIENT}_{timestamp}.csv"
MEM_CSV_FILE = f"bm_mem_{NUM_CLIENTS}_{REQUESTS_PER_CLIENT}_{timestamp}.csv"

mem_stream = io.StringIO()

class ClientContext:
    def __init__(self, email: str, app: ClientApp):
        self.email = email
        self.app = app

def xor_encrypt(plain_text: str, secret_key: str) -> str:
    """Encripta el comando en formato XOR + Base64 para que Decryptor lo procese."""
    key_bytes = secret_key.encode('utf-8')
    text_bytes = plain_text.encode('utf-8')
    encrypted_bytes = bytes([
        b ^ key_bytes[i % len(key_bytes)] 
        for i, b in enumerate(text_bytes)
    ])
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def provision_clients(conn: sqlite3.Connection, num_clients: int, admin_email: str) -> list:
    clients = []
    user_mgr = UserManager(conn)
    user_mgr.bootstrap_admin(admin_email)

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    table_columns = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        table_columns[table] = [col[1] for col in cursor.fetchall()]

    for i in range(1, num_clients + 1):
        email = f"client_{i}@test.com"
        table_name = f"data_client_{i}"
        
        user_mgr.add_to_allowlist(admin_email, email)
        user_mgr.register_user(email, role=Role.USER, encryption=UserEncryption.ACTIVE)

        with conn:
            if "user_keys" in table_columns:
                cols = table_columns["user_keys"]
                email_col = "email" if "email" in cols else cols[0]
                key_col = "secret_key" if "secret_key" in cols else ("user_key" if "user_key" in cols else cols[1])
                conn.execute(
                    f"INSERT OR REPLACE INTO user_keys ({email_col}, {key_col}) VALUES (?, ?)",
                    (email, BENCHMARK_SECRET_KEY)
                )

            if "user_table_permissions" in table_columns:
                cols = table_columns["user_table_permissions"]
                email_col = "email" if "email" in cols else cols[0]
                tbl_col = "table_name" if "table_name" in cols else cols[1]
                conn.execute(
                    f"INSERT OR REPLACE INTO user_table_permissions ({email_col}, {tbl_col}) VALUES (?, ?)",
                    (email, table_name)
                )

        app_instance = ClientApp()
        clients.append(ClientContext(email=email, app=app_instance))

    return clients

def _prepare_payload(ctx: ClientContext, raw_command: str, secret_key: str) -> dict:
    """Construye el payload compatible con Authenticator y Decryptor."""
    encrypted_cmd = xor_encrypt(raw_command, secret_key)
    
    return {
        "user_id": ctx.email,
        "encrypted_command": encrypted_cmd
    }

def _execute_multi_client_loop(clients: list, orchestrator: SystemOrchestrator, verbose: bool):
    secret_key = BENCHMARK_SECRET_KEY
    
    # 1. Creación de tablas por cliente
    for idx, ctx in enumerate(clients, 1):
        table_name = f"data_client_{idx}"
        create_cmd = f"CREAR_TABLA {table_name} (id INTEGER, valor TEXT)"
        payload = _prepare_payload(ctx, create_cmd, secret_key)
        
        try:
            res = orchestrator.process_request(payload, user_email=ctx.email)
            if verbose:
                print(f"[SETUP CLIENTE {idx}] Tabla '{table_name}' -> Resultado: {res}")
        except Exception as e:
            if verbose:
                print(f"[SETUP CLIENTE {idx}] Error: {e}")

    # 2. Bucle principal de peticiones CRUD
    total_ops = len(clients) * REQUESTS_PER_CLIENT
    op_counter = 0

    for i in range(REQUESTS_PER_CLIENT):
        for idx, ctx in enumerate(clients, 1):
            op_counter += 1
            table_name = f"data_client_{idx}"
            
            if i % 5 == 0:
                raw_cmd = f"LEER DE {table_name} WHERE id={i}"
            else:
                raw_cmd = f"CREAR EN {table_name} SET id={i}, valor='Dato_{i}'"
                
            payload = _prepare_payload(ctx, raw_cmd, secret_key)
            
            try:
                result = orchestrator.process_request(payload, user_email=ctx.email)
                if verbose:
                    print(f"[{op_counter}/{total_ops}] [{ctx.email}] Res: {result}")
            except Exception as e:
                if verbose:
                    print(f"[{op_counter}/{total_ops}] [{ctx.email}] Error: {e}")

@profile(stream=mem_stream)
def run_benchmark_simulation(clients: list, orchestrator: SystemOrchestrator, verbose: bool):
    if verbose:
        _execute_multi_client_loop(clients, orchestrator, verbose=True)
    else:
        with patch('builtins.print'):
            _execute_multi_client_loop(clients, orchestrator, verbose=False)

def export_cpu_to_csv(pr, filename):
    ps = pstats.Stats(pr).sort_stats('cumulative')
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Llamadas (ncalls)', 'Tiempo Total (tottime)', 'Tiempo/Llamada', 'Tiempo Acumulado (cumtime)', 'Funcion'])
            for func, stat in ps.stats.items():
                ccalls, ncalls, tottime, cumtime, callers = stat
                func_name = f"{func[0]}:{func[1]} ({func[2]})"
                percall = tottime / ncalls if ncalls > 0 else 0
                writer.writerow([ncalls, f"{tottime:.6f}", f"{percall:.6f}", f"{cumtime:.6f}", func_name])
        print(f"[*] Reporte CPU guardado en: {filename}")
    except PermissionError:
        print(f"[❌ ERROR PERMISOS] Cierra el archivo '{filename}' antes de reintentar.")

def export_memory_to_csv(mem_stream, filename):
    mem_stream.seek(0)
    regex = re.compile(r"^\s*(\d+)\s+([0-9.]+)\s+MiB\s+([0-9.-]+)\s+MiB\s*(\d+)?\s+(.*)$")
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Linea', 'Uso Memoria (MiB)', 'Incremento (MiB)', 'Iteraciones', 'Codigo'])
            for line in mem_stream:
                match = regex.match(line)
                if match:
                    writer.writerow([match.group(1), match.group(2), match.group(3), match.group(4) or "1", match.group(5).strip()])
        print(f"[*] Reporte Memoria guardado en: {filename}")
    except PermissionError:
        print(f"[❌ ERROR PERMISOS] Cierra el archivo '{filename}' antes de reintentar.")

def main():
    global VERBOSE
    if "--verbose" in sys.argv or "-v" in sys.argv:
        VERBOSE = True

    total_requests = NUM_CLIENTS * REQUESTS_PER_CLIENT
    print(f"--- Iniciando Multi-Client Benchmark ---")
    print(f"[*] Clientes Activos: {NUM_CLIENTS}")
    print(f"[*] Peticiones por Cliente: {REQUESTS_PER_CLIENT}")
    print(f"[*] Operaciones Totales: {total_requests}")
    print(f"[*] Modo Verbose: {'ACTIVADO' if VERBOSE else 'DESACTIVADO'}")

    conn = sqlite3.connect(":memory:")

    print("[*] Ejecutando SystemInstaller.install_system()...")
    installer = SystemInstaller(conn)
    installer.install_system(ADMIN_EMAIL)

    print(f"[*] Registrando y creando {NUM_CLIENTS} instancias de ClientApp...")
    clients = provision_clients(conn, NUM_CLIENTS, ADMIN_EMAIL)

    orchestrator = SystemOrchestrator(conn, secret_key=BENCHMARK_SECRET_KEY)

    # REGISTRO DE USUARIOS AUTORIZADOS EN EL AUTHENTICATOR
    for ctx in clients:
        auth = getattr(orchestrator, 'authenticator', None) or getattr(getattr(orchestrator, 'pipeline', None), 'authenticator', None)
        if auth and hasattr(auth, 'valid_users'):
            if isinstance(auth.valid_users, list):
                if ctx.email not in auth.valid_users:
                    auth.valid_users.append(ctx.email)
            elif isinstance(auth.valid_users, set):
                auth.valid_users.add(ctx.email)

    print("[*] Midiendo rendimiento (CPU y RAM)...")
    pr = cProfile.Profile()
    pr.enable()

    run_benchmark_simulation(clients, orchestrator, verbose=VERBOSE)

    pr.disable()

    print("\n--- Guardando Resultados ---")
    export_cpu_to_csv(pr, CPU_CSV_FILE)
    export_memory_to_csv(mem_stream, MEM_CSV_FILE)

    conn.close()
    print("--- Benchmark Finalizado con Éxito ---")

if __name__ == "__main__":
    main()