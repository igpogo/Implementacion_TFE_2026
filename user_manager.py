import sqlite3
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any

class Role(Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class UserEncryption(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class UnauthorizedError(Exception):
    """Excepción lanzada cuando un usuario no tiene permisos para la operación."""
    pass

class UserNotFoundError(Exception):
    """Excepción lanzada cuando un usuario no existe en la base de datos."""
    pass

class UserManager:
    """Módulo para gestionar la lista de permitidos (allowlist) y usuarios con esquema RBAC y estado de encriptación[cite: 3, 4]."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self._init_db()

    def _init_db(self) -> None:
        """Crea las tablas independientes para allowlist y usuarios[cite: 3]."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS allowlist (
                    email TEXT PRIMARY KEY,
                    added_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    encryption TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def bootstrap_admin(self, admin_email: str) -> None:
        """Añade el primer administrador del sistema sin requerir verificación previa[cite: 3]."""
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO allowlist (email, added_by) VALUES (?, ?)",
                (admin_email, "SYSTEM")
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO users (email, role, status, encryption) VALUES (?, ?, ?, ?)",
                (admin_email, Role.ADMIN.value, UserStatus.ACTIVE.value, UserEncryption.ACTIVE.value)
            )

    def _verify_admin(self, admin_email: str) -> None:
        """Verifica si quien ejecuta la acción posee rol Administrador[cite: 3]."""
        user = self.get_user(admin_email)
        if user["role"] != Role.ADMIN.value or user["status"] != UserStatus.ACTIVE.value:
            raise UnauthorizedError(f"El usuario {admin_email} no posee permisos de Administrador.")

    def add_to_allowlist(self, admin_email: str, target_email: str) -> bool:
        """Añade una dirección de correo a la lista permitida[cite: 1, 2, 4]."""
        self._verify_admin(admin_email)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO allowlist (email, added_by) VALUES (?, ?)",
                (target_email, admin_email)
            )
        return True

    def remove_from_allowlist(self, admin_email: str, target_email: str) -> bool:
        """Elimina un correo de la lista permitida[cite: 1, 2, 4]."""
        self._verify_admin(admin_email)
        with self.conn:
            cursor = self.conn.execute("DELETE FROM allowlist WHERE email = ?", (target_email,))
            return cursor.rowcount > 0

    def is_on_allowlist(self, email: str) -> bool:
        """Comprueba si un correo está en la lista permitida[cite: 1, 2, 4]."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM allowlist WHERE email = ?", (email,))
        return cursor.fetchone() is not None

    def register_user(
        self, 
        email: str, 
        role: Role = Role.USER, 
        encryption: UserEncryption = UserEncryption.ACTIVE
    ) -> Dict[str, Any]:
        """Registra un usuario activo si se encuentra en la allowlist[cite: 1, 2, 3]."""
        if not self.is_on_allowlist(email):
            raise UnauthorizedError(f"El correo {email} no pertenece a la lista de direcciones permitidas.")
        
        status = UserStatus.ACTIVE.value
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (email, role, status, encryption) VALUES (?, ?, ?, ?)",
                (email, role.value, status, encryption.value)
            )
        return self.get_user(email)

    def update_user_role(self, admin_email: str, target_email: str, new_role: Role) -> Dict[str, Any]:
        """Modifica el rol de un usuario en el sistema[cite: 1, 3, 4]."""
        self._verify_admin(admin_email)
        self.get_user(target_email)  # Lanza UserNotFoundError si no existe
        
        with self.conn:
            self.conn.execute(
                "UPDATE users SET role = ? WHERE email = ?",
                (new_role.value, target_email)
            )
        return self.get_user(target_email)

    def update_user_encryption(self, user_email: str, encryption: UserEncryption) -> Dict[str, Any]:
        """Modifica la preferencia de encriptación de un usuario[cite: 2]."""
        self.get_user(user_email)  # Lanza UserNotFoundError si no existe
        with self.conn:
            self.conn.execute(
                "UPDATE users SET encryption = ? WHERE email = ?",
                (encryption.value, user_email)
            )
        return self.get_user(user_email)

    def get_user(self, email: str) -> Dict[str, Any]:
        """Obtiene la información de un usuario registrado[cite: 3]."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT email, role, status, encryption, created_at FROM users WHERE email = ?", 
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            raise UserNotFoundError(f"Usuario {email} no registrado.")
        
        return {
            "email": row[0],
            "role": row[1],
            "status": row[2],
            "encryption": row[3],
            "created_at": row[4]
        }