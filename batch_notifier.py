from typing import Dict, Any, List
from system_config import SystemConfigManager

class BatchResponseManager:
    """
    Gestiona el envío de notificaciones resultantes del procesamiento de comandos.
    Basado en la configuración del administrador, envía las respuestas al instante
    o las almacena para enviar un reporte consolidado.
    """

    def __init__(self, config_manager: SystemConfigManager, notification_service: Any):
        self.config = config_manager
        self.notifier = notification_service
        self.pending_responses: Dict[str, List[Dict[str, Any]]] = {}

    def add_response(self, recipient_email: str, code: str, action_result: Dict[str, Any] = None):
        """Añade el resultado de un comando al flujo de salida."""
        
        # Verificar la decisión del administrador en tiempo real
        if self.config.get_compile_responses_enabled():
            # Agrupar respuesta en memoria
            if recipient_email not in self.pending_responses:
                self.pending_responses[recipient_email] = []
            
            self.pending_responses[recipient_email].append({
                "code": code,
                "action_result": action_result
            })
        else:
            # Despachar inmediatamente como correos separados
            self.notifier.send_notification(
                recipient_email=recipient_email, 
                code=code, 
                action_result=action_result
            )

    def flush(self):
        """
        Envía todos los mensajes retenidos en un único correo consolidado por usuario.
        Debe llamarse al final del procesamiento del lote de correos descargados.
        """
        for email, results_list in self.pending_responses.items():
            if not results_list:
                continue

            # Si solo hay un mensaje, se puede usar el flujo normal para no sobrecargar visualmente
            if len(results_list) == 1:
                single = results_list[0]
                self.notifier.send_notification(email, single["code"], single["action_result"])
            else:
                # Enviar utilizando el método de compilación de la HU 2.3
                self._dispatch_compiled_email(email, results_list)

        # Limpiar búfer
        self.pending_responses.clear()

    def _dispatch_compiled_email(self, recipient_email: str, results_list: List[Dict[str, Any]]):
        """
        Construye el cuerpo del mensaje combinando todas las respuestas y utiliza 
        el NotificationService (que debe extenderse) para enviarlo.
        """
        # Delegamos la construcción final al servicio de notificaciones,
        # llamando al método encargado de correos en bloque.
        if hasattr(self.notifier, "send_compiled_notification"):
            self.notifier.send_compiled_notification(recipient_email, results_list)
        else:
            # Fallback si el notificador no está actualizado: enviar uno por uno
            for res in results_list:
                self.notifier.send_notification(recipient_email, res["code"], res["action_result"])