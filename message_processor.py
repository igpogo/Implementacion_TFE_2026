import re
import base64
from typing import Dict, Any, List
from command_grammar import CommandGrammarParser, SyntaxValidationError

# --- EXCEPCIONES DEL PIPELINE ---
class PipelineError(Exception):
    """Excepción base para fallos en el pipeline de procesamiento."""
    pass

class DecryptionError(PipelineError):
    """Fallo durante la desencriptación del mensaje."""
    pass

class AuthenticationError(PipelineError):
    """Fallo en la verificación de identidad del usuario."""
    pass

class SanitizationError(PipelineError):
    """El mensaje contiene caracteres o patrones no permitidos/peligrosos."""
    pass


# --- COMPONENTES DEL PIPELINE ---

class Decryptor:
    """Implementación de desencriptación (Cifrado XOR/Base64 para demostración)."""
    def __init__(self, secret_key: str = "SECRET_KEY_123"):
        self.secret_key = secret_key

    def decrypt(self, encrypted_data: str) -> str:
        try:
            decoded_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            key_bytes = self.secret_key.encode('utf-8')
            decrypted_chars = [
                chr(b ^ key_bytes[i % len(key_bytes)]) 
                for i, b in enumerate(decoded_bytes)
            ]
            return "".join(decrypted_chars)
        except Exception as e:
            raise DecryptionError(f"No se pudo desencriptar el mensaje: payload corrupto o clave incorrecta ({str(e)})")


class Authenticator:
    """Validador de identidad basado únicamente en ID de usuario."""
    def __init__(self, valid_users: List[str] = None):
        self.valid_users = set(valid_users or ["admin", "user1", "admin_rh"])

    def authenticate(self, user_id: str = None, *args, **kwargs) -> bool:
        """Acepta user_id y omite de forma transparente argumentos adicionales obsoletos."""
        if not user_id or user_id not in self.valid_users:
            raise AuthenticationError(f"Usuario desconocido o no autorizado: '{user_id}'.")
        return True


class Sanitizer:
    """Limpia y valida que el texto no contenga inyecciones ni caracteres nulos."""
    
    BANNED_PATTERNS = [
        r"\x00",            # Null bytes
        r";\s*DROP\s+",     # Intentos destructivos fuera del DSL
        r"--",              # Comentarios SQL
        r"/\*.*?\*/",       # Comentarios multilínea
    ]

    def sanitize(self, raw_text: str) -> str:
        if not isinstance(raw_text, str):
            raise SanitizationError("El payload desencriptado no es una cadena válida.")

        sanitized = raw_text.strip()

        for pattern in self.BANNED_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise SanitizationError(f"El mensaje contiene patrones de seguridad no permitidos ('{pattern}').")

        sanitized = "".join(ch for ch in sanitized if ch.isprintable() or ch in "\n\r\t")
        return sanitized


class SecureMessagePipeline:
    """Fachada principal de procesamiento secuencial."""

    def __init__(self, secret_key: str = "SECRET_KEY_123"):
        self.decryptor = Decryptor(secret_key=secret_key)
        self.authenticator = Authenticator()
        self.sanitizer = Sanitizer()
        self.parser = CommandGrammarParser()

    def process_incoming_message(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = request_payload.get("user_id") if isinstance(request_payload, dict) else None
        encrypted_command = request_payload.get("encrypted_command") if isinstance(request_payload, dict) else None

        self.authenticator.authenticate(user_id)

        if not encrypted_command:
            raise DecryptionError("El campo 'encrypted_command' es obligatorio.")
        
        raw_command = self.decryptor.decrypt(encrypted_command)
        clean_command = self.sanitizer.sanitize(raw_command)
        action, parsed_data = self.parser.parse(clean_command)

        return {
            "status": "SUCCESS",
            "user": user_id,
            "action": action,
            "data": parsed_data,
            "raw_sanitized_command": clean_command
        }