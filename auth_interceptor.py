import sqlite3
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from cryptography.fernet import Fernet, InvalidToken

from user_manager import UserManager, UserEncryption, UserStatus, UserNotFoundError

class AuthenticationError(Exception):
    """Excepción lanzada cuando falla la autenticación o el desencriptado."""
    pass

class InvalidTokenError(Exception):
    """Excepción lanzada cuando la estructura del JSON o token es inválida."""
    pass

class ExpiredTokenError(Exception):
    """Excepción lanzada cuando la estampa de tiempo excede la tolerancia."""
    pass

class AuthInterceptor:
    """Interceptor para deserializar JSON, autenticar identidad y extraer acción/datos."""

    def __init__(self, user_manager: UserManager, db_connection: sqlite3.Connection, max_clock_skew_seconds: int = 300):
        self.user_manager = user_manager
        self.conn = db_connection
        self.max_clock_skew = timedelta(seconds=max_clock_skew_seconds)

    def _get_user_secret_key(self, email: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT secret_key FROM user_keys WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            raise AuthenticationError(f"No existe clave criptográfica registrada para el correo {email}.")
        return row[0]

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        pattern = r"^(\d{4}-\d{2}-\d{2})-(\d{5})$"
        match = re.match(pattern, str(timestamp_str).strip())
        if not match:
            raise InvalidTokenError(f"Formato de timestamp inválido '{timestamp_str}'. Se esperaba YYYY-MM-DD-SSSSS.")

        date_part, seconds_part = match.groups()
        try:
            base_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            seconds = int(seconds_part)
            if seconds >= 86400:
                raise InvalidTokenError(f"Los segundos '{seconds}' exceden el máximo diario.")
            return base_date + timedelta(seconds=seconds)
        except ValueError as e:
            raise InvalidTokenError(f"Fecha inválida en timestamp: {str(e)}")

    def _validate_clock_skew(self, token_time: datetime) -> None:
        now = datetime.now(timezone.utc)
        diff = abs(now - token_time)
        if diff > self.max_clock_skew:
            raise ExpiredTokenError(
                f"El timestamp difiere {diff.total_seconds():.0f}s del servidor UTC (máximo: {self.max_clock_skew.total_seconds():.0f}s)."
            )

    def authenticate_request(self, sender_email: str, raw_payload: str) -> Dict[str, Any]:
        user = self.user_manager.get_user(sender_email)
        if user["status"] != UserStatus.ACTIVE.value:
            raise AuthenticationError(f"El usuario {sender_email} no está activo.")

        plain_text = raw_payload.strip()
        if user["encryption"] == UserEncryption.ACTIVE.value:
            secret_key = self._get_user_secret_key(sender_email)
            try:
                fernet = Fernet(secret_key.encode('utf-8'))
                plain_text = fernet.decrypt(raw_payload.encode('utf-8')).decode('utf-8')
            except InvalidToken:
                raise AuthenticationError("No se pudo desencriptar el paquete: Clave o mensaje inválidos.")

        try:
            payload = json.loads(plain_text)
        except json.JSONDecodeError:
            raise InvalidTokenError("El paquete desencriptado no contiene un JSON válido.")

        required_keys = ["email", "mac", "timestamp", "action"]
        for key in required_keys:
            if key not in payload:
                raise InvalidTokenError(f"Campo obligatorio faltante en el JSON: '{key}'.")

        token_email = payload["email"]
        if token_email.lower() != sender_email.lower():
            raise AuthenticationError(f"Discrepancia de remitente '{sender_email}' vs payload '{token_email}'.")

        token_time = self._parse_timestamp(payload["timestamp"])
        self._validate_clock_skew(token_time)

        return {
            "authenticated": True,
            "email": sender_email,
            "mac_address": payload["mac"],
            "timestamp": token_time,
            "role": user["role"],
            "encryption": user["encryption"],
            "action": payload["action"],
            "data": payload.get("data")
        }