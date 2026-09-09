from typing import Dict, Any, Optional

class ResponseFormatter:
    """Formatea la respuesta final estandarizada para el cliente."""

    @staticmethod
    def format_success_response(code: str, action_data: Dict[str, Any], raw_cmd: str) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "code": code,
            "action": action_data.get("action"),
            "tabla": action_data.get("tabla"),
            "filas_afectadas": action_data.get("filas_afectadas", 0),
            "data": action_data.get("resultados", []),
            "command": raw_cmd
        }

    @staticmethod
    def format_error_response(code: str, user_message: str) -> Dict[str, Any]:
        return {
            "status": "ERROR",
            "code": code,
            "message": user_message
        }