import os
import time
import sqlite3
import json
import ctypes
from ctypes import wintypes
import pyautogui
from cryptography.fernet import Fernet

from system_orchestrator import SystemOrchestrator
from client_app import ClientApp

# Configuración y claves
FERNET_KEY = Fernet.generate_key().decode('utf-8')
SCREENSHOT_DIR = "capturas_manual_usuario"
DESTINATARIO_SISTEMA = "sistema_procesamiento@empresa.com"

def setup_directories():
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_console_region():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    hwnd = kernel32.GetConsoleWindow()
    if not hwnd or not user32.IsWindowVisible(hwnd):
        hwnd = user32.GetForegroundWindow()

    if hwnd:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
        left = rect.left
        top = rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        if width > 0 and height > 0:
            return (left, top, width, height)
            
    return None

def take_terminal_screenshot(filename: str):
    time.sleep(1.5)
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    region = get_console_region()
    if region:
        captura = pyautogui.screenshot(region=region)
    else:
        captura = pyautogui.screenshot()
        
    captura.save(filepath)
    print(f"\n[📸 CAPTURA GUARDADA] -> {filepath}\n")
    time.sleep(1.0)

def imprimir_simulacion_correo(envelope: dict, destinatario: str = DESTINATARIO_SISTEMA):
    print("------------------ CORREO ENVIADO POR EL USUARIO ------------------")
    print(f"De: {envelope['email']}")
    print(f"Para: {destinatario}")
    print(f"Asunto: [EJECUCION_COMANDO] - {envelope['timestamp']}")
    print("Cuerpo del mensaje (Envolvente JSON cifrada):")
    print(json.dumps(envelope, indent=2))
    print("-------------------------------------------------------------------\n")

