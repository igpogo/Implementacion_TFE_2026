from typing import Dict, Any, Optional
from response_catalog import CATALOGO_RESPUESTAS

class NotificationService:
    def __init__(self, smtp_sender_mock: bool = True):
        self.smtp_sender_mock = smtp_sender_mock

    def send_notification(self, recipient_email: str, code: str, action_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera y envía el correo al usuario.
        - Éxito (OK-200): Envía confirmación con el resultado de la acción realizada.
        - Fallo (ERR-xxx): Envía la explicación segura predefinida SIN datos sensibles (PII).
        """
        info = CATALOGO_RESPUESTAS.get(code, CATALOGO_RESPUESTAS["ERR-500"])
        is_success = (info["tipo"] == "Éxito")

        subject = f"[{'ÉXITO' if is_success else 'ERROR'}] Estado del Procesamiento de Comando - {code}"

        if is_success:
            # En caso de éxito, se incluye la confirmación del resultado de la acción
            accion = action_result.get("action", "PROCESADO") if action_result else "PROCESADO"
            tabla = action_result.get("tabla", "N/A") if action_result else "N/A"
            body = (
                f"Estimado usuario,\n\n"
                f"{info['user_message']}\n\n"
                f"--- Resumen de Operación ---\n"
                f"Acción Realizada: {accion}\n"
                f"Tabla / Entidad: {tabla}\n"
                f"Estado: COMPLETADO CON ÉXITO\n\n"
                f"Atentamente,\nEl Equipo de Plataforma."
            )
        else:
            # En caso de fallo, se envía únicamente la explicación segura sin PII ni detalles técnicos expuestos
            body = (
                f"Estimado usuario,\n\n"
                f"No se pudo procesar su solicitud.\n\n"
                f"Detalle del Problema:\n"
                f"• Código: {code}\n"
                f"• Mensaje: {info['user_message']}\n\n"
                f"Por favor revise los requisitos de su solicitud y vuelva a intentarlo.\n\n"
                f"Atentamente,\nEl Equipo de Plataforma."
            )

        email_payload = {
            "to": recipient_email,
            "subject": subject,
            "body": body,
            "code": code
        }

        if self.smtp_sender_mock:
            self._dispatch_mock_email(email_payload)

        return email_payload

    def _dispatch_mock_email(self, email_data: Dict[str, Any]):
        """Simulación de envío por servidor SMTP."""
        print("\n=================== CORREO ENVIADO ===================")
        print(f"Para: {email_data['to']}")
        print(f"Asunto: {email_data['subject']}")
        print(f"Cuerpo:\n{email_data['body']}")
        print("======================================================\n")