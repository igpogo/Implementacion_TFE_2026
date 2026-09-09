from system_logger import SystemLogger
from notification_service import NotificationService

class MessagePipelineHandler:
    def __init__(self):
        self.logger = SystemLogger()
        self.notifier = NotificationService()

    def handle_response(self, user_email: str, user_id: str, code: str, action_result: dict = None, extra_log_ctx: dict = None):
        # 1. Registro obligatorio en el Log del Sistema
        log_entry = self.logger.log_event(code=code, user_id=user_id, extra_context=extra_log_ctx)
        
        # 2. Envío de Correo (Éxito o Fallo)
        email_sent = self.notifier.send_notification(
            recipient_email=user_email,
            code=code,
            action_result=action_result
        )

        return {
            "log": log_entry,
            "notification": email_sent
        }

# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    handler = MessagePipelineHandler()

    # Ejemplo 1: Notificación de Éxito
    handler.handle_response(
        user_email="usuario@empresa.com",
        user_id="usr_123",
        code="OK-200",
        action_result={"action": "CREAR", "tabla": "productos"}
    )

    # Ejemplo 2: Notificación de Fallo por Base de Datos (ERR-501)
    handler.handle_response(
        user_email="usuario@empresa.com",
        user_id="usr_123",
        code="ERR-501",
        extra_log_ctx={"detail": "psycopg2.OperationalError: could not connect to server"}
    )