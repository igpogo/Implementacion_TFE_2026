import sqlite3
import logging
from user_manager import Role, UserStatus, UserEncryption

logger = logging.getLogger(__name__)

class SystemInstaller:
    """Módulo de aprovisionamiento e instalación inicial del sistema.
    
    Crea la estructura de tablas (DDL) y registra al Administrador inicial (Bootstrap).
    Diseñado para ejecutarse una única vez durante el despliegue/setup.
    """

    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection

    def create_schema(self) -> None:
        """Crea todas las tablas requeridas por los módulos del sistema."""
        with self.conn:
            # 1. Tabla de Lista Blanca (Allowlist)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS allowlist (
                    email TEXT PRIMARY KEY,
                    added_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Tabla de Usuarios
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    encryption TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Tabla de Claves Criptográficas Simétricas (Fernet)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_keys (
                    email TEXT PRIMARY KEY,
                    secret_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
                );
            """)

            # 4. Tabla de Permisos de Tablas por Usuario (RBAC para BD)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_table_permissions (
                    email TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    parent_table TEXT,
                    PRIMARY KEY (email, table_name),
                    FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
                );
            """)

            # 5. Tabla de Rastreo de Secuencia de Peticiones (Spike 2.1 - Mensajes Desordenados)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_request_tracker (
                    email TEXT PRIMARY KEY,
                    last_processed_timestamp TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
                );
            """)

    def bootstrap_admin(self, admin_email: str) -> None:
        """Registra el correo del Administrador principal en la lista permitida y la tabla de usuarios."""
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO allowlist (email, added_by) VALUES (?, ?)",
                (admin_email, "SYSTEM_INSTALLER")
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO users (email, role, status, encryption) VALUES (?, ?, ?, ?)",
                (admin_email, Role.ADMIN.value, UserStatus.ACTIVE.value, UserEncryption.ACTIVE.value)
            )

    def install_system(self, initial_admin_email: str) -> bool:
        """Ejecuta el proceso completo de aprovisionamiento inicial."""
        try:
            self.create_schema()
            self.bootstrap_admin(initial_admin_email)
            return True
        except sqlite3.Error as e:
            logger.error(f"Error durante la instalación de la base de datos: {e}")
            raise e

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Script de Instalación Inicial del Sistema")
    parser.add_argument("--db", default="system_database.db", help="Ruta del archivo de base de datos SQLite.")
    parser.add_argument("--admin", required=True, help="Correo electrónico del Administrador inicial del sistema.")

    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    installer = SystemInstaller(conn)
    
    print(f"Iniciando instalación del esquema de base de datos en '{args.db}'...")
    installer.install_system(args.admin)
    print(f"¡Instalación completada con éxito! Administrador registrado: {args.admin}")
    conn.close()

if __name__ == "__main__":
    main()