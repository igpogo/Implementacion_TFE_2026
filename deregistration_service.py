import sqlite3
from typing import Dict, Any
from user_manager import UserManager, UserStatus, UserNotFoundError
from registration_service import EmailSenderInterface

class AlreadyInactiveError(Exception):
    """Excepción lanzada cuando el usuario ya se encuentra desactivado en el sistema[cite: 2, 4]."""
    pass

class DeregistrationService:
    """Servicio para procesar la baja, desactivación o eliminación de cuentas de usuario[cite: 1, 2, 4]."""

    def __init__(self, user_manager: UserManager, email_sender: EmailSenderInterface, db_connection: sqlite3.Connection):
        self.user_manager = user_manager
        self.email_sender = email_sender
        self.conn = db_connection

    def deregister_user(self, user_email: str, hard_delete: bool = False) -> Dict[str, Any]:
        """Procesa la orden de baja del servicio para un usuario registrado[cite: 2, 4].
        
        Soporta desactivación lógica (marcado como INACTIVE) o eliminación física de registros.
        Emite un correo de confirmación al usuario tras completar la operación[cite: 2].
        """
        # 1. Obtener y verificar usuario registrado
        user = self.user_manager.get_user(user_email)

        # 2. Validar estado actual del usuario
        if user["status"] == UserStatus.INACTIVE.value:
            raise AlreadyInactiveError(f"La cuenta de usuario {user_email} ya se encuentra inactiva.")

        if hard_delete:
            # Eliminación física de registros en la BD y allowlist
            with self.conn:
                self.conn.execute("DELETE FROM user_keys WHERE email = ?", (user_email,))
                self.conn.execute("DELETE FROM users WHERE email = ?", (user_email,))
                self.conn.execute("DELETE FROM allowlist WHERE email = ?", (user_email,))
            final_status = "DELETED"
        else:
            # Desactivación lógica (marcado como INACTIVE)
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET status = ? WHERE email = ?",
                    (UserStatus.INACTIVE.value, user_email)
                )
            final_status = UserStatus.INACTIVE.value

        # 3. Notificación vía correo electrónico con la confirmación de la baja (HU11 AC1)
        subject = "Confirmación de Baja del Servicio"
        body = (
            f"Estimado usuario,\n\n"
            f"Le confirmamos que su solicitud de baja para la cuenta {user_email} "
            f"ha sido procesada correctamente. Su cuenta ha sido desactivada en el sistema.\n\n"
            f"Atentamente,\n"
            f"El Equipo de Soporte."
        )
        self.email_sender.send_email(to_address=user_email, subject=subject, body=body)

        return {
            "success": True,
            "email": user_email,
            "status": final_status
        }