def ejecutar_ejemplos():
    setup_directories()
    
    client = ClientApp()
    conn = sqlite3.connect(":memory:")
    orchestrator = SystemOrchestrator(conn, secret_key=FERNET_KEY)
    
    # Registrar usuario de prueba en Authenticator
    orchestrator.authenticator.valid_users.add("admin_rh")

    # Desencriptador compatible con Fernet
    def custom_decrypt(encrypted_cmd: str) -> str:
        try:
            f = Fernet(FERNET_KEY.encode('utf-8'))
            decrypted_bytes = f.decrypt(encrypted_cmd.encode('utf-8'))
            data = json.loads(decrypted_bytes.decode('utf-8'))
            if isinstance(data, dict):
                return data.get("command", str(data))
            return str(data)
        except Exception:
            return orchestrator.decryptor.decrypt(encrypted_cmd)

    orchestrator.decryptor.decrypt = custom_decrypt

    # Pre-requisito silencioso: Crear la tabla 'empleados'
    cmd_crear_tabla = "CREAR_TABLA empleados (id INTEGER, nombre TEXT, rol TEXT, salario REAL)"
    pre_envelope = client.generate_payload_grammar("admin@empresa.com", cmd_crear_tabla, FERNET_KEY)
    orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": pre_envelope["payload"]
    }, pre_envelope["email"])

    # =========================================================
    # EJEMPLO 1: Alta Exitosa (CREAR via ClientApp)
    # =========================================================
    clear_console()
    print("=" * 67)
    print(" EJEMPLO 1: CREACIÓN DE REGISTRO VÁLIDO (CLIENT_APP -> CORREO)")
    print("=" * 67)
    
    cmd_1 = "CREAR EN empleados SET id=101, nombre='Laura Gomez', rol='Ventas', salario=2500.0"
    envelope_1 = client.generate_payload_grammar("admin@empresa.com", cmd_1, FERNET_KEY)
    
    imprimir_simulacion_correo(envelope_1)
    
    res1 = orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": envelope_1["payload"]
    }, envelope_1["email"])
    
    print("[RESPUESTA DEL ORQUESTADOR]")
    print(f"• Estado: {res1.get('status')}")
    print(f"• Código: {res1.get('code')}")
    print(f"• Mensaje: {res1.get('message')}")
    
    take_terminal_screenshot("01_ejemplo_crear_exito.png")

    # =========================================================
    # EJEMPLO 2: Lectura de Datos (LEER via ClientApp)
    # =========================================================
    clear_console()
    print("=" * 67)
    print(" EJEMPLO 2: CONSULTA DE REGISTROS CON FILTRO (LEER)")
    print("=" * 67)
    
    cmd_2 = "LEER DE empleados WHERE id=101"
    envelope_2 = client.generate_payload_grammar("admin@empresa.com", cmd_2, FERNET_KEY)
    
    imprimir_simulacion_correo(envelope_2)
    
    res2 = orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": envelope_2["payload"]
    }, envelope_2["email"])
    
    print("[RESPUESTA DEL ORQUESTADOR]")
    print(f"• Estado: {res2.get('status')}")
    print(f"• Código: {res2.get('code')}")
    print(f"• Mensaje: {res2.get('message')}")
    
    datos_obtenidos = res2.get('data')
    if isinstance(datos_obtenidos, dict):
        datos_obtenidos = datos_obtenidos.get('resultados', datos_obtenidos)
    print(f"• Datos devueltos: {datos_obtenidos}")
    
    take_terminal_screenshot("02_ejemplo_leer_exito.png")

    # =========================================================
    # EJEMPLO 3: Modificación Exitosa (MODIFICAR via ClientApp)
    # =========================================================
    clear_console()
    print("=" * 67)
    print(" EJEMPLO 3: ACTUALIZACIÓN DE REGISTRO (MODIFICAR)")
    print("=" * 67)
    
    cmd_3 = "MODIFICAR EN empleados SET salario=2800.0 WHERE id=101"
    envelope_3 = client.generate_payload_grammar("admin@empresa.com", cmd_3, FERNET_KEY)
    
    imprimir_simulacion_correo(envelope_3)
    
    res3 = orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": envelope_3["payload"]
    }, envelope_3["email"])
    
    print("[RESPUESTA DEL ORQUESTADOR]")
    print(f"• Estado: {res3.get('status')}")
    print(f"• Código: {res3.get('code')}")
    print(f"• Mensaje: {res3.get('message')}")
    
    take_terminal_screenshot("03_ejemplo_modificar_exito.png")

    # =========================================================
    # EJEMPLO 4: Bloqueo de Seguridad (Falta WHERE en ELIMINAR)
    # =========================================================
    clear_console()
    print("=" * 67)
    print(" EJEMPLO 4: BLOQUEO POR REGLA DE SEGURIDAD (SIN WHERE)")
    print("=" * 67)
    
    cmd_4 = "ELIMINAR DE empleados"
    envelope_4 = client.generate_payload_grammar("admin@empresa.com", cmd_4, FERNET_KEY)
    
    imprimir_simulacion_correo(envelope_4)
    
    res4 = orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": envelope_4["payload"]
    }, envelope_4["email"])
    
    print("[RESPUESTA DEL ORQUESTADOR]")
    print(f"• Estado: {res4.get('status')}")
    print(f"• Código: {res4.get('code')}")
    print(f"• Respuesta de Error: {res4.get('message')}")
    
    take_terminal_screenshot("04_ejemplo_bloqueo_seguridad.png")

    # =========================================================
    # EJEMPLO 5: Error Sintáctico (Comillas sin cerrar)
    # =========================================================
    clear_console()
    print("=" * 67)
    print(" EJEMPLO 5: ERROR DE SINTAXIS (COMILLAS ABIERTAS)")
    print("=" * 67)
    
    cmd_5 = "CREAR EN empleados SET id=102, nombre='Carlos Lopez"
    envelope_5 = client.generate_payload_grammar("admin@empresa.com", cmd_5, FERNET_KEY)
    
    imprimir_simulacion_correo(envelope_5)
    
    res5 = orchestrator.process_request({
        "user_id": "admin_rh",
        "encrypted_command": envelope_5["payload"]
    }, envelope_5["email"])
    
    print("[RESPUESTA DEL ORQUESTADOR]")
    print(f"• Estado: {res5.get('status')}")
    print(f"• Código: {res5.get('code')}")
    print(f"• Respuesta de Error: {res5.get('message')}")
    
    take_terminal_screenshot("05_ejemplo_error_sintaxis.png")

    conn.close()
    
    clear_console()
    print("=" * 67)
    print(" ✅ Pruebas finalizadas exitosamente.")
    print(" 📸 Capturas con correo simulado en 'capturas_manual_usuario/'.")
    print("=" * 67)

if __name__ == "__main__":
    ejecutar_ejemplos()