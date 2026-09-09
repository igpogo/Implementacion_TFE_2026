import sqlite3
from mail_ingestion_service import MailReaderService
from system_orchestrator import SystemOrchestrator
from system_config import SystemConfigManager
from batch_notifier import BatchResponseManager

def run_single_cycle():
    """Ejecuta un único ciclo completo de lectura, procesamiento y notificación."""
    print("Iniciando ciclo de ejecución del Motor DSL...")
    
    # 1. Inicializar la base de datos y Orquestador
    conn = sqlite3.connect("database.db")
    orchestrator = SystemOrchestrator(conn, secret_key="SECRET_KEY_123")
    
    # Configuración de notificaciones en lote
    config_manager = SystemConfigManager(conn)
    batch_manager = BatchResponseManager(config_manager, orchestrator.notifier)

    # 2. Configurar el lector de correos (IMAP)
    mail_reader = MailReaderService(
        imap_server="imap.tudominio.com",
        email_account="procesador@tudominio.com",
        password="tu_password_seguro"
    )

    try:
        mail_reader.connect()
        pendientes = mail_reader.fetch_unread_messages()
        
        if pendientes:
            print(f"[*] Procesando {len(pendientes)} correos nuevos...")
            for remitente, payload in pendientes:
                resultado = orchestrator.process_request(payload=payload, user_email=remitente)
                # Añadir al gestor de lotes para el envío
                batch_manager.add_response(remitente, resultado["code"], resultado)
            
            # Ejecutar el envío de correos retenidos
            batch_manager.flush()
        else:
            print("[-] No hay correos nuevos.")
            
    except Exception as e:
        print(f"[!] Error inesperado durante el ciclo de ejecución: {e}")
    finally:
        # Asegurar siempre el cierre de conexiones
        mail_reader.disconnect()
        conn.close()
        print("Ciclo finalizado.")

if __name__ == "__main__":
    # Permite que el script sea llamado directamente por un Cron Job o tarea de Windows
    run_single_cycle()