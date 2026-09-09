import json
from datetime import datetime
from typing import Dict, Any
from cryptography.fernet import Fernet

class ClientApp:
    """Cliente encargado de construir y cifrar mensajes para el pipeline."""

    @staticmethod
    def get_current_timestamp() -> str:
        """Genera el timestamp en formato YYYY-MM-DD-SSSSS."""
        now = datetime.now()
        seconds_of_day = now.hour * 3600 + now.minute * 60 + now.second
        return f"{now.strftime('%Y-%m-%d')}-{seconds_of_day:05d}"

    def generate_payload_json(self, email: str, action: str, data: Dict[str, Any], user_key: str) -> Dict[str, Any]:
        """Genera un mensaje cifrado usando el formato JSON directo."""
        inner_content = {
            "format_type": "json",
            "action": action,
            "data": data
        }
        return self._build_envelope(email, inner_content, user_key)

    def generate_payload_grammar(self, email: str, command: str, user_key: str) -> Dict[str, Any]:
        """Genera un mensaje cifrado usando comandos en lenguaje estructurado/gramática."""
        inner_content = {
            "format_type": "grammar",
            "command": command
        }
        return self._build_envelope(email, inner_content, user_key)

    def _build_envelope(self, email: str, inner_content: Dict[str, Any], user_key: str) -> Dict[str, Any]:
        """Cifra el contenido interno y construye la envolvente con metadatos no cifrados."""
        fernet = Fernet(user_key.encode('utf-8'))
        encrypted_bytes = fernet.encrypt(json.dumps(inner_content).encode('utf-8'))
        
        return {
            "email": email,
            "timestamp": self.get_current_timestamp(),
            "payload": encrypted_bytes.decode('utf-8')
        }