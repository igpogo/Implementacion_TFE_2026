import re
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, Any
from cryptography.fernet import Fernet

from user_manager import UserManager, Role, UnauthorizedError, UserNotFoundError

class EmailSenderInterface(ABC):
    """Interfaz abstracta para el servicio de envío de correo electrónico."""
    @abstractmethod
    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        pass

class UnauthorizedEmailError(Exception):
    """Excepción lanzada cuando el correo no figura en la lista permitida."""
    pass

class RegistrationService:
    """Servicio de alta que registra usuarios, asigna su tabla principal y gestiona sus claves."""

    def __init__(self, user_manager: UserManager, email_sender: EmailSenderInterface, db_connection: sqlite3.Connection):
        self.user_manager = user_manager
        self.email_sender = email_sender
        self.conn = db_connection

    def _generate_symmetric_key(self) -> str:
        """Genera una clave simétrica con Fernet."""
        return Fernet.generate_key().decode('utf-8')

    def _derive_default_table_name(self, email: str) -> str:
        """Genera un nombre de tabla válido asignado por defecto a partir del correo del usuario."""
        username = email.split('@')[0]
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', username)
        return f"tabla_{sanitized_name}"

    def process_registration(self, user_email: str) -> Dict[str, Any]:
        """Procesa el alta del usuario, asigna su tabla en user_table_permissions y guarda la clave."""
        
        # 1. Verificar allowlist
        if not self.user_manager.is_on_allowlist(user_email):
            error_body = (
                "Estimado usuario,\n\n"
                "Su dirección de correo electrónico no se encuentra en la lista de direcciones "
                "permitidas. No se puede completar el registro en el sistema."
            )
            self.email_sender.send_email(
                to_address=user_email,
                subject="Error de Alta: Correo no autorizado",
                body=error_body
            )
            raise UnauthorizedEmailError(f"El correo {user_email} no está en la lista permitida.")

        # 2. Registrar usuario en la base de datos
        user_info = self.user_manager.register_user(user_email, role=Role.USER)

        # 3. Generar clave simétrica y asignar la tabla principal al usuario
        user_key = self._generate_symmetric_key()
        assigned_table = self._derive_default_table_name(user_email)

        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO user_keys (email, secret_key) VALUES (?, ?)",
                (user_email, user_key)
            )
            # Asignación automática de permisos de tabla primaria en el registro
            self.conn.execute(
                "INSERT OR REPLACE INTO user_table_permissions (email, table_name, parent_table) VALUES (?, ?, NULL)",
                (user_email, assigned_table)
            )

        # 4. Enviar correo con instrucciones
        welcome_body = (
            f"Bienvenido al servicio de interacción con Base de Datos.\n\n"
            f"Su cuenta ha sido activada correctamente.\n"
            f"Se le ha asignado automáticamente la tabla principal: '{assigned_table}'.\n\n"
            f"AVISO DE SEGURIDAD:\n"
            f"Su clave criptográfica simétrica ha sido generada y el Administrador del sistema "
            f"se la proporcionará a través de un canal seguro alternativo (fuera de banda).\n\n"
            f"INSTRUCCIONES DE USO:\n"
            f"Una vez recibida la clave por el canal seguro, envíe un token encriptado en el "
            f"cuerpo de sus correos con la estructura JSON correspondiente."
        )
        self.email_sender.send_email(
            to_address=user_email,
            subject="Bienvenido al Sistema - Instrucciones de Inicio",
            body=welcome_body
        )

        return {
            "success": True,
            "user": user_info,
            "user_key": user_key,
            "assigned_table": assigned_table
        }

    def get_user_key_as_admin(self, admin_email: str, target_email: str) -> str:
        """Permite únicamente al Administrador recuperar la clave simétrica de un usuario."""
        user_admin = self.user_manager.get_user(admin_email)
        if user_admin["role"] != Role.ADMIN.value or user_admin["status"] != "ACTIVE":
            raise UnauthorizedError("Solo un Administrador activo puede consultar las claves simétricas de los usuarios.")

        cursor = self.conn.cursor()
        cursor.execute("SELECT secret_key FROM user_keys WHERE email = ?", (target_email,))
        row = cursor.fetchone()
        
        if not row:
            raise UserNotFoundError(f"No existe una clave asignada para el usuario {target_email}.")

        return row[0